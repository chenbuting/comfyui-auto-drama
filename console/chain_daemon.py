#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""链式生成守护进程：独立于 Web 控制台运行，持续推进链条。

用法（后台运行，关掉终端也不停）：
    nohup python3 chain_daemon.py > chain_daemon.log 2>&1 &

逻辑：每 20 秒先 get_status（对账/下载），再 advance_chain 推进下一段。
上一段完成即自动抽帧上传、提交下一段，直到所有任务结束。
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batch_console as bc


def main():
    server = bc.DEFAULT_SERVER
    print(f"[daemon] 启动，服务器 {server}，每 20 秒检查一次", flush=True)
    while True:
        try:
            state = bc.load_state()
            tasks = [t for t in state.get("tasks", []) if t.get("prompt_id") or t.get("chain_waiting")]
            if not tasks:
                print(f"[daemon] {time.strftime('%H:%M:%S')} 无活动任务，持续待命", flush=True)
                time.sleep(20)
                continue
            result = bc.get_status(server)
            if not result.get("server_ok"):
                print(f"[daemon] 服务器异常：{result.get('error')}", flush=True)
            else:
                st = bc.load_state()
                # 按项目暂停：某个项目停了仍推进其他项目
                if bc.advance_chain(server, st):
                    bc.save_state(st)
                active = [t for t in result["tasks"] if t["status"] in ("queued", "running", "waiting")]
                done = [t for t in result["tasks"] if t["status"] == "completed"]
                brief = ", ".join(
                    "{}:{}".format(t.get("name", "?"), t["status"]) for t in result["tasks"][-12:]
                )
                print(
                    "[daemon] {} 活动 {} 完成 {} | {}".format(
                        time.strftime("%H:%M:%S"), len(active), len(done), brief
                    ),
                    flush=True,
                )
        except Exception as e:
            print(f"[daemon] 错误：{e}", flush=True)
        time.sleep(20)


if __name__ == "__main__":
    main()
