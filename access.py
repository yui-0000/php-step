"""Shared entrance gate, independent of each browser's study progress."""
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from flask import abort, jsonify, redirect, render_template, request, session, url_for
from peewee import CharField, IntegerField, Model
from werkzeug.security import check_password_hash


def init_access(app, db):
    path = Path(app.instance_path) / 'access.json'
    stored = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    password_hash = app.config.get('ACCESS_PASSWORD_HASH', stored.get('password_hash', ''))
    required = app.config.get('ACCESS_REQUIRED', app.config['SESSION_COOKIE_SECURE'])
    if (required and not password_hash) or (password_hash and not password_hash.startswith('scrypt:')):
        raise RuntimeError('合言葉の設定が必要です。python tools/set_passphrase.py を実行してください。')
    enabled = bool(password_hash)
    app.config['ACCESS_ENABLED'] = enabled
    version = hashlib.sha256(password_hash.encode()).hexdigest()

    class EntranceAttempt(Model):
        address = CharField(primary_key=True)
        started = IntegerField()
        count = IntegerField(default=0)

        class Meta:
            database = db

    with db.connection_context():
        db.create_tables([EntranceAttempt])

    def authenticated():
        return not enabled or (
            hmac.compare_digest(session.get('entrance_version', ''), version)
            and 0 <= time.time() - session.get('entrance_at', 0) < 7 * 86400
        )

    def csrf_token():
        if 'entrance_csrf' not in session:
            session['entrance_csrf'] = secrets.token_hex(24)
        return session['entrance_csrf']

    def check_csrf():
        supplied = request.form.get('csrf', '')
        if not supplied or not hmac.compare_digest(supplied.encode(), session.get('entrance_csrf', '').encode()):
            abort(400)

    @app.before_request
    def entrance_gate():
        if enabled and (request.path == '/' or request.path.startswith('/api/')) and not authenticated():
            if request.path.startswith('/api/'):
                return jsonify(error='entrance_required'), 401
            return redirect(url_for('entrance'), code=303)

    @app.after_request
    def private_headers(response):
        if enabled and (request.path in ('/', '/login', '/logout') or request.path.startswith('/api/')):
            response.headers['Cache-Control'] = 'no-store'
            response.vary.add('Cookie')
        return response

    @app.get('/login')
    @app.post('/login')
    def entrance():
        if not enabled:
            return redirect(url_for('index'), code=303)
        error, status = None, 200
        if request.method == 'POST':
            check_csrf()
            phrase = request.form.get('passphrase', '')
            # Persist attempt counts across cookies and worker restarts.
            address = hmac.new(str(app.secret_key).encode(), (request.remote_addr or '').encode(), hashlib.sha256).hexdigest()
            now = int(time.time())
            db.connect(reuse_if_open=True)
            with db.atomic('IMMEDIATE'):
                EntranceAttempt.delete().where(EntranceAttempt.started <= now - 300).execute()
                row, _ = EntranceAttempt.get_or_create(address=address, defaults={'started': now, 'count': 0})
                limited = row.count >= 30
                retry_after = max(1, row.started + 300 - now)
                if not limited:
                    row.count += 1
                    row.save()
            if limited:
                response = app.make_response((render_template('login.html', csrf=csrf_token(), error='入力が続いたため、5分ほど待ってからお試しください。', entered=False), 429))
                response.headers['Retry-After'] = str(retry_after)
                return response
            if len(phrase) <= 128 and check_password_hash(password_hash, phrase):
                # Keep browser_id/csrf so re-entering never merges or erases progress.
                session['entrance_version'] = version
                session['entrance_at'] = int(time.time())
                session['entrance_csrf'] = secrets.token_hex(24)
                session.permanent = True
                return redirect(url_for('index'), code=303)
            error, status = '合言葉が違います。教えてもらった合言葉を確認してください。', 401
        return render_template('login.html', csrf=csrf_token(), error=error, entered=authenticated()), status

    @app.post('/logout')
    def leave_entrance():
        check_csrf()
        session.pop('entrance_version', None)
        session.pop('entrance_at', None)
        session.pop('entrance_csrf', None)
        return redirect(url_for('entrance'), code=303)
