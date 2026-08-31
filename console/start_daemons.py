#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动 web 服务和链式守护进程（后台常驻，跨平台）。

用法：
    python3 start_daemons.py

macOS/Linux 通过 setsid 独立成会话；Windows 通过 CREATE_NEW_PROCESS_GROUP
脱离控制台。日志写入本目录 *.log。
"""

import os
import shutil
import subprocess
import sys
import platform

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def _ffmpeg_dirs():
    """找出 ffmpeg 所在目录：环境变量 → PATH → 本机旧路径（仅当还在）。"""
    dirs = []
    hint = (os.environ.get("FFMPEG_BIN") or os.environ.get("FFMPEG_PATH") or "").strip()
    if hint:
        if os.path.isfile(hint):
            dirs.append(os.path.dirname(os.path.abspath(hint)))
        elif os.path.isdir(hint):
            dirs.append(os.path.abspath(hint))
    which = shutil.which("ffmpeg")
    if which:
        dirs.append(os.path.dirname(os.path.abspath(which)))
    # 本机以前装过的路径，只在目录还在时当兜底，不写死依赖
    legacy = r"E:\AIDATA\tools\ffmpeg\ffmpeg-9.0.1-essentials_build\bin"
    if os.path.isdir(legacy):
        dirs.append(legacy)
    seen = set()
    out = []
    for d in dirs:
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _child_env():
    """子进程环境：把能找到的 ffmpeg 目录补进 PATH（链式抽帧依赖）。"""
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    extra = _ffmpeg_dirs()
    if extra:
        env["PATH"] = os.pathsep.join(extra) + os.pathsep + env.get("PATH", "")
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
