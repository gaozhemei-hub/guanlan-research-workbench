"""Adapter failure paths with mock workers; no real model/network in routine CI."""
import os
import subprocess
import unittest
from unittest.mock import patch
from server import semantic
from server.retrieval import retrieve_selected

PAYLOAD={'query':'利润', 'method':'vector', 'materials':[{'id':'a','text':'矿企利润需要核查成本。'}]}


class SemanticAdapter(unittest.TestCase):
    def test_missing_environment_never_falls_back(self):
        with patch.dict(os.environ, {'GUANLAN_RAG_PYTHON':'/nonexistent/guanlan-python'}), patch.object(semantic.subprocess,'run') as call:
            with self.assertRaisesRegex(ValueError,'未安装'):
                retrieve_selected(PAYLOAD)
            call.assert_not_called()

    def test_timeout_releases_lock_and_keeps_offline_boundary(self):
        with patch.object(semantic.Path,'is_file',return_value=True), patch.object(semantic.subprocess,'run',side_effect=subprocess.TimeoutExpired('worker',38)) as call:
            with self.assertRaisesRegex(ValueError,'超时'):
                semantic.retrieve(PAYLOAD)
            self.assertEqual(call.call_args.kwargs['env']['HF_HUB_OFFLINE'],'1')
            self.assertNotIn('矿企利润',str(call.call_args.args[0]))
        self.assertFalse(semantic.LOCK.locked())

    def test_worker_failure_does_not_echo_raw_error(self):
        result=subprocess.CompletedProcess([],1,stdout='private source',stderr='private text')
        with patch.object(semantic.Path,'is_file',return_value=True), patch.object(semantic.subprocess,'run',return_value=result):
            with self.assertRaises(ValueError) as error:
                semantic.retrieve(PAYLOAD)
        self.assertNotIn('private',str(error.exception))

    def test_limits_and_unknown_method_do_not_start_worker(self):
        for payload in ({**PAYLOAD,'method':'unknown'}, {**PAYLOAD,'query':'金'*151},
                        {**PAYLOAD,'materials':[{'id':'a','text':'金'*10001}]}):
            with patch.object(semantic,'retrieve') as call:
                with self.assertRaises(ValueError):retrieve_selected(payload)
                call.assert_not_called()

    def test_concurrency_is_bounded(self):
        semantic.LOCK.acquire()
        try:
            with patch.object(semantic.Path,'is_file',return_value=True):
                with self.assertRaisesRegex(ValueError,'其他请求'):semantic.retrieve(PAYLOAD)
        finally:
            semantic.LOCK.release()


if __name__=='__main__':unittest.main()
