"""Set/rotate the phrase interactively, without shell history or plaintext storage."""
import argparse
import getpass
import json
import os
from pathlib import Path
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description='共通の合言葉を設定・変更します。')
    parser.add_argument('--min-length', type=int, default=12, metavar='N', help='今回の入力に使う最低文字数（5〜128、通常は12）')
    args = parser.parse_args(argv)
    if not 5 <= args.min_length <= 128:
        parser.error('最低文字数は5〜128の範囲で指定してください。')
    minimum = args.min_length
    if minimum < 12:
        print('今回は仮設定用の文字数です。共有前に通常の命令で長い合言葉へ変更してください。')
    phrase = getpass.getpass(f'新しい合言葉（{minimum}〜128文字、入力は表示されません）: ')
    if not minimum <= len(phrase) <= 128:
        raise SystemExit(f'{minimum}〜128文字の合言葉にしてください。変更していません。')
    if phrase != getpass.getpass('確認のためもう一度入力: '):
        raise SystemExit('入力が一致しません。変更していません。')
    directory = ROOT / 'instance'
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / 'access.json.tmp'
    with open(temporary, 'w', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        json.dump({'password_hash': generate_password_hash(phrase)}, handle)
        handle.write('\n')
    temporary.replace(directory / 'access.json')
    print('合言葉を設定しました。アプリを再起動（公開先ではReload）してください。履歴は引き継がれます。')


if __name__ == '__main__':
    main()
