import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scout_finance.db')

# When set (e.g. on Render), PostgreSQL is used instead of the local SQLite file.
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection(db_path=None):
    if DATABASE_URL and not db_path:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def _is_postgres(conn):
    return not isinstance(conn, sqlite3.Connection)

def _execute(conn, cursor, query, params=()):
    """Run a query written with SQLite '?' placeholders on either backend."""
    if _is_postgres(conn):
        query = query.replace('?', '%s')
    cursor.execute(query, params)

def init_db(db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    pg = _is_postgres(conn)
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS transactions (
            id {'SERIAL PRIMARY KEY' if pg else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            amount {'DOUBLE PRECISION' if pg else 'REAL'} NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('USD', 'LBP')),
            party_or_purpose TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            notes TEXT DEFAULT '',
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            owner TEXT
        )
    ''')
    # Each user has a separate treasury: transactions belong to the email that created them.
    # Databases created before accounts existed get the column added here.
    if pg:
        cursor.execute('ALTER TABLE transactions ADD COLUMN IF NOT EXISTS owner TEXT')
    else:
        cursor.execute('PRAGMA table_info(transactions)')
        if 'owner' not in [row[1] for row in cursor.fetchall()]:
            cursor.execute('ALTER TABLE transactions ADD COLUMN owner TEXT')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_currency ON transactions(currency)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_owner ON transactions(owner)')
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {'SERIAL PRIMARY KEY' if pg else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'user')),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'declined')),
            language TEXT NOT NULL DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            decided_at TIMESTAMP
        )
    ''')
    # Phones (Android app installs) that receive push notifications for an email address
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'en',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_email ON devices(email)')
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS volunteer_applications (
            id {'SERIAL PRIMARY KEY' if pg else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            full_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'accepted', 'declined')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            decided_at TIMESTAMP
        )
    ''')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_volunteer_applications_status '
        'ON volunteer_applications(status, created_at)'
    )
    conn.commit()
    conn.close()

def _owner_key(owner):
    if not owner:
        raise ValueError('A transaction owner (user email) is required')
    return owner.strip().lower()

def claim_unowned_transactions(owner, db_path=None):
    """Gives transactions from before per-user treasuries existed to `owner`. Returns how many."""
    owner = _owner_key(owner)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'UPDATE transactions SET owner = ? WHERE owner IS NULL', (owner,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected

def add_transaction(type_, amount, currency, party_or_purpose, category='General', notes='', date=None, db_path=None, *, owner):
    owner = _owner_key(owner)
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = '''
        INSERT INTO transactions (type, amount, currency, party_or_purpose, category, notes, date, owner)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    if _is_postgres(conn):
        query += ' RETURNING id'
    _execute(conn, cursor, query, (type_, float(amount), currency.upper(), party_or_purpose.strip(), category.strip() or 'General', (notes or '').strip(), date, owner))
    new_id = cursor.fetchone()['id'] if _is_postgres(conn) else cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_transaction(id_, type_, amount, currency, party_or_purpose, category='General', notes='', date=None, db_path=None, *, owner):
    owner = _owner_key(owner)
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, '''
        UPDATE transactions
        SET type = ?, amount = ?, currency = ?, party_or_purpose = ?, category = ?, notes = ?, date = ?
        WHERE id = ? AND owner = ?
    ''', (type_, float(amount), currency.upper(), party_or_purpose.strip(), category.strip() or 'General', (notes or '').strip(), date, id_, owner))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def delete_transaction(id_, db_path=None, *, owner):
    owner = _owner_key(owner)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'DELETE FROM transactions WHERE id = ? AND owner = ?', (id_, owner))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_transaction(id_, db_path=None, *, owner):
    owner = _owner_key(owner)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'SELECT * FROM transactions WHERE id = ? AND owner = ?', (id_, owner))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_transactions(start_date=None, end_date=None, currency=None, type_=None, search=None, db_path=None, *, owner):
    owner = _owner_key(owner)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = 'SELECT * FROM transactions WHERE owner = ?'
    params = [owner]

    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    if currency and currency.upper() in ('USD', 'LBP'):
        query += ' AND currency = ?'
        params.append(currency.upper())
    if type_ and type_.lower() in ('income', 'expense'):
        query += ' AND type = ?'
        params.append(type_.lower())
    if search:
        # SQLite LIKE is case-insensitive; ILIKE keeps that behaviour on PostgreSQL
        like = 'ILIKE' if _is_postgres(conn) else 'LIKE'
        query += f' AND (party_or_purpose {like} ? OR notes {like} ? OR category {like} ?)'
        wildcard = f'%{search.strip()}%'
        params.extend([wildcard, wildcard, wildcard])

    query += ' ORDER BY date DESC, id DESC'
    _execute(conn, cursor, query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_wallet_balance(db_path=None, *, owner):
    """
    Returns the owner's total all-time wallet balance for USD and LBP.
    """
    owner = _owner_key(owner)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, '''
        SELECT
            currency,
            type,
            COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE owner = ?
        GROUP BY currency, type
    ''', (owner,))
    rows = cursor.fetchall()
    conn.close()

    summary = {
        'usd_income': 0.0,
        'usd_expense': 0.0,
        'usd_balance': 0.0,
        'lbp_income': 0.0,
        'lbp_expense': 0.0,
        'lbp_balance': 0.0
    }

    for row in rows:
        curr = row['currency']
        t_type = row['type']
        tot = float(row['total'])
        if curr == 'USD':
            if t_type == 'income':
                summary['usd_income'] = tot
            elif t_type == 'expense':
                summary['usd_expense'] = tot
        elif curr == 'LBP':
            if t_type == 'income':
                summary['lbp_income'] = tot
            elif t_type == 'expense':
                summary['lbp_expense'] = tot

    summary['usd_balance'] = summary['usd_income'] - summary['usd_expense']
    summary['lbp_balance'] = summary['lbp_income'] - summary['lbp_expense']
    return summary

