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
FFMPEG_BIN = r"E:\AIDATA\tools\ffmpeg\ffmpeg-9.0.1-essentials_build\bin"


def _child_env():
    """子进程环境：确保 ffmpeg 在 PATH 中（Windows 链式抽帧依赖）。"""
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    if os.path.isdir(FFMPEG_BIN):
        env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")
    return env


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
            env=_child_env(),
        )
        return p
    p = subprocess.Popen(
        [PY] + args,
        cwd=BASE,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=err,
        start_new_session=True,  # setsid：脱离当前会话
        env=_child_env(),
    )
    return p


def kill_existing(name):
    """杀掉同名旧进程，防止重复守护实例互相竞争。"""
    if platform.system() == "Windows":
        try:
            subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -match '{name}\\.py' }} "
                    f"| ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}",
                ],
                capture_output=True, text=True,
            )
        except Exception:
            pass
        return
    try:
        out = subprocess.run(
            ["pgrep", "-f", f"{name}\\.py"],
            capture_output=True, text=True,
        )
        for pid in out.stdout.split():
            try:
                os.kill(int(pid), 15)
                print(f"[start] 已停止旧 {name} 实例 pid={pid}", flush=True)
            except Exception:
                pass
    except Exception:
        pass


def main():
    kill_existing("batch_console")
    kill_existing("chain_daemon")
    web = spawn("batch_console", ["batch_console.py", "8890"])
    daemon = spawn("chain_daemon", ["chain_daemon.py"])
    print(f"web pid={web.pid}, daemon pid={daemon.pid}", flush=True)


if __name__ == "__main__":
    main()
