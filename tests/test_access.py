import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash
from app import ROOT, create_app


class AccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phrase = 'study-entrance-test-only'
        cls.hashed = generate_password_hash(cls.phrase)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.config = dict(TESTING=True, SECRET_KEY='entrance-test-only', DATABASE=str(Path(self.temp.name) / 'db.sqlite3'), ACCESS_PASSWORD_HASH=self.hashed, ACCESS_REQUIRED=True)
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions['progress_database'].close()
        self.temp.cleanup()

    def token(self, client=None):
        client = client or self.client
        client.get('/login')
        with client.session_transaction() as session:
            return session['entrance_csrf']

    def enter(self, client=None, phrase=None):
        client = client or self.client
        return client.post('/login', data={'csrf': self.token(client), 'passphrase': phrase or self.phrase})

    def test_gate_protects_questions_and_both_state_methods(self):
        self.assertEqual(self.client.get('/').location, '/login')
        for method, path in [('get', '/api/questions'), ('get', '/api/state'), ('put', '/api/state')]:
            response = getattr(self.client, method)(path)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.enter(phrase='違う合言葉').status_code, 401)
        self.assertEqual(self.client.get('/api/questions').status_code, 401)
        self.assertEqual(self.enter().status_code, 303)
        self.assertEqual(len(self.client.get('/api/questions').get_json()['questions']), 300)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_csrf_required_for_entry_and_exit(self):
        for csrf in ['', 'wrong', '不正']:
            self.assertEqual(self.client.post('/login', data={'csrf': csrf, 'passphrase': self.phrase}).status_code, 400)
        self.enter()
        self.assertEqual(self.client.post('/logout').status_code, 400)
        self.assertEqual(self.client.get('/logout').status_code, 405)
        self.assertEqual(self.client.post('/logout', data={'csrf': self.token()}).status_code, 303)
        self.assertEqual(self.client.get('/api/state').status_code, 401)

    def test_progress_survives_exit_and_reentry_and_stays_separate(self):
        self.enter()
        info = self.client.get('/api/state').get_json()
        payload = {'version': 1, 'settings': {'examDate': '2026-11-16', 'dailyGoal': 20}, 'records': {}, 'daily': {}, 'session': None, 'lastResult': None}
        self.assertEqual(self.client.put('/api/state', json={'revision': 0, 'state': payload}, headers={'X-CSRF-Token': info['csrf']}).status_code, 200)
        self.client.post('/logout', data={'csrf': self.token()})
        self.enter()
        after = self.client.get('/api/state').get_json()
        self.assertEqual(after['browserId'], info['browserId'])
        self.assertEqual(after['state'], payload)
        other = self.app.test_client()
        self.enter(other)
        self.assertIsNone(other.get('/api/state').get_json()['state'])

    def test_rotation_and_expiry_require_reentry_without_losing_browser_id(self):
        self.enter()
        before = self.client.get('/api/state').get_json()['browserId']
        with self.client.session_transaction() as session:
            session['entrance_at'] -= 7 * 86400
        self.assertEqual(self.client.get('/api/state').status_code, 401)
        self.enter()
        rotated = create_app({**self.config, 'ACCESS_PASSWORD_HASH': generate_password_hash('new-test-phrase-only')})
        client = rotated.test_client()
        client.set_cookie('session', self.client.get_cookie('session').value)
        self.assertEqual(client.get('/api/questions').status_code, 401)
        self.enter(client, 'new-test-phrase-only')
        self.assertEqual(client.get('/api/state').get_json()['browserId'], before)
        rotated.extensions['progress_database'].close()

    def test_rate_limit_survives_new_cookies_and_restart_then_expires(self):
        with patch('access.time.time', return_value=1800000000), patch('access.check_password_hash', return_value=False):
            for _ in range(30):
                self.assertEqual(self.enter(phrase='wrong').status_code, 401)
            restarted = create_app(self.config)
            response = self.enter(restarted.test_client())
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers['Retry-After'], '300')
            restarted.extensions['progress_database'].close()
        with patch('access.time.time', return_value=1800000301):
            self.assertEqual(self.enter().status_code, 303)

    def test_public_mode_fails_closed_without_phrase(self):
        with self.assertRaisesRegex(RuntimeError, '合言葉'):
            create_app({**self.config, 'ACCESS_PASSWORD_HASH': ''})

    def test_secure_cookie_and_login_page_not_cached(self):
        secure = create_app({**self.config, 'SESSION_COOKIE_SECURE': True}).test_client()
        response = secure.get('/login', base_url='https://localhost')
        self.assertIn('Secure', response.headers['Set-Cookie'])
        self.assertIn('HttpOnly', response.headers['Set-Cookie'])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertNotIn('serviceWorker', response.get_data(as_text=True))
        self.assertNotIn(self.phrase, response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
