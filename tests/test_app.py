import json
import tempfile
import unittest
from pathlib import Path
from app import create_app, ROOT


def state():
    return {'version': 1, 'settings': {'examDate': '2026-11-16', 'dailyGoal': 15}, 'records': {}, 'daily': {}, 'session': None, 'lastResult': None}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'tests')
        self.config = {'TESTING': True, 'SECRET_KEY': 'test-key-only', 'DATABASE': str(Path(self.temp.name) / 'test.sqlite3')}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions['progress_database'].close()
        self.temp.cleanup()

    def put(self, client, csrf, revision=0, payload=None):
        return client.put('/api/state', json={'revision': revision, 'state': payload or state()}, headers={'X-CSRF-Token': csrf})

    def test_state_persists_and_other_browsers_cannot_read_it(self):
        info = self.client.get('/api/state').get_json()
        self.assertEqual(self.put(self.client, info['csrf']).status_code, 200)
        self.assertEqual(self.client.get('/api/state').get_json()['state'], state())
        other = self.app.test_client().get('/api/state').get_json()
        self.assertIsNone(other['state'])
        self.assertNotEqual(info['browserId'], other['browserId'])
        restarted = create_app(self.config).test_client()
        restarted.set_cookie('session', self.client.get_cookie('session').value)
        self.assertEqual(restarted.get('/api/state').get_json()['state'], state())

    def test_csrf_required(self):
        self.client.get('/api/state')
        self.assertEqual(self.put(self.client, 'wrong').status_code, 403)

    def test_question_notes_roundtrip_and_validation(self):
        info = self.client.get('/api/state').get_json()
        payload = state()
        payload['questionNotes'] = {'q02': {'note': 'どうして5？', 'selected': [0], 'confidence': 'unsure', 'savedAt': 1000}}
        self.assertEqual(self.put(self.client, info['csrf'], payload=payload).status_code, 200)
        self.assertEqual(self.client.get('/api/state').get_json()['state'], payload)
        payload['questionNotes']['q02']['selected'] = [99]
        self.assertEqual(self.put(self.client, info['csrf'], revision=1, payload=payload).status_code, 400)
        self.assertEqual(self.client.get('/api/state').get_json()['state']['questionNotes']['q02']['selected'], [0])

    def test_revision_conflict_does_not_overwrite(self):
        info = self.client.get('/api/state').get_json()
        self.put(self.client, info['csrf'])
        changed = state(); changed['settings']['dailyGoal'] = 30
        self.assertEqual(self.put(self.client, info['csrf'], payload=changed).status_code, 409)
        self.assertEqual(self.client.get('/api/state').get_json()['state']['settings']['dailyGoal'], 15)

    def test_invalid_backup_does_not_overwrite(self):
        info = self.client.get('/api/state').get_json()
        bad = state(); bad['records']['unknown'] = {}
        self.assertEqual(self.put(self.client, info['csrf'], payload=bad).status_code, 400)
        self.assertIsNone(self.client.get('/api/state').get_json()['state'])

    def test_html_assets_and_public_questions(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(len(self.client.get('/api/questions').get_json()['questions']), 300)
        for asset in ['app.js', 'core.js', 'questions.js', 'sync.js', 'style.css', 'icon-192.png', 'icon-512.png']:
            with self.client.get('/static/' + asset) as response:
                self.assertEqual(response.status_code, 200)
        with self.client.get('/sw.js') as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/instance/php_step.sqlite3').status_code, 404)
        self.assertEqual(self.client.get('/app.py').status_code, 404)

    def test_private_state_is_not_cacheable(self):
        self.assertEqual(self.client.get('/api/state').headers['Cache-Control'], 'no-store')

    def test_new_question_progress_roundtrip(self):
        info = self.client.get('/api/state').get_json()
        payload = state()
        payload['records']['q100'] = {'attempts': 1, 'correct': True, 'confidence': 'unsure', 'streak': 0, 'lastAt': 1000, 'dueAt': 86401000}
        payload['questionNotes'] = {'q100': {'note': '追記', 'selected': [0], 'confidence': 'unsure', 'savedAt': 1000}}
        payload['session'] = {'mode': 'review', 'ids': ['q100'], 'index': 0, 'responses': {'q100': {'selected': [0], 'confidence': 'unsure', 'correct': True}}}
        self.assertEqual(self.put(self.client, info['csrf'], payload=payload).status_code, 200)
        self.assertEqual(self.client.get('/api/state').get_json()['state'], payload)

    def test_pending_answer_survives_server_backup_and_rejects_invalid_pending(self):
        info = self.client.get('/api/state').get_json()
        payload = state()
        payload['session'] = {'mode': 'learn', 'ids': ['q01', 'q02'], 'index': 0, 'responses': {}, 'pending': {'id': 'q01', 'selected': [0]}}
        self.assertEqual(self.put(self.client, info['csrf'], payload=payload).status_code, 200)
        self.assertEqual(self.client.get('/api/state').get_json()['state'], payload)
        for pending in [None, {'id': 'q02', 'selected': [0]}, {'id': 'q01', 'selected': []}, {'id': 'q01', 'selected': [99]}, {'id': 'q01', 'selected': [0, 0]}]:
            payload['session']['pending'] = pending
            self.assertEqual(self.put(self.client, info['csrf'], revision=1, payload=payload).status_code, 400)


    def test_difficulty_and_latest_question_roundtrip(self):
        info = self.client.get('/api/state').get_json()
        payload = state()
        payload['settings']['difficulty'] = 'practice'
        q = next(q for q in self.client.get('/api/questions').get_json()['questions'] if q['id'] == 'q300')
        response = {'selected': q['answer'], 'correct': True, 'confidence': 'unsure'}
        payload['session'] = {'mode': 'learn', 'ids': ['q300'], 'index': 0, 'responses': {'q300': response}}
        self.assertEqual(self.put(self.client, info['csrf'], payload=payload).status_code, 200)
        self.assertEqual(self.client.get('/api/state').get_json()['state'], payload)
        payload['settings']['difficulty'] = 'invalid'
        self.assertEqual(self.put(self.client, info['csrf'], revision=1, payload=payload).status_code, 400)


if __name__ == '__main__':
    unittest.main()
