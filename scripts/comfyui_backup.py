#!/usr/bin/env python3
"""
ComfyUI 历史与输出资产备份脚本

作用：
1. 把服务器的执行历史 (/history) 保存为 JSON（ComfyUI 历史存在内存，重启即丢）
2. 把历史里所有输出资产（图片/视频/音频）下载到本机备份

用法：
    python3 comfyui_backup.py

可配置环境变量：
    COMFYUI_URL   ComfyUI 地址，默认 http://192.168.1.23:8188
    BACKUP_DIR    备份目录，默认脚本所在目录下的 comfyui_backup/
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

SERVER = os.environ.get("COMFYUI_URL", "http://192.168.1.23:8188")
BACKUP_DIR = os.environ.get(
    "BACKUP_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "comfyui_backup"),
)


def api_get(path: str):
    with urllib.request.urlopen(SERVER + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download(path: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(SERVER + path, timeout=300) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    hist_dir = os.path.join(BACKUP_DIR, "history")
    out_dir = os.path.join(BACKUP_DIR, "outputs")
    os.makedirs(hist_dir, exist_ok=True)

    print(f"服务器: {SERVER}")
    try:
        history = api_get("/history?max_items=1000")
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    hist_file = os.path.join(hist_dir, f"history-{ts}.json")
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"历史记录: {len(history)} 条 -> {hist_file}")

    count = 0
    for pid, entry in history.items():
        for nid, out in entry.get("outputs", {}).items():
            for kind in ("images", "videos", "audio"):
                for item in out.get(kind, []):
                    fn = item.get("filename")
                    if not fn:
                        continue
                    sub = item.get("subfolder", "")
                    typ = item.get("type", "output")
                    query = urllib.parse.urlencode(
                        {"filename": fn, "subfolder": sub, "type": typ}
                    )
                    rel = os.path.join(sub, fn)
                    dest = os.path.join(out_dir, typ, rel)
                    try:
                        download("/view?" + query, dest)
                        count += 1
                        print("  资产: " + rel)
                    except Exception as e:
                        print(f"  失败: {rel} -> {e}")

    print(f"完成: 下载 {count} 个资产 -> {out_dir}")


if __name__ == "__main__":
    main()
