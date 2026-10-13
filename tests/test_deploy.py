"""Task 04 candidate: run the real server process under deployment settings. No upstream network.
    python3 -m unittest tests.test_deploy -v
"""
import base64, json, os, socket, subprocess, sys, tempfile, time, unittest, urllib.request, urllib.error
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p

class Server:
    def __init__(self, **env):
        self.port = free_port(); self.tmp = tempfile.TemporaryDirectory()
        base = {k: v for k, v in os.environ.items() if not k.startswith(('GUANLAN_', 'LLM_'))}
        self.env = {**base, 'GUANLAN_PORT': str(self.port), 'GUANLAN_DATA_DIR': self.tmp.name, 'GUANLAN_SCHEDULE': '0', **env}
    def __enter__(self):
        self.proc = subprocess.Popen([sys.executable, str(ROOT / 'server' / 'app.py')], env=self.env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if self.proc.poll() is not None: break
            try: urllib.request.urlopen(f'http://127.0.0.1:{self.port}/healthz', timeout=0.5); return self
            except Exception: time.sleep(0.1)
        return self
    def __exit__(self, *a):
        if self.proc.poll() is None: self.proc.terminate(); self.proc.wait(5)
        self.tmp.cleanup()
    def req(self, path, method='GET', host=None, origin=None, auth=None, body=None):
        r = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', method=method, data=json.dumps(body).encode() if body is not None else None)
        r.add_header('Host', host or f'127.0.0.1:{self.port}')
        if origin: r.add_header('Origin', origin)
        if body is not None: r.add_header('Content-Type', 'application/json')
        if auth: r.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
        try:
            with urllib.request.urlopen(r, timeout=5) as resp: return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e: return e.code, dict(e.headers), e.read()

class Defaults(unittest.TestCase):
    def test_local_default_unchanged(self):
        with Server() as s:
            st, h, _ = s.req('/api/state'); self.assertEqual(st, 200)
            self.assertEqual(s.req('/api/state', host='evil.example')[0], 403)
            o = f'http://127.0.0.1:{s.port}'
            self.assertEqual(s.req('/api/refresh', 'POST', origin='http://evil.example', body={})[0], 403)
            self.assertEqual(h.get('X-Content-Type-Options'), 'nosniff')
    def test_healthz_minimal(self):
        with Server() as s:
            st, _, b = s.req('/healthz', host='internal-probe:1234'); self.assertEqual((st, json.loads(b)), (200, {'ok': True}))

class Refusal(unittest.TestCase):
    def test_public_bind_without_auth_refuses(self):
        s = Server(GUANLAN_BIND='0.0.0.0')
        p = subprocess.run([sys.executable, str(ROOT / 'server' / 'app.py')], env=s.env, capture_output=True, text=True, timeout=30)
        s.tmp.cleanup()
        self.assertNotEqual(p.returncode, 0); self.assertIn('GUANLAN_BASIC_AUTH', p.stderr)
    def test_weak_password_refuses(self):
        s = Server(GUANLAN_BIND='0.0.0.0', GUANLAN_BASIC_AUTH='a:short', GUANLAN_ALLOWED_HOSTS='x.example')
        p = subprocess.run([sys.executable, str(ROOT / 'server' / 'app.py')], env=s.env, capture_output=True, text=True, timeout=30)
        s.tmp.cleanup(); self.assertNotEqual(p.returncode, 0); self.assertIn('至少 12 位', p.stderr)

class Authenticated(unittest.TestCase):
    CRED = 'reviewer:correct-horse-battery'
    def env(self, **k):
        return dict(GUANLAN_BIND='0.0.0.0', GUANLAN_BASIC_AUTH=self.CRED, GUANLAN_ALLOWED_HOSTS='guanlan.example.com', GUANLAN_ALLOWED_ORIGINS='https://guanlan.example.com', **k)
    def test_every_path_requires_auth_including_static(self):
        with Server(**self.env()) as s:
            for path in ('/', '/index.html', '/app.js', '/api/state'):
                st, h, _ = s.req(path, host='guanlan.example.com')
                self.assertEqual(st, 401, path); self.assertIn('Basic', h.get('WWW-Authenticate', ''))
            self.assertEqual(s.req('/api/state', host='guanlan.example.com', auth='reviewer:wrong-password!!')[0], 401)
            self.assertEqual(s.req('/api/state', host='guanlan.example.com', auth=self.CRED)[0], 200)
            self.assertEqual(s.req('/', host='guanlan.example.com', auth=self.CRED)[0], 200)
    def test_head_requires_host_and_auth(self):
        with Server(**self.env()) as s:
            for path in ('/', '/app.js', '/api/state'):
                self.assertEqual(s.req(path, method='HEAD', host='guanlan.example.com')[0], 401)
            self.assertEqual(s.req('/app.js', method='HEAD', host='evil.example', auth=self.CRED)[0], 403)
            self.assertEqual(s.req('/app.js', method='HEAD', host='guanlan.example.com', auth=self.CRED)[0], 200)

    def test_post_needs_origin_and_auth(self):
        with Server(**self.env(GUANLAN_DISABLE_AI='1')) as s:
            H = 'guanlan.example.com'
            self.assertEqual(s.req('/api/analyze', 'POST', host=H, origin='https://guanlan.example.com', body={'text': 'x'})[0], 401)
            self.assertEqual(s.req('/api/analyze', 'POST', host=H, origin='https://other.example', auth=self.CRED, body={'text': 'x'})[0], 403)
            st, _, b = s.req('/api/analyze', 'POST', host=H, origin='https://guanlan.example.com', auth=self.CRED, body={'text': 'x'})
            self.assertEqual(st, 403); self.assertIn('未开启', json.loads(b)['error'])
            st, _, b = s.req('/api/state', host=H, auth=self.CRED); self.assertTrue(json.loads(b)['ai'].get('disabled'))
    def test_price_rate_limit(self):
        with Server(**self.env(GUANLAN_PRICES_PER_MINUTE='2')) as s:
            H, O = 'guanlan.example.com', 'https://guanlan.example.com'
            codes = [s.req('/api/prices', 'POST', host=H, origin=O, auth=self.CRED, body={'code': 'bad'})[0] for _ in range(3)]
            self.assertEqual(codes, [400, 400, 429])  # invalid code never reaches upstream; 3rd call is throttled
    def test_ai_daily_cap(self):
        with Server(**self.env(GUANLAN_AI_DAILY_LIMIT='1')) as s:
            H, O = 'guanlan.example.com', 'https://guanlan.example.com'
            first = s.req('/api/analyze', 'POST', host=H, origin=O, auth=self.CRED, body={'text': 'x'})[0]
            second = s.req('/api/analyze', 'POST', host=H, origin=O, auth=self.CRED, body={'text': 'x'})[0]
            self.assertEqual((first, second), (400, 429))  # first: not configured (no LLM env) → 400; second: capped
    def test_refresh_can_be_disabled(self):
        with Server(**self.env(GUANLAN_DISABLE_REFRESH='1')) as s:
            self.assertEqual(s.req('/api/refresh', 'POST', host='guanlan.example.com', origin='https://guanlan.example.com', auth=self.CRED, body={})[0], 403)

if __name__ == '__main__': unittest.main(verbosity=2)
