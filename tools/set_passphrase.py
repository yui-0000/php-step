"""Set/rotate the phrase interactively, without shell history or plaintext storage."""
import getpass
import json
import os
from pathlib import Path
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    phrase = getpass.getpass('新しい合言葉（12〜128文字、入力は表示されません）: ')
    if not 12 <= len(phrase) <= 128:
        raise SystemExit('12〜128文字の合言葉にしてください。')
    if phrase != getpass.getpass('確認のためもう一度入力: '):
        raise SystemExit('入力が一致しません。変更していません。')
    directory = ROOT / 'instance'
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / 'access.json.tmp'
    with temporary.open('w', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        json.dump({'password_hash': generate_password_hash(phrase)}, handle)
        handle.write('\n')
    temporary.replace(directory / 'access.json')
    print('合言葉を設定しました。アプリを再起動（公開先ではReload）してください。履歴は引き継がれます。')


if __name__ == '__main__':
    main()
