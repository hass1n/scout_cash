import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scout_finance.db')

def get_db_connection(db_path=None):
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    path = db_path or DEFAULT_DB_PATH
    conn = get_db_connection(path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            amount REAL NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('USD', 'LBP')),
            party_or_purpose TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            notes TEXT DEFAULT '',
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_currency ON transactions(currency)')
    conn.commit()
    conn.close()

def add_transaction(type_, amount, currency, party_or_purpose, category='General', notes='', date=None, db_path=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (type, amount, currency, party_or_purpose, category, notes, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (type_, float(amount), currency.upper(), party_or_purpose.strip(), category.strip() or 'General', (notes or '').strip(), date))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_transaction(id_, type_, amount, currency, party_or_purpose, category='General', notes='', date=None, db_path=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transactions
        SET type = ?, amount = ?, currency = ?, party_or_purpose = ?, category = ?, notes = ?, date = ?
        WHERE id = ?
    ''', (type_, float(amount), currency.upper(), party_or_purpose.strip(), category.strip() or 'General', (notes or '').strip(), date, id_))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def delete_transaction(id_, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (id_,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_transaction(id_, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE id = ?', (id_,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_transactions(start_date=None, end_date=None, currency=None, type_=None, search=None, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = 'SELECT * FROM transactions WHERE 1=1'
    params = []

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
        query += ' AND (party_or_purpose LIKE ? OR notes LIKE ? OR category LIKE ?)'
        wildcard = f'%{search.strip()}%'
        params.extend([wildcard, wildcard, wildcard])

    query += ' ORDER BY date DESC, id DESC'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_wallet_balance(db_path=None):
    """
    Returns the total all-time wallet balance for USD and LBP.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            currency,
            type,
            COALESCE(SUM(amount), 0) as total
        FROM transactions
        GROUP BY currency, type
    ''')
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

def get_summary_stats(start_date=None, end_date=None, db_path=None):
    """
    Returns statistics within a specific date range (income sum, expense sum, counts, net for USD and LBP).
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    query = '''
        SELECT 
            currency,
            type,
            COUNT(*) as count,
            COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE 1=1
    '''
    params = []
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    query += ' GROUP BY currency, type'

    cursor.execute(query, params)
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
