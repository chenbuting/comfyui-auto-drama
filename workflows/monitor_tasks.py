#!/usr/bin/env python3
"""监控 ComfyUI 生成任务：记录耗时、下载输出资产。

轮询 /history，任务完成后把 execution_start/execution_success 毫秒时间戳换算成耗时，
追加到 生成耗时记录.md，并下载输出资产到 comfyui_backup/outputs/。
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

SERVER = os.environ.get("COMFYUI_URL", "http://192.168.1.23:8188")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = json.load(open("/tmp/submit_manifest.json"))
RECORD = os.path.join(BASE, "生成耗时记录.md")
OUT_DIR = os.path.join(BASE, "comfyui_backup", "outputs")

NAME_MAP = {
    "T0_title": "片头 MINIMAX H3",
    "T1_opening": "开场出镜+对白",
    "T2_scifi": "展示①科幻",
    "T3_3d": "展示②3D 动画",
    "T4_paper": "展示③纸拼贴",
    "T5_config": "配置介绍+对白",
    "T6_humor": "幽默段+对白",
    "T7_cta": "结尾 CTA",
}


def api_get(path):
    with urllib.request.urlopen(SERVER + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def download(path, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(SERVER + path, timeout=600) as r, open(dest, "wb") as f:
        f.write(r.read())


def fmt(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}分{s:02d}秒"


def ensure_record_header():
    if not os.path.exists(RECORD):
        with open(RECORD, "w", encoding="utf-8") as f:
            f.write(
                "# MiniMax H3 生成耗时记录\n\n"
                "> 项目：《MiniMax H3 开源模型介绍视频》 2026-08-12\n"
                "> 数据来源：ComfyUI /history execution 时间戳（毫秒），真实记录\n\n"
                "| 任务 | 内容 | 模式 | 时长 | 分辨率 | 开始时间 | 结束时间 | 耗时 | 状态 | 输出 |\n"
                "|---|---|---|---|---|---|---|---|---|---|\n"
            )


def main():
    ensure_record_header()
    pending = {m["prompt_id"]: m for m in MANIFEST}
    print(f"监控 {len(pending)} 个任务，服务器 {SERVER}")
    while pending:
        try:
            history = api_get("/history?max_items=100")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 轮询失败: {e}")
            time.sleep(30)
            continue
        for pid, entry in history.items():
            if pid not in pending:
                continue
            task = pending[pid]
            status = entry.get("status", {})
            msgs = {m[0]: m[1] for m in status.get("messages", [])}
            t0 = msgs.get("execution_start", {}).get("timestamp")
            t1 = msgs.get("execution_success", {}).get("timestamp")
            st = status.get("status_str")
            duration = (t1 - t0) / 1000.0 if t0 and t1 else None
            outputs = []
            for nid, out in entry.get("outputs", {}).items():
                for kind in ("images", "videos", "audio"):
                    for item in out.get(kind, []):
                        fn = item.get("filename")
                        if not fn:
                            continue
                        outputs.append(f"{kind}:{fn}")
                        sub = item.get("subfolder", "")
                        typ = item.get("type", "output")
                        q = urllib.parse.urlencode({"filename": fn, "subfolder": sub, "type": typ})
                        try:
                            download("/view?" + q, os.path.join(OUT_DIR, typ, sub, fn))
                        except Exception as e:
                            print(f"  下载失败 {fn}: {e}")
            t0s = time.strftime("%H:%M:%S", time.localtime(t0 / 1000)) if t0 else "-"
            t1s = time.strftime("%H:%M:%S", time.localtime(t1 / 1000)) if t1 else "-"
            dur_s = fmt(duration) if duration else "-"
            row = (
                f"| {task['task']} | {NAME_MAP.get(task['task'], task['task'])} "
                f"| {task['mode']} | {task['duration']}s | 9:16 480x864 "
                f"| {t0s} | {t1s} | {dur_s} | {st} | {', '.join(outputs) or '-'} |\n"
            )
            with open(RECORD, "a", encoding="utf-8") as f:
                f.write(row)
            print(f"[{time.strftime('%H:%M:%S')}] 完成 {task['task']}: {dur_s} -> {', '.join(outputs)}")
            del pending[pid]
        if pending:
            time.sleep(30)
    print("全部任务完成。" if False else "ALL_DONE")


if __name__ == "__main__":
    main()
