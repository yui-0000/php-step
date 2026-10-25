"""PHP STEP: Flask + Peewee. PHP itself is never executed."""
import json
import os
import secrets
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory, session
from peewee import CharField, IntegerField, Model, SqliteDatabase, TextField

ROOT = Path(__file__).resolve().parent
CONTENT = json.loads((ROOT / 'data' / 'questions.json').read_text(encoding='utf-8'))
QUESTIONS = {q['id']: q for q in CONTENT['questions']}


def valid_int(value, minimum=0, maximum=1_000_000_000):
    return type(value) is int and minimum <= value <= maximum


def validate_state(state):
    if not isinstance(state, dict) or state.get('version') != 1:
        raise ValueError('Unsupported backup version')
    settings = state.get('settings')
    if not isinstance(settings, dict):
        raise ValueError('Invalid settings')
    date.fromisoformat(settings.get('examDate', ''))
    if not valid_int(settings.get('dailyGoal'), 5, 100):
        raise ValueError('Invalid daily goal')
    records, daily = state.get('records'), state.get('daily')
    if not isinstance(records, dict) or not isinstance(daily, dict) or len(daily) > 36600:
        raise ValueError('Invalid records')
    for key, record in records.items():
        if key not in QUESTIONS or not isinstance(record, dict):
            raise ValueError('Unknown question')
        if not valid_int(record.get('attempts'), 1) or not valid_int(record.get('streak')):
            raise ValueError('Invalid attempts')
        if type(record.get('correct')) is not bool or record.get('confidence') not in ('sure', 'unsure', 'unknown'):
            raise ValueError('Invalid confidence')
        if type(record.get('bookmark', False)) is not bool:
            raise ValueError('Invalid bookmark')
        for field in ('lastAt', 'dueAt'):
            if not valid_int(record.get(field), 0, 9_000_000_000_000):
                raise ValueError('Invalid timestamp')
    for day, count in daily.items():
        date.fromisoformat(day)
        if not valid_int(count):
            raise ValueError('Invalid daily count')
    for current in (state.get('session'), state.get('lastResult')):
        if current is None:
            continue
        if not isinstance(current, dict) or current.get('mode') not in ('learn', 'review', 'topic', 'quiz'):
            raise ValueError('Invalid session')
        ids = current.get('ids')
        if not isinstance(ids, list) or not 1 <= len(ids) <= len(QUESTIONS) or any(not isinstance(i, str) or i not in QUESTIONS for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Invalid question list')
        if not valid_int(current.get('index'), 0, len(ids) - 1) or not isinstance(current.get('responses'), dict):
            raise ValueError('Invalid session index')
        for key, answer in current['responses'].items():
            if key not in ids or not isinstance(answer, dict):
                raise ValueError('Invalid answer')
            selected = answer.get('selected')
            if not isinstance(selected, list) or not selected or any(not valid_int(i, 0, len(QUESTIONS[key]['options']) - 1) for i in selected) or len(selected) != len(set(selected)):
                raise ValueError('Invalid choices')
            expected = set(selected) == set(QUESTIONS[key]['answer'])
            if type(answer.get('correct')) is not bool or answer['correct'] != expected or answer.get('confidence') not in ('sure', 'unsure', 'unknown'):
                raise ValueError('Invalid answer result')
    notes = state.get('questionNotes', {})
    if not isinstance(notes, dict):
        raise ValueError('Invalid question notes')
    for key, note in notes.items():
        if key not in QUESTIONS or not isinstance(note, dict):
            raise ValueError('Unknown question note')
        if not isinstance(note.get('note'), str) or len(note['note']) > 2000 or not valid_int(note.get('savedAt'), 0, 9_000_000_000_000):
            raise ValueError('Invalid question note')
        selected = note.get('selected')
        if not isinstance(selected, list) or any(not valid_int(i, 0, len(QUESTIONS[key]['options']) - 1) for i in selected) or len(selected) != len(set(selected)) or note.get('confidence') not in ('sure', 'unsure', 'unknown'):
            raise ValueError('Invalid note answer')
    return state


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(MAX_CONTENT_LENGTH=1_000_000,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                      SESSION_COOKIE_SECURE=os.environ.get('PHP_STEP_HTTPS') == '1',
                      PERMANENT_SESSION_LIFETIME=timedelta(days=180),
                      DATABASE=str(Path(app.instance_path) / 'php_step.sqlite3'))
    if config:
        app.config.update(config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config.get('SECRET_KEY'):
        key_file = Path(app.instance_path) / 'secret.key'
        try:
            with key_file.open('x', encoding='ascii') as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config['SECRET_KEY'] = os.environ.get('PHP_STEP_SECRET_KEY') or key_file.read_text(encoding='ascii').strip()
    db = SqliteDatabase(app.config['DATABASE'], pragmas={'journal_mode': 'wal', 'foreign_keys': 1}, timeout=10)

    class Progress(Model):
        browser_id = CharField(primary_key=True)
        revision = IntegerField(default=0)
        payload = TextField()

        class Meta:
            database = db

    with db.connection_context():
        db.create_tables([Progress])
    app.extensions['progress_database'] = db

    @app.before_request
    def connect_database():
        if request.path == '/api/state':
            db.connect(reuse_if_open=True)

    @app.teardown_request
    def close_database(error=None):
        if not db.is_closed():
            db.close()

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.path == '/api/state':
            response.headers['Cache-Control'] = 'no-store'
        if request.path in ('/sw.js', '/'):
            response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/questions')
    def question_list():
        return jsonify(CONTENT)

    @app.get('/sw.js')
    def service_worker():
        return send_from_directory(app.static_folder, 'sw.js', mimetype='application/javascript')

    @app.get('/manifest.webmanifest')
    def manifest():
        return send_from_directory(app.static_folder, 'manifest.webmanifest', mimetype='application/manifest+json')

    @app.get('/api/state')
    def read_state():
        if 'browser_id' not in session:
            session['browser_id'] = secrets.token_hex(24)
            session['csrf'] = secrets.token_hex(24)
            session.permanent = True
        row = Progress.get_or_none(Progress.browser_id == session['browser_id'])
        return jsonify(browserId=session['browser_id'], csrf=session['csrf'], revision=row.revision if row else 0, state=json.loads(row.payload) if row else None)

    @app.put('/api/state')
    def write_state():
        if not session.get('browser_id') or not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), session.get('csrf', 'missing')):
            abort(403)
        if not request.is_json:
            abort(415)
        body = request.get_json()
        if not isinstance(body, dict) or not valid_int(body.get('revision')):
            return jsonify(error='Invalid revision'), 400
        try:
            state = validate_state(body.get('state'))
        except (ValueError, TypeError, KeyError):
            return jsonify(error='Invalid backup data'), 400
        with db.atomic('IMMEDIATE'):
            row = Progress.get_or_none(Progress.browser_id == session['browser_id'])
            revision = row.revision if row else 0
            if revision != body['revision']:
                return jsonify(error='revision_conflict', revision=revision), 409
            payload = json.dumps(state, ensure_ascii=False, separators=(',', ':'))
            if row:
                row.payload, row.revision = payload, revision + 1
                row.save()
            else:
                Progress.create(browser_id=session['browser_id'], revision=1, payload=payload)
        return jsonify(revision=revision + 1)

    return app


if __name__ == '__main__':
    from waitress import serve
    print('PHP STEP: http://127.0.0.1:5000', flush=True)
    serve(create_app(), host='127.0.0.1', port=5000)
