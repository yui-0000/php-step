# Androidで出先から使うための公開手順

PythonAnywhereの無料Beginnerアカウントを使う手順です。独自ドメインの購入は不要です。
この手順を実施するまでは、インターネットには公開されません。
無料枠は1アプリ・1 worker・512MiB・公開期限1か月です。利用時に公式ページと管理画面で最新条件を確認してください。

## 1. アカウントとアップロード

https://www.pythonanywhere.com/pricing/ の「Create a Beginner account」から無料アカウントを作ります。
アカウントのパスワードやアプリの合言葉を、チャットやGitHubに書かないでください。
以下の `YOUR_USERNAME` は登録したユーザー名に読み替えます。

パソコンのGit Bashで、公開用ZIPを作成します。

```bash
cd ~/my-apps/php-step
./.venv/Scripts/python.exe tools/package_deploy.py
```

できた `dist/php-step.zip` をPythonAnywhereのFiles画面でホームフォルダにアップロードします。
このZIPには合言葉・既存履歴・秘密キー・パソコンの仮想環境を含めません。
公開先は新しい環境です。パソコンの学習履歴を移す場合は、アプリの設定でJSONバックアップを書き出しておきます。

## 2. 公開先で準備する

以下は **PythonAnywhereのConsoles → Bash** で実行します。パソコンのターミナルとは別です。
既に `~/php-step` が存在する場合は、上書き展開する前にファイルとinstanceをバックアップしてください。

```bash
unzip ~/php-step.zip -d ~/php-step
cd ~/php-step
mkvirtualenv --python=/usr/bin/python3.13 php-step-env
python -m pip install -r requirements.lock.txt
python tools/set_passphrase.py
```

Python 3.13を選べない環境では、ここで止めて利用可能なバージョンを確認します。
合言葉は12〜128文字で、他のサービスのパスワードを使い回さず、推測されにくいものにします。
入力中は文字が表示されません。2回入力すると、`instance/access.json` にハッシュだけを保存します。

最低文字数を一時的に指定する場合は、修正版の `tools/set_passphrase.py` を公開先にも反映してから実行します。

```bash
python tools/set_passphrase.py --min-length 9
```

この指定は今回の入力にだけ適用します。通常の命令では引き続き12〜128文字です。
仮設定の動作確認後、共有前に `python tools/set_passphrase.py` で長い合言葉へ変更してWebのReloadを押します。
文字数を指定しただけで安全性を保証するものではありません。推測しやすい名前や連続する数字は避けます。
既にZIPを展開済みの場合は、Filesで `php-step/tools` を開き、修正版の `set_passphrase.py` だけをアップロードして置き換えられます。

## 3. Web画面の設定

1. Web → Add a new web app → 無料の標準ドメイン → Manual configuration → Python 3.13。
2. Source codeに `/home/YOUR_USERNAME/php-step` を設定。
3. Virtualenvに `/home/YOUR_USERNAME/.virtualenvs/php-step-env` を設定。
4. WSGI configuration fileを開き、既定のサンプルを次に置き換えて保存。

```python
import os
import sys

project = '/home/YOUR_USERNAME/php-step'
if project not in sys.path:
    sys.path.insert(0, project)
os.environ['PHP_STEP_HTTPS'] = '1'

from wsgi import application
```

5. Web画面のHTTPS強制（Force HTTPS）を有効にし、Reload。
6. `https://YOUR_USERNAME.pythonanywhere.com/` を開き、合言葉の画面が出ることを確認。

Static filesの追加設定は最初は不要です。Flaskから配信します。
**プロジェクト全体やinstanceをStatic filesに割り当てないでください。** DBや秘密の設定は公開しません。
`python app.py` を公開先で常駐起動する必要はありません。Web画面とWSGIから動きます。
HTTPSモードで合言葉が未設定の場合は、アプリが起動を止めます。

## 4. 公開直後の確認

- 未入室のChromeのシークレットタブで `/api/questions` と `/api/state` が401になる。
- 違う合言葉では入れず、正しい合言葉で問題を開ける。
- 自分とクラスメートの別々のブラウザで、履歴が混ざらない。
- Androidで数問解き、再読み込みして続きが残る。
- Chromeのメニューからホーム画面へ追加。初回の保存完了後に、機内モードでも問題が開けるか実機確認する。
- 設定からパソコンで書き出した履歴JSONを読み込める。別端末で自動同期する機能はまだない。

実際の公開先とAndroidでは、これらの確認をこれから行います。テスト成功だけで公開完了にはなりません。
新しいURLはパソコンの127.0.0.1とは別の保存場所なので、履歴は自動では移りません。

## 5. 維持・合言葉の変更・バックアップ

無料アプリはWeb画面の有効期限を確認し、期限前に延長操作をします。
更新後はReload。更新時に `instance/` を削除・上書きしないでください。
SQLite DB、secret.key、access.jsonは公開先の永続ファイルとして維持します。
アプリ内のJSONバックアップも各自が定期的に保存してください。

合言葉を変更するときは、公開先のBashで次を実行します。

```bash
workon php-step-env
cd ~/php-step
python tools/set_passphrase.py
```

WebでReloadすると、オンラインでの利用には新しい合言葉が必要になります。履歴の識別Cookieは保持します。
通常は7日ごとに再入室が必要です。接続元アドレスごとに5分間で30回までの入力に制限します。
公開先のプロキシ構成によっては、同じアドレスとして複数人の試行を数える場合があります。

オフライン用に保存済みの問題や履歴は、合言葉の変更では端末から削除できません。
「入力し直す」はオンラインの入室許可を外す操作で、端末内の教材を消す操作ではありません。
個別ログインは未実装です。将来、本人の確認後にブラウザの既存履歴を各アカウントへ移す対応を追加します。

## 検証と参照

この変更でPythonのテスト17件、JavaScriptのテスト24件が成功しました。
入室制限、CSRF、入力回数制限、7日間の期限、合言葉変更、履歴の保持・分離、キャッシュと入室の挙動を確認しています。
サーバー公開とAndroid実機の確認は未実施です。

- https://help.pythonanywhere.com/pages/Flask/
- https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- https://www.pythonanywhere.com/pricing/
- https://flask.palletsprojects.com/en/stable/web-security/
- https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash
