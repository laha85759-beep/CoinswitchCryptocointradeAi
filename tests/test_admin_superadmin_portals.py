import unittest
import json
from webhook_server import app

class TestAdminSuperAdminPortals(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_superadmin_page(self):
        res = self.client.get('/superadmin')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'SOVEREIGN SUPER ADMIN', res.data)

    def test_admin_page(self):
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'OPERATIONS ADMIN COCKPIT', res.data)

    def test_admin_login_and_saas_apis(self):
        login_res = self.client.post('/api/admin/login', json={
            'username': 'admin@thesmartmag.com',
            'password': 'SmartMag@Quant2026!'
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = json.loads(login_res.data)
        token = login_data.get('token')
        self.assertTrue(bool(token))

        # Check users list
        users_res = self.client.get('/api/admin/saas/users', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(users_res.status_code, 200)
        users_data = json.loads(users_res.data)
        self.assertIn('users', users_data)

        # Check payments list
        pay_res = self.client.get('/api/admin/saas/payments', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(pay_res.status_code, 200)
        pay_data = json.loads(pay_res.data)
        self.assertIn('payments', pay_data)

if __name__ == '__main__':
    unittest.main()
