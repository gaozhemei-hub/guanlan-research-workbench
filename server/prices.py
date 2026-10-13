"""Bounded daily-price requests for the five verified sample codes.

Candidate (task 01, based on v0.8 handoff): adds an explicit error contract,
per-attempt diagnostics, an optional ordered provider list, and stricter
response validation. Behaviour with GUANLAN_PRICE_PROVIDERS=eastmoney is the same request as v0.8;
the default is tencent first, eastmoney second (see 01 report, probe results).
"""
from datetime import date,timedelta
from pathlib import Path
import json,sys,subprocess,hashlib,math,os,time,threading
from datetime import datetime
import os
CACHE_DIR=Path(os.environ.get('GUANLAN_DATA_DIR') or Path(__file__).resolve().parents[1]/'data')/'price-cache'
from providers import AK_SOURCES
ADJUSTMENTS={'前复权':'qfq','后复权':'hfq','不复权':''}
WORKER_TIMEOUT=40
# One live upstream price request per service process: concurrent bursts to the
# same host are a suspected trigger for upstream throttling (see report E3).
_FETCH_LOCK=threading.Lock()

# Ordered list of public daily-price adapters. Each request is served by ONE
# provider end-to-end; series are never stitched across providers.
PROVIDER_META={
 'eastmoney':{'source':'东方财富历史日线 / AKShare','url':lambda m,c:f'https://quote.eastmoney.com/{m}{c}.html'},
 'tencent':{'source':'腾讯证券历史日线 / AKShare','url':lambda m,c:f'https://gu.qq.com/{m}{c}'},
}
def provider_order():
    # Default chosen from the 2026-10-12 probe on the owner's Mac: Tencent 30/30, Eastmoney 9/30,
    # identical closes on all 9 comparable series. Override with GUANLAN_PRICE_PROVIDERS.
    raw=os.environ.get('GUANLAN_PRICE_PROVIDERS','tencent,eastmoney')
    order=[p.strip() for p in raw.split(',') if p.strip() in PROVIDER_META]
    return list(dict.fromkeys(order)) or ['tencent','eastmoney']

class PriceError(ValueError):
    """User-facing failure with a stable machine code. str(e) stays Chinese UI text."""
    def __init__(self,code,message,attempts=None):
        super().__init__(message);self.code=code;self.attempts=attempts or []

USER_MESSAGES={
 'upstream_proxy':'连接公开行情时经过的代理出错（已重试），原记录未变。请检查本机代理/VPN设置，或稍后重试、导入有来源的CSV',
 'upstream_connect':'公开行情服务器断开或拒绝连接（已重试），原记录未变；可能是来源限流或网络问题，可稍后重试或导入有来源的CSV',
 'upstream_timeout':'公开行情响应超时（已重试），原记录未变；可稍后重试或导入CSV',
 'upstream_tls':'与公开行情建立加密连接失败，原记录未变；请检查网络环境或代理证书',
 'upstream_bad_payload':'公开行情返回了无法识别的内容（可能是验证页或接口变更），原记录未变',
 'upstream_empty':'所选区间没有有效行情，请检查日期或改用CSV',
 'upstream_invalid_data':'公开行情返回的数据未通过校验（日期、重复或价格无效），原记录未变',
 'busy':'另一条行情请求仍在进行，请等它完成后再试；原记录未变',
 'worker_timeout':'公开行情获取超时，原记录未变；可稍后重试或导入CSV',
 'worker_crash':'行情接口未返回有效结果，原记录未变',
}

def validate(payload):
    if not isinstance(payload,dict):raise ValueError('价格请求格式错误')
    code=payload.get('code')
    if not isinstance(code,str):raise ValueError('此代码尚未支持公开价格获取，请使用有来源的CSV')
    source=next((s for s in AK_SOURCES if s['kind']=='financial' and s['symbol'].split('.')[0]==code),None)
    if not source:raise ValueError('此代码尚未支持公开价格获取，请使用有来源的CSV')
    adjustment=payload.get('adjustment')
    if not isinstance(adjustment,str) or adjustment not in ADJUSTMENTS:raise ValueError('请选择前复权、后复权或不复权')
    try:start=date.fromisoformat(payload['start']);end=date.fromisoformat(payload['end'])
    except (KeyError,ValueError,TypeError):raise ValueError('请选择有效开始与结束日期')
    if start>end or (end-start).days>730 or end>=date.today():raise ValueError('开始日不能晚于结束日，区间最多730天；结束日须早于今天，避免未收盘数据')
    return source,start,end,adjustment

