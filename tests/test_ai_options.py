"""任务02候选：服务商参数选项。不联网。python -m unittest tests.test_ai_options -v"""
import json, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import ai
BASE = {'LLM_BASE_URL': 'https://example.com/v1', 'LLM_API_KEY': 'test-key-not-real', 'LLM_MODEL': 'm'}
TEXT = '前言\n\n某种议题可能改变规则，但不能确定。'
S = {'node': 'policy', 'segment': 2, 'quote': '可能改变规则', 'claim': 'c', 'question': 'q', 'counter': 'x', 'keywords': 'k'}
class Fake:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def read(self, *a): return json.dumps({'choices': [{'message': {'content': json.dumps({'suggestions': [S]})}}]}).encode()
def sent_body(cfg):
    with patch.object(ai, 'config', return_value=cfg), patch.object(ai, 'build_opener') as op:
        op.return_value.open.return_value = Fake(); ai.analyze({'text': TEXT})
        return json.loads(op.return_value.open.call_args.args[0].data)
class Options(unittest.TestCase):
    def test_default_unchanged(self):
        b = sent_body(BASE); self.assertEqual(b['max_completion_tokens'], 3500); self.assertNotIn('max_tokens', b)
    def test_max_tokens_and_extra_body(self):
        b = sent_body({**BASE, 'LLM_MAX_TOKENS_PARAM': 'max_tokens', 'LLM_EXTRA_BODY': '{"thinking":{"type":"disabled"}}'})
        self.assertEqual(b['max_tokens'], 3500); self.assertNotIn('max_completion_tokens', b); self.assertEqual(b['thinking'], {'type': 'disabled'})
    def test_invalid_options_rejected_before_network(self):
        for bad in [{'LLM_MAX_TOKENS_PARAM': 'tokens'}, {'LLM_EXTRA_BODY': 'not json'}, {'LLM_EXTRA_BODY': '[1]'}, {'LLM_EXTRA_BODY': '{"model":"other"}'}, {'LLM_EXTRA_BODY': '{"max_tokens":99999}'}]:
            with self.subTest(bad=bad), patch.object(ai, 'config', return_value={**BASE, **bad}), patch.object(ai, 'build_opener') as op:
                with self.assertRaises(ValueError): ai.analyze({'text': TEXT})
                op.assert_not_called()
    def test_env_file_keys_read(self):
        self.assertIn('LLM_EXTRA_BODY', ai.KEYS)
if __name__ == '__main__': unittest.main(verbosity=2)
