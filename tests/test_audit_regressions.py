"""任务07 候选回归测试（后端）。不联网、不调用模型。
python -m unittest tests.test_audit_regressions -v
"""
import json, sys, threading, unittest, urllib.request, urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import ai, app

class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler); cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.httpd.shutdown(); cls.httpd.server_close()
    def post(self, path, raw):
        r = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=raw, method='POST',
            headers={'Host': '127.0.0.1:8765', 'Origin': 'http://127.0.0.1:8765', 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp: return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
    def test_non_object_body_is_400_not_500(self):
        for path in ('/api/technical', '/api/analyze', '/api/prices'):
            code, body = self.post(path, b'[1,2]')
            self.assertEqual(code, 400, path); self.assertIn('JSON 对象', body['error'])
    def test_csv_missing_columns_has_clear_message(self):
        code, body = self.post('/api/technical', json.dumps({'csv': 'day,price\n2026-01-02,1\n'}).encode())
        self.assertEqual(code, 400); self.assertIn('date,close', body['error'])
    def test_csv_bad_row_reports_line_number(self):
        code, body = self.post('/api/technical', json.dumps({'csv': 'date,close\n2026-01-02,1\n2026/01/03,2\n'}).encode())
        self.assertEqual(code, 400); self.assertIn('第 3 行', body['error'])
    def test_csv_header_with_spaces_is_accepted(self):
        rows = '\n'.join(f'2026-01-{d:02d},{d}' for d in range(1, 30))
        code, body = self.post('/api/technical', json.dumps({'csv': ' date , close \n' + rows}).encode())
        self.assertEqual(code, 200); self.assertEqual(body['rows'], 29)

class Quote(unittest.TestCase):
    TEXT = '前言\n\n这是一段很长的材料，讨论通缩与信用的关系，以及作者对未来的判断。'
    def s(self, quote): return {'node': 'inflation', 'segment': 2, 'quote': quote, 'claim': 'c', 'question': 'q', 'counter': 'c', 'keywords': 'k'}
    def test_too_short_quote_rejected(self):
        for q in ('的', '通缩', '  信用 '):
            with self.assertRaisesRegex(ValueError, '过短'): ai.validate({'suggestions': [self.s(q)]}, self.TEXT)
    def test_normal_quote_still_accepted(self):
        self.assertEqual(ai.validate({'suggestions': [self.s('讨论通缩与信用的关系')]}, self.TEXT)['suggestions'][0]['segment'], 2)

if __name__ == '__main__': unittest.main(verbosity=2)
