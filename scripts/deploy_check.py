#!/usr/bin/env python3
"""观澜部署前自检（任务04候选）。不打印密钥；默认不联网。

  python scripts/deploy_check.py                 # 依赖、配置安全、数据目录
  python scripts/deploy_check.py --memory        # 估算单个行情子进程内存（导入 akshare/pandas）
  python scripts/deploy_check.py --network       # 对上游来源域名做一次轻量连通性检查（不下载正文）
退出码：0 通过；1 有阻断问题。
"""
import argparse, importlib, json, os, re, resource, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))

HOSTS = ['https://push2his.eastmoney.com/', 'https://datacenter-web.eastmoney.com/', 'https://www.cls.cn/', 'https://finance.sina.com.cn/',
         'https://www.sge.com.cn/', 'https://fred.stlouisfed.org/', 'https://www.federalreserve.gov/', 'https://datacenter.jin10.com/']

def pins():
    out = {}
    for line in (ROOT / 'requirements.txt').read_text().splitlines():
        m = re.match(r'\s*([A-Za-z0-9_.-]+)==([^\s;]+)', line)
        if m: out[m[1].lower()] = m[2]
    return out

def check_imports(report):
    mods = {'akshare': 'akshare', 'ta-lib': 'talib', 'feedparser': 'feedparser', 'certifi': 'certifi', 'numpy': 'numpy', 'pandas': 'pandas'}
    pinned = pins()
    for dist, mod in mods.items():
        t0 = time.monotonic()
        try:
            m = importlib.import_module(mod); v = getattr(m, '__version__', '?')
            norm = lambda x: tuple(int(p) if p.isdigit() else p for p in str(x).split('.'))
            ok = dist not in pinned or norm(pinned[dist]) == norm(v)
            report['imports'][dist] = {'version': v, 'pinned': pinned.get(dist), 'matchesPin': ok, 'importSeconds': round(time.monotonic() - t0, 2)}
            if not ok: report['warnings'].append(f'{dist} 实际 {v} 与 requirements 固定的 {pinned[dist]} 不一致')
        except Exception as e:
            report['imports'][dist] = {'error': type(e).__name__}
            report['blocking'].append(f'无法导入 {dist}（{type(e).__name__}）')

def check_config(report):
    import deploy, ai
    report['config'] = {'bind': deploy.BIND, 'port': deploy.PORT, 'dataDir': str(deploy.DATA_DIR), 'allowedHosts': deploy.ALLOWED_HOSTS,
                        'allowedOrigins': deploy.ALLOWED_ORIGINS, 'basicAuth': bool(deploy.BASIC_AUTH), 'aiDisabled': deploy.DISABLE_AI,
                        'aiDailyLimit': deploy.AI_DAILY_LIMIT, 'pricesPerMinute': deploy.PRICE_PER_MINUTE, 'schedule': deploy.SCHEDULE,
                        'trustProxy': deploy.TRUST_PROXY, 'refreshWorkers': deploy.REFRESH_WORKERS, 'aiConfigured': ai.status()['configured']}
    report['blocking'] += deploy.startup_problems()
    if not deploy.is_loopback(deploy.BIND):
        if not deploy.DISABLE_AI and not deploy.AI_DAILY_LIMIT: report['warnings'].append('公开部署开启 AI 但未设置 GUANLAN_AI_DAILY_LIMIT')
        if not deploy.PRICE_PER_MINUTE: report['warnings'].append('公开部署未设置 GUANLAN_PRICES_PER_MINUTE')
        if any(o.startswith('http://') and 'localhost' not in o and '127.0.0.1' not in o for o in deploy.ALLOWED_ORIGINS):
            report['warnings'].append('公网 Origin 使用了 http://，Basic 鉴权凭据会明文传输；请在 HTTPS 之后提供服务')
    if (ROOT / '.env').exists() and not deploy.is_loopback(deploy.BIND):
        report['warnings'].append('镜像/目录中存在 .env；公开部署应改用平台密钥配置')
    try:
        deploy.DATA_DIR.mkdir(parents=True, exist_ok=True); probe = deploy.DATA_DIR / '.write-test'; probe.write_text('ok'); probe.unlink()
        report['config']['dataDirWritable'] = True
    except OSError as e:
        report['config']['dataDirWritable'] = False; report['blocking'].append(f'数据目录不可写：{e.__class__.__name__}')

def check_memory(report):
    code = 'import resource,akshare,pandas;print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)'
    p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=120)
    if p.returncode: report['memory'] = {'error': p.stderr.strip()[-200:]}; return
    kb = int(p.stdout.strip()); mb = kb / 1024 if sys.platform != 'darwin' else kb / 1024 / 1024
    report['memory'] = {'workerImportMB': round(mb), 'refreshPeakEstimateMB': round(mb * __import__('deploy').REFRESH_WORKERS + 80),
                        'note': '刷新并发数=GUANLAN_REFRESH_WORKERS；估算=并发数×单进程导入内存+主进程约80MB，未计算数据处理开销'}

def check_network(report):
    import requests
    report['network'] = {}
    for url in HOSTS:
        t0 = time.monotonic()
        try:
            r = requests.get(url, timeout=8, stream=True); r.close()
            report['network'][url] = {'status': r.status_code, 'ms': int((time.monotonic() - t0) * 1000)}
        except Exception as e:
            report['network'][url] = {'error': type(e).__name__, 'ms': int((time.monotonic() - t0) * 1000)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--memory', action='store_true'); ap.add_argument('--network', action='store_true'); a = ap.parse_args()
    report = {'python': sys.version.split()[0], 'imports': {}, 'blocking': [], 'warnings': []}
    check_imports(report); check_config(report)
    if a.memory: check_memory(report)
    if a.network: check_network(report)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(1 if report['blocking'] else 0)

if __name__ == '__main__': main()
