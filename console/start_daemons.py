#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动 web 服务和链式守护进程（后台常驻，跨平台）。

用法：
    python3 start_daemons.py

macOS/Linux 通过 setsid 独立成会话；Windows 通过 CREATE_NEW_PROCESS_GROUP
脱离控制台。日志写入本目录 *.log。
"""

import os
import subprocess
import sys
import platform

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def spawn(name, args):
    log = open(os.path.join(BASE, f"{name}.log"), "ab", buffering=0)
    err = open(os.path.join(BASE, f"{name}.err.log"), "ab", buffering=0)
    if platform.system() == "Windows":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)
        p = subprocess.Popen(
            [sys.executable] + args,
            cwd=BASE,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=err,
            creationflags=creationflags,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        return p
    p = subprocess.Popen(
        [PY] + args,
        cwd=BASE,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=err,
        start_new_session=True,  # setsid：脱离当前会话
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    return p


def main():
    web = spawn("batch_console", ["batch_console.py", "8890"])
    daemon = spawn("chain_daemon", ["chain_daemon.py"])
    print(f"web pid={web.pid}, daemon pid={daemon.pid}", flush=True)


if __name__ == "__main__":
    main()
