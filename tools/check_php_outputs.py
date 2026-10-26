"""Run trusted, authored output exercises with a separately supplied PHP CLI.

Usage: python tools/check_php_outputs.py C:/path/to/php.exe
No server is started. Runtime is a development-only dependency.
"""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
questions = {q['id']: q for q in json.loads((root/'data/questions.json').read_text(encoding='utf-8'))['questions']}
cases = json.loads((root/'tests/php-output-cases.json').read_text(encoding='utf-8'))
failed = []
for case in cases:
    q = questions[case['id']]
    assert q['code'] == case['code'], f"Stale fixture: {q['id']}"
    assert len(q['answer']) == 1 and q['options'][q['answer'][0]] == case['expected'], f"Wrong answer mapping: {q['id']}"
    result = subprocess.run([sys.argv[1], '-n', '-d', 'date.timezone=UTC', '-d', 'error_reporting=-1',
                             '-d', 'display_errors=stderr', '-r', q['code']], capture_output=True, timeout=5)
    output = result.stdout.decode('utf-8', errors='replace')
    errors = result.stderr.decode('utf-8', errors='replace')
    if result.returncode or errors or output != case['expected']:
        failed.append({'id':q['id'], 'expected':case['expected'], 'actual':output,'stderr':errors,'exit':result.returncode})
for failure in failed:
    print(json.dumps(failure, ensure_ascii=True))
print(f"PHP output checks: {len(cases)-len(failed)}/{len(cases)} passed")
sys.exit(bool(failed))
