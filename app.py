import csv
import hmac
import io
import os
import re
import secrets
from datetime import datetime, date
from calendar import monthrange
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response, jsonify, abort, make_response
)
from werkzeug.security import generate_password_hash, check_password_hash

import database
import push

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'scout_sandou2_secret_key_2026_!@#')

# Admin credentials (override with environment variables in production).
# The admin can do everything a user can, plus approve sign-ups and create users.
AUTHORIZED_EMAIL = os.environ.get('ADMIN_EMAIL', 'sahmarany.hassan11@gmail.com')
AUTHORIZED_PASSWORD = os.environ.get('ADMIN_PASSWORD', '1234')

MIN_PASSWORD_LENGTH = 6

# Initialize database on module load. Transactions recorded before each user had
# a separate treasury belong to the admin, who entered them.
database.init_db()
database.claim_unowned_transactions(AUTHORIZED_EMAIL)


def is_admin():
    return session.get('user', '').lower() == AUTHORIZED_EMAIL.lower()


def current_owner():
    """The signed-in user's email: every transaction query is limited to it."""
    return session['user'].lower()


def current_language():
    language = session.get('language', 'en')
    return language if language in ('en', 'ar') else 'en'


def get_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please sign in to access Scout Treasury.', 'warning')
            if request.endpoint == 'secretary':
                return redirect(url_for('login', next=request.path))
            return redirect(url_for('login'))
        if not is_admin():
            # The admin may have removed this account or changed its email since sign-in
            user = database.get_user_by_email(session['user'])
            if not user or user['status'] != 'approved':
                session.pop('user', None)
                flash('Your account is no longer active. Please contact the admin.', 'warning')
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_language():
    return {'language': current_language()}


@app.context_processor
def inject_user_role():
    admin = 'user' in session and is_admin()
    return {
        'is_admin': admin,
        'pending_requests_count': database.count_pending_users() if admin else 0,
    }


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
    login_next = request.values.get('next', '')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if email == AUTHORIZED_EMAIL.lower() and password == AUTHORIZED_PASSWORD:
            session['user'] = AUTHORIZED_EMAIL
            flash('أهلاً وسهلاً بك في صندوق فوج الدورة', 'success')
            if login_next == url_for('secretary'):
                return redirect(url_for('secretary'))
            return redirect(url_for('dashboard'))

        user = database.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            if user['status'] == 'approved':
                session['user'] = user['email']
                flash('أهلاً وسهلاً بك في صندوق فوج الدورة', 'success')
                return redirect(url_for('dashboard'))
            if user['status'] == 'pending':
                flash('Your sign-up request is still waiting for admin approval.', 'warning')
            else:
                flash('Your sign-up request was declined by the admin.', 'danger')
        else:
            flash('Invalid email or password.', 'danger')

    if 'user' in session:
        return redirect(url_for('dashboard'))

    return render_template(
        'login.html',
        authorized_email=AUTHORIZED_EMAIL,
        login_next=login_next if login_next == url_for('secretary') else '',
    )


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard'))

    form = {'name': '', 'email': ''}
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        push_token = request.form.get('push_token', '').strip()
        form = {'name': name, 'email': email}

        error = validate_new_account(name, email, password, confirm)
        existing = database.get_user_by_email(email) if not error else None
        if not error and existing and existing['status'] != 'declined':
            error = 'An account or request with this email already exists.'

        if error:
            flash(error, 'danger')
            return render_template('signup.html', form=form)

        password_hash = generate_password_hash(password)
        if existing:
            database.reopen_request(existing['id'], name, password_hash, current_language())
        else:
            database.create_user(name, email, password_hash, status='pending', language=current_language())

        if push_token:
            database.register_device(push_token, email, current_language())
        push.notify_email(AUTHORIZED_EMAIL, {
            'en': ('New sign-up request', f'{name} ({email}) wants to join Scout Treasury.'),
            'ar': ('طلب تسجيل جديد', f'{name} ({email}) يريد الانضمام إلى صندوق الكشاف.'),
        })

        flash('Your request was sent. You will be notified when the admin approves or declines it.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html', form=form)


def validate_volunteer_application(full_name, contact, date_of_birth):
    if not full_name or len(full_name) > 120:
        return 'Please enter your full name (up to 120 characters).'
    if not contact or len(contact) > 254:
        return 'Please enter an email address or phone number.'
    if '@' in contact:
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', contact):
            return 'Please enter a valid email address or phone number.'
    else:
        if not re.fullmatch(r'\+?[0-9][0-9\s().-]{5,24}', contact):
            return 'Please enter a valid email address or phone number.'
        if sum(character.isdigit() for character in contact) < 7:
            return 'Please enter a valid email address or phone number.'
    try:
        birth_date = date.fromisoformat(date_of_birth)
    except ValueError:
        return 'Please enter a valid date of birth.'
    if birth_date > date.today():
        return 'Date of birth cannot be in the future.'
    return None


@app.route('/volunteer/register', methods=['GET', 'POST'])
def volunteer_register():
    form = {'full_name': '', 'contact': '', 'date_of_birth': ''}
    if request.method == 'POST':
        csrf_token = session.get('csrf_token')
        if (
            not csrf_token
            or not hmac.compare_digest(
                request.form.get('csrf_token', '').encode('utf-8'),
                csrf_token.encode('utf-8'),
            )
        ):
            abort(400)
        form = {
            'full_name': request.form.get('full_name', '').strip(),
            'contact': request.form.get('contact', '').strip(),
            'date_of_birth': request.form.get('date_of_birth', '').strip(),
        }
        error = validate_volunteer_application(**form)
        if not error:
            form['contact'] = (
                form['contact'].lower() if '@' in form['contact'] else form['contact']
            )
            if database.has_pending_volunteer_application(form['contact']):
                error = 'An application with this contact is already awaiting review.'

        if error:
            flash(error, 'danger')
        else:
            database.create_volunteer_application(**form)
            flash('Thank you. Your volunteer application has been sent for review.', 'success')
            return redirect(url_for('volunteer_register'))

    response = make_response(render_template(
        'volunteer_register.html',
        form=form,
        today=date.today().isoformat(),
        csrf_token=get_csrf_token(),
    ))
    response.headers['Cache-Control'] = 'no-store'
    return response


def validate_new_account(name, email, password, confirm=None, password_required=True):
    """Returns an error message, or None if the details are valid."""
    if not name or not email or (password_required and not password):
        return 'Please fill in all fields.'
    if '@' not in email or '.' not in email.split('@')[-1]:
        return 'Please enter a valid email address.'
    if email == AUTHORIZED_EMAIL.lower():
        return 'An account or request with this email already exists.'
    if password and len(password) < MIN_PASSWORD_LENGTH:
        return f'Password must be at least {MIN_PASSWORD_LENGTH} characters.'
    if confirm is not None and password != confirm:
        return 'Passwords do not match.'
    return None


@app.route('/device/register', methods=['POST'])
@login_required
def register_device():
    """Links the Android app's push token to the signed-in account."""
    token = request.form.get('token', '').strip()
    if not token or len(token) > 4096:
        abort(400)
    database.register_device(token, session['user'], current_language())
    return '', 204


def render_users_page(form=None):
    all_users = database.get_users()
    others = [u for u in all_users if u['status'] != 'pending']
    for u in others:
        # Shown in the "Remove user" confirmation
        u['transaction_count'] = database.count_transactions(u['email'])
    return render_template(
        'users.html',
        pending=[u for u in all_users if u['status'] == 'pending'],
        others=others,
        form=form or {'name': '', 'email': ''},
        push_configured=push.is_configured(),
    )


@app.route('/users')
@admin_required
def users():
    return render_users_page()


@app.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    error = validate_new_account(name, email, password)
    if not error and database.get_user_by_email(email):
        error = 'An account or request with this email already exists.'
    if error:
        flash(error, 'danger')
        return render_users_page({'name': name, 'email': email})

    database.create_user(name, email, generate_password_hash(password), status='approved')
    flash(f'User {email} was created. They can sign in now.', 'success')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/update', methods=['POST'])
@admin_required
def update_user(user_id):
    user = database.get_user(user_id)
    if not user:
        abort(404)
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')  # blank keeps the current password

    error = validate_new_account(name, email, password, password_required=False)
    if not error and email != user['email'] and database.get_user_by_email(email):
        error = 'An account or request with this email already exists.'
    if error:
        flash(error, 'danger')
        return redirect(url_for('users'))

    database.update_user(user_id, name, email, generate_password_hash(password) if password else None)
    flash(f'User {email} was updated.', 'success')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/remove', methods=['POST'])
@admin_required
def remove_user(user_id):
    user = database.get_user(user_id)
    if not user:
        abort(404)
    database.delete_user_and_data(user_id)
    flash(f'User {user["email"]} and all their data were removed.', 'info')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/<decision>', methods=['POST'])
