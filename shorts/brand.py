"""채널 프로필 사진과 배너를 모니 픽셀 그림으로 만든다.

  python -m shorts.brand        # assets/brand/avatar.png, banner.png
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .jobs import Fonts, big_title, text
from .pixel import art
from .pixel.art import C

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "brand"
NAME = "모니의 하루"
SKY = (90, 150, 230)


def avatar() -> Image.Image:
    im = Image.new("RGB", (50, 50), SKY)
    d = ImageDraw.Draw(im)
    art.draw_bot(d, 25, 52, 0.25, "wave", "happy", C["teal"])
    return im.crop((5, 7, 45, 47)).resize((800, 800), Image.NEAREST)


def banner() -> Image.Image:
    # 2560x1440, 모든 기기에서 보이는 가운데 안전 영역은 1546x423
    lo = Image.new("RGB", (320, 180), SKY)
    d = ImageDraw.Draw(lo)
    d.rectangle([0, 100, 320, 118], fill=(70, 120, 200))
    for k, (x, w, h) in enumerate([(4, 18, 50), (24, 14, 34), (40, 20, 60), (262, 20, 54), (284, 14, 36), (300, 18, 62)]):
        art.p_building(d, x, 118, 0, w=w, h=h, c=[(150, 160, 190), (120, 130, 170), (170, 150, 180)][k % 3])
    d.rectangle([0, 118, 320, 180], fill=(80, 84, 96))
    for x in range(0, 320, 16):
        d.rectangle([x, 140, x + 7, 141], fill=(230, 230, 220))
    art.draw_bot(d, 92, 118, 0.25, "wave", "happy", C["teal"])
    img = lo.resize((2560, 1440), Image.NEAREST)
    F = Fonts()
    big_title(img, 560, NAME, F[128], C["white"], max_w=1000, max_scale=1.7, cx=1460)
    dd = ImageDraw.Draw(img)
    text(dd, (1460, 790), "직업체험 · 세계여행 매일 업로드", F[64], C["yellow"], "mt", 5)
    return img


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    avatar().save(OUT / "avatar.png")
    banner().save(OUT / "banner.png")
    print(f"[brand] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