def get_summary_stats(start_date=None, end_date=None, db_path=None, *, owner):
    """
    Returns the owner's statistics within a specific date range (income sum, expense sum, counts, net for USD and LBP).
    """
    owner = _owner_key(owner)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = '''
        SELECT
            currency,
            type,
            COUNT(*) as count,
            COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE owner = ?
    '''
    params = [owner]
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    query += ' GROUP BY currency, type'

    _execute(conn, cursor, query, params)
    rows = cursor.fetchall()
    conn.close()

    stats = {
        'usd_income': 0.0,
        'usd_expense': 0.0,
        'usd_net': 0.0,
        'usd_income_count': 0,
        'usd_expense_count': 0,
        'lbp_income': 0.0,
        'lbp_expense': 0.0,
        'lbp_net': 0.0,
        'lbp_income_count': 0,
        'lbp_expense_count': 0,
        'total_income_count': 0,
        'total_expense_count': 0,
        'total_count': 0
    }

    for row in rows:
        curr = row['currency']
        t_type = row['type']
        tot = float(row['total'])
        cnt = int(row['count'])

        if curr == 'USD':
            if t_type == 'income':
                stats['usd_income'] = tot
                stats['usd_income_count'] = cnt
            elif t_type == 'expense':
                stats['usd_expense'] = tot
                stats['usd_expense_count'] = cnt
        elif curr == 'LBP':
            if t_type == 'income':
                stats['lbp_income'] = tot
                stats['lbp_income_count'] = cnt
            elif t_type == 'expense':
                stats['lbp_expense'] = tot
                stats['lbp_expense_count'] = cnt

    stats['usd_net'] = stats['usd_income'] - stats['usd_expense']
    stats['lbp_net'] = stats['lbp_income'] - stats['lbp_expense']
    stats['total_income_count'] = stats['usd_income_count'] + stats['lbp_income_count']
    stats['total_expense_count'] = stats['usd_expense_count'] + stats['lbp_expense_count']
    stats['total_count'] = stats['total_income_count'] + stats['total_expense_count']
    return stats

# ---------------------------------------------------------------------------
# Users (sign-up requests and approved accounts)
# ---------------------------------------------------------------------------

