#!/usr/bin/env python3
"""MiniMax H3 介绍视频后期合成（最终版）。

流程：8 段 H3 成片 + 速度对比卡片段 -> 统一 1080x1920/24fps -> 拼接 ->
响度归一 -> 动画字幕/数据卡/CTA 叠加 -> 输出最终成片。
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID_DIR = os.path.join(BASE, "comfyui_backup", "outputs", "output", "video")
TMP = os.path.join(BASE, "工作流", "tmp")
OUT = os.path.join(BASE, "MiniMax_H3_介绍视频_1080x1920.mp4")
os.makedirs(TMP, exist_ok=True)

# 段：前缀（取最新版本）或固定文件
SEGMENTS = [
    ("H3_00_title", "片头"),
    ("H3_01_opening", "开场出镜"),
    ("H3_02_scifi", "展示①科幻"),
    ("H3_03_3d", "展示②3D"),
    ("H3_04_paper", "展示③纸拼贴"),
    ("H3_05_config", "配置介绍"),
    ("SPEED_CARD", "速度对比卡片"),
    ("H3_06_humor", "幽默段"),
    ("H3_07_cta", "结尾 CTA"),
]


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + args, check=True)


def resolve_latest(prefix):
    pat = os.path.join(VID_DIR, f"{prefix}_*.mp4")
    files = glob.glob(pat)
    if not files:
        return None
    def key(f):
        m = re.search(r"_(\d+)_\.mp4$", os.path.basename(f))
        return int(m.group(1)) if m else 0
    return max(files, key=key)


def build_speed_card():
    """速度对比卡片段：卡片图居中 + 深色背景 + 淡入 + 克隆音色旁白，16.5s。"""
    card = os.path.join(BASE, "素材", "速度对比表_卡片边缘.png")
    vo = "/tmp/speed_vo.wav"
    out = os.path.join(TMP, "speed_card.mp4")
    ffmpeg(
        ["-i", card, "-i", vo,
         "-filter_complex",
         "[0:v]scale=900:980,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0b1220,"
         "zoompan=z='1+0.00028*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
         "d=396:s=1080x1920:fps=24,fade=t=in:st=0:d=0.4,format=yuv420p[v];"
         "[1:a]atempo=1.12,afade=t=in:st=0:d=0.2,afade=t=out:st=16.2:d=0.3,"
         "aresample=48000,aformat=channel_layouts=stereo[a]",
         "-map", "[v]", "-map", "[a]", "-t", "16.5", "-r", "24",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", out]
    )
    print("  速度卡片段完成")
    return out


def main():
    ascii_dir = "/tmp/h3_assets"
    os.makedirs(ascii_dir, exist_ok=True)
    for name in ("datacard.png",):
        src = os.path.join(BASE, "工作流", "tmp", name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(ascii_dir, name))

    # 1. 解析素材 + 统一规格
    norm = []
    for prefix, label in SEGMENTS:
        if prefix == "SPEED_CARD":
            src = build_speed_card()
        else:
            src = resolve_latest(prefix)
        if not src or not os.path.exists(src):
            print(f"缺少素材: {prefix} ({label})")
            sys.exit(1)
        out = os.path.join(TMP, f"n_{os.path.basename(src)}.mp4")
        dur = float(
            subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", src]
            ).decode().strip()
        )
        ffmpeg(
            ["-i", src, "-vf", "scale=1080:1920:flags=lanczos+accurate_rnd",
             "-r", "24", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-af", f"afade=t=in:st=0:d=0.12,afade=t=out:st={max(0.0, dur-0.12):.3f}:d=0.12",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", out]
        )
        norm.append(out)
        print(f"  规范化: {label} -> {os.path.basename(out)}")

    # 2. 拼接
    listfile = os.path.join(TMP, "concat.txt")
    with open(listfile, "w") as f:
        for p in norm:
            f.write(f"file '{p.replace(os.sep, '/')}'\n")
    joined = os.path.join(TMP, "joined.mp4")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", joined])
    print("  拼接完成")

    # 3. 响度归一
    step1 = os.path.join(TMP, "step1.mp4")
    ffmpeg(
        ["-i", joined, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
         "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "192k", step1]
    )
    print("  响度归一完成")

    # 4. 动态字幕层 + 数据卡 + CTA 叠加
    meta_file = os.path.join(ascii_dir, "overlays.json")
    if os.path.exists(meta_file):
        overlays = json.load(open(meta_file))
        sub_frames = os.path.join("/tmp/sub_frames", "f_%05d.png")
        if not os.path.exists("/tmp/sub_frames/f_00000.png"):
            print("缺少动态字幕层，先运行 make_subtitles.py")
            sys.exit(1)
        inputs = ["-i", step1, "-framerate", "24", "-i", sub_frames]
        cta_frames = os.path.join("/tmp/cta_frames", "f_%05d.png")
        if os.path.exists("/tmp/cta_frames/f_00000.png"):
            inputs += ["-framerate", "24", "-i", cta_frames]
        for o in overlays:
            inputs += ["-loop", "1", "-i", os.path.join(ascii_dir, o["file"])]
        chains = []
        chains.append("[0:v][1:v]overlay=0:1440[sub]")
        if os.path.exists("/tmp/cta_frames/f_00000.png"):
            chains.append("[2:v]setpts=PTS+88/TB,format=rgba[ctadel]")
            chains.append("[sub][ctadel]overlay=0:0[cta]")
            prev = "[cta]"
            offset = 3
        else:
            prev = "[sub]"
            offset = 2
        for i, o in enumerate(overlays, 1):
            S, E = o["start"], o["end"]
            nxt = f"[v{i}]"
            if o["pos"] == "card":
                x, y = "W-w-40", "180"
            elif o["pos"] == "cta_main":
                x, y = "(W-w)/2", "1120"
            elif o["pos"] == "cta_sub1":
                x, y = "(W-w)/2", "1240"
            elif o["pos"] == "cta_sub2":
                x, y = "(W-w)/2", "1320"
            else:
                x = "(W-w)/2"
                y = f"(H-h-70)+if(lt(t,{S}+0.25),20*(1-(t-{S})/0.25),0)"
            chains.append(
                f"[{i+offset}:v]fade=t=in:st={S}:d=0.25,fade=t=out:st={E-0.25:.2f}:d=0.25[si{i}]"
            )
            chains.append(
                f"{prev}[si{i}]overlay=x='{x}':y='{y}':enable='between(t,{S},{E})'{nxt}"
            )
            prev = nxt
        chains.append(f"{prev}format=yuv420p[vout]")
        ffmpeg(
            inputs + [
                "-filter_complex", ";".join(chains),
                "-map", "[vout]", "-map", "0:a",
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-c:a", "copy", "-movflags", "+faststart", "-shortest", OUT,
            ]
        )
    else:
        shutil.copy(step1, OUT)
    print(f"完成: {OUT}")


if __name__ == "__main__":
    main()
