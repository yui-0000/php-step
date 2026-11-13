# 1回に解く問題数の選択

ホーム、分野別、苦手一覧の「1回に解く問題数」から5・10・20・40問を選択できます。初期値は10問です。
設定は保存され、次に開始するセットへ適用します。途中の学習は現在の問題数で再開します。
分野や苦手問題が選択数より少ない場合は、その件数まで出題します。
10問チェックは10問のままです。通常練習の40問は、時間制限のある模擬試験ではありません。

## PythonAnywhereへの反映

公開済みのアプリには次の4ファイルを同時に反映します。

- app.py
- static/app.js
- static/core.js
- static/sw.js

`dist/php-step-question-count-update.zip` は、この4ファイルだけを含む更新用ZIPです。
合言葉、秘密キー、データベース、学習履歴は含みません。
更新前にアプリの設定から学習履歴のJSONを保存しておくと、手元にもバックアップを残せます。

PythonAnywhereのFiles画面で `/home/yuit` に更新用ZIPをアップロードします。
アプリ用のBashで次を実行すると、変更する4ファイルを日付付きフォルダへコピーしてから展開できます。
バックアップ命令がエラーになった場合は、展開せず内容を確認してください。

```bash
cd ~/php-step
backup_dir="$HOME/php-step-backups/count-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir/static"
cp app.py "$backup_dir/app.py"
cp static/app.js static/core.js static/sw.js "$backup_dir/static/"
unzip -o ~/php-step-question-count-update.zip -d ~/php-step
```

Web画面でReloadし、アプリを再読み込みします。WindowsのChromeではCtrl+Shift+Rも使えます。
スマホで古い画面が残る場合は、アプリのタブやホーム画面から開いたアプリを一度すべて閉じて、開き直してください。
学習履歴を残すため、ブラウザのサイトデータを削除する必要はありません。

確認点：ホームに選択欄があること、20問を選ぶと20問のセットが始まること、途中保存と苦手復習が機能すること。
