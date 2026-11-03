import unittest
import os
import tempfile
from datetime import date

from werkzeug.security import generate_password_hash

import database
import push
from app import app, AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD

OWNER = 'treasurer@example.com'

class ScoutFinanceTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for testing
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        database.init_db(self.db_path)

        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        self.client = app.test_client()

        # Monkey-patch default db path for the app session
        self.orig_db_path = database.DEFAULT_DB_PATH
        database.DEFAULT_DB_PATH = self.db_path

    def tearDown(self):
        database.DEFAULT_DB_PATH = self.orig_db_path
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_database_crud_and_balances(self):
        # 1. Add USD Income
        inc_id = database.add_transaction(
            type_='income',
            amount=500.0,
            currency='USD',
            party_or_purpose='Donor Mr. Smith',
            category='Donation',
            notes='For camping equipment',
            date='2026-10-01',
            db_path=self.db_path,
            owner=OWNER
        )
        self.assertIsNotNone(inc_id)

        # 2. Add LBP Income
        database.add_transaction(
            type_='income',
            amount=15000000.0,
            currency='LBP',
            party_or_purpose='Troop Membership Dues',
            category='Monthly Dues',
            date='2026-10-05',
            db_path=self.db_path,
            owner=OWNER
        )

        # 3. Add USD Expense
        database.add_transaction(
            type_='expense',
            amount=120.0,
            currency='USD',
            party_or_purpose='Tents & Rope Hardware',
            category='Camping Equipment',
            date='2026-10-10',
            db_path=self.db_path,
            owner=OWNER
        )

        # 4. Add LBP Expense
        database.add_transaction(
            type_='expense',
            amount=5000000.0,
            currency='LBP',
            party_or_purpose='Snacks & Water for Hike',
            category='Food & Snacks',
            date='2026-10-12',
            db_path=self.db_path,
            owner=OWNER
        )

        # Check Wallet Balance
        wallet = database.get_wallet_balance(self.db_path, owner=OWNER)
        self.assertEqual(wallet['usd_income'], 500.0)
        self.assertEqual(wallet['usd_expense'], 120.0)
        self.assertEqual(wallet['usd_balance'], 380.0)

        self.assertEqual(wallet['lbp_income'], 15000000.0)
        self.assertEqual(wallet['lbp_expense'], 5000000.0)
        self.assertEqual(wallet['lbp_balance'], 10000000.0)

        # Check Date Range Filter
        stats = database.get_summary_stats(
            start_date='2026-10-01',
            end_date='2026-10-09',
            db_path=self.db_path,
            owner=OWNER
        )
        # In this date window: USD income 500, LBP income 15,000,000, zero expenses
        self.assertEqual(stats['usd_income'], 500.0)
        self.assertEqual(stats['usd_expense'], 0.0)
        self.assertEqual(stats['lbp_income'], 15000000.0)
        self.assertEqual(stats['lbp_expense'], 0.0)
        self.assertEqual(stats['total_count'], 2)

        # Update transaction
        ok = database.update_transaction(
            id_=inc_id,
            type_='income',
            amount=600.0,
            currency='USD',
            party_or_purpose='Donor Mr. Smith & Family',
            category='Donation',
            notes='Updated donation',
            date='2026-10-01',
            db_path=self.db_path,
            owner=OWNER
        )
        self.assertTrue(ok)
        updated = database.get_transaction(inc_id, self.db_path, owner=OWNER)
        self.assertEqual(updated['amount'], 600.0)
        self.assertEqual(updated['party_or_purpose'], 'Donor Mr. Smith & Family')

        # Delete transaction
        ok = database.delete_transaction(inc_id, self.db_path, owner=OWNER)
        self.assertTrue(ok)
        self.assertIsNone(database.get_transaction(inc_id, self.db_path, owner=OWNER))

    def test_auth_and_protected_routes(self):
        # Accessing dashboard without login redirects to /login
        res = self.client.get('/', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # Attempt invalid login
        res = self.client.post('/login', data={
            'email': 'wrong@scout.com',
            'password': 'bad'
        }, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res.data)

        # Attempt valid login with authorized credentials
        res = self.client.post('/login', data={
            'email': AUTHORIZED_EMAIL,
            'password': AUTHORIZED_PASSWORD
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('أهلاً وسهلاً بك في صندوق فوج الدورة'.encode('utf-8'), res.data)
        self.assertIn(b'Scout Treasury Overview', res.data)
        self.assertIn(b'$ Wallet', res.data)
        self.assertIn('ل.ل Wallet'.encode('utf-8'), res.data)

        # Now test adding transaction through web endpoint
        res = self.client.post('/transaction/add', data={
            'type': 'income',
            'amount': '250',
            'currency': 'USD',
            'party_or_purpose': 'Summer Camp Registration',
            'category': 'Camp Fees',
            'notes': 'Paid in cash',
            'date': '2026-10-15'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Summer Camp Registration', res.data)
        self.assertIn(b'Transaction #1', res.data)
        self.assertIn(b'>#1</td>', res.data)

        # Expense transactions also display their unique ID in the dashboard.
        res = self.client.post('/transaction/add', data={
            'type': 'expense',
            'amount': '25',
            'currency': 'USD',
            'party_or_purpose': 'Camp supplies',
            'category': 'Supplies',
            'date': '2026-10-16'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Transaction #2', res.data)
        self.assertIn(b'>#2</td>', res.data)
        self.assertIn(b'id="period-summary"', res.data)

        # Test "This Month" filter view
        res = self.client.get('/?preset=this_month')
        self.assertEqual(res.status_code, 200)

        # Test CSV export
        res = self.client.get('/export')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Summer Camp Registration', res.data)
        self.assertIn(b'From Who / For What', res.data)

        # Test Logout
        res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'You have been logged out safely', res.data)

    def test_language_switch_sets_locale_and_text_direction(self):
        response = self.client.get('/language/ar?next=%2Flogin')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/login')

        response = self.client.get('/login')
        self.assertIn(b'<html lang="ar" dir="rtl">', response.data)
        self.assertIn(b'bootstrap.rtl.min.css', response.data)
        self.assertIn(b'js/i18n.js', response.data)

        with self.client.session_transaction() as browser_session:
            browser_session['user'] = AUTHORIZED_EMAIL
        response = self.client.get('/export')
        self.assertIn('المصدر / الغرض'.encode('utf-8'), response.data)

        response = self.client.get('/language/en?next=%2F')
        self.assertEqual(response.headers['Location'], '/')

        response = self.client.get('/')
        self.assertIn(b'<html lang="en" dir="ltr">', response.data)
        self.assertIn(b'bootstrap.min.css', response.data)


class UserAccountsTestCase(unittest.TestCase):
    """Sign-up requests, admin approval, roles and push notifications."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.orig_db_path = database.DEFAULT_DB_PATH
        database.DEFAULT_DB_PATH = self.db_path
        database.init_db()

        app.config['TESTING'] = True
        self.client = app.test_client()

        # Record push notifications instead of sending them
        self.pushes = []
        self.orig_notify = push.notify_email
        push.notify_email = lambda email, messages: self.pushes.append((email, messages)) or 1

    def tearDown(self):
        push.notify_email = self.orig_notify
        database.DEFAULT_DB_PATH = self.orig_db_path
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def signup(self, email='scout@example.com', password='secret1', confirm=None, push_token=''):
        return self.client.post('/signup', data={
            'name': 'Ali Scout',
            'email': email,
            'password': password,
            'confirm_password': password if confirm is None else confirm,
            'push_token': push_token,
        }, follow_redirects=True)

    def decide(self, email, decision):
        user = database.get_user_by_email(email)
        return self.client.post(f"/users/{user['id']}/{decision}", follow_redirects=True)

    def test_signup_waits_for_approval_and_notifies_on_approve(self):
        res = self.signup(email='Scout@Example.com', push_token='phone-token-1')
        self.assertIn(b'Your request was sent', res.data)
        self.assertEqual(database.get_user_by_email('scout@example.com')['status'], 'pending')
        self.assertEqual(database.get_devices('scout@example.com')[0]['token'], 'phone-token-1')
        # The admin is told about the new request
        self.assertEqual(self.pushes[-1][0], AUTHORIZED_EMAIL)

        # Pending users cannot sign in
        res = self.login('scout@example.com', 'secret1')
        self.assertIn(b'still waiting for admin approval', res.data)
        self.assertNotIn(b'Scout Treasury Overview', res.data)

        # Admin approves -> the applicant gets a push notification
        self.login(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        res = self.client.get('/users')
        self.assertIn(b'scout@example.com', res.data)
        res = self.decide('scout@example.com', 'approve')
        self.assertIn(b'scout@example.com was approved.', res.data)
        self.assertEqual(self.pushes[-1][0], 'scout@example.com')
        self.assertIn('approved', self.pushes[-1][1]['en'][1])

        # A second decision on the same request is ignored
        res = self.decide('scout@example.com', 'decline')
        self.assertIn(b'already handled', res.data)
        self.assertEqual(database.get_user_by_email('scout@example.com')['status'], 'approved')

        # The approved user can sign in and use the dashboard, but not admin pages
        self.client.get('/logout')
        res = self.login('scout@example.com', 'secret1')
        self.assertIn(b'Scout Treasury Overview', res.data)
        self.assertNotIn(b'href="/users"', res.data)
        self.assertEqual(self.client.get('/users').status_code, 403)
        res = self.client.post('/transaction/add', data={
            'type': 'expense', 'amount': '20', 'currency': 'USD',
            'party_or_purpose': 'Rope', 'category': 'Gear', 'date': '2026-11-02'
        }, follow_redirects=True)
        self.assertIn(b'Rope', res.data)

    def test_declined_request_is_notified_and_blocks_sign_in(self):
        self.signup()
        self.login(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        self.decide('scout@example.com', 'decline')
        self.assertEqual(self.pushes[-1][0], 'scout@example.com')
        self.assertIn('declined', self.pushes[-1][1]['en'][1])

        self.client.get('/logout')
        res = self.login('scout@example.com', 'secret1')
        self.assertIn(b'was declined by the admin', res.data)

        # A declined person may send a new request
        res = self.signup(password='newpass1')
        self.assertIn(b'Your request was sent', res.data)
        self.assertEqual(database.get_user_by_email('scout@example.com')['status'], 'pending')

    def test_signup_validation(self):
        self.assertIn(b'Passwords do not match', self.signup(confirm='other12').data)
        self.assertIn(b'at least 6 characters', self.signup(password='123').data)
        self.assertIn(b'valid email', self.signup(email='not-an-email').data)
        self.assertIn(b'already exists', self.signup(email=AUTHORIZED_EMAIL).data)
        self.signup()
        self.assertIn(b'already exists', self.signup().data)
        self.assertEqual(len(database.get_users()), 1)

    def test_wrong_password_does_not_reveal_request_status(self):
        self.signup()
        res = self.login('scout@example.com', 'wrong-password')
        self.assertIn(b'Invalid email or password', res.data)
        self.assertNotIn(b'waiting for admin approval', res.data)

    def test_admin_creates_user_who_can_sign_in_immediately(self):
        self.login(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        res = self.client.post('/users/create', data={
            'name': 'Leader Rami', 'email': 'rami@example.com', 'password': 'camp2026'
        }, follow_redirects=True)
        self.assertIn(b'User rami@example.com was created', res.data)

        res = self.client.post('/users/create', data={
            'name': 'Dup', 'email': 'rami@example.com', 'password': 'camp2026'
        }, follow_redirects=True)
        self.assertIn(b'already exists', res.data)

        self.client.get('/logout')
        res = self.login('rami@example.com', 'camp2026')
        self.assertIn(b'Scout Treasury Overview', res.data)

    def test_only_admin_can_manage_users(self):
        database.create_user('U', 'user@example.com', generate_password_hash('secret1'), status='approved')
        self.login('user@example.com', 'secret1')
        self.assertEqual(self.client.get('/users').status_code, 403)
        self.assertEqual(self.client.post('/users/create', data={
            'name': 'X', 'email': 'x@example.com', 'password': 'secret1'}).status_code, 403)
        pending_id = database.create_user('P', 'p@example.com', generate_password_hash('secret1'))
        self.assertEqual(self.client.post(f'/users/{pending_id}/approve').status_code, 403)
        self.assertEqual(database.get_user(pending_id)['status'], 'pending')

        # Signed-out visitors are sent to the login page
        self.client.get('/logout')
        self.assertIn('/login', self.client.get('/users').headers['Location'])

    def test_device_registration_and_logout_unlinks_phone(self):
        self.login(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        self.assertEqual(self.client.post('/device/register', data={'token': 'admin-phone'}).status_code, 204)
        self.assertEqual(database.get_devices(AUTHORIZED_EMAIL)[0]['token'], 'admin-phone')
        self.client.get('/logout?token=admin-phone')
        self.assertEqual(database.get_devices(AUTHORIZED_EMAIL), [])
        # Registering requires being signed in
        self.assertEqual(self.client.post('/device/register', data={'token': 't'}).status_code, 302)

    def test_push_is_skipped_without_firebase_credentials(self):
        os.environ.pop('FIREBASE_CREDENTIALS', None)
        database.register_device('t1', 'scout@example.com')
        self.assertEqual(self.orig_notify('scout@example.com', {'en': ('t', 'b')}), 0)


class SeparateTreasuriesTestCase(unittest.TestCase):
    """Every user has their own dashboard: transactions, balances and exports are never shared."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.orig_db_path = database.DEFAULT_DB_PATH
        database.DEFAULT_DB_PATH = self.db_path
        database.init_db()
        for email in ('ali@example.com', 'rami@example.com'):
            database.create_user(email.split('@')[0], email, generate_password_hash('secret1'), status='approved')
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        database.DEFAULT_DB_PATH = self.orig_db_path
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def sign_in_as(self, email, password='secret1'):
        self.client.get('/logout')
        self.client.post('/login', data={'email': email, 'password': password})

    def add(self, purpose, amount, currency='USD', type_='income'):
        return self.client.post('/transaction/add', data={
            'type': type_, 'amount': str(amount), 'currency': currency,
            'party_or_purpose': purpose, 'category': 'General', 'date': '2026-11-02'
        }, follow_redirects=True)

    def test_each_user_sees_only_their_own_numbers(self):
        self.sign_in_as('ali@example.com')
        self.add('Ali dues', 300)
        self.sign_in_as('rami@example.com')
        self.add('Rami tents', 75, type_='expense')

        res = self.client.get('/')
        self.assertIn(b'Rami tents', res.data)
        self.assertNotIn(b'Ali dues', res.data)
        self.assertNotIn(b'Ali dues', self.client.get('/export').data)

        self.assertEqual(database.get_wallet_balance(owner='rami@example.com')['usd_balance'], -75.0)
        self.assertEqual(database.get_wallet_balance(owner='ali@example.com')['usd_balance'], 300.0)
        self.assertEqual(database.get_summary_stats(owner='ali@example.com')['total_count'], 1)

    def test_users_cannot_edit_or_delete_each_others_transactions(self):
        ali_id = database.add_transaction('income', 300, 'USD', 'Ali dues', owner='ali@example.com')
        self.sign_in_as('rami@example.com')

        res = self.client.post(f'/transaction/edit/{ali_id}', data={
            'type': 'income', 'amount': '1', 'currency': 'USD', 'party_or_purpose': 'hacked'
        }, follow_redirects=True)
        self.assertIn(b'Transaction not found', res.data)
        res = self.client.post(f'/transaction/delete/{ali_id}', follow_redirects=True)
        self.assertIn(b'Transaction not found', res.data)

        untouched = database.get_transaction(ali_id, owner='ali@example.com')
        self.assertEqual((untouched['amount'], untouched['party_or_purpose']), (300.0, 'Ali dues'))

    def test_admin_has_a_separate_treasury_too(self):
        database.add_transaction('income', 300, 'USD', 'Ali dues', owner='ali@example.com')
        self.sign_in_as(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        self.add('Admin donation', 50)
        res = self.client.get('/')
        self.assertIn(b'Admin donation', res.data)
        self.assertNotIn(b'Ali dues', res.data)

    def test_older_transactions_without_owner_go_to_admin(self):
        conn = database.get_db_connection()
        conn.execute("INSERT INTO transactions (type, amount, currency, party_or_purpose, date) "
                     "VALUES ('income', 10, 'USD', 'Before accounts', '2026-10-01')")
        conn.commit()
        conn.close()

        self.assertEqual(database.claim_unowned_transactions(AUTHORIZED_EMAIL), 1)
        self.assertEqual(len(database.get_transactions(owner=AUTHORIZED_EMAIL)), 1)
        self.assertEqual(database.get_transactions(owner='ali@example.com'), [])

    def test_owner_is_required(self):
        with self.assertRaises(TypeError):
            database.get_transactions()
        with self.assertRaises(ValueError):
            database.get_wallet_balance(owner='')

    # --- Admin: remove and edit users -------------------------------------

    def user_id(self, email):
        return database.get_user_by_email(email)['id']

    def test_admin_removes_user_and_all_their_data(self):
        database.add_transaction('income', 300, 'USD', 'Ali dues', owner='ali@example.com')
        database.add_transaction('expense', 20, 'USD', 'Ali rope', owner='ali@example.com')
        database.add_transaction('income', 75, 'USD', 'Rami dues', owner='rami@example.com')
        database.register_device('ali-phone', 'ali@example.com')

        # Ali is signed in on another device
        ali_client = app.test_client()
        ali_client.post('/login', data={'email': 'ali@example.com', 'password': 'secret1'})
        self.assertEqual(ali_client.get('/').status_code, 200)

        self.sign_in_as(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        res = self.client.get('/users')
        self.assertIn(b'data-count="2"', res.data)
        res = self.client.post(f"/users/{self.user_id('ali@example.com')}/remove", follow_redirects=True)
        self.assertIn(b'User ali@example.com and all their data were removed.', res.data)

        self.assertIsNone(database.get_user_by_email('ali@example.com'))
        self.assertEqual(database.get_transactions(owner='ali@example.com'), [])
        self.assertEqual(database.get_devices('ali@example.com'), [])
        self.assertEqual(len(database.get_transactions(owner='rami@example.com')), 1)

        # Ali's open session ends on the next click, and Ali can no longer sign in
        res = ali_client.get('/', follow_redirects=True)
        self.assertIn(b'Your account is no longer active', res.data)
        res = ali_client.post('/login', data={'email': 'ali@example.com', 'password': 'secret1'}, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res.data)

    def test_admin_edits_user_details_and_data_follows_new_email(self):
        database.add_transaction('income', 75, 'USD', 'Rami dues', owner='rami@example.com')
        database.register_device('rami-phone', 'rami@example.com')
        rami_client = app.test_client()
        rami_client.post('/login', data={'email': 'rami@example.com', 'password': 'secret1'})

        self.sign_in_as(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        rami_id = self.user_id('rami@example.com')
        res = self.client.post(f'/users/{rami_id}/update', data={
            'name': 'Leader Rami', 'email': 'Rami.New@Example.com', 'password': ''
        }, follow_redirects=True)
        self.assertIn(b'User rami.new@example.com was updated.', res.data)

        user = database.get_user(rami_id)
        self.assertEqual((user['name'], user['email']), ('Leader Rami', 'rami.new@example.com'))
        self.assertEqual(len(database.get_transactions(owner='rami.new@example.com')), 1)
        self.assertEqual(database.get_devices('rami.new@example.com')[0]['token'], 'rami-phone')

        # The old sign-in no longer works; the new email with the unchanged password does
        self.assertIn(b'no longer active', rami_client.get('/', follow_redirects=True).data)
        res = rami_client.post('/login', data={'email': 'rami.new@example.com', 'password': 'secret1'}, follow_redirects=True)
        self.assertIn(b'Rami dues', res.data)

        # Setting a new password replaces the old one
        self.client.post(f'/users/{rami_id}/update', data={
            'name': 'Leader Rami', 'email': 'rami.new@example.com', 'password': 'newpass9'})
        fresh = app.test_client()
        res = fresh.post('/login', data={'email': 'rami.new@example.com', 'password': 'secret1'}, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res.data)
        res = fresh.post('/login', data={'email': 'rami.new@example.com', 'password': 'newpass9'}, follow_redirects=True)
        self.assertIn(b'Rami dues', res.data)

    def test_edit_user_validation(self):
        self.sign_in_as(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        rami_id = self.user_id('rami@example.com')
        for data, message in [
            ({'name': 'R', 'email': 'ali@example.com'}, b'already exists'),
            ({'name': 'R', 'email': AUTHORIZED_EMAIL}, b'already exists'),
            ({'name': 'R', 'email': 'bad-email'}, b'valid email'),
            ({'name': '', 'email': 'rami@example.com'}, b'fill in all fields'),
            ({'name': 'R', 'email': 'rami@example.com', 'password': '123'}, b'at least 6 characters'),
        ]:
            res = self.client.post(f'/users/{rami_id}/update', data=data, follow_redirects=True)
            self.assertIn(message, res.data)
        self.assertEqual(database.get_user(rami_id)['email'], 'rami@example.com')

        # Saving with the same email is fine
        res = self.client.post(f'/users/{rami_id}/update', data={'name': 'Rami B', 'email': 'rami@example.com'}, follow_redirects=True)
        self.assertIn(b'was updated', res.data)

    def test_only_admin_can_remove_or_edit_users(self):
        database.add_transaction('income', 300, 'USD', 'Ali dues', owner='ali@example.com')
        self.sign_in_as('rami@example.com')
        ali_id = self.user_id('ali@example.com')
        self.assertEqual(self.client.post(f'/users/{ali_id}/remove').status_code, 403)
        self.assertEqual(self.client.post(f'/users/{ali_id}/update', data={
            'name': 'x', 'email': 'x@example.com'}).status_code, 403)
        self.assertIsNotNone(database.get_user_by_email('ali@example.com'))
        self.assertEqual(len(database.get_transactions(owner='ali@example.com')), 1)

        self.sign_in_as(AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD)
        self.assertEqual(self.client.post('/users/9999/remove').status_code, 404)


if __name__ == '__main__':
    unittest.main()
