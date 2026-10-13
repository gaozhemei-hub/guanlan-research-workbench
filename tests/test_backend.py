"""Deterministic contract tests. No network/model calls or private sources."""
import sys, unittest, json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import app, ai

class Contracts(unittest.TestCase):
    def test_talib_actual_calculation(self):
        from datetime import date,timedelta
        data='date,close\n'+'\n'.join(f'{date(2026,1,1)+timedelta(days=i)},{100+i}' for i in range(50))
        r=app.technical({'csv':data})
        self.assertEqual(r['rows'],50); self.assertEqual(r['close'],149)
        self.assertEqual(r['ma20'],139.5); self.assertEqual(r['rsi14'],100)
        self.assertAlmostEqual(r['hist'],r['macd']-r['signal'])
    def test_insufficient_sample_is_null(self):
        r=app.technical({'csv':'date,close\n2026-01-01,5'})
        self.assertIsNone(r['ma20']); self.assertIsNone(r['rsi14']); self.assertIsNone(r['macd'])
    def test_price_input_validation(self):
        for rows in ['2026-01-01,5\n2026-01-01,6','2026-01-01,nan','2026-01-01,-2','2099-01-01,2','wrong,3']:
            with self.assertRaises(ValueError): app.technical({'csv':'date,close\n'+rows})
    def test_failed_fetch_preserves_old_observations(self):
        s=app.SOURCES[0]; old={'fetchedAt':'2026-01-01T00:00:00Z','points':[{'date':'2025-12-31','value':1.2}]}
        with patch.dict(app.STATE,{'sources':{s['id']:old}}),patch.object(app,'urlopen',side_effect=TimeoutError('test')):
            r=app.fetch(s)
        self.assertEqual(r['status'],'stale');self.assertEqual(r['points'],old['points']);self.assertEqual(r['fetchedAt'],old['fetchedAt']);self.assertNotEqual(r['checkedAt'],old['fetchedAt'])
    def suggestion(self):
        return {'node':'policy','segment':2,'quote':'可能改变规则','claim':'讨论者提出一种可能性','question':'是否进入正式议程？','counter':'没有落地或被反向规则抵消','keywords':'policy,规则'}
    def test_ai_valid_quote_and_structure(self):
        result=ai.validate({'suggestions':[self.suggestion()]},'前言\n\n某种议题可能改变规则，但不能确定。')
        self.assertEqual(result['suggestions'][0]['segment'],2)
    def test_ai_hallucinated_quote_node_or_segment_rejected(self):
        for key,value in [('quote','一定会改变规则'),('segment',3),('segment',True),('node','nonexistent'),('claim','')]:
            s=self.suggestion();s[key]=value
            with self.assertRaises(ValueError): ai.validate({'suggestions':[s]},'前言\n\n某种议题可能改变规则，但不能确定。')
    def test_ai_missing_config_does_not_call_network(self):
        with patch.object(ai,'config',return_value={}),patch.object(ai,'build_opener') as network:
            with self.assertRaises(ValueError): ai.analyze({'text':'材料'})
            network.assert_not_called()
    def test_ai_adapter_contract_with_mock_response(self):
        response={'choices':[{'message':{'content':json.dumps({'suggestions':[self.suggestion()]})}}]}
        class Fake:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,*args): return json.dumps(response).encode()
        with patch.object(ai,'config',return_value={'LLM_BASE_URL':'https://example.com/v1','LLM_API_KEY':'test-key-not-real','LLM_MODEL':'test-model'}),patch.object(ai,'build_opener') as opener:
            opener.return_value.open.return_value=Fake()
            r=ai.analyze({'text':'前言\n\n某种议题可能改变规则，但不能确定。'})
            request=opener.return_value.open.call_args.args[0]
            body=json.loads(request.data)
            self.assertEqual(request.full_url,'https://example.com/v1/chat/completions')
            self.assertNotIn('test-key-not-real',json.dumps(body))
            self.assertEqual(r['model'],'test-model')
            self.assertEqual(body['response_format'],{'type':'json_object'})

if __name__=='__main__':unittest.main(verbosity=2)
