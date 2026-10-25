"""Deterministic HTTP handler contracts; mock peer address, no network/model."""
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import app


class RetrievalHTTPReview(unittest.TestCase):
    def request(self,query='黄金',peer='127.0.0.1'):
        body=json.dumps({'query':query,'materials':[{'id':'a','text':'黄金库存'}]}).encode()
        handler=object.__new__(app.Handler)
        handler.path='/api/retrieve';handler.client_address=(peer,123)
        handler.headers={'Content-Length':str(len(body))};handler.rfile=io.BytesIO(body)
        replies=[];handler.reply=lambda data,status=200:replies.append((status,data))
        handler.host_valid=lambda:True;handler.authorized=lambda:True
        with patch.object(app.deploy,'origin_ok',return_value=True),patch.object(app.deploy,'client_id',return_value='review-peer'):
            handler.do_POST()
        return replies[0]

    def test_non_loopback_is_forbidden(self):
        self.assertEqual(self.request(peer='192.0.2.8')[0],403)

    def test_request_21_is_rate_limited(self):
        with patch.object(app.deploy,'LIMITER',app.deploy.Limiter()):
            self.assertEqual([self.request()[0] for _ in range(21)],[200]*20+[429])

    def test_no_terms_returns_actionable_400(self):
        with patch.object(app.deploy,'LIMITER',app.deploy.Limiter()):
            status,body=self.request('！？🙂')
        self.assertEqual(status,400)
        self.assertIn('没有可用于词法检索的词',body['error'])


if __name__=='__main__':unittest.main()
