import csv
import io
import os
from datetime import datetime, date
from calendar import monthrange
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response, jsonify, abort
)#hi
import database

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'scout_sandou2_secret_key_2026_!@#')

# Predefined authorized credentials
AUTHORIZED_EMAIL = 'sahmarany.hassan11@gmail.com'
AUTHORIZED_PASSWORD = '1234'

# Initialize database on module load
database.init_db()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please sign in to access Scout Money Management.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_language():
    language = session.get('language', 'en')
    return {'language': language if language in ('en', 'ar') else 'en'}


@app.template_filter('format_currency')
def format_currency_filter(amount, currency='USD'):
    try:
        val = float(amount or 0)
    except (ValueError, TypeError):
        val = 0.0

    if currency.upper() == 'USD':
        return f"${val:,.2f}"
    elif currency.upper() == 'LBP':
        # LBP is commonly represented without decimals
        return f"{int(round(val)):,} ل.ل"
    return f"{val:,.2f} {currency}"


@app.template_filter('format_num')
def format_num_filter(amount):
    try:
        val = float(amount or 0)
    except (ValueError, TypeError):
        val = 0.0
    if val.is_integer():
        return f"{int(val):,}"
    return f"{val:,.2f}"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if email == AUTHORIZED_EMAIL.lower() and password == AUTHORIZED_PASSWORD:
            session['user'] = AUTHORIZED_EMAIL
            flash('أهلاً وسهلاً بك في صندوق فوج الدورة', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Access is restricted to authorized account only.', 'danger')

    if 'user' in session:
        return redirect(url_for('dashboard'))

    return render_template('login.html', authorized_email=AUTHORIZED_EMAIL)


@app.route('/language/<language>')
def set_language(language):
    if language not in ('en', 'ar'):
        abort(404)

    session['language'] = language
    next_url = request.args.get('next', '')
    if next_url.startswith('/') and not next_url.startswith('//'):
        return redirect(next_url)
    return redirect(url_for('dashboard' if 'user' in session else 'login'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    today = date.today()

    # Preset filters or custom dates
    preset = request.args.get('preset', 'all').lower()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    currency = request.args.get('currency', '').strip().upper()
    trans_type = request.args.get('type', '').strip().lower()
    search = request.args.get('search', '').strip()

    # Handle presets
    if preset == 'this_month':
        start_date = date(today.year, today.month, 1).strftime('%Y-%m-%d')
        _, last_day = monthrange(today.year, today.month)
        end_date = date(today.year, today.month, last_day).strftime('%Y-%m-%d')
    elif preset == 'today':
        start_date = today.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    elif preset == 'this_year':
        start_date = date(today.year, 1, 1).strftime('%Y-%m-%d')
        end_date = date(today.year, 12, 31).strftime('%Y-%m-%d')
    elif preset == 'custom':
        # Keep start_date and end_date as provided
        pass
    elif preset == 'all':
        start_date = ''
        end_date = ''

    # Overall Total Wallet Balance (all time)
    wallet = database.get_wallet_balance()

    # Period Statistics (filtered by date range)
    period_stats = database.get_summary_stats(
        start_date=start_date or None,
        end_date=end_date or None
    )

    # All filtered transactions
    transactions = database.get_transactions(
        start_date=start_date or None,
        end_date=end_date or None,
        currency=currency if currency in ('USD', 'LBP') else None,
        type_=trans_type if trans_type in ('income', 'expense') else None,
        search=search or None
    )

    # Split for quick inspection: Incomes ("From Who") vs Expenses ("For What")
    incomes = [t for t in transactions if t['type'] == 'income']
    expenses = [t for t in transactions if t['type'] == 'expense']

    # Current month labels
    current_month_name = today.strftime('%B %Y')

    return render_template(
        'dashboard.html',
        wallet=wallet,
        period_stats=period_stats,
        transactions=transactions,
        incomes=incomes,
        expenses=expenses,
        preset=preset,
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        trans_type=trans_type,
        search=search,
        today_date=today.strftime('%Y-%m-%d'),
        current_month_name=current_month_name,
        user=session.get('user')
    )


@app.route('/transaction/add', methods=['POST'])
@login_required
def add_transaction():
    trans_type = request.form.get('type', 'income').strip().lower()
    amount_str = request.form.get('amount', '0').strip()
    currency = request.form.get('currency', 'USD').strip().upper()
    party_or_purpose = request.form.get('party_or_purpose', '').strip()
    category = request.form.get('category', 'General').strip()
    notes = request.form.get('notes', '').strip()
    t_date = request.form.get('date', '').strip() or date.today().strftime('%Y-%m-%d')

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
    except ValueError:
        flash('Invalid amount entered.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    if not party_or_purpose:
        field_name = 'From Who' if trans_type == 'income' else 'For What'
        flash(f'Please provide "{field_name}".', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    if currency not in ('USD', 'LBP'):
        currency = 'USD'

    if trans_type not in ('income', 'expense'):
        trans_type = 'income'

    database.add_transaction(
        type_=trans_type,
        amount=amount,
        currency=currency,
        party_or_purpose=party_or_purpose,
        category=category or 'General',
        notes=notes,
        date=t_date
    )

    t_label = 'Income (وارد)' if trans_type == 'income' else 'Expense (مصروف)'
    flash(f'{t_label} of {format_currency_filter(amount, currency)} added successfully!', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/transaction/edit/<int:trans_id>', methods=['POST'])
@login_required
def edit_transaction(trans_id):
    existing = database.get_transaction(trans_id)
    if not existing:
        flash('Transaction not found.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    trans_type = request.form.get('type', existing['type']).strip().lower()
    amount_str = request.form.get('amount', str(existing['amount'])).strip()
    currency = request.form.get('currency', existing['currency']).strip().upper()
    party_or_purpose = request.form.get('party_or_purpose', existing['party_or_purpose']).strip()
    category = request.form.get('category', existing['category']).strip()
    notes = request.form.get('notes', '').strip()
    t_date = request.form.get('date', existing['date']).strip()

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
    except ValueError:
        flash('Invalid amount entered.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    if not party_or_purpose:
        field_name = 'From Who' if trans_type == 'income' else 'For What'
        flash(f'Please provide "{field_name}".', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    database.update_transaction(
        id_=trans_id,
        type_=trans_type,
        amount=amount,
        currency=currency if currency in ('USD', 'LBP') else 'USD',
        party_or_purpose=party_or_purpose,
        category=category or 'General',
        notes=notes,
        date=t_date
    )

    flash('Transaction updated successfully!', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/transaction/delete/<int:trans_id>', methods=['POST'])
@login_required
def delete_transaction(trans_id):
    existing = database.get_transaction(trans_id)
    if not existing:
        flash('Transaction not found.', 'danger')
    else:
        database.delete_transaction(trans_id)
        flash('Transaction deleted successfully.', 'info')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/export')
@login_required
def export_csv():
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    currency = request.args.get('currency', '').strip().upper()
    trans_type = request.args.get('type', '').strip().lower()
    search = request.args.get('search', '').strip()

    transactions = database.get_transactions(
        start_date=start_date or None,
        end_date=end_date or None,
        currency=currency if currency in ('USD', 'LBP') else None,
        type_=trans_type if trans_type in ('income', 'expense') else None,
        search=search or None
    )

    si = io.StringIO()
    cw = csv.writer(si)
    is_arabic = session.get('language') == 'ar'
    if is_arabic:
        cw.writerow(['المعرف', 'التاريخ', 'النوع', 'المبلغ', 'العملة', 'المصدر / الغرض', 'الفئة', 'ملاحظات'])
    else:
        cw.writerow(['ID', 'Date', 'Type', 'Amount', 'Currency', 'From Who / For What', 'Category', 'Notes'])

    for t in transactions:
        if is_arabic:
            type_label = 'إيراد' if t['type'] == 'income' else 'مصروف'
        else:
            type_label = 'Income' if t['type'] == 'income' else 'Expense'
        cw.writerow([
            t['id'],
            t['date'],
            type_label,
            t['amount'],
            t['currency'],
            t['party_or_purpose'],
            t['category'],
            t['notes'] or ''
        ])

    output = si.getvalue()
    si.close()

    filename = f"scout_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