@admin_required
def decide_user(user_id, decision):
    if decision not in ('approve', 'decline'):
        abort(404)
    user = database.get_user(user_id)
    if not user:
        abort(404)

    status = 'approved' if decision == 'approve' else 'declined'
    if not database.set_user_status(user_id, status):
        flash('This request was already handled.', 'info')
        return redirect(url_for('users'))

    if status == 'approved':
        push.notify_email(user['email'], {
            'en': ('Request approved ✅', 'Your Scout Treasury account was approved. You can sign in now.'),
            'ar': ('تمت الموافقة ✅', 'تمت الموافقة على حسابك في صندوق الكشاف. يمكنك تسجيل الدخول الآن.'),
        })
        flash(f'{user["email"]} was approved.', 'success')
    else:
        push.notify_email(user['email'], {
            'en': ('Request declined', 'Your Scout Treasury sign-up request was declined.'),
            'ar': ('تم رفض الطلب', 'تم رفض طلب تسجيلك في صندوق الكشاف.'),
        })
        flash(f'{user["email"]} was declined.', 'info')
    return redirect(url_for('users'))


@app.route('/language/<language>')
def set_language(language):
    if language not in ('en', 'ar'):
        abort(404)

    session['language'] = language
    next_url = request.args.get('next', '')
    if next_url.startswith('/') and not next_url.startswith('//'):
        return redirect(next_url)
    return redirect(url_for('dashboard' if 'user' in session else 'home'))


@app.route('/logout')
def logout():
    # Stop sending this phone notifications meant for the account that signed out
    token = request.args.get('token', '').strip()
    if token and 'user' in session:
        database.delete_device(token, session['user'])
    session.pop('user', None)
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('login'))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/secretary')
@admin_required
def secretary():
    applications = database.get_volunteer_applications()
    response = make_response(render_template(
        'secretary.html',
        volunteer_applications=applications,
        pending_volunteer_count=sum(
            application['status'] == 'pending' for application in applications
        ),
        csrf_token=get_csrf_token(),
    ))
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/volunteers/<int:application_id>/<decision>', methods=['POST'])
@admin_required
def decide_volunteer(application_id, decision):
    csrf_token = session.get('csrf_token')
    if (
        not csrf_token
        or not hmac.compare_digest(
            request.form.get('csrf_token', '').encode('utf-8'),
            csrf_token.encode('utf-8'),
        )
    ):
        abort(400)
    if decision not in ('accept', 'decline'):
        abort(404)
    status = 'accepted' if decision == 'accept' else 'declined'
    if not database.decide_volunteer_application(application_id, status):
        flash('This volunteer application was already reviewed.', 'info')
    else:
        flash(
            'Volunteer application accepted.' if status == 'accepted'
            else 'Volunteer application declined.',
            'success' if status == 'accepted' else 'info',
        )
    return redirect(url_for('secretary'))


@app.route('/treasury')
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
    wallet = database.get_wallet_balance(owner=current_owner())

    # Period Statistics (filtered by date range)
    period_stats = database.get_summary_stats(
        start_date=start_date or None,
        end_date=end_date or None,
        owner=current_owner()
    )

    # All filtered transactions
    transactions = database.get_transactions(
        start_date=start_date or None,
        end_date=end_date or None,
        currency=currency if currency in ('USD', 'LBP') else None,
        type_=trans_type if trans_type in ('income', 'expense') else None,
        search=search or None,
        owner=current_owner()
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

    transaction_id = database.add_transaction(
        type_=trans_type,
        amount=amount,
        currency=currency,
        party_or_purpose=party_or_purpose,
        category=category or 'General',
        notes=notes,
        date=t_date,
        owner=current_owner()
    )

    t_label = 'Income (وارد)' if trans_type == 'income' else 'Expense (مصروف)'
    flash(
        f'Transaction #{transaction_id}: {t_label} of '
        f'{format_currency_filter(amount, currency)} added successfully!',
        'success'
    )
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/transaction/edit/<int:trans_id>', methods=['POST'])
@login_required
def edit_transaction(trans_id):
    existing = database.get_transaction(trans_id, owner=current_owner())
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
        date=t_date,
        owner=current_owner()
    )

    flash('Transaction updated successfully!', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/transaction/delete/<int:trans_id>', methods=['POST'])
@login_required
def delete_transaction(trans_id):
    existing = database.get_transaction(trans_id, owner=current_owner())
    if not existing:
        flash('Transaction not found.', 'danger')
    else:
        database.delete_transaction(trans_id, owner=current_owner())
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
        search=search or None,
        owner=current_owner()
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
