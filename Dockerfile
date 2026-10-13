# 观澜 v0.8 · 候选容器（任务04；未在真实平台构建或发布）
# TA-Lib 0.6.8 在 PyPI 提供 cp312 manylinux x86_64/aarch64 wheel（自带 C 库），无需单独编译。
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
# 建议改为 requirements.lock（pip freeze 自本机已验证的 .venv），避免传递依赖漂移
RUN pip install -r requirements.txt
COPY server/ server/
COPY prototype/dist/ prototype/dist/
COPY scripts/deploy_check.py scripts/deploy_check.py
RUN useradd --system --uid 10001 guanlan && mkdir -p /data && chown guanlan /data
USER guanlan
# 默认安全：监听全部地址时，若未设置 GUANLAN_BASIC_AUTH，服务拒绝启动
ENV GUANLAN_BIND=0.0.0.0 GUANLAN_PORT=8765 GUANLAN_DATA_DIR=/data \
    GUANLAN_SCHEDULE=0 GUANLAN_REFRESH_WORKERS=2 GUANLAN_PRICES_PER_MINUTE=6 GUANLAN_AI_DAILY_LIMIT=20 GUANLAN_DISABLE_AI=1
EXPOSE 8765
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"GUANLAN_PORT\",\"8765\")}/healthz',timeout=4)"
# GUANLAN_SCHEDULE=0：会休眠的平台上，每次冷启动都会全量刷新（20 余个子进程集中请求上游），默认关闭；
# 常驻 VPS 可设为 1。登录用户仍可手动刷新；缓存写入 /data 卷，重启后同日不重复抓取。
CMD ["python", "server/app.py"]
