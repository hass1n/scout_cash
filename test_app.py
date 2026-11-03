import unittest
import os
import tempfile
from datetime import date

import database
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


if __name__ == '__main__':
    unittest.main()