def get_user_by_email(email, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'SELECT * FROM users WHERE email = ?', ((email or '').strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user(id_, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'SELECT * FROM users WHERE id = ?', (id_,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(name, email, password_hash, status='pending', role='user', language='en', db_path=None):
    """Creates a user (or sign-up request). Returns the new id."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = '''
        INSERT INTO users (name, email, password_hash, role, status, language, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    if _is_postgres(conn):
        query += ' RETURNING id'
    decided_at = None if status == 'pending' else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _execute(conn, cursor, query, (name.strip(), email.strip().lower(), password_hash, role, status, language, decided_at))
    new_id = cursor.fetchone()['id'] if _is_postgres(conn) else cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def reopen_request(id_, name, password_hash, language='en', db_path=None):
    """Turns a declined sign-up back into a pending request with new details."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, '''
        UPDATE users
        SET name = ?, password_hash = ?, language = ?, status = 'pending', decided_at = NULL, created_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'declined'
    ''', (name.strip(), password_hash, language, id_))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def set_user_status(id_, status, db_path=None):
    """Approves or declines a pending request. Returns False if it was not pending."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, '''
        UPDATE users SET status = ?, decided_at = ?
        WHERE id = ? AND status = 'pending'
    ''', (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), id_))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_users(status=None, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = 'SELECT * FROM users'
    params = []
    if status:
        query += ' WHERE status = ?'
        params.append(status)
    query += ' ORDER BY created_at DESC, id DESC'
    _execute(conn, cursor, query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def count_pending_users(db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, "SELECT COUNT(*) AS n FROM users WHERE status = 'pending'")
    row = cursor.fetchone()
    conn.close()
    return int(row['n'])


def create_volunteer_application(full_name, contact, date_of_birth, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = '''
        INSERT INTO volunteer_applications (full_name, contact, date_of_birth)
        VALUES (?, ?, ?)
    '''
    if _is_postgres(conn):
        query += ' RETURNING id'
    _execute(conn, cursor, query, (full_name.strip(), contact.strip(), date_of_birth))
    application_id = cursor.fetchone()['id'] if _is_postgres(conn) else cursor.lastrowid
    conn.commit()
    conn.close()
    return application_id


def get_volunteer_applications(status=None, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = 'SELECT * FROM volunteer_applications'
    params = []
    if status:
        query += ' WHERE status = ?'
        params.append(status)
    query += ' ORDER BY created_at DESC, id DESC'
    _execute(conn, cursor, query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def has_pending_volunteer_application(contact, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, '''
        SELECT 1 FROM volunteer_applications
        WHERE lower(contact) = lower(?) AND status = 'pending'
        LIMIT 1
    ''', (contact.strip(),))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def decide_volunteer_application(application_id, status, db_path=None):
    if status not in ('accepted', 'declined'):
        raise ValueError('Volunteer application status must be accepted or declined')
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, '''
        UPDATE volunteer_applications
        SET status = ?, decided_at = ?
        WHERE id = ? AND status = 'pending'
    ''', (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), application_id))
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed

def update_user(id_, name, email, password_hash=None, db_path=None):
    """
    Changes a user's name, email and (optionally) password. When the email changes,
    their transactions and linked phones move with it. Returns False if the user is gone.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'SELECT email FROM users WHERE id = ?', (id_,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    old_email, new_email = row['email'], email.strip().lower()

    if password_hash:
        _execute(conn, cursor, 'UPDATE users SET name = ?, email = ?, password_hash = ? WHERE id = ?',
                 (name.strip(), new_email, password_hash, id_))
    else:
        _execute(conn, cursor, 'UPDATE users SET name = ?, email = ? WHERE id = ?', (name.strip(), new_email, id_))
    if new_email != old_email:
        _execute(conn, cursor, 'UPDATE transactions SET owner = ? WHERE owner = ?', (new_email, old_email))
        _execute(conn, cursor, 'UPDATE devices SET email = ? WHERE email = ?', (new_email, old_email))
    conn.commit()
    conn.close()
    return True

def delete_user_and_data(id_, db_path=None):
    """
    Permanently removes a user together with all their transactions and linked phones.
    Returns the number of transactions deleted, or None if the user did not exist.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'SELECT email FROM users WHERE id = ?', (id_,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    email = row['email']
    _execute(conn, cursor, 'DELETE FROM transactions WHERE owner = ?', (email,))
    deleted_transactions = cursor.rowcount
    _execute(conn, cursor, 'DELETE FROM devices WHERE email = ?', (email,))
    _execute(conn, cursor, 'DELETE FROM users WHERE id = ?', (id_,))
    conn.commit()
    conn.close()
    return deleted_transactions

def count_transactions(owner, db_path=None):
    owner = _owner_key(owner)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'SELECT COUNT(*) AS n FROM transactions WHERE owner = ?', (owner,))
    row = cursor.fetchone()
    conn.close()
    return int(row['n'])

# ---------------------------------------------------------------------------
# Devices (push notification tokens from the Android app)
# ---------------------------------------------------------------------------

def register_device(token, email, language='en', db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, '''
        INSERT INTO devices (token, email, language, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (token) DO UPDATE
        SET email = excluded.email, language = excluded.language, updated_at = CURRENT_TIMESTAMP
    ''', (token, email.strip().lower(), language))
    conn.commit()
    conn.close()

def get_devices(email, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    _execute(conn, cursor, 'SELECT * FROM devices WHERE email = ?', ((email or '').strip().lower(),))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_device(token, email=None, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    if email is None:
        _execute(conn, cursor, 'DELETE FROM devices WHERE token = ?', (token,))
    else:
        _execute(conn, cursor, 'DELETE FROM devices WHERE token = ? AND email = ?', (token, email.strip().lower()))
    conn.commit()
    conn.close()
