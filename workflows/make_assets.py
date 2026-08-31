#!/usr/bin/env python3
"""【勿用】旧介绍片后期素材脚本。日常成片请用控制台第 8 步，不要单独跑本文件。

生成后期素材：动画字幕 PNG + 配置数据卡 PNG + 叠加清单 JSON。

时间轴（含速度卡片段 8s，无庭院段）：
T0(0-10) T1(10-20.125) T2(20.125-30.25) T3(30.25-40.375) T4(40.375-50.5)
T5(50.5-60.625) 速度卡(60.625-68.625) T6(68.625-78.75) T7(78.75-86.75)
"""

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = "/tmp/h3_assets"
os.makedirs(OUT_DIR, exist_ok=True)


def _find_font():
    """跨平台字体查找：环境变量 H3_FONT > 项目内字体 > 系统字体（macOS/Windows）。"""
    candidates = [
        os.environ.get("H3_FONT", ""),
        os.path.join(BASE, "素材", "字体", "NotoSansSC.ttf"),
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return candidates[1]


FONT_PATH = _find_font()

def make_text_png(text, out, size=56, bar=True):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(_find_font(), size)
    try:
        font.set_variation_by_axes([800])
    except Exception:
        pass
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=6)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 34, 18
    w = tw + pad_x * 2
    h = th + pad_y * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if bar:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(h / 2),
                            fill=(8, 12, 22, 200), outline=(255, 255, 255, 70), width=2)
        d.rounded_rectangle([10, 10, 22, h - 10], radius=6, fill=(255, 108, 55, 255))
    d.text((pad_x - bbox[0], pad_y - bbox[1]), text, font=font,
           fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))
    img.save(out)


def main():
    overlays = []
    with open(os.path.join(OUT_DIR, "overlays.json"), "w") as f:
        json.dump(overlays, f, ensure_ascii=False, indent=1)
    print(f"素材完成（CTA 已改动画层）-> {OUT_DIR}")


if __name__ == "__main__":
    main()
