"""'모니의 세계여행': 픽셀 3D(복셀) 거리를 3인칭 시점으로 걸으며 나라를 소개하는 쇼츠.

- 무대: shorts/pixel/world.py가 나라별 색, 국기, 나무, 랜드마크로 거리를 만든다
- 숫자: 세계은행 API에서 그 나라와 한국의 최신 값(기대수명, 1인당 GDP 등)을 받아 비교
- 말: config/travel.yaml에 나라마다 직접 쓴 첫인사, 랜드마크, 문화, 마무리 + 데이터 문장
- 카메라: 하늘에서 내려와 → 모니 뒤 3인칭 → 랜드마크 올려다보기 → 모니 정면(셀카) → 하늘로

사용법:
  python -m shorts.travel --no-upload                    # 다음 차례 나라
  python -m shorts.travel --country france --tts silent --offline --no-upload
  python -m shorts.travel --country france --offline --frames 2,10,20
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import random
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

from .once import uploaded_recently
from . import upload_instagram, upload_make, upload_youtube
from .jobs import Fonts, cta, josa, mix_voice, pixel_panel, synthesize, text, wrap
from .pixel import chiptune
from .pixel import world as Wd
from .pixel.art import C
from .pixel.voxel import render as vrender
from .tts import duration

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "travel_history.json"
W, H = 1080, 1920
LW, LH = 180, 320                 # 3D를 그리는 해상도(6배 확대)
FPS = int(os.environ.get("TRAVEL_FPS", "15"))
GAP, TAIL = 0.12, 1.2
MAX_BYTES = int(os.environ.get("TRAVEL_MAX_BYTES", str(4_500_000)))
HERO = "모니"

# 세계은행 지표: (라벨, 형식, 위가 '많다'의 뜻)
INDICATORS = {
    "SP.DYN.LE00.IN": ("기대수명", "years"),
    "NY.GDP.PCAP.CD": ("1인당 GDP", "usd"),
    "SP.DYN.TFRT.IN": ("출산율", "births"),
    "IT.NET.USER.ZS": ("인터넷 사용률", "pct"),
    "SP.URB.TOTL.IN.ZS": ("도시 인구 비율", "pct"),
    "AG.LND.FRST.ZS": ("숲 면적 비율", "pct"),
    "SP.POP.TOTL": ("인구", "people"),
    "SP.POP.65UP.TO.ZS": ("65세 이상 비율", "pct"),
    "SP.POP.0014.TO.ZS": ("14세 이하 비율", "pct"),
}

FACT_LINES = {
    "SP.DYN.LE00.IN": ["여기 사람들 기대수명은 {v}. 한국은 {k}야.", "{c} 기대수명은 {v}, 한국은 {k}."],
    "NY.GDP.PCAP.CD": ["1인당 GDP는 {v}. 한국은 {k}.", "{c} 사람 한 명이 버는 돈, 평균 {v}. 한국은 {k}야."],
    "SP.DYN.TFRT.IN": ["출산율은 {v}. 한국은 {k}.", "여성 한 명이 낳는 아이 수, {v}. 한국은 {k}."],
    "IT.NET.USER.ZS": ["인터넷 쓰는 사람은 {v}. 한국은 {k}.", "여기 인터넷 사용률 {v}. 한국은 {k}야."],
    "SP.URB.TOTL.IN.ZS": ["도시에 사는 사람이 {v}. 한국은 {k}.", "도시 인구 비율은 {v}, 한국은 {k}야."],
    "AG.LND.FRST.ZS": ["땅의 {v}가 숲이야. 한국은 {k}.", "숲 면적은 국토의 {v}. 한국은 {k}."],
    "SP.POP.TOTL": ["인구는 {v}. 한국은 {k}야.", "여기 사는 사람은 {v}. 한국은 {k}."],
    "SP.POP.65UP.TO.ZS": ["65세 이상이 {v}. 한국은 {k}.", "노인 인구 비율은 {v}, 한국은 {k}야."],
    "SP.POP.0014.TO.ZS": ["14세 이하 어린이가 {v}. 한국은 {k}.", "어린이 비율은 {v}, 한국은 {k}야."],
}
REACT_MORE = ["한국의 {r}배!", "무려 {r}배 차이야.", "생각보다 차이가 크지?"]
REACT_LESS = ["한국보다 훨씬 적어.", "한국의 {p} 수준이야.", "의외지?"]
REACT_SAME = ["거의 비슷해!", "한국이랑 거의 같아."]
OUTROS = ["다음 여행지는 댓글로 정해 줘! 구독이랑 좋아요도 꾹!", "다음엔 어디 갈까? 댓글로 추천해 줘! 구독, 좋아요 부탁해!",
          "너는 여기 살아 보고 싶어? 댓글로 알려 줘! 구독이랑 좋아요도!"]
TITLES = ["AI 로봇이 {c} 가봤더니 #Shorts", "모니의 {c} 여행, 한국이랑 이렇게 달라 #Shorts",
          "{c} vs 한국, 숫자로 비교해 봤어 #Shorts", "픽셀 로봇의 {c} 여행 #Shorts"]


def fmt(v: float, kind: str) -> str:
    if kind == "years":
        return f"{v:.1f}세"
    if kind == "usd":
        return f"{v / 1e4:.1f}만 달러" if v >= 1e4 else f"{v:,.0f}달러"
    if kind == "births":
        return f"{v:.2f}명"
    if kind == "pct":
        return f"{v:.0f}%"
    if kind == "people":
        return f"{v / 1e8:.1f}억 명" if v >= 1e8 else f"{v / 1e4:,.0f}만 명"
    return f"{v:,.1f}"


# ---------------------------------------------------------------- 데이터

def fetch_facts(iso2: str, fixture: Path | None = None) -> dict[str, dict]:
    """{지표: {"c": 나라 값, "k": 한국 값, "year": 연도}}"""
    if fixture:
        return json.loads(fixture.read_text())[iso2]
    from .data import _get
    out = {}
    for ind in INDICATORS:
        try:
            rows = _get(f"country/{iso2};KR/indicator/{ind}", mrnev=1)
        except Exception as e:
            print(f"[travel] {ind} 실패: {e}")
            continue
        vals = {r["country"]["id"]: (r["value"], r["date"]) for r in rows if r["value"] is not None}
        if iso2 in vals and "KR" in vals:
            out[ind] = {"c": vals[iso2][0], "k": vals["KR"][0], "year": vals[iso2][1]}
    return out


def pick_facts(facts: dict, rnd: random.Random, n=3, prefer: list[str] | None = None) -> list[str]:
    """한국과 차이가 큰 지표를 고르되, 매번 같은 조합이 되지 않게 약간 섞는다."""
    def score(ind):
        c, k = facts[ind]["c"], facts[ind]["k"]
        if c <= 0 or k <= 0:
            return 0
        return abs(math.log(c / k)) + rnd.random() * 0.25
    pool = sorted(facts, key=score, reverse=True)
    chosen = [p for p in (prefer or []) if p in facts][:1]
    for ind in pool:
        if ind not in chosen and len(chosen) < n:
            chosen.append(ind)
    return chosen


# ---------------------------------------------------------------- 대본

@dataclass
class Seg:
    kind: str           # hook | fact | landmark | culture | closing | outro
    text: str
    fact: str | None = None
    start: float = 0.0
    end: float = 0.0


def fact_line(ind: str, cname: str, f: dict, rnd: random.Random) -> str:
    label, kind = INDICATORS[ind]
    v, k = f["c"], f["k"]
    line = rnd.choice(FACT_LINES[ind]).format(c=cname, v=fmt(v, kind), k=fmt(k, kind))
    ratio = v / k if k else 1
    if 0.9 <= ratio <= 1.1:
        react = rnd.choice(REACT_SAME)
    elif ratio > 1:
        react = rnd.choice(REACT_MORE[:2] if ratio >= 1.5 else REACT_MORE[2:]).format(r=f"{ratio:.1f}".rstrip("0").rstrip("."))
    else:
        react = rnd.choice(REACT_LESS).format(p=f"{ratio * 100:.0f}%")
    return f"{line} {react}"


def build_segments(ct: dict, facts: dict, seed: int) -> list[Seg]:
    rnd = random.Random(seed)
    chosen = pick_facts(facts, rnd, 3, ct.get("prefer"))
    segs = [Seg("hook", ct["hook"])]
    for ind in chosen[:2]:
        segs.append(Seg("fact", fact_line(ind, ct["name"], facts[ind], rnd), ind))
    segs.append(Seg("landmark", ct["landmark_say"]))
    segs.append(Seg("culture", ct["culture_say"]))
    for ind in chosen[2:]:
        segs.append(Seg("fact", fact_line(ind, ct["name"], facts[ind], rnd), ind))
    segs.append(Seg("closing", ct["closing"]))
    segs.append(Seg("outro", ct.get("outro") or rnd.choice(OUTROS)))
    return segs


def timeline(segs: list[Seg], audio: list[Path]) -> float:
    t = 1.0                                       # 첫 1초는 하늘에서 내려오는 장면
    for s, p in zip(segs, audio):
        d = duration(p) + GAP + (0.4 if s.kind == "fact" else 0)
        s.start, s.end = t, t + d
        t += d
    segs[0].start = 0.0
    return t + TAIL


def metadata(ct: dict, segs: list[Seg], facts: dict, seed: int) -> dict:
    rnd = random.Random(seed)
    lines = []
    for s in segs:
        if s.fact:
            label, kind = INDICATORS[s.fact]
            f = facts[s.fact]
            lines.append(f"- {label}: {ct['name']} {fmt(f['c'], kind)} / 한국 {fmt(f['k'], kind)} ({f['year']}년)")
    desc = (f"모니의 세계여행 #{ct['num']:02d}: {ct['name']}\n\n" + "\n".join(lines) +
            "\n\n자료: 세계은행(World Bank) 오픈데이터, 각 지표의 최신 공개 연도\n"
            "\n"
            f"#Shorts #세계여행 #{ct['name'].replace(' ', '')} #픽셀아트")
    return {"title": (ct.get("title") or rnd.choice(TITLES).format(c=ct["name"]))[:100], "description": desc,
            "tags": ["세계여행", ct["name"], "나라비교", "픽셀아트", "복셀", "shorts"]}


# ---------------------------------------------------------------- 카메라와 장면

def lerp(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


def smooth(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


class Director:
    """시간 t에 모니 위치, 카메라 위치/시선, 모니 표정을 정한다."""

    def __init__(self, segs: list[Seg], total: float, seed: int):
        self.segs, self.total = segs, total
        self.z0, self.z1 = 18.0, float(Wd.LANDMARK_Z - 44)
        # 셀카(문화) 구간에서는 멈춘다
        walk = sum(s.end - s.start for s in segs if s.kind not in ("culture",))
        self.speed = (self.z1 - self.z0) / max(1.0, walk + TAIL)
        self.side = random.Random(seed).choice([-1, 1])

    def seg_at(self, t):
        return max((i for i, s in enumerate(self.segs) if s.start <= t), default=0)

    def moni_z(self, t):
        z = self.z0
        for s in self.segs:
            if s.start >= t:
                break
            dt = min(t, s.end) - s.start
            if s.kind != "culture":
                z += dt * self.speed
        if t > self.segs[-1].end:
            z += (t - self.segs[-1].end) * self.speed
        return min(z, self.z1)

    def walking(self, t):
        return self.segs[self.seg_at(t)].kind != "culture"

    def behind(self, mz, t):
        sway = math.sin(t * 0.6) * 1.5
        return (Wd.CENTER + 5 * self.side + sway, 21.0, mz - 24), (Wd.CENTER, 5.0, mz + 30)

    def camera(self, t):
        i = self.seg_at(t)
        s = self.segs[i]
        mz = self.moni_z(t)
        since, dur = t - s.start, max(0.1, s.end - s.start)
        cam, tgt = self.behind(mz, t)
        if s.kind == "hook":
            k = smooth(since / max(1.0, dur + 1.0 - 0.4))
            air = ((Wd.CENTER + 22 * self.side, 56.0, mz - 34), (Wd.CENTER, 4.0, mz + 50))
            cam, tgt = lerp(air[0], cam, k), lerp(air[1], tgt, k)
        elif s.kind == "landmark":
            k = smooth(since / 1.2)
            # 모니 눈높이 1인칭: 모니가 보는 랜드마크
            up = ((Wd.CENTER - 1, 11.0, mz + 3), (Wd.CENTER, 28.0, Wd.LANDMARK_Z + 12))
            cam, tgt = lerp(cam, up[0], k), lerp(tgt, up[1], k)
        elif s.kind == "culture":
            k = smooth(since / 1.0)
            a = math.pi * 0.15 * self.side + since * 0.08
            front = ((Wd.CENTER + math.sin(a) * 21, 13.0, mz + math.cos(a) * 21), (Wd.CENTER, 8.0, mz))
            cam, tgt = lerp(cam, front[0], k), lerp(tgt, front[1], k)
        elif s.kind == "fact" and i and self.segs[i - 1].kind == "culture":
            # 셀카 시점에서 다시 뒤로 돌아온다
            k = smooth(since / 1.0)
            pc, pt = self.camera(self.segs[i - 1].end - 1e-3)
            cam, tgt = lerp(pc, cam, k), lerp(pt, tgt, k)
        elif s.kind in ("closing", "outro"):
            base = self.segs[[x.kind for x in self.segs].index("closing")].start
            k = smooth((t - base) / 4.0)
            air = ((Wd.CENTER + 18 * self.side, 46.0, mz - 26), (Wd.CENTER, 26.0, Wd.LANDMARK_Z + 10))
            cam, tgt = lerp(cam, air[0], k), lerp(tgt, air[1], k)
        return cam, tgt

    def clamp(self, p):
        lim = (Wd.GX - 2, Wd.GY - 2, Wd.GZ - 2)
        return tuple(min(max(v, 1.0), m) for v, m in zip(p, lim))

    def face(self, t):
        s = self.segs[self.seg_at(t)]
        return "shock" if s.kind in ("landmark",) else "happy"


class Frames:
    def __init__(self, ct: dict, segs: list[Seg], facts: dict, total: float, seed: int):
        self.ct, self.segs, self.facts = ct, segs, facts
        self.grid, self.pal, self.info = Wd.build_world(ct, seed)
        for name, rgb in ct.get("flag_colors", {}).items():
            self.pal(name, tuple(rgb))
        self.dir = Director(segs, total, seed)
        rnd = random.Random(seed + 1)
        self.walkers = []
        for _ in range(12):
            side = rnd.choice([-1, 1])
            x = (Wd.ROAD_X0 - rnd.randint(2, 4)) if side < 0 else (Wd.ROAD_X1 + rnd.randint(1, 3))
            self.walkers.append({"x": x, "z": rnd.uniform(10, Wd.LANDMARK_Z - 40), "v": rnd.choice([-1, 1]) * rnd.uniform(2, 4),
                                 "look": {"shirt": f"shirt{rnd.randint(0, 7)}", "skin": rnd.choice(["skin1", "skin2", "skin3"]),
                                          "hair": rnd.choice(["hair1", "hair2", "hair3"])}})
        self.sky = [tuple(x) for x in ct.get("sky", [(90, 150, 230), (190, 220, 245)])]
        self.F = None

    def scene(self, t: float) -> Image.Image:
        g = self.grid.copy()
        for fx, fz in self.info["flags"]:
            Wd.flagpole(g, self.pal, fx, fz, self.ct["flag"], t=t)
        span = Wd.LANDMARK_Z - 50
        for w in self.walkers:
            z = 10 + (w["z"] + w["v"] * t - 10) % span
            Wd.person(g, self.pal, w["x"], int(z), t, w["look"], 1 if w["v"] > 0 else -1)
        mz = self.dir.moni_z(t)
        Wd.moni(g, self.pal, Wd.CENTER - 1, mz, t, self.dir.walking(t), self.dir.face(t))
        cam, tgt = self.dir.camera(t)
        cam = self.dir.clamp(cam)
        img = vrender(g, self.pal, cam, tgt, LW, LH, sky_top=self.sky[0], sky_bottom=self.sky[1],
                      fog=self.sky[1], fog_dist=190)
        return Image.fromarray(img).resize((W, H), Image.NEAREST)

    def flag_icon(self, d, x, y, u=10):
        px = Wd.flag_pixels(self.ct["flag"])
        d.rectangle([x - 4, y - 4, x + len(px[0]) * u + 3, y + len(px) * u + 3], fill=C["black"])
        for j, row in enumerate(px):
            for i, name in enumerate(row):
                c = tuple(int(v) for v in self.pal.colors[self.pal(name)])
                d.rectangle([x + i * u, y + j * u, x + i * u + u - 1, y + j * u + u - 1], fill=c)

    def frame(self, t: float) -> Image.Image:
        if self.F is None:
            self.F = Fonts()
        F, ct = self.F, self.ct
        img = self.scene(t)
        d = ImageDraw.Draw(img, "RGBA")
        i = self.dir.seg_at(t)
        seg = self.segs[i]
        since = t - seg.start

        # 위쪽: 시리즈 이름, 나라 이름, 국기
        d.rectangle([0, 0, W, 250], fill=(10, 12, 24, 150))
        text(d, (W // 2, 28), f"모니의 세계여행 #{ct['num']:02d}", F[48], C["yellow"], "mt", 4)
        name_w = d.textlength(ct["name"], font=F[96])
        fx = int(W // 2 - (name_w + 120) // 2)
        self.flag_icon(d, fx, 112, 10)
        text(d, (fx + 120, 96), ct["name"], F[96], C["white"], "la", 6)

        # 데이터 카드
        if seg.kind == "fact":
            label, kind = INDICATORS[seg.fact]
            f = self.facts[seg.fact]
            k = min(1.0, since / 0.8)
            y0 = 300
            pixel_panel(d, 50, y0, W - 50, y0 + 330, (16, 20, 44), C["cyan"])
            text(d, (W // 2, y0 + 34), label, F[64], C["cyan"], "mt", 4)
            mx = max(f["c"], f["k"]) or 1
            for r, (nm, v, col) in enumerate([(ct["name"], f["c"], C["orange"]), ("한국", f["k"], C["blue"])]):
                yy = y0 + 130 + r * 92
                text(d, (90, yy), nm, F[48], C["white"], "la", 3)
                bx0, bx1 = 300, W - 360
                blocks = 14
                lit = int(round(v / mx * blocks * k))
                bw = (bx1 - bx0) // blocks
                for b in range(blocks):
                    d.rectangle([bx0 + b * bw, yy + 4, bx0 + b * bw + bw - 6, yy + 48],
                                fill=col if b < lit else C["dgrey"])
                text(d, (W - 80, yy), fmt(v, kind), F[48], col, "ra", 3)

        if seg.kind == "outro":
            cta(d, F, 1200, since)

        # 대화창
        y0, y1 = 1440, 1700
        pixel_panel(d, 24, y0, W - 24, y1, (20, 22, 40), C["white"])
        pixel_panel(d, 50, y0 - 46, 50 + 60 + 48 * len(HERO), y0 + 30, C["teal"], C["white"])
        text(d, (80 + 48 * len(HERO) // 2, y0 - 22), HERO, F[48], C["white"], "mt", 3)
        dur = max(0.1, seg.end - seg.start)
        shown = len(seg.text) if since > dur * 0.55 else int(len(seg.text) * since / (dur * 0.55)) + 1
        left = shown
        for k2, ln in enumerate(wrap(d, seg.text, F[48], W - 160)[:3]):
            text(d, (80, y0 + 54 + k2 * 64), ln[:max(0, left)], F[48], C["white"], "la", 3)
            left -= len(ln) + 1
        if seg.kind == "fact":
            text(d, (W // 2, 1726), "자료: 세계은행 오픈데이터", F[32], (190, 190, 210), "mt", 3)
        return img


_FR: Frames | None = None


def _work(t: float) -> bytes:
    return _FR.frame(t).convert("RGB").tobytes()


def render_video(fr: Frames, segs: list[Seg], audio: list[Path], total: float, out: Path, work: Path, seed: int):
    global _FR
    voice = work / "voice.wav"
    mix_voice(segs, audio, total, voice)
    cues = [(0.05, "title")] + [(s.start, "reveal") for s in segs if s.kind == "fact"] + \
           [(s.start, "levelup") for s in segs if s.kind == "outro"]
    bgm = work / "bgm.wav"
    chiptune.write_track(bgm, total, seed, cues, "happy")
    _FR = fr
    n = int(total * FPS)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(voice), "-i", str(bgm),
         "-filter_complex", "[2:a]volume=0.3[m];[1:a][m]amix=inputs=2:normalize=0:duration=first[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "27",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
         "-t", f"{total:.2f}", str(out)], stdin=subprocess.PIPE)
    procs = max(1, (os.cpu_count() or 2))
    ctx = mp.get_context("fork")
    with ctx.Pool(procs) as pool:
        for i, buf in enumerate(pool.imap(_work, [k / FPS for k in range(n)], chunksize=4)):
            proc.stdin.write(buf)
            if i % (FPS * 5) == 0:
                print(f"[travel] {i}/{n} 프레임")
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 인코딩 실패")
    # Make.com 무료 요금제 파일 크기 제한(5MB)을 넘지 않게 필요하면 다시 압축
    crf = 27
    while out.stat().st_size > MAX_BYTES and crf < 40:
        crf += 4
        tmp = out.with_suffix(".tmp.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-c:v", "libx264", "-preset", "medium",
                        "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp)],
                       check=True)
        tmp.replace(out)
        print(f"[travel] 용량 줄이기: crf {crf}, {out.stat().st_size / 1e6:.1f}MB")


# ---------------------------------------------------------------- 실행

def load_countries() -> list[dict]:
    return yaml.safe_load((ROOT / "config" / "travel.yaml").read_text())["countries"]


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--country")
    ap.add_argument("--tts", choices=["edge", "silent"])
    ap.add_argument("--out", type=Path, default=ROOT / "out")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--offline", action="store_true", help="세계은행 대신 tests/fixtures/travel.json 사용")
    ap.add_argument("--frames")
    args = ap.parse_args(argv)

    countries = load_countries()
    history = load_history()
    if not args.no_upload and not args.country and uploaded_recently(history):
        print("[travel] 최근 4시간 안에 이미 올렸어요. 하루 한 편이라 건너뜁니다.")
        return 0
    if args.country:
        ct = next(c for c in countries if c["id"] == args.country)
    else:
        done = {h["country"] for h in history}
        todo = [c for c in countries if c["id"] not in done]
        if not todo:
            print("[travel] 남은 나라가 없어요. config/travel.yaml에 추가하세요.")
            return 0
        ct = min(todo, key=lambda c: c["num"])
    seed = (ct["num"] * 104729 + len(history)) & 0xFFFF
    fixture = ROOT / "tests" / "fixtures" / "travel.json" if args.offline else None
    facts = fetch_facts(ct["iso2"], fixture)
    if len(facts) < 3:
        raise SystemExit(f"[travel] {ct['name']} 데이터가 부족해요 ({len(facts)}개)")
    segs = build_segments(ct, facts, seed)
    print(f"[travel] #{ct['num']:02d} {ct['name']}: " + " / ".join(s.text for s in segs))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    work = args.out / f"work-travel-{stamp}"
    audio, engine = synthesize([s.text for s in segs], work / "tts", args.tts)
    total = timeline(segs, audio)
    args.out.mkdir(parents=True, exist_ok=True)
    fr = Frames(ct, segs, facts, total, seed)
    if args.frames:
        for ts in args.frames.split(","):
            p = args.out / f"travel-{ct['id']}-{float(ts):05.1f}s.png"
            fr.frame(float(ts)).save(p)
            print(f"[travel] {p}")
        shutil.rmtree(work, ignore_errors=True)
        return 0

    video = args.out / f"{stamp}-travel-{ct['id']}.mp4"
    render_video(fr, segs, audio, total, video, work, seed)
    meta = metadata(ct, segs, facts, seed)
    (args.out / f"{stamp}-travel-{ct['id']}.json").write_text(json.dumps(
        {**meta, "script": [s.text for s in segs], "seconds": round(total, 1), "tts": engine},
        ensure_ascii=False, indent=2))
    shutil.rmtree(work, ignore_errors=True)
    print(f"[travel] 영상: {video} ({total:.1f}초, {video.stat().st_size / 1e6:.1f}MB, 음성 {engine})")

    video_id = None
    if not args.no_upload and upload_make.configured():
        video_id = f"make:{upload_make.upload(video, meta)}"
        print(f"[travel] Make.com으로 전송 완료 ({video_id})")
    elif not args.no_upload and upload_youtube.configured():
        video_id = upload_youtube.upload(video, meta)
        print(f"[travel] 업로드 완료: https://youtu.be/{video_id}")
    if not args.no_upload:
        upload_instagram.try_upload(video, meta, "travel")
        history.append({"country": ct["id"], "at": stamp, "video_id": video_id})
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
