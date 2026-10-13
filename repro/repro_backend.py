"""任务07 · 后端缺陷复现（不联网、不调用模型；基于 v0.8 交接副本）。
运行：python -m unittest repro.repro_backend -v   （在副本根目录；HTTP 场景需要服务已在 127.0.0.1:8765 运行）
每个测试断言的是**当前（有缺陷的）行为**；应用 candidate.patch 后，对应断言会失败，由 tests/test_audit_regressions.py 接管。
"""
import json, sys, types, unittest, subprocess, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
import ai, prices
import pandas as pd

def post(path, body, raw=None):
    data = raw if raw is not None else json.dumps(body).encode()
    r = urllib.request.Request('http://127.0.0.1:8765' + path, data=data, method='POST', headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8765'})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp: return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())

class Current(unittest.TestCase):
    def test_B1_single_character_quote_passes_verification(self):
        text = '前言\n\n这是一段很长的材料，讨论通缩与信用的关系，以及作者对未来的判断。'
        s = {'node': 'inflation', 'segment': 2, 'quote': '的', 'claim': '任意观点', 'question': 'q', 'counter': 'c', 'keywords': 'k'}
        self.assertEqual(ai.validate({'suggestions': [s]}, text)['suggestions'][0]['quote'], '的')

    def test_B2_non_object_body_gives_misleading_500(self):
        code, body = post('/api/technical', None, raw=b'[1,2]')  # same for /api/analyze once AI is configured
        self.assertEqual(code, 500); self.assertIn('依赖安装', body['error'])

    def test_B3_csv_missing_column_leaks_raw_key_error(self):
        code, body = post('/api/technical', {'csv': 'day,price\n2026-01-02,1\n'})
        self.assertEqual(code, 400); self.assertEqual(body['error'], "'date'")

    def test_B4_nan_close_from_upstream_reaches_csv(self):
        fake = types.ModuleType('akshare')
        fake.stock_zh_a_hist = lambda **k: pd.DataFrame({'日期': ['2026-01-05', '2026-01-06'], '收盘': [10.0, float('nan')], '股票代码': ['300750', '300750']})
        with patch.dict(sys.modules, {'akshare': fake}):
            out = prices.worker({'code': '300750', 'start': '2026-01-01', 'end': '2026-01-31', 'adjustment': '前复权'})
        self.assertIn('2026-01-06,\n', out['csv'])  # empty close written; technical() later fails with a raw float() error

    def test_B6_test_prices_runs_zero_tests_when_executed_directly(self):
        p = subprocess.run([sys.executable, str(ROOT / 'tests' / 'test_prices.py')], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(p.returncode, 0); self.assertNotIn('Ran ', p.stderr + p.stdout)

if __name__ == '__main__': unittest.main(verbosity=2)
