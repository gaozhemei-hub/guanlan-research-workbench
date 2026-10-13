"""Candidate tests for task 01 (price adapter, error contract, cache states).
No network: akshare is replaced with a fake module. Run:
    python3 -m unittest tests.test_prices_candidate -v
"""
import unittest,sys,json,os,types,tempfile,subprocess,textwrap
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
SERVER=Path(__file__).resolve().parents[1]/'server'
sys.path.insert(0,str(SERVER))
import pandas as pd
import requests
import prices

def em_df(rows):return pd.DataFrame([{'日期':d,'股票代码':'300750','收盘':c} for d,c in rows])
def tx_df(rows):return pd.DataFrame([{'date':d,'close':c} for d,c in rows])
GOOD=[('2026-01-05',100.0),('2026-01-06',101.5),('2026-01-07',99.9)]

class FakeAk(types.ModuleType):
    def __init__(self,em=None,tx=None):
        super().__init__('akshare');self.em=list(em or []);self.tx=list(tx or []);self.calls=[]
    def _next(self,queue,name):
        self.calls.append(name);item=queue.pop(0) if queue else Exception('no more fake responses')
        if isinstance(item,BaseException):raise item
        return item
    def stock_zh_a_hist(self,**k):return self._next(self.em,'em')
    def stock_zh_a_hist_tx(self,**k):return self._next(self.tx,'tx')