def cache_path(code,start,end,adjustment):
    identity=json.dumps([code,start.isoformat(),end.isoformat(),adjustment])
    return CACHE_DIR/(hashlib.sha256(identity.encode()).hexdigest()+'.json')

def read_cache(cache):
    try:
        previous=json.loads(cache.read_text(encoding='utf8'))
        datetime.fromisoformat(previous['fetchedAt'])
        if not isinstance(previous.get('csv'),str):return None
        return previous
    except (OSError,ValueError,KeyError,TypeError):return None

def fetch(payload):
    source,start,end,adjustment=validate(payload)
    cache=cache_path(payload['code'],start,end,adjustment)
    previous=read_cache(cache)
    force=payload.get('force') is True  # 'false' strings must not force a refresh
    if previous and not force and datetime.fromisoformat(previous['fetchedAt']).astimezone().date()==date.today():
        return {**previous,'cacheState':'same-day-cache'}
    clean={'code':payload['code'],'start':start.isoformat(),'end':end.isoformat(),'adjustment':adjustment}
    if not _FETCH_LOCK.acquire(timeout=3):
        if previous:return {**previous,'cacheState':'stale','refreshError':USER_MESSAGES['busy'],'refreshErrorCode':'busy'}
        raise PriceError('busy',USER_MESSAGES['busy'])
    try:
        try:
            proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker'],input=json.dumps(clean),text=True,capture_output=True,timeout=WORKER_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise PriceError('worker_timeout',USER_MESSAGES['worker_timeout'])
        try:data=json.loads(proc.stdout)
        except json.JSONDecodeError:raise PriceError('worker_crash',USER_MESSAGES['worker_crash'])
        if proc.returncode or data.get('error'):
            code=data.get('errorCode','worker_crash')
            raise PriceError(code,data.get('error') or USER_MESSAGES.get(code,USER_MESSAGES['worker_crash']),data.get('attempts'))
        CACHE_DIR.mkdir(parents=True,exist_ok=True)
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w',dir=CACHE_DIR,delete=False,encoding='utf8') as f:
            f.write(json.dumps(data,ensure_ascii=False));temporary=Path(f.name)
        temporary.replace(cache)
        return {**data,'cacheState':'fresh'}
    except PriceError as error:
        if previous:
            return {**previous,'cacheState':'stale','refreshError':'本次公开行情更新失败；以下是同代码、区间和复权口径的旧缓存，查看原获取时间。','refreshErrorCode':error.code,'refreshAttempts':error.attempts}
        raise
    finally:_FETCH_LOCK.release()

# ---------------------------------------------------------------- worker side
def classify_exception(error):
    """Map a requests/akshare exception to a stable code. Order matters:
    ProxyError and SSLError are ConnectionError subclasses; JSONDecodeError is a
    RequestException subclass in requests>=2.27 but means a non-JSON body."""
    import requests
    ex=requests.exceptions
    if isinstance(error,ex.ProxyError):return 'upstream_proxy'
    if isinstance(error,ex.SSLError):return 'upstream_tls'
    if isinstance(error,(ex.ConnectTimeout,ex.ReadTimeout,ex.Timeout)):return 'upstream_timeout'
    if isinstance(error,(ex.JSONDecodeError,json.JSONDecodeError)):return 'upstream_bad_payload'
    if isinstance(error,ex.ConnectionError):return 'upstream_connect'
    if isinstance(error,ex.RequestException):return 'upstream_connect'
    if isinstance(error,(KeyError,IndexError,TypeError,AttributeError)):return 'upstream_bad_payload'
    return 'upstream_bad_payload'

RETRYABLE={'upstream_proxy','upstream_connect','upstream_timeout'}

def proxy_summary(url):
    """Which proxy requests will use for url — scheme://host:port only, never credentials."""
    try:
        import requests
        from urllib.parse import urlsplit
        proxies=requests.utils.get_environ_proxies(url)
        p=proxies.get('https') or proxies.get('all')
        if not p:return 'direct'
        parts=urlsplit(p if '://' in p else 'http://'+p)
        return f'{parts.scheme}://{parts.hostname}:{parts.port or ""}'
    except Exception:return 'unknown'

def fetch_eastmoney(ak,code,start,end,adjust):
    df=ak.stock_zh_a_hist(symbol=code,period='daily',start_date=start.strftime('%Y%m%d'),end_date=end.strftime('%Y%m%d'),adjust=adjust,timeout=12)
    if df.empty:return []
    if not {'日期','收盘'}.issubset(df.columns):raise KeyError('missing columns')
    # NOTE: akshare fills 股票代码 from the requested symbol, so it cannot prove
    # the upstream returned the requested security; do not rely on it.
    return list(zip(df['日期'],df['收盘']))

