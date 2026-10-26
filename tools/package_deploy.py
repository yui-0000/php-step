"""Build a deploy-only ZIP using an allowlist; no credentials or progress."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = ['app.py', 'access.py', 'wsgi.py', 'requirements.lock.txt', 'requirements.txt', 'DEPLOY_PYTHONANYWHERE.md', 'tools/set_passphrase.py', 'tools/package_deploy.py']
FOLDERS = ['static', 'templates', 'data']


def main():
    output = ROOT / 'dist' / 'php-step.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, name)
        for folder in FOLDERS:
            for path in sorted((ROOT / folder).rglob('*')):
                if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts:
                    archive.write(path, path.relative_to(ROOT).as_posix())
    print(f'公開用ZIPを作成しました: {output}')


if __name__ == '__main__':
    main()
