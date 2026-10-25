"""Optional isolated CPU worker. Corpus is stdin-only and never persisted."""
import json
import os
from pathlib import Path
import subprocess
import threading

LOCK = threading.Lock()


def retrieve(payload):
    root = Path(__file__).resolve().parents[1]
    python = Path(os.environ.get('GUANLAN_RAG_PYTHON', str(root/'.venv-rag/bin/python')))
    if not python.is_file():
        raise ValueError('本地语义环境未安装，请按说明配置 .venv-rag；也可手动选择词法检索。')
    if not LOCK.acquire(blocking=False):
        raise ValueError('本地语义模型正在处理其他请求，请稍后再试。')
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith(('LLM_', 'GUANLAN_'))}
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                   TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='2')
        try:
            result = subprocess.run([str(python), str(root/'server/semantic_worker.py')],
                                    input=json.dumps(payload, ensure_ascii=False), text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                    cwd=root, timeout=38)
        except subprocess.TimeoutExpired:
            raise ValueError('本地语义检索超时，请减少材料；没有自动降级或生成结果。') from None
        except OSError:
            raise ValueError('无法启动本地语义环境，请检查 GUANLAN_RAG_PYTHON。') from None
        if result.returncode:
            raise ValueError('本地模型不可用或材料超过处理上限，请检查模型缓存与安装说明；没有自动下载或降级。')
        try:
            response = json.loads(result.stdout)
            if not isinstance(response.get('hits'), list):
                raise ValueError()
            return response
        except (ValueError, AttributeError):
            raise ValueError('本地语义服务返回格式异常，没有展示结果。') from None
    finally:
        LOCK.release()
