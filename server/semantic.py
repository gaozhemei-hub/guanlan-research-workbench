"""Optional isolated CPU worker. Corpus is stdin-only and never persisted."""
import json
import os
from pathlib import Path
import subprocess
import threading
import signal
import time

LOCK = threading.Lock()
WORKER_TIMEOUT = 38
TERMINATE_GRACE = .5
CLEANUP_TIMEOUT = 5
CLEANUP_FAILED = False


class CleanupError(ValueError):
    pass


def reap_group(process):
    """Terminate our dedicated group, including descendants of shell wrappers."""
    deadline = time.monotonic() + CLEANUP_TIMEOUT
    def remaining():
        seconds = deadline-time.monotonic()
        if seconds <= 0:
            raise CleanupError('本地语义进程清理超时；请重启服务后再试。')
        return seconds
    def wait_child():
        try:
            process.wait(timeout=remaining())
        except subprocess.TimeoutExpired:
            raise CleanupError('本地语义进程清理超时；请重启服务后再试。') from None
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        wait_child()
        return
    time.sleep(min(TERMINATE_GRACE, remaining()))
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    wait_child()
    # A descendant may not be our child; wait for it to stop executing, ignoring zombies.
    while True:
        budget = remaining()
        try:
            listing = subprocess.check_output(['ps', '-axo', 'pgid=,stat='], text=True, timeout=budget)
            live = any(len(p) == 2 and p[0] == str(process.pid) and not p[1].startswith('Z')
                       for line in listing.splitlines() if (p := line.split()))
        except (OSError, subprocess.SubprocessError):
            # Without ps we cannot distinguish zombies; conservatively wait until
            # the whole group disappears, bounded by the same cleanup deadline.
            try:
                os.killpg(process.pid, 0)
                live = True
            except ProcessLookupError:
                live = False
        if not live:
            break
        time.sleep(.02)


def retrieve(payload):
    global CLEANUP_FAILED
    root = Path(__file__).resolve().parents[1]
    python = Path(os.environ.get('GUANLAN_RAG_PYTHON', str(root/'.venv-rag/bin/python')))
    if not python.is_file():
        raise ValueError('本地语义环境未安装，请按说明配置 .venv-rag；也可手动选择词法检索。')
    if not LOCK.acquire(blocking=False):
        raise ValueError('本地语义模型正在处理其他请求，请稍后再试。')
    try:
        if CLEANUP_FAILED:
            raise ValueError('先前进程清理未确认完成，请重启服务后再试。')
        env = {k: v for k, v in os.environ.items() if not k.startswith(('LLM_', 'GUANLAN_'))}
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                   TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='2')
        try:
            process = subprocess.Popen([str(python), str(root/'server/semantic_worker.py')],
                                       stdin=subprocess.PIPE, text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                       cwd=root, start_new_session=True)
            try:
                output, _ = process.communicate(json.dumps(payload, ensure_ascii=False), timeout=WORKER_TIMEOUT)
            finally:
                try:
                    reap_group(process)
                except CleanupError:
                    # Unlock the request, but do not launch another model alongside
                    # an unconfirmed survivor. Recovery requires a service restart.
                    CLEANUP_FAILED = True
                    raise
                finally:
                    for stream in (process.stdin, process.stdout, process.stderr):
                        if stream is not None:
                            stream.close()
        except subprocess.TimeoutExpired:
            raise ValueError('本地语义检索超时，请减少材料；没有自动降级或生成结果。') from None
        except OSError:
            raise ValueError('无法启动本地语义环境，请检查 GUANLAN_RAG_PYTHON。') from None
        if process.returncode:
            try:
                code = json.loads(output).get('error_code')
            except (ValueError, AttributeError):
                code = None
            messages = {
                'MODEL_UNAVAILABLE': '本地依赖或模型缺失，请检查安装与模型缓存；不会自动下载。',
                'CHUNK_LIMIT': '材料分块超过 100 块，请合并段落或减少材料。',
                'TOKEN_BUDGET': '本地模型 token 预算超限，请缩短问题或材料段落。',
            }
            raise ValueError(messages.get(code, '本地语义处理失败，请检查本地环境；没有展示结果。'))
        try:
            response = json.loads(output)
            if not isinstance(response.get('hits'), list):
                raise ValueError()
            return response
        except (ValueError, AttributeError):
            raise ValueError('本地语义服务返回格式异常，没有展示结果。') from None
    finally:
        LOCK.release()
