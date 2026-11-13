"""장면 + 음성으로 1080x1920 세로 영상을 렌더링한다 (Pillow + FFmpeg)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .data import Ranking
from .script import Scene, fmt
from .tts import duration

W, H, FPS = 1080, 1920, 30
GAP = 0.25          # 문장 사이 쉬는 시간(초)
TAIL = 0.8          # 영상 끝 여유
BG_TOP, BG_BOTTOM = (11, 18, 38), (30, 41, 66)
FG, MUTED, ACCENT, KOREA = (245, 247, 250), (120, 134, 160), (255, 196, 0), (64, 156, 255)
BAR = (88, 110, 160)

FONT_CANDIDATES = [
    os.environ.get("SHORTS_FONT", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]


def _font_path() -> str:
    for p in FONT_CANDIDATES:
        if p and Path(p).exists():
            return p
    raise RuntimeError("한글 폰트를 찾을 수 없어요. fonts-noto-cjk를 설치하거나 SHORTS_FONT를 지정하세요.")


class Fonts:
    def __init__(self):
        path = _font_path()
        idx = 1 if path.endswith(".ttc") else 0  # Noto CJK .ttc의 1번이 KR
        self.f = {s: ImageFont.truetype(path, s, index=idx) for s in (34, 40, 46, 52, 60, 76)}

    def __getitem__(self, size: int) -> ImageFont.FreeTypeFont:
        return self.f[size]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split(" "):
        test = f"{cur} {word}".strip()
        if draw.textlength(test, font=font) <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _background() -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        px.line([(0, y), (W, y)], fill=c)
    return img


def _ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def build_timeline(scenes: list[Scene], groups: list[tuple[str, list[int]]], audio: list[Path]):
    """장면별 (시작, 끝) 시간. 한 문장이 여러 장면을 덮으면 시간을 나눈다."""
    times = [(0.0, 0.0)] * len(scenes)
    t = 0.0
    for (_, idxs), path in zip(groups, audio):
        d = duration(path) + GAP
        step = d / len(idxs)
        for j, i in enumerate(idxs):
            times[i] = (t + j * step, t + (j + 1) * step)
        t += d
    return times, t + TAIL


def mix_audio(audio: list[Path], out: Path) -> None:
    inputs, filt = [], []
    for i, p in enumerate(audio):
        inputs += ["-i", str(p)]
        filt.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,apad=pad_dur={GAP}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1,apad=pad_dur={TAIL}[out]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "[out]", "-c:a", "aac", "-b:a", "160k", str(out)], check=True)


class Frame:
    def __init__(self, r: Ranking, scenes: list[Scene]):
        self.r, self.scenes, self.fonts, self.bg = r, scenes, Fonts(), _background()
        vals = [abs(e.value) for e in r.top] or [1]
        self.vmax = max(vals) or 1

    def draw(self, t: float, times) -> Image.Image:
        cur = max((i for i, (s, _) in enumerate(times) if s <= t), default=0)
        scene, (s0, _) = self.scenes[cur], times[cur]
        revealed = {sc.reveal_rank: times[i][0] for i, sc in enumerate(self.scenes[:cur + 1]) if sc.reveal_rank}

        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        F = self.fonts
        topic = self.r.topic

        # 제목
        y = 120
        for line in _wrap(d, topic["title"], F[76], W - 120):
            d.text((W // 2, y), line, font=F[76], fill=FG, anchor="mt")
            y += 92
        d.text((W // 2, y + 14), f"TOP 10 · {self.r.year}년", font=F[46], fill=ACCENT, anchor="mt")

        # 순위 행 (1위가 맨 위)
        top_y, row_h = 430, 100
        for e in self.r.top:
            ry = top_y + (e.rank - 1) * row_h
            is_cur = scene.reveal_rank == e.rank
            if is_cur:
                d.rounded_rectangle([40, ry - 8, W - 40, ry + row_h - 14], radius=18, fill=(46, 58, 92))
            d.text((70, ry + 10), f"{e.rank}", font=F[52], fill=ACCENT if e.rank <= 3 else MUTED)
            if e.rank in revealed:
                p = _ease((t - revealed[e.rank]) / 0.6)
                color = KOREA if e.iso2 == "KR" else FG
                d.text((160, ry + 4), e.name, font=F[46], fill=color)
                d.text((W - 70, ry + 4), fmt(e.value, topic), font=F[40], fill=color, anchor="ra")
                bw = int((W - 230) * abs(e.value) / self.vmax * p)
                d.rounded_rectangle([160, ry + 64, 160 + max(bw, 8), ry + 80], radius=8,
                                    fill=KOREA if e.iso2 == "KR" else (ACCENT if e.rank == 1 else BAR))
            else:
                d.text((160, ry + 4), "?", font=F[46], fill=MUTED)

        # 한국 박스
        k = self.r.korea
        if k and scene.kind in ("korea", "outro") and k.rank > len(self.r.top):
            by = top_y + 10 * row_h + 8
            d.rounded_rectangle([40, by, W - 40, by + 100], radius=18, outline=KOREA, width=4)
            d.text((70, by + 22), f"{k.rank}위  한국", font=F[46], fill=KOREA)
            d.text((W - 70, by + 22), fmt(k.value, topic), font=F[40], fill=KOREA, anchor="ra")

        # 자막
        lines = _wrap(d, scene.text, F[52], W - 140)
        sy = H - 170 - 66 * len(lines)
        d.rounded_rectangle([50, sy - 24, W - 50, sy + 66 * len(lines) + 10], radius=22, fill=(0, 0, 0))
        for i, line in enumerate(lines):
            d.text((W // 2, sy + i * 66), line, font=F[52], fill=FG, anchor="mt")
        d.text((W // 2, H - 70), "출처: 세계은행 오픈데이터", font=F[34], fill=MUTED, anchor="mt")
        return img


def render(r: Ranking, scenes: list[Scene], groups, audio: list[Path], out: Path, workdir: Path) -> float:
    times, total = build_timeline(scenes, groups, audio)
    wav = workdir / "voice.m4a"
    mix_audio(audio, wav)
    frame = Frame(r, scenes)
    n = int(total * FPS)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(frame.draw(i / FPS, times).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 인코딩 실패")
    return total
