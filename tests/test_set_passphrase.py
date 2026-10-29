import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import check_password_hash
from tools import set_passphrase


class PassphraseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        self.patch = patch.object(set_passphrase, 'ROOT', self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def run_command(self, phrase, argv=None, confirmation=None):
        output = StringIO()
        with patch('getpass.getpass', side_effect=[phrase, phrase if confirmation is None else confirmation]), redirect_stdout(output):
            set_passphrase.main(argv or [])
        return output.getvalue()

    def test_nine_character_temporary_phrase_stored_only_as_hash(self):
        phrase = 'test987xy'
        output = self.run_command(phrase, ['--min-length', '9'])
        content = (self.root / 'instance/access.json').read_text(encoding='utf-8')
        self.assertNotIn(phrase, content + output)
        self.assertTrue(check_password_hash(json.loads(content)['password_hash'], phrase))

    def test_default_remains_twelve_after_temporary_setting(self):
        self.run_command('test987xy', ['--min-length', '9'])
        before = (self.root / 'instance/access.json').read_bytes()
        with self.assertRaises(SystemExit):
            self.run_command('test987xy')
        self.assertEqual((self.root / 'instance/access.json').read_bytes(), before)

    def test_japanese_length_and_confirmation(self):
        phrase = 'あいうえおかきくけ'
        self.run_command(phrase, ['--min-length', '9'])
        content = json.loads((self.root / 'instance/access.json').read_text(encoding='utf-8'))
        self.assertTrue(check_password_hash(content['password_hash'], phrase))
        with self.assertRaises(SystemExit):
            self.run_command(phrase, ['--min-length', '9'], confirmation='違う入力')

    def test_invalid_lengths_do_not_write_or_prompt(self):
        for number in ['4', '129', 'abc']:
            with patch('getpass.getpass') as prompt, redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                set_passphrase.main(['--min-length', number])
            prompt.assert_not_called()
        self.assertFalse((self.root / 'instance/access.json').exists())

    def test_too_short_and_too_long_do_not_create_settings(self):
        for phrase in ['12345678', 'x' * 129]:
            with self.assertRaises(SystemExit):
                self.run_command(phrase, ['--min-length', '9'])
        self.assertFalse((self.root / 'instance/access.json').exists())


if __name__ == '__main__':
    unittest.main()
