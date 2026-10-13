#!/bin/zsh
cd -- "${0:A:h}/.." || exit 1
if [[ ! -x .venv/bin/python ]]; then
  echo '首次使用请在此项目目录运行：python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt'
  read 'reply?按回车退出'
  exit 1
fi
.venv/bin/python server/app.py --open
if [[ $? -ne 0 ]]; then
  echo '启动失败。若 8765 端口已被占用，请关闭旧服务后重试。'
  read 'reply?按回车退出'
fi