class Base(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.addCleanup(self.dir.cleanup)
        p=patch.object(prices,'CACHE_DIR',Path(self.dir.name));p.start();self.addCleanup(p.stop)
        s=patch.object(prices.time,'sleep',lambda *_:None);s.start();self.addCleanup(s.stop)
    def payload(self,**k):return {'code':'300750','start':'2026-01-01','end':'2026-01-31','adjustment':'前复权',**k}
    def run_worker(self,fake,providers='eastmoney',env=None):
        with patch.dict(sys.modules,{'akshare':fake}),patch.dict(os.environ,{'GUANLAN_PRICE_PROVIDERS':providers,**(env or {})}):
            return prices.worker(self.payload())

class Classification(unittest.TestCase):
    def test_order_of_subclasses(self):
        ex=requests.exceptions
        cases={ex.ProxyError('x'):'upstream_proxy',ex.SSLError('x'):'upstream_tls',ex.ConnectTimeout('x'):'upstream_timeout',
               ex.ReadTimeout('x'):'upstream_timeout',ex.JSONDecodeError('Expecting value','<html>',0):'upstream_bad_payload',
               ex.ConnectionError('Connection aborted. RemoteDisconnected'):'upstream_connect',KeyError('data'):'upstream_bad_payload'}
        for error,code in cases.items():
            with self.subTest(error=type(error).__name__):self.assertEqual(prices.classify_exception(error),code)

class Worker(Base):
    def test_success_reports_actual_window_and_provider(self):
        out=self.run_worker(FakeAk(em=[em_df(GOOD)]))
        self.assertEqual((out['provider'],out['rows'],out['actualStart'],out['actualEnd']),('eastmoney',3,'2026-01-05','2026-01-07'))
        self.assertTrue(out['csv'].startswith('date,close\n2026-01-05,100.0'))
    def test_proxy_error_retried_once_and_credentials_never_reported(self):
        fake=FakeAk(em=[requests.exceptions.ProxyError('p'),requests.exceptions.ProxyError('p')])
        with self.assertRaises(prices.PriceError) as cm:
            self.run_worker(fake,env={'HTTPS_PROXY':'http://alice:s3cret@127.0.0.1:7890','https_proxy':'http://alice:s3cret@127.0.0.1:7890','NO_PROXY':'','no_proxy':''})
        e=cm.exception;self.assertEqual(e.code,'upstream_proxy');self.assertEqual(fake.calls,['em','em'])
        dumped=json.dumps(e.attempts)
        self.assertIn('127.0.0.1:7890',dumped);self.assertNotIn('s3cret',dumped);self.assertNotIn('alice',dumped)
    def test_bad_payload_not_retried_on_same_provider(self):
        fake=FakeAk(em=[requests.exceptions.JSONDecodeError('Expecting value','<html>captcha',0)])
        with self.assertRaises(prices.PriceError) as cm:self.run_worker(fake)
        self.assertEqual(cm.exception.code,'upstream_bad_payload');self.assertEqual(fake.calls,['em'])
    def test_fallback_serves_whole_series_from_second_provider(self):
        err=requests.exceptions.ConnectionError('RemoteDisconnected')
        fake=FakeAk(em=[err,err],tx=[tx_df(GOOD)])
        out=self.run_worker(fake,'eastmoney,tencent')
        self.assertEqual(out['provider'],'tencent');self.assertIn('腾讯',out['source'])
        self.assertEqual([a.get('errorCode') for a in out['attempts']],['upstream_connect','upstream_connect',None])
    def test_default_order_is_tencent_then_eastmoney(self):
        env={k:v for k,v in os.environ.items() if k!='GUANLAN_PRICE_PROVIDERS'}
        with patch.dict(os.environ,env,clear=True):self.assertEqual(prices.provider_order(),['tencent','eastmoney'])
        err=requests.exceptions.ConnectionError('x')
        fake=FakeAk(em=[em_df(GOOD)],tx=[err,err])
        with patch.dict(sys.modules,{'akshare':fake}),patch.dict(os.environ,env,clear=True):out=prices.worker(self.payload())
        self.assertEqual(out['provider'],'eastmoney');self.assertEqual(fake.calls,['tx','tx','em'])
    def test_eastmoney_only_setting_never_calls_tencent(self):
        err=requests.exceptions.ConnectionError('x')
        fake=FakeAk(em=[err,err],tx=[tx_df(GOOD)])
        with self.assertRaises(prices.PriceError):self.run_worker(fake)
        self.assertNotIn('tx',fake.calls)
    def test_invalid_rows_rejected_not_retried(self):
        for name,rows,msg in [('nan',[('2026-01-05',float('nan'))],'缺失'),('zero',[('2026-01-05',0)],'非正'),
                              ('dup',[('2026-01-05',1),('2026-01-05',2)],'重复'),('outside',[('2025-12-31',1)],'超出')]:
            with self.subTest(name):
                fake=FakeAk(em=[em_df(rows)])
                with self.assertRaisesRegex(prices.PriceError,msg) as cm:self.run_worker(fake)
                self.assertEqual(cm.exception.code,'upstream_invalid_data');self.assertEqual(fake.calls,['em'])
    def test_empty_is_its_own_code(self):
        with self.assertRaises(prices.PriceError) as cm:self.run_worker(FakeAk(em=[pd.DataFrame()]))
        self.assertEqual(cm.exception.code,'upstream_empty')

class FetchContract(Base):
    def ok(self,fetched=None):
        return subprocess.CompletedProcess([],0,json.dumps({'csv':'date,close\n2026-01-05,1\n','fetchedAt':fetched or datetime.now(timezone.utc).isoformat(),'provider':'eastmoney'}))
    def test_string_false_does_not_force(self):
        with patch.object(prices.subprocess,'run',return_value=self.ok()) as run:
            prices.fetch(self.payload());out=prices.fetch(self.payload(force='false'))
        self.assertEqual(out['cacheState'],'same-day-cache');self.assertEqual(run.call_count,1)
    def test_worker_receives_only_validated_fields(self):
        with patch.object(prices.subprocess,'run',return_value=self.ok()) as run:prices.fetch(self.payload(force=True,extra='<script>'))
        sent=json.loads(run.call_args.kwargs['input'])
        self.assertEqual(set(sent),{'code','start','end','adjustment'})
    def test_stale_fallback_carries_error_code_and_original_time(self):
        old=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        with patch.object(prices.subprocess,'run',return_value=self.ok(old)):prices.fetch(self.payload())
        failed=subprocess.CompletedProcess([],1,json.dumps({'error':'x','errorCode':'upstream_proxy','attempts':[{'provider':'eastmoney','errorCode':'upstream_proxy'}]}))
        with patch.object(prices.subprocess,'run',return_value=failed):out=prices.fetch(self.payload())
        self.assertEqual((out['cacheState'],out['fetchedAt'],out['refreshErrorCode']),('stale',old,'upstream_proxy'))
    def test_no_cache_failure_raises_coded_error(self):
        failed=subprocess.CompletedProcess([],1,json.dumps({'error':'代理出错','errorCode':'upstream_proxy'}))
        with patch.object(prices.subprocess,'run',return_value=failed):
            with self.assertRaises(prices.PriceError) as cm:prices.fetch(self.payload())
        self.assertEqual(cm.exception.code,'upstream_proxy')
    def test_corrupt_cache_is_ignored_then_replaced(self):
        c=prices.cache_path('300750',*[datetime.fromisoformat(x).date() for x in ('2026-01-01','2026-01-31')],'前复权')
        c.write_text('{not json')
        with patch.object(prices.subprocess,'run',return_value=self.ok()):self.assertEqual(prices.fetch(self.payload())['cacheState'],'fresh')
        self.assertIn('csv',json.loads(c.read_text()))
    def test_worker_timeout_code(self):
        with patch.object(prices.subprocess,'run',side_effect=subprocess.TimeoutExpired('w',40)):
            with self.assertRaises(prices.PriceError) as cm:prices.fetch(self.payload())
        self.assertEqual(cm.exception.code,'worker_timeout');self.assertIn('超时',str(cm.exception))
    def test_concurrent_request_gets_busy_not_second_upstream_call(self):
        prices._FETCH_LOCK.acquire()
        try:
            with patch.object(prices.subprocess,'run') as run:
                with self.assertRaises(prices.PriceError) as cm:prices.fetch(self.payload())
            self.assertEqual(cm.exception.code,'busy');run.assert_not_called()
        finally:prices._FETCH_LOCK.release()
    def test_same_day_cache_served_even_while_busy(self):
        with patch.object(prices.subprocess,'run',return_value=self.ok()):prices.fetch(self.payload())
        prices._FETCH_LOCK.acquire()
        try:self.assertEqual(prices.fetch(self.payload())['cacheState'],'same-day-cache')
        finally:prices._FETCH_LOCK.release()

class RealSubprocessContract(Base):
    """Runs the actual worker subprocess with a fake akshare package on PYTHONPATH."""
    def test_subprocess_json_contract(self):
        fake=Path(self.dir.name)/'fakepkgs'/'akshare';fake.mkdir(parents=True)
        (fake/'__init__.py').write_text(textwrap.dedent('''
            import requests
            def stock_zh_a_hist(**k): raise requests.exceptions.ProxyError("boom")
        '''))
        env={**os.environ,'PYTHONPATH':str(fake.parent),'GUANLAN_PRICE_PROVIDERS':'eastmoney'}
        proc=subprocess.run([sys.executable,str(SERVER/'prices.py'),'worker'],input=json.dumps({'code':'300750','start':'2026-01-01','end':'2026-01-31','adjustment':'前复权'}),text=True,capture_output=True,timeout=60,env=env)
        out=json.loads(proc.stdout)
        self.assertEqual(proc.returncode,1);self.assertEqual(out['errorCode'],'upstream_proxy');self.assertEqual(len(out['attempts']),2)

if __name__=='__main__':unittest.main(verbosity=2)