def fetch_tencent(ak,code,start,end,adjust):
    df=ak.stock_zh_a_hist_tx(symbol=code,start_date=start.strftime('%Y%m%d'),end_date=end.strftime('%Y%m%d'),adjust=adjust,timeout=12)
    if df.empty:return []
    if not {'date','close'}.issubset(df.columns):raise KeyError('missing columns')
    return list(zip(df['date'],df['close']))

ADAPTERS={'eastmoney':fetch_eastmoney,'tencent':fetch_tencent}

def check_rows(rows,start,end):
    """Return sorted (iso_date, close) or raise PriceError('upstream_invalid_data'/'upstream_empty')."""
    if not rows:raise PriceError('upstream_empty',USER_MESSAGES['upstream_empty'])
    out,seen=[],set()
    for raw_date,raw_close in rows:
        try:
            d=date.fromisoformat(str(raw_date)[:10]);close=float(raw_close)
        except (TypeError,ValueError):raise PriceError('upstream_invalid_data',USER_MESSAGES['upstream_invalid_data'])
        if d<start or d>end:raise PriceError('upstream_invalid_data','返回行情超出请求区间')
        if d in seen:raise PriceError('upstream_invalid_data','返回行情存在重复交易日，原记录未变')
        if not math.isfinite(close) or close<=0:raise PriceError('upstream_invalid_data','返回行情含缺失或非正收盘价，原记录未变')
        seen.add(d);out.append((d.isoformat(),close))
    return sorted(out)

def worker(payload):
    source,start,end,adjustment=validate(payload)
    import ak_worker  # applies bounded requests and removes unsolicited tracking cookies
    import akshare as ak
    code=payload['code'];market=source['symbol'].split('.')[1].lower()
    attempts=[];last=None
    for provider in provider_order():
        probe_url={'eastmoney':'https://push2his.eastmoney.com/','tencent':'https://proxy.finance.qq.com/'}[provider]
        for attempt in range(2):
            t0=time.monotonic()
            try:
                rows=check_rows(ADAPTERS[provider](ak,code,start,end,ADJUSTMENTS[adjustment]),start,end)
            except PriceError as error:
                attempts.append({'provider':provider,'errorCode':error.code,'elapsedMs':int((time.monotonic()-t0)*1000)})
                last=error;break  # data problems are not retried on the same provider
            except Exception as error:
                code_=classify_exception(error)
                attempts.append({'provider':provider,'errorCode':code_,'exception':type(error).__name__,'proxy':proxy_summary(probe_url),'elapsedMs':int((time.monotonic()-t0)*1000)})
                last=PriceError(code_,USER_MESSAGES[code_])
                if code_ in RETRYABLE and attempt==0:time.sleep(1);continue
                break
            else:
                from datetime import timezone
                attempts.append({'provider':provider,'ok':True,'elapsedMs':int((time.monotonic()-t0)*1000)})
                csv='date,close\n'+''.join(f'{d},{c}\n' for d,c in rows)
                meta=PROVIDER_META[provider]
                return {'csv':csv,'code':code,'company':source['company'],'adjustment':adjustment,'currency':'CNY','provider':provider,'source':meta['source'],'sourceURL':meta['url'](market,code),'fetchedAt':datetime.now(timezone.utc).isoformat(),'requestedStart':start.isoformat(),'requestedEnd':end.isoformat(),'actualStart':rows[0][0],'actualEnd':rows[-1][0],'rows':len(rows),'attempts':attempts}
    last=last or PriceError('worker_crash',USER_MESSAGES['worker_crash'])
    last.attempts=attempts
    raise last

if __name__=='__main__':
    import contextlib
    try:
        payload=json.load(sys.stdin)
        with contextlib.redirect_stdout(sys.stderr):result=worker(payload)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
    except PriceError as e:
        print(json.dumps({'error':str(e),'errorCode':e.code,'attempts':e.attempts},ensure_ascii=False));sys.exit(1)
    except ValueError as e:
        print(json.dumps({'error':str(e)[:200],'errorCode':'invalid_request'},ensure_ascii=False));sys.exit(1)
    except Exception as e:
        print(json.dumps({'error':USER_MESSAGES['worker_crash'],'errorCode':'worker_crash','exception':type(e).__name__},ensure_ascii=False));sys.exit(1)
