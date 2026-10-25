"""SIMULATED MODELS: actual worker subprocess with fake torch/transformers.

Process-cleanup cases use a sleeping fake worker, not model inference.
"""
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
from server import semantic
from server.retrieval import retrieve_selected

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures/semantic_models'


class WorkerProcess(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.log=self.directory/'models.jsonl'
        self.wrapper=self.directory/'python-wrapper'
        self.wrapper.write_text('#!/bin/sh\nexport PYTHONPATH='+shlex.quote(str(FIXTURES))+'\n'+shlex.quote(sys.executable)+' "$@"\n')
        self.wrapper.chmod(0o700)
        self.env=patch.dict(os.environ,{'GUANLAN_RAG_PYTHON':str(self.wrapper),'FAKE_MODEL_LOG':str(self.log)})
        self.env.start();self.addCleanup(self.env.stop)

    def payload(self,mode='vector',text='黄金👩\u200d🔬库存\r\n\r\n白银需求'):
        return {'method':mode,'query':'库存','materials':[{'id':'a','text':text}]}

    def test_vector_and_reranked_offsets_metadata_and_loading_contract(self):
        for mode in ('vector','reranked'):
            with self.subTest(mode=mode):
                p=self.payload(mode);result=retrieve_selected(p)
                self.assertTrue(result['hits'])
                self.assertIsNone(result['generated_answer'])
                for hit in result['hits']:
                    self.assertEqual(p['materials'][0]['text'][hit['start']:hit['end']],hit['text'])
                    self.assertIsInstance(hit['metadata'],dict)
        loads=[json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertIn('CrossEncoder',{load['class'] for load in loads})
        for load in loads:
            self.assertTrue(load['kwargs']['local_files_only'])
            self.assertFalse(load['kwargs']['trust_remote_code'])
            expected='1427fd652930e4ba29e8149678df786c240d8825' if load['class']=='CrossEncoder' else '7999e1d3359715c523056ef9478215996d62a620'
            self.assertEqual(load['kwargs']['revision'],expected)

    def test_100_paragraphs_succeed_101_never_launches_model(self):
        result=retrieve_selected(self.payload(text='\r\n'.join(['黄金库存']*100)))
        self.assertTrue(result['hits'])
        previous=self.log.read_text()
        with self.assertRaisesRegex(ValueError,'段落.*100|100.*段'):
            retrieve_selected(self.payload(text='\r\n'.join(['黄金库存']*101)))
        self.assertEqual(self.log.read_text(),previous)

    def test_reranker_token_budget_has_specific_error(self):
        p=self.payload('reranked','金'*382);p['query']='金'*150
        with self.assertRaisesRegex(ValueError,'token.*超|超.*token'):
            retrieve_selected(p)

    def test_missing_model_is_not_a_budget_error(self):
        with patch.dict(os.environ,{'FAKE_MODEL_FAILURE':'missing'}):
            with self.assertRaisesRegex(ValueError,'依赖或模型缺失'):
                retrieve_selected(self.payload())

    def test_other_error_has_safe_distinct_message(self):
        with patch.dict(os.environ,{'FAKE_MODEL_FAILURE':'other'}):
            with self.assertRaisesRegex(ValueError,'处理失败') as error:
                retrieve_selected(self.payload())
        self.assertNotIn('private',str(error.exception))

    def test_direct_worker_chunk_overflow_emits_fixed_code(self):
        env={**os.environ,'PYTHONPATH':str(FIXTURES),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
        p=self.payload(text='\n'.join(['黄金']*101))
        result=subprocess.run([str(self.wrapper),str(ROOT/'server/semantic_worker.py')],input=json.dumps(p),text=True,capture_output=True,env=env,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout),{'error_code':'CHUNK_LIMIT'})

    def group_live(self,pgid):
        result=subprocess.run([shutil.which('ps') or '/bin/ps','-axo','pid=,pgid=,stat='],capture_output=True,text=True,check=True)
        return [line for line in result.stdout.splitlines() if (parts:=line.split()) and len(parts)>=3 and int(parts[1])==pgid and not parts[2].startswith('Z')]

    def cleanup_case(self,normal=False,no_ps=False,unexpected=False):
        pidfile=self.directory/'process.json'
        sleeper=self.directory/'sleeper.py'
        sleeper.write_text('import os,json,signal,time\nfrom pathlib import Path\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nPath('+repr(str(pidfile))+').write_text(json.dumps({"pid":os.getpid(),"pgid":os.getpgid(0)}))\ntime.sleep(60)\n')
        command=shlex.quote(sys.executable)+' '+shlex.quote(str(sleeper))
        if normal:
            self.wrapper.write_text('#!/bin/sh\n'+command+' >/dev/null 2>&1 &\nwhile [ ! -s '+shlex.quote(str(pidfile))+' ]; do sleep 0.02; done\nprintf \'{"hits":[]}\\n\'\n')
        else:
            self.wrapper.write_text('#!/bin/sh\n'+command+'\n')
        real_lock=semantic.LOCK
        releases=[]
        def release():
            try:
                data=json.loads(pidfile.read_text())
                self.assertEqual(self.group_live(data['pgid']),[], 'descendant alive at LOCK.release')
                releases.append(True)
            finally:real_lock.release()
        lock=Mock(wraps=real_lock);lock.release.side_effect=release
        original_communicate=subprocess.Popen.communicate
        def communicate(process,*args,**kwargs):
            if unexpected and process.args[0]==str(self.wrapper):
                deadline=time.monotonic()+3
                while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.01)
                raise RuntimeError('injected communicate failure')
            return original_communicate(process,*args,**kwargs)
        data=None
        try:
            with patch.object(semantic,'WORKER_TIMEOUT',3),patch.object(semantic,'TERMINATE_GRACE',.15),patch.object(semantic,'LOCK',lock),patch.object(subprocess.Popen,'communicate',communicate),patch.dict(os.environ,{'PATH':str(self.directory)} if no_ps else {}):
                if normal:semantic.retrieve(self.payload())
                elif unexpected:
                    with self.assertRaisesRegex(RuntimeError,'injected communicate'):semantic.retrieve(self.payload())
                else:
                    with self.assertRaisesRegex(ValueError,'超时'):semantic.retrieve(self.payload())
            data=json.loads(pidfile.read_text())
            self.assertEqual(releases,[True])
            self.assertFalse(real_lock.locked())
            self.assertNotEqual(data['pgid'],os.getpgrp(),'worker must have a dedicated process group')
            self.assertEqual(self.group_live(data['pgid']),[],'model descendants survived cleanup')
        finally:
            # Clean the intentionally failing pre-fix case without touching our own group.
            if pidfile.exists():
                data=json.loads(pidfile.read_text())
                try:os.kill(data['pid'],signal.SIGKILL)
                except ProcessLookupError:pass

    def test_timeout_reaps_non_exec_wrapper_group_before_unlock(self):
        self.cleanup_case()

    def test_normal_exit_reaps_background_descendant(self):
        self.cleanup_case(normal=True)

    def test_timeout_without_ps_preserves_error_and_reaps_before_unlock(self):
        self.cleanup_case(no_ps=True)

    def test_unexpected_communicate_error_reaps_before_unlock(self):
        self.cleanup_case(unexpected=True)

    def test_cleanup_deadline_is_bounded(self):
        process=Mock(pid=123456)
        ticks=iter(range(100))
        with patch.object(semantic.os,'killpg'),patch.object(semantic.subprocess,'check_output',return_value='123456 S'),patch.object(semantic.time,'monotonic',side_effect=lambda:next(ticks)),patch.object(semantic.time,'sleep',side_effect=[None]*20+[RuntimeError('unbounded cleanup')]),patch.object(semantic,'CLEANUP_TIMEOUT',5,create=True):
            with self.assertRaisesRegex(ValueError,'清理.*超时'):
                semantic.reap_group(process)

    def test_cleanup_failure_blocks_next_worker_until_restart(self):
        process=Mock(returncode=0)
        process.communicate.return_value=('｛｝','')
        error_type=getattr(semantic,'CleanupError',ValueError)
        with patch.object(semantic,'CLEANUP_FAILED',False,create=True),patch.object(semantic.subprocess,'Popen',return_value=process) as launch,patch.object(semantic,'reap_group',side_effect=error_type('进程清理超时')):
            with self.assertRaisesRegex(ValueError,'清理.*超时'):semantic.retrieve(self.payload())
            with self.assertRaisesRegex(ValueError,'重启'):semantic.retrieve(self.payload())
            self.assertEqual(launch.call_count,1)
            self.assertFalse(semantic.LOCK.locked())


if __name__=='__main__':unittest.main()
