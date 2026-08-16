#!/usr/bin/env python3
"""环境一键检查：确认控制台所有依赖是否就绪，输出 ✅/❌/⚠️ 与修复建议。

用法：
    python3 scripts/check_env.py

检查项：
    Python 版本 / ffmpeg / config.json / 远程 ComfyUI / 语言模型(本地或云端)
    / 文生图(本地或云端) / 视觉质检 / 合成依赖
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.environ.get("BATCH_CONSOLE_CONFIG") or os.path.join(ROOT, "config.json")

OK, BAD, WARN = "✅", "❌", "⚠️"


def check(name, ok, detail=""):
    mark = OK if ok else BAD
    print(f"  {mark} {name}{(' — ' + detail) if detail else ''}")


def http_ok(url, timeout=5, auth_ok=False):
    """检查服务可达；auth_ok=True 时 401（需鉴权）视为服务在线。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "env-check"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True if r.status < 400 else (auth_ok and r.status == 401)
    except urllib.error.HTTPError as e:
        return auth_ok and e.code == 401
    except Exception:
        return False


def main():
    print("=" * 56)
    print("ComfyUI 短剧系统 · 环境检查")
    print("=" * 56)

    # 1. Python
    print("\n[1/6] Python")
    ver = sys.version_info
    ok = ver >= (3, 10)
    check(f"Python {ver.major}.{ver.minor}.{ver.micro}（需 ≥3.10）", ok,
          "" if ok else "请安装 Python 3.10+：https://www.python.org/downloads/")

    # 2. ffmpeg（合成/转码/抽帧）
    print("\n[2/6] ffmpeg（合成/转码必需）")
    ff = shutil.which("ffmpeg")
    if ff:
        try:
            out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=8)
            ver_line = out.stdout.splitlines()[0] if out.stdout else "?"
            check("ffmpeg 已安装", True, ver_line[:60])
        except Exception:
            check("ffmpeg 已找到但无法运行", False, "请重新安装 ffmpeg")
    else:
        check("ffmpeg 未安装", False,
              "macOS: brew install ffmpeg | Windows: winget install ffmpeg | Linux: sudo apt install ffmpeg")

    # 3. config.json
    print("\n[3/6] 配置文件")
    if not os.path.isfile(CONFIG_PATH):
        check("config.json 不存在", False, f"复制 config.example.json 为 config.json（{CONFIG_PATH}）")
        return
    try:
        cfg = json.load(open(CONFIG_PATH, encoding="utf-8"))
        check("config.json 可解析", True, CONFIG_PATH)
    except Exception as e:
        check("config.json 解析失败", False, str(e))
        return

    # 4. 远程 ComfyUI
    print("\n[4/6] 远程 ComfyUI（视频生成）")
    server = (cfg.get("comfyui") or {}).get("server") or ""
    if server:
        ok = http_ok(server.rstrip("/") + "/system_stats")
        check(f"ComfyUI {server}", ok,
              "" if ok else "地址不可达：检查远程机是否开机、ComfyUI 是否运行、网络/防火墙")
    else:
        check("ComfyUI 服务器地址未配置", False, "config.json -> comfyui.server")

    # 5. 语言模型（本地或云端）
    print("\n[5/6] 语言模型（剧本/提示词）")
    llm = cfg.get("llm") or {}
    provider = llm.get("provider") or "local"
    if provider == "cloud":
        cloud = llm.get("cloud") or {}
        ok = bool(cloud.get("base_url") and cloud.get("api_key"))
        check("云端 LLM 配置", ok, "" if ok else "填 base_url/api_key/model")
    else:
        local = llm.get("local") or {}
        url = local.get("url") or ""
        ok = bool(url) and http_ok(url.rstrip("/") + "/v1/models", auth_ok=True)
        check(f"本地 LLM {url}", ok,
              "" if ok else "LM Studio 未运行或模型未加载：打开 LM Studio 加载模型，或改配云端")

    # 6. 文生图 + 视觉 + 合成
    print("\n[6/6] 文生图 / 视觉质检")
    img = cfg.get("image_gen") or {}
    iprov = img.get("provider") or "local"
    if iprov == "cloud":
        icloud = img.get("cloud") or {}
        ok = bool(icloud.get("base_url") and icloud.get("api_key"))
        check("云端文生图配置", ok, "" if ok else "填 base_url/api_key/model")
    else:
        iurl = (img.get("local") or {}).get("url") or ""
        ok = bool(iurl) and http_ok(iurl.rstrip("/") + "/v1/models")
        check(f"本地生图 {iurl}", ok,
              "" if ok else "Boogu-Image 未运行：bash scripts/deploy_boogu.sh 部署后启动；非 Apple Silicon 用云端")
    vision = cfg.get("vision") or {}
    vurl = vision.get("base_url") or ""
    ok = bool(vurl) and http_ok(vurl.rstrip("/") + "/models", auth_ok=True)
    check(f"视觉质检 {vurl}（模型 {vision.get('model') or '?'}）", ok,
          "" if ok else "视觉服务未运行或模型名错误；可改用云端通义 qwen-vl-max")

    print("\n" + "=" * 56)
    print("检查完成。所有 ✅ 即可运行；❌ 按提示安装/配置；⚠️ 见说明。")
    print("详细配置见 CONFIG.md，部署见 README.md")
    print("=" * 56)


if __name__ == "__main__":
    main()
