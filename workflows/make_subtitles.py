#!/usr/bin/env python3
"""【勿用】旧介绍片字幕脚本。日常成片请用控制台第 8 步，不要单独跑本文件。

渲染动态字幕层：每段 ≤10 字，逐字弹出动画，输出透明 PNG 序列。

规则：字幕单行不超屏；字符逐个弹出（0.25s 缩放+弹跳）；当前弹出字橙色高亮；
全部出现后保持到该段结束。输出到 /tmp/sub_frames/（1080x220 底部字幕带）。
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.environ.get("H3_FONT", os.path.join(BASE, "素材", "字体", "NotoSansSC.ttf"))
FPS = 24
DURATION = 95.5
BAND_W, BAND_H = 1080, 280
OUT_DIR = "/tmp/sub_frames"

# 父行：(开始, 结束, 手工分词列表)。每段 ≤10 字，按语感切分不切断词。
LINES = [
    (0.6, 5.2, ["MiniMax H3", "开源了！"]),
    (5.0, 9.8, ["文字图片视频声音", "一次全理解", "直接生成", "原生立体声视频"]),
    (10.6, 15.4, ["以前AI视频", "是土豪的玩具", "一条五秒", "几十块"]),
    (15.6, 19.9, ["直到MiniMax", "把H3开源了"]),
    (20.6, 28.0, ["这段科幻镜头", "画面和声音", "是模型一次生成的", "这就是", "原生立体声"]),
    (30.6, 38.0, ["3D动画", "角色一致", "表演有弹性", "指令遵循", "运动控制很稳"]),
    (40.6, 48.5, ["连纸拼贴", "这种手作质感", "都能做", "风格控制同样能打"]),
    (51.0, 56.0, ["我的配置很普通", "U7 265K处理器", "48G内存", "RTX 5070 Ti", "16G显存"]),
    (56.2, 60.4, ["跑MiniMax H3", "基本够用", "无非就是慢一点"]),
    (61.2, 68.5, ["同样的提示词", "480p预览", "实测3分钟一条", "768p高清", "实测12分钟一条"]),
    (68.8, 76.5, ["开了三个加速插件", "Turbo4步", "SageAttention", "int8量化", "不加速时间至少翻倍"]),
    (77.7, 82.5, ["以前一个片段", "顶一周奶茶钱"]),
    (82.7, 86.9, ["现在电费", "只是一杯奶茶的零头"]),
]


def build_chunks():
    out = []
    for S, E, chunks in LINES:
        total = sum(len(c) for c in chunks)
        span = max(0.8, E - S - 1.2)
        acc = 0
        starts = []
        for c in chunks:
            cs = S + 0.4 + (acc / total) * span
            starts.append(cs)
            acc += len(c)
        for i, c in enumerate(chunks):
            end = starts[i + 1] - 0.06 if i + 1 < len(chunks) else E
            out.append((starts[i], end, c))
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    chunks = build_chunks()
    font = ImageFont.truetype(FONT_PATH, 78)
    font.set_variation_by_axes([800])  # 粗体
    n_frames = int(DURATION * FPS)
    print(f"字幕段数: {len(chunks)}, 帧数: {n_frames}")
    for fi in range(n_frames):
        t = fi / FPS
        img = Image.new("RGBA", (BAND_W, BAND_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for S, E, text in chunks:
            if not (S <= t < E + 0.05):
                continue
            # 逐字测量宽度
            widths = [d.textlength(c, font=font) for c in text]
            visible = []
            for j, (ch, cw) in enumerate(zip(text, widths)):
                a = S + j * 0.13
                if t >= a:
                    visible.append((ch, cw, a))
            if not visible:
                continue
            vis_w = sum(cw for _, cw, _ in visible)
            x0 = (BAND_W - vis_w) / 2 - 26
            y0 = (BAND_H - 150) / 2 - 14
            x1 = (BAND_W + vis_w) / 2 + 26
            y1 = (BAND_H + 150) / 2 + 14
            # 抖音式胶囊底
            d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2,
                                fill=(0, 0, 0, 140))
            x = (BAND_W - vis_w) / 2
            y = (BAND_H - 150) / 2
            for ch, cw, a in visible:
                p = min(1.0, (t - a) / 0.22)  # 弹出进度
                # 缩放：0.3 -> 1.15 -> 1.0（弹跳）
                scale = 0.3 + 0.85 * p if p < 1 else 1.0
                if p >= 1:
                    scale = 1.0 + 0.15 * math.sin(min(1.0, (t - a - 0.22) / 0.12) * math.pi)
                if scale < 0.05:
                    continue
                ch_img = Image.new("RGBA", (int(cw) + 24, 150), (0, 0, 0, 0))
                dc = ImageDraw.Draw(ch_img)
                color = (255, 196, 0, 255) if t - a < 0.55 else (255, 255, 255, 255)
                dc.text((12, 8), ch, font=font, fill=color,
                        stroke_width=7, stroke_fill=(0, 0, 0, 255))
                sw = int(ch_img.width * scale)
                sh = int(ch_img.height * scale)
                if sw < 2 or sh < 2:
                    continue
                ch_img = ch_img.resize((sw, sh), Image.LANCZOS)
                img.alpha_composite(ch_img, (int(x + cw / 2 - sw / 2), int(y + 65 - sh / 2)))
                x += cw
        img.save(os.path.join(OUT_DIR, f"f_{fi:05d}.png"))
        if fi % 240 == 0:
            print(f"  帧 {fi}/{n_frames}")
    print("字幕层渲染完成:", OUT_DIR)


if __name__ == "__main__":
    main()
