"""Loopback-only research dashboard: official public data + reusable parsers.
Run with ../.venv/bin/python app.py. No model or paid-market credentials required.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta, date
import csv, io, json, threading, time, math, argparse, hashlib
import ssl, certifi
import feedparser
import ai
import prices
import deploy
import subprocess, sys
from providers import AK_SOURCES

ROOT = Path(__file__).resolve().parents[1]
CACHE = deploy.DATA_DIR / 'public-cache.json'
LOCK = threading.Lock()
SOURCES = [
    dict(id='DGS10',kind='series',name='美国 10 年期名义国债收益率',unit='%',frequency='日度 · 收盘口径',nodes=['financial'],url='https://fred.stlouisfed.org/series/DGS10',note='名义收益率，不是 DFII10 实际收益率。日度观测不能直接证明播客所述盘中最高值。'),
    dict(id='DFII10', kind='series', name='美国 10 年期实际国债收益率', unit='%', frequency='日度 · 非季调', nodes=['financial','gold'], url='https://fred.stlouisfed.org/series/DFII10'),
    dict(id='T10YIE', kind='series', name='美国 10 年期盈亏平衡通胀率', unit='%', frequency='日度 · 非季调', nodes=['inflation','gold'], url='https://fred.stlouisfed.org/series/T10YIE'),
    dict(id='DTWEXBGS', kind='series', name='美元广义贸易加权指数', unit='2006年1月=100', frequency='日度 · 非季调', nodes=['financial','gold','silver'], url='https://fred.stlouisfed.org/series/DTWEXBGS'),
    dict(id='fed', kind='feed', name='美联储 · 货币政策公告', nodes=['policy','financial','gold'], url='https://www.federalreserve.gov/feeds/press_monetary.xml'),
    dict(id='bls', kind='feed', name='美国劳工统计局 · CPI', nodes=['inflation'], url='https://www.bls.gov/feed/cpi.rss'),
]
SOURCES += AK_SOURCES
def now(): return datetime.now(timezone.utc).isoformat()
def read_cache():
    try: return json.loads(CACHE.read_text())
    except (FileNotFoundError, ValueError): return {'sources': {}, 'checkedAt': None}
STATE = read_cache()

def fetch(source):
    sid = source['id']
    previous = STATE['sources'].get(sid, {})
    result = {**source, 'checkedAt': now()}
    try:
        if source.get('driver') == 'akshare':
            proc = subprocess.run([sys.executable, str(ROOT/'server'/'ak_worker.py'), sid],capture_output=True,text=True,timeout=35)
            data = json.loads(proc.stdout)
            if proc.returncode or data.get('error'): raise ValueError(data.get('error','接口调用失败'))
            result.update(data)
            if source['kind'] == 'feed': result['items'] = merge_items(result['items'], previous.get('items', []))
            result.update(status='ok', fetchedAt=now(), error=None)
            return result
        url = source['url']
        if source['kind'] == 'series':
            since = (date.today() - timedelta(days=180)).isoformat()
            url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={since}'
        with urlopen(Request(url, headers={'User-Agent': 'GuanlanResearch/0.2 (personal local research)'}), timeout=18, context=ssl.create_default_context(cafile=certifi.where())) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000: raise ValueError('响应超过大小限制')
        if source['kind'] == 'series':
            rows = csv.DictReader(io.StringIO(body.decode('utf-8-sig')))
            points = []
            for row in rows:
                if row.get(sid) not in ('', '.', None):
                    value = float(row[sid])
                    if not math.isfinite(value): continue
                    observed = row.get('observation_date', row.get('DATE'))
                    date.fromisoformat(observed)
                    if observed <= date.today().isoformat(): points.append({'date': observed, 'value': value})
            if not points: raise ValueError('未返回有效观察值')
            result['points'] = sorted(points, key=lambda p: p['date'])[-100:]
            result['publishedAt'] = None  # CSV does not include a publication timestamp.
        else:
            parsed = feedparser.parse(body)
            items = []
            for entry in parsed.entries[:50]:
                link = entry.get('link', '')
                if urlparse(link).scheme not in ('http','https'): continue
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                pubdate = datetime(*published[:6], tzinfo=timezone.utc).isoformat() if published else None
                items.append({'id': hashlib.sha256(link.encode()).hexdigest()[:20], 'title': entry.get('title','无标题'), 'url': link, 'publishedAt': pubdate, 'source': source['name'], 'nodes': source['nodes'], 'feedId': sid})
            if not items: raise ValueError('未返回可用新闻条目')
            result['items'] = merge_items(items, previous.get('items', []))
        result.update(status='ok', fetchedAt=now(), error=None)
    except Exception as error:
        result.update({k: v for k, v in previous.items() if k in ('points','items','reports','fields','fetchedAt','publishedAt')})
        result.update(status='stale' if previous.get('fetchedAt') else 'error', error=f'{type(error).__name__}: {str(error)[:180]}')
    return result

def merge_items(current, previous):
    merged={i['id']:i for i in previous}
    for item in current:
        item['firstFetchedAt']=merged.get(item['id'],{}).get('firstFetchedAt',now())
        item['lastSeenAt']=now()
        merged[item['id']]=item
    return sorted(merged.values(), key=lambda i:i.get('publishedAt') or '',reverse=True)[:500]

def refresh():
    global STATE
    if not LOCK.acquire(blocking=False): return False
    try:
        with ThreadPoolExecutor(max_workers=deploy.REFRESH_WORKERS) as pool: results = list(pool.map(fetch, SOURCES))
        STATE = {'sources': {item['id']: item for item in results}, 'checkedAt': now()}
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix('.tmp')
        tmp.write_text(json.dumps(STATE, ensure_ascii=False))
        tmp.replace(CACHE)
    finally: LOCK.release()
    return True

def scheduler():
    while True:
        checked = STATE.get('checkedAt')
        if not checked or any(s['id'] not in STATE['sources'] for s in SOURCES) or datetime.fromisoformat(checked).astimezone().date() < date.today(): refresh()
        time.sleep(60)

def technical(payload):
    import numpy as np
    import talib
    # Preserve adjustment / currency metadata supplied by the user; do not infer it.
    text = payload.get('csv','')
    if not isinstance(text, str) or len(text) > 500_000: raise ValueError('CSV 最大 500 KB')
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not {'date','close'}.issubset({(h or '').strip() for h in (reader.fieldnames or [])}): raise ValueError('CSV 第一行须包含 date,close 两列')
    rows = [{(k or '').strip(): v for k, v in r.items()} for r in reader]
    if not rows or len(rows) > 5000: raise ValueError('需要 1–5000 行 date,close 数据')
    points, seen = [], set()
    for i, row in enumerate(rows, 2):
        try:
            d = date.fromisoformat((row.get('date') or '').strip())
            close = float(row.get('close') or 'nan')
        except ValueError: raise ValueError(f'第 {i} 行日期或收盘价无效（日期须为 YYYY-MM-DD，收盘价须为数字）')
        if d > date.today() or not math.isfinite(close) or close <= 0: raise ValueError('日期不能在未来，收盘价须是正数')
        if d in seen: raise ValueError('存在重复交易日期，请先清理')
        seen.add(d); points.append((d.isoformat(), close))
    points.sort()
    values = np.array([p[1] for p in points], dtype=float)
    def last(arr): return float(arr[-1]) if math.isfinite(arr[-1]) else None
    macd, signal, hist = talib.MACD(values, fastperiod=12, slowperiod=26, signalperiod=9)
    return {'engine': f'TA-Lib {talib.__version__}', 'rows': len(points), 'asOf': points[-1][0], 'firstDate': points[0][0], 'close': points[-1][1], 'ma20': last(talib.SMA(values,20)), 'rsi14': last(talib.RSI(values,14)), 'macd': last(macd), 'signal': last(signal), 'hist': last(hist), 'points': [{'date': d, 'value': v} for d,v in points[-100:]], 'calculatedAt': now()}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT/'prototype'/'dist'), **kwargs)
    def reply(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def end_headers(self):
        for k,v in deploy.SECURITY_HEADERS.items(): self.send_header(k,v)
        super().end_headers()
    def host_valid(self): return deploy.host_ok(self.headers)
    def authorized(self):
        if deploy.auth_ok(self.headers): return True
        body=json.dumps({'error':'需要登录'},ensure_ascii=False).encode()
        self.send_response(401); self.send_header('WWW-Authenticate','Basic realm="guanlan", charset="UTF-8"'); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        return False
    def do_HEAD(self):
        # HEAD must pass the same host/auth checks as GET before static metadata.
        if not self.host_valid(): return self.reply({'error':'Invalid host'},403)
        if not self.authorized(): return
        if self.path.startswith('/api/'): return self.reply({'error':'Not found'},404)
        return super().do_HEAD()
    def do_GET(self):
        if self.path == '/healthz': return self.reply({'ok':True})
        if not self.host_valid(): return self.reply({'error':'Invalid host'},403)
        if not self.authorized(): return
        if self.path == '/api/state': return self.reply({**STATE, 'catalog': SOURCES, 'refreshing': LOCK.locked(), 'mode':'local-public-data', 'schedule':'服务运行期间，每个自然日检查一次；新闻按源保留最多 500 条，失败保留旧值', 'technicalEngine':'TA-Lib', 'ai': deploy.ai_status(ai.status())})
        if self.path.startswith('/api/'): return self.reply({'error':'Not found'},404)
        return super().do_GET()
    def do_POST(self):
        if not self.host_valid() or not deploy.origin_ok(self.headers): return self.reply({'error':'仅允许本地同源请求'},403)
        if not self.authorized(): return
        who = deploy.client_id(self)
        try:
            n = int(self.headers.get('Content-Length','0'))
            if n < 0 or n > 600_000: return self.reply({'error':'请求体过大'},413)
            payload = json.loads(self.rfile.read(n) or b'{}')
            if not isinstance(payload, dict): return self.reply({'error':'请求格式错误：需要 JSON 对象'},400)
            if self.path == '/api/refresh':
                if deploy.DISABLE_REFRESH: return self.reply({'error':'此部署未开放手动刷新'},403)
                if LOCK.locked(): return self.reply({'error':'正在检查，请稍候'},409)
                threading.Thread(target=refresh,daemon=True).start(); return self.reply({'started':True},202)
            if self.path == '/api/analyze':
                if deploy.DISABLE_AI: return self.reply({'error':'此部署未开启 AI 辅助拆解，可继续手动整理'},403)
                if not deploy.LIMITER.allow('ai:global', deploy.AI_DAILY_LIMIT, 86400): return self.reply({'error':'今日 AI 调用额度已用完，可继续手动整理'},429)
                return self.reply(ai.analyze(payload))
            if self.path == '/api/prices':
                if not deploy.LIMITER.allow('prices:'+who, deploy.PRICE_PER_MINUTE, 60): return self.reply({'error':'请求过于频繁，请稍后再试'},429)
                try: quote = prices.fetch(payload)
                except prices.PriceError as error: return self.reply({'error':str(error),'errorCode':error.code,'attempts':error.attempts},502)
                return self.reply({**quote, 'technical': technical({'csv':quote['csv']})})
            if self.path == '/api/technical': return self.reply(technical(payload))
            return self.reply({'error':'Not found'},404)
        except (ValueError, KeyError, TypeError) as error: return self.reply({'error':str(error)},400)
        except Exception: return self.reply({'error':'本地计算失败，请检查依赖安装'},500)
    def log_message(self, fmt, *args): pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--open',action='store_true'); parser.add_argument('--no-schedule',action='store_true'); args=parser.parse_args()
    problems = deploy.startup_problems()
    if problems: sys.exit('拒绝启动：' + '；'.join(problems))
    server = ThreadingHTTPServer((deploy.BIND,deploy.PORT),Handler)
    if not args.no_schedule and deploy.SCHEDULE: threading.Thread(target=scheduler,daemon=True).start()
    print(f'观澜：http://{deploy.BIND}:{deploy.PORT} · Ctrl+C 停止；关闭服务后不会自动抓取。',flush=True)
    if args.open:
        import webbrowser
        webbrowser.open('http://127.0.0.1:8765')
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
