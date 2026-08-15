#!/usr/bin/env python3
"""渲染片尾 CTA 动画层：头像弹入 + 分层文字动效，输出透明 PNG 序列。

时间窗 88.0-95.2s（视频时间轴），24fps，1080x1920 RGBA。
元素：圆形头像（橙圈）居中弹入；"跟着辉哥学AI"逐字弹出；
"关注我"、"下期手把手教你！"分两行上浮错峰出现。
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.environ.get("H3_FONT", os.path.join(BASE, "素材", "字体", "NotoSansSC.ttf"))
AVATAR_SRC = os.environ.get("H3_AVATAR", os.path.join(BASE, "出镜素材", "3号_1s.png"))
OUT_DIR = "/tmp/cta_frames"
START = 88.0
END = 95.2
FPS = 24
W, H = 1080, 1920


def load_avatar(size=340):
    img = Image.open(AVATAR_SRC).convert("RGB")
    # 裁出脸部方形区域（半身像，脸在上中部）
    crop = img.crop((200, 400, 960, 1160)).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    return crop, mask


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    avatar, mask = load_avatar()
    f_title = ImageFont.truetype(FONT, 72)
    f_title.set_variation_by_axes([900])
    f_sub = ImageFont.truetype(FONT, 48)
    f_sub.set_variation_by_axes([800])

    n = int((END - START) * FPS)
    for fi in range(n):
        t = fi / FPS
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(frame)

        # 头像：0-0.5s 弹入，之后轻微脉动
        if t < 0.7:
            p = min(1.0, t / 0.45)
            scale = 0.3 + 0.85 * p if p < 1 else 1.15 - 0.15 * math.sin(min(1.0, (t - 0.45) / 0.2) * math.pi)
        else:
            scale = 1.0 + 0.02 * math.sin((t - 0.7) * 2.2)
        size = int(340 * scale)
        if size > 4:
            av = avatar.resize((size, size), Image.LANCZOS)
            mk = mask.resize((size, size), Image.LANCZOS)
            x0 = (W - size) // 2
            y0 = 780 + (340 - size) // 2
            ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse([x0 - 8, y0 - 8, x0 + size + 8, y0 + size + 8],
                                         outline=(255, 108, 55, 255), width=8)
            frame.alpha_composite(ring, (0, 0))
            frame.paste(av, (x0, y0), mk)

        # 主标题：逐字弹出
        title = "跟着辉哥学AI"
        widths = [d.textlength(c, font=f_title) for c in title]
        total = sum(widths)
        tx = (W - total) / 2
        ty = 1090
        for j, (ch, cw) in enumerate(zip(title, widths)):
            a = 0.7 + j * 0.14
            if t < a:
                continue
            p = min(1.0, (t - a) / 0.22)
            scale = 0.3 + 0.85 * p if p < 1 else 1.0 + 0.12 * math.sin(min(1.0, (t - a - 0.22) / 0.12) * math.pi)
            color = (255, 196, 0, 255) if t - a < 0.5 else (255, 255, 255, 255)
            ch_img = Image.new("RGBA", (int(cw) + 24, 140), (0, 0, 0, 0))
            dc = ImageDraw.Draw(ch_img)
            dc.text((12, 8), ch, font=f_title, fill=color,
                    stroke_width=6, stroke_fill=(0, 0, 0, 255))
            sw, sh = int(ch_img.width * scale), int(ch_img.height * scale)
            ch_img = ch_img.resize((sw, sh), Image.LANCZOS)
            frame.alpha_composite(ch_img, (int(tx + cw / 2 - sw / 2), int(ty + 70 - sh / 2)))
            tx += cw

        # 副标题两行：上浮错峰
        for label, ybase, a in [("关注我", 1340, 1.7), ("下期手把手教你！", 1430, 2.3)]:
            if t < a:
                continue
            p = min(1.0, (t - a) / 0.3)
            y = ybase + int(50 * (1 - p))
            alpha = int(255 * p)
            wl = d.textlength(label, font=f_sub)
            sub_img = Image.new("RGBA", (int(wl) + 34, 86), (0, 0, 0, 0))
            dc = ImageDraw.Draw(sub_img)
            dc.rounded_rectangle([0, 0, int(wl) + 33, 85], radius=43,
                                 fill=(8, 12, 22, int(alpha * 0.75)),
                                 outline=(255, 255, 255, int(alpha * 0.7)), width=2)
            dc.text((17, 12), label, font=f_sub, fill=(255, 255, 255, alpha),
                    stroke_width=5, stroke_fill=(0, 0, 0, alpha))
            frame.alpha_composite(sub_img, ((W - sub_img.width) // 2, y))

        frame.save(os.path.join(OUT_DIR, f"f_{fi:05d}.png"))
    print(f"CTA 层渲染完成: {n} 帧 -> {OUT_DIR}")


if __name__ == "__main__":
    main()
