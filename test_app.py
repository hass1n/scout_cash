import unittest
import os
import tempfile
from datetime import date

from werkzeug.security import generate_password_hash

import database
import push
from app import app, AUTHORIZED_EMAIL, AUTHORIZED_PASSWORD

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
            db_path=self.db_path
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
            db_path=self.db_path
        )

        # 3. Add USD Expense
        database.add_transaction(
            type_='expense',
            amount=120.0,
            currency='USD',
            party_or_purpose='Tents & Rope Hardware',
            category='Camping Equipment',
            date='2026-10-10',
            db_path=self.db_path
        )

        # 4. Add LBP Expense
        database.add_transaction(
            type_='expense',
            amount=5000000.0,
            currency='LBP',
            party_or_purpose='Snacks & Water for Hike',
            category='Food & Snacks',
            date='2026-10-12',
            db_path=self.db_path
        )

        # Check Wallet Balance
        wallet = database.get_wallet_balance(self.db_path)
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
            db_path=self.db_path
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
            db_path=self.db_path
        )
        self.assertTrue(ok)
        updated = database.get_transaction(inc_id, self.db_path)
        self.assertEqual(updated['amount'], 600.0)
        self.assertEqual(updated['party_or_purpose'], 'Donor Mr. Smith & Family')

        # Delete transaction
        ok = database.delete_transaction(inc_id, self.db_path)
        self.assertTrue(ok)
        self.assertIsNone(database.get_transaction(inc_id, self.db_path))

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


if __name__ == '__main__':
    unittest.main()
