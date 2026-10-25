"""Repeatable offline engineering checks; optional isolated Playwright checks."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ['test_backend', 'test_providers', 'test_prices', 'test_prices_candidate',
           'test_ai_options', 'test_ai_quote', 'test_audit_regressions', 'test_deploy',
           'test_retrieval', 'test_retrieval_metrics', 'test_retrieval_request', 'test_semantic', 'test_review_retrieval', 'test_semantic_worker',
           'test_retrieval_http_review', 'test_review_docs']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ui-python', help='Python environment with Playwright and Chromium installed')
    args = parser.parse_args()
    parent = ROOT / 'data' / 'verification'
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='run-', dir=parent))
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GUANLAN_', 'LLM_'))}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    results = []

    def run(name, command, timeout):
        print('Running:', name, flush=True)
        start = time.monotonic()
        with (output / (name + '.log')).open('w') as log:
            try:
                code = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                      stderr=subprocess.STDOUT, timeout=timeout).returncode
            except subprocess.TimeoutExpired:
                code = 124
            except OSError as error:
                log.write(str(error)); code = 127
        results.append(dict(check=name, exit_code=code, seconds=round(time.monotonic()-start, 3)))

    run('backend', [sys.executable, '-u', '-m', 'unittest', *['tests.'+n for n in BACKEND], '-v'], 180)
    if args.ui_python:
        with tempfile.TemporaryDirectory(prefix='guanlan-check-') as cache:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            url = f'http://127.0.0.1:{port}/'
            env.update(GUANLAN_PORT=str(port), GUANLAN_TEST_URL=url, GUANLAN_DATA_DIR=cache,
                       GUANLAN_DISABLE_AI='1', GUANLAN_SCHEDULE='0')
            with (output / 'server.log').open('w') as log:
                process = subprocess.Popen([sys.executable, 'server/app.py', '--no-schedule'],
                                           cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    ready = False
                    for _ in range(100):
                        if process.poll() is not None: break
                        try:
                            with urllib.request.urlopen(url+'healthz', timeout=.5) as response:
                                ready = response.status == 200
                            if ready: break
                        except OSError: time.sleep(.1)
                    if ready:
                        run('ui', [args.ui_python, '-m', 'unittest', 'tests.test_ui_regressions',
                                   'tests.test_reliability_followup', 'tests.test_retrieval_ui', '-v'], 180)
                    else: results.append(dict(check='server-start', exit_code=1))
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try: process.wait(5)
                        except subprocess.TimeoutExpired: process.kill(); process.wait()
    report = dict(results=results, python=sys.version, ui_requested=bool(args.ui_python),
                  scope='Engineering only; no live model evaluation or human testing',
                  passed=all(r['exit_code'] == 0 for r in results))
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2)); print('Artifacts:', output)
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    sys.exit(main())
