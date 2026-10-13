"""Deployment settings for 观澜 (task 04 candidate, based on v0.8 handoff).

Every default reproduces the v0.8 local behaviour: bind 127.0.0.1:8765, only
127.0.0.1/localhost Host headers, same-origin POST, no auth, data under ./data.
A non-loopback bind refuses to start unless server-side auth is configured.
"""
import base64, hmac, ipaddress, os, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _list(name, default):
    raw = os.environ.get(name)
    return [x.strip() for x in raw.split(',') if x.strip()] if raw else default

BIND = os.environ.get('GUANLAN_BIND', '127.0.0.1')
PORT = int(os.environ.get('GUANLAN_PORT') or os.environ.get('PORT') or 8765)
DATA_DIR = Path(os.environ.get('GUANLAN_DATA_DIR') or ROOT / 'data')
ALLOWED_HOSTS = _list('GUANLAN_ALLOWED_HOSTS', [f'127.0.0.1:{PORT}', f'localhost:{PORT}'])
ALLOWED_ORIGINS = _list('GUANLAN_ALLOWED_ORIGINS', [f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'])
BASIC_AUTH = os.environ.get('GUANLAN_BASIC_AUTH', '')          # "user:password", set as a platform secret
DISABLE_AI = os.environ.get('GUANLAN_DISABLE_AI') == '1'
DISABLE_REFRESH = os.environ.get('GUANLAN_DISABLE_REFRESH') == '1'
SCHEDULE = os.environ.get('GUANLAN_SCHEDULE', '1') != '0'  # 0: no daily refresh thread (sleeping PaaS)
TRUST_PROXY = os.environ.get('GUANLAN_TRUST_PROXY') == '1'     # only behind a proxy you control
AI_DAILY_LIMIT = int(os.environ.get('GUANLAN_AI_DAILY_LIMIT', '0'))  # 0 = unlimited (local default)
REFRESH_WORKERS = max(1, int(os.environ.get('GUANLAN_REFRESH_WORKERS', '5')))  # each worker is a python+akshare subprocess
PRICE_PER_MINUTE = int(os.environ.get('GUANLAN_PRICES_PER_MINUTE', '0'))  # 0 = unlimited

def is_loopback(host):
    try: return ipaddress.ip_address(host).is_loopback
    except ValueError: return host == 'localhost'

def startup_problems():
    """Reasons the configuration is unsafe to serve; empty list means OK."""
    problems = []
    if not is_loopback(BIND) and not BASIC_AUTH and os.environ.get('GUANLAN_ALLOW_UNAUTHENTICATED') != '1':
        problems.append('非本机地址监听时必须设置 GUANLAN_BASIC_AUTH（服务端鉴权）；仅在已有外层鉴权时才可设 GUANLAN_ALLOW_UNAUTHENTICATED=1')
    if BASIC_AUTH and (':' not in BASIC_AUTH or len(BASIC_AUTH.split(':', 1)[1]) < 12):
        problems.append('GUANLAN_BASIC_AUTH 格式应为 用户名:密码，密码至少 12 位')
    if not is_loopback(BIND) and any(h.startswith(('127.0.0.1', 'localhost')) for h in ALLOWED_HOSTS) and not os.environ.get('GUANLAN_ALLOWED_HOSTS'):
        problems.append('公开部署需设置 GUANLAN_ALLOWED_HOSTS / GUANLAN_ALLOWED_ORIGINS 为实际域名')
    return problems

def host_ok(headers): return headers.get('Host') in ALLOWED_HOSTS
def origin_ok(headers): return headers.get('Origin') in ALLOWED_ORIGINS

def auth_ok(headers):
    if not BASIC_AUTH: return True
    value = headers.get('Authorization', '')
    if not value.startswith('Basic '): return False
    try: supplied = base64.b64decode(value[6:], validate=True).decode('utf-8')
    except Exception: return False
    return hmac.compare_digest(supplied.encode(), BASIC_AUTH.encode())

def client_id(handler):
    if TRUST_PROXY:
        forwarded = handler.headers.get('X-Forwarded-For', '')
        if forwarded: return forwarded.split(',')[0].strip()
    return handler.client_address[0]

class Limiter:
    """In-memory, per-process. Resets on restart; good enough for one small instance."""
    def __init__(self): self.lock = threading.Lock(); self.events = {}
    def allow(self, key, limit, window, now=None):
        if limit <= 0: return True
        now = time.time() if now is None else now
        with self.lock:
            recent = [t for t in self.events.get(key, []) if now - t < window]
            if len(recent) >= limit: self.events[key] = recent; return False
            recent.append(now); self.events[key] = recent; return True
LIMITER = Limiter()

def ai_status(status):
    return {**status, 'configured': False, 'disabled': True} if DISABLE_AI else status

SECURITY_HEADERS = {'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY'}
