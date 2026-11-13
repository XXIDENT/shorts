"""픽셀아트 시리즈 'AI 신입 모니의 직업체험' 한 편을 만든다.

에피소드 대본은 config/jobs.yaml에 사람이(또는 Claude가) 직업마다 따로 쓴다.
퀘스트, 대사, 성공/실패, 무대, 효과가 편마다 다르고, 마지막 데이터 카드는
Frey & Osborne(2013, 옥스퍼드대) 연구의 실제 자동화 확률을 보여준다.

사용법:
  python -m shorts.jobs --no-upload                 # 다음 차례 직업으로 생성
  python -m shorts.jobs --job barista --tts silent --no-upload
  python -m shorts.jobs --list                      # 에피소드 목록
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from . import upload_make, upload_youtube
from .pixel import art, chiptune
from .pixel.art import C, FLOOR, SH, SW
from .pixel.scenes import SCENES
from .tts import _silence, duration

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "jobs_history.json"
W, H, FPS = 1080, 1920, 30
STAGE_Y = 300                      # 무대(1080x1080)가 시작하는 y
SCALE = W // SW                    # 6배
GAP, TAIL = 0.12, 1.0
BOT_Y = FLOOR + 30
HERO = "모니"
VOICE = os.environ.get("JOBS_TTS_VOICE", "ko-KR-SunHiNeural")
VOICE_RATE = os.environ.get("JOBS_TTS_RATE", "+28%")
VOICE_PITCH = os.environ.get("JOBS_TTS_PITCH", "+18Hz")

FONT_CANDIDATES = [
    os.environ.get("JOBS_FONT", ""),
    "/usr/share/fonts/opentype/unifont/unifont.otf",
    "/usr/share/fonts/truetype/unifont/unifont.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]

DATA_LINES = [
    "옥스퍼드대 연구가 본 {label} 자동화 확률은 {p}.",
    "2013년 옥스퍼드대 연구로는 {label} 자동화 확률 {p}.",
    "연구에선 {label}{iga} 기계로 바뀔 확률이 {p}래.",
]
OUTROS = [
    "다음 직업은 댓글로 추천해 줘!",
    "다음 체험할 직업, 댓글로 정해 줘!",
    "너라면 AI한테 맡길래? 댓글로 알려 줘.",
]
TITLES = [
    "AI가 {job} 하루 해봤더니 #Shorts",
    "AI 신입이 {job} 체험해 봄 #Shorts",
    "AI한테 {job}를 시켜봤다 #Shorts",
    "{job}, AI가 하면 몇 점? #Shorts",
]


def josa(word: str, pair=("이", "가")) -> str:
    ch = word.strip()[-1]
    if "가" <= ch <= "힣":
        return pair[0] if (ord(ch) - 0xAC00) % 28 else pair[1]
    return pair[1]


def pct(p: float) -> str:
    v = p * 100
    if v >= 10:
        return f"{v:.0f}%"
    if v >= 1:
        return f"{v:.1f}%".replace(".0%", "%")
    return f"{v:.1f}%"


# ---------------------------------------------------------------- 대본

@dataclass
class Seg:
    kind: str                 # hook | say | result | data | verdict | outro
    text: str
    q: int | None = None      # 퀘스트 번호(0부터)
    start: float = 0.0
    end: float = 0.0


def build_segments(ep: dict, seed: int) -> list[Seg]:
    rnd = random.Random(seed)
    segs = [Seg("hook", ep["hook"])]
    for i, q in enumerate(ep["quests"]):
        for line in q["say"]:
            segs.append(Seg("say", line, i))
        segs.append(Seg("result", q["after"], i))
    d = ep["data"]
    label = d["label"]
    segs.append(Seg("data", ep.get("data_say") or rnd.choice(DATA_LINES).format(
        label=label, iga=josa(label), p=pct(d["prob"]))))
    segs.append(Seg("verdict", ep["verdict_say"]))
    segs.append(Seg("outro", ep.get("outro") or rnd.choice(OUTROS)))
    return segs


def metadata(ep: dict, seed: int) -> dict:
    rnd = random.Random(seed)
    job = ep["job"]
    title = ep.get("title") or rnd.choice(TITLES).format(job=job)
    lines = [f"퀘스트 {i + 1}. {q['title']} - {'성공' if q['result'] == 'clear' else '실패'}"
             for i, q in enumerate(ep["quests"])]
    d = ep["data"]
    desc = (f"AI 신입 '{HERO}'의 직업체험 #{ep['num']:02d}: {job}\n\n" + "\n".join(lines) +
            f"\n\n2013년 연구의 자동화 확률: {pct(d['prob'])} ({d['occupation']})\n"
            f"{HERO}의 체감 대체 가능도: {ep['verdict']}% (영상 속 캐릭터의 의견이에요)\n\n"
            "자료: Frey, C. B. & Osborne, M. A. (2013), The Future of Employment, 옥스퍼드대 "
            "(미국 702개 직업 기준)\n픽셀아트, 음악, 음성은 코드로 만들었어요(AI 음성).\n\n"
            f"#Shorts #직업체험 #AI #{job.replace(' ', '')} #픽셀아트")
    return {"title": title[:100], "description": desc,
            "tags": ["직업체험", "AI", "픽셀아트", job, "자동화", "미래직업", "shorts"]}


# ---------------------------------------------------------------- 음성

def synthesize(lines: list[str], workdir: Path, engine: str | None = None) -> tuple[list[Path], str]:
    workdir.mkdir(parents=True, exist_ok=True)
    order = [engine] if engine else ["edge", "silent"]
    last = None
    for eng in order:
        try:
            paths = []
            for i, text in enumerate(lines):
                p = workdir / f"line{i:02d}.mp3"
                if eng == "edge":
                    import edge_tts
                    asyncio.run(edge_tts.Communicate(text, VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH).save(str(p)))
                else:
                    _silence(text, p)
                if p.stat().st_size == 0:
                    raise RuntimeError("빈 음성 파일")
                paths.append(p)
            return paths, eng
        except Exception as e:
            last = e
            print(f"[jobs] 음성 {eng} 실패: {e}")
    raise RuntimeError(f"모든 TTS 실패: {last}")


def timeline(segs: list[Seg], audio: list[Path]) -> float:
    t = 0.6                                   # 첫 0.6초는 타이틀만
    for s, p in zip(segs, audio):
        d = duration(p) + GAP
        if s.kind == "result":
            d += 0.35                         # 성공/실패 도장 볼 시간
        s.start, s.end = t, t + d
        t += d
    segs[0].start = 0.0
    return t + TAIL


def mix_voice(segs: list[Seg], audio: list[Path], total: float, out: Path) -> None:
    """각 문장을 자기 시작 시간에 놓는다."""
    inputs, filt = [], []
    for i, (s, p) in enumerate(zip(segs, audio)):
        inputs += ["-i", str(p)]
        start = s.start if i else 0.6
        filt.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,adelay={int(start * 1000)}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(audio))) +
                f"amix=inputs={len(audio)}:normalize=0,apad,atrim=0:{total:.2f}[out]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "[out]", "-c:a", "pcm_s16le", str(out)], check=True)


# ---------------------------------------------------------------- 화면

def _font_path() -> str:
    for p in FONT_CANDIDATES:
        if p and Path(p).exists():
            return p
    raise RuntimeError("폰트가 없어요: sudo apt install fonts-unifont")


class Fonts:
    def __init__(self):
        p = _font_path()
        idx = 1 if p.endswith(".ttc") else 0
        self.f = {s: ImageFont.truetype(p, s, index=idx) for s in (32, 48, 64, 96, 128)}

    def __getitem__(self, s):
        return self.f[s]


def text(d, xy, s, font, fill, anchor="la", shadow=6):
    x, y = xy
    if shadow:
        d.text((x + shadow, y + shadow), s, font=font, fill=C["black"], anchor=anchor)
    d.text((x, y), s, font=font, fill=fill, anchor=anchor)


def wrap(d, s: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for word in s.split(" "):
        test = f"{cur} {word}".strip()
        if d.textlength(test, font=font) <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:   # 한 단어가 너무 길면 글자 단위로 자른다
        while d.textlength(ln, font=font) > width:
            k = len(ln)
            while k > 1 and d.textlength(ln[:k], font=font) > width:
                k -= 1
            out.append(ln[:k])
            ln = ln[k:]
        out.append(ln)
    return out


def pixel_panel(d, x0, y0, x1, y1, fill, border=C["white"], u=6):
    """두꺼운 픽셀 테두리 상자(모서리 깎음)."""
    d.rectangle([x0 + u, y0, x1 - u, y1], fill=C["black"])
    d.rectangle([x0, y0 + u, x1, y1 - u], fill=C["black"])
    d.rectangle([x0 + u, y0 + u, x1 - u, y1 - u], fill=border)
    d.rectangle([x0 + 2 * u, y0 + 2 * u, x1 - 2 * u, y1 - 2 * u], fill=fill)


def heart(d, x, y, full: bool, u=6):
    rows = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#":
                d.rectangle([x + i * u, y + j * u, x + i * u + u - 1, y + j * u + u - 1],
                            fill=C["red"] if full else C["dgrey"])


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


class Renderer:
    def __init__(self, ep: dict, segs: list[Seg], seed: int):
        self.ep, self.segs, self.F = ep, segs, Fonts()
        self.scene = dict(SCENES[ep["scene"]])
        if ep.get("time"):
            self.scene["time"] = ep["time"]
        self.scene["props"] = list(self.scene.get("props", [])) + [tuple(p) for p in ep.get("props", [])]
        rnd = random.Random(seed)
        self.accent = rnd.choice([C["teal"], C["blue"], C["purple"], C["green"], C["pink"]])
        self.bg_hi = tuple(int(v * 0.35) for v in self.scene["wall"])
        self.looks = [art.npc_look(random.Random(seed + i)) for i in range(len(ep["quests"]) + 1)]
        self.quest_starts = [next(s.start for s in segs if s.q == i) for i in range(len(ep["quests"]))]
        self.results = [(s.start, ep["quests"][s.q]["result"]) for s in segs if s.kind == "result"]

    # 모니가 서 있어야 할 x
    def spot(self, seg: Seg) -> int:
        sp = self.scene["spots"]
        if seg.q is not None:
            return sp.get(self.ep["quests"][seg.q].get("spot", "center"), sp["center"])
        return sp["center"]

    def seg_at(self, t) -> int:
        return max((i for i, s in enumerate(self.segs) if s.start <= t), default=0)

    def stage(self, t: float) -> Image.Image:
        i = self.seg_at(t)
        seg = self.segs[i]
        q = self.ep["quests"][seg.q] if seg.q is not None else None
        img = art.background(self.scene, t)
        d = ImageDraw.Draw(img)
        art.draw_props(d, self.scene, t)
        if q:
            for name, x, *rest in q.get("props", []):
                kw = dict(rest[0]) if rest else {}
                y = kw.pop("y", FLOOR + 18)
                art.PROPS[name](d, x, y, t, **kw)

        # 손님
        npc_cfg = (q or {}).get("npc")
        if npc_cfg is not False and q is not None and (npc_cfg or self.scene.get("npc") is not None):
            nx = (npc_cfg or {}).get("x", self.scene.get("npc", 30)) if isinstance(npc_cfg, dict) else self.scene["npc"]
            mood = "normal"
            if seg.kind == "result":
                mood = "happy" if q["result"] == "clear" else "angry"
            mood = (npc_cfg or {}).get("mood", mood) if isinstance(npc_cfg, dict) and seg.kind != "result" else mood
            art.draw_npc(d, nx, BOT_Y + 2, t, self.looks[seg.q], mood, flip=nx > 90)

        # 모니 위치와 자세
        prev = self.spot(self.segs[i - 1]) if i else self.scene["spots"]["enter"]
        target = self.spot(seg)
        since = t - seg.start
        walk_t = 0.7 if i else 1.2
        x = target
        pose, face = "idle", "normal"
        if prev != target and since < walk_t:
            x = prev + (target - prev) * ease(since / walk_t)
            pose = "walk"
        if pose != "walk":
            if seg.kind == "hook":
                pose, face = "wave", "happy"
            elif seg.kind == "say":
                pose, face = q.get("pose", "work"), q.get("face", "focus")
            elif seg.kind == "result":
                ok = q["result"] == "clear"
                pose = ("jump" if since < 1.0 else "idle") if ok else ("shake" if since < 1.0 else "sad")
                face = q.get("face_after", "happy" if ok else "dizzy")
            elif seg.kind == "data":
                face = self.ep.get("data_face", "shock" if self.ep["data"]["prob"] >= 0.5 else "smug")
            elif seg.kind == "verdict":
                face = self.ep.get("verdict_face", "happy")
                pose = "idle"
            elif seg.kind == "outro":
                pose, face = "wave", "happy"
        self.bot_x = x
        htop = art.draw_bot(d, int(x), BOT_Y, t, pose, face, self.accent)

        # 효과
        if pose != "walk" and q:
            if seg.kind == "say":
                for fx in q.get("fx", []):
                    art.FX[fx](d, int(x) + 14, htop + 8, t)
            elif seg.kind == "result":
                ok = q["result"] == "clear"
                for fx in q.get("fx_after", ["sparkle", "coins"] if ok else ["smoke", "sweat"]):
                    fx_x = int(x) + (12 if fx in ("sweat",) else 0)
                    art.FX[fx](d, fx_x, htop + (2 if fx == "sweat" else 0), t)
        if seg.kind == "outro":
            art.fx_confetti(d, 0, 0, t)
        return img

    def frame(self, t: float) -> Image.Image:
        F = self.F
        i = self.seg_at(t)
        seg = self.segs[i]
        since = t - seg.start
        img = Image.new("RGB", (W, H), self.bg_hi)
        st = self.stage(t)
        if seg.kind in ("say", "result"):
            # 퀘스트 중에는 모니 쪽으로 카메라를 당긴다(120px 창 = 9배, 픽셀 격자 유지)
            q = ep_q = self.ep["quests"][seg.q]
            focus = self.bot_x
            npc = q.get("npc")
            if npc is not False and self.scene.get("npc") is not None:
                nx = npc.get("x", self.scene["npc"]) if isinstance(npc, dict) else self.scene["npc"]
                if abs(nx - focus) < 90:
                    focus = (focus + nx) / 2
            cx = int(min(max(focus, 60), SW - 60))
            st = st.crop((cx - 60, 54, cx + 60, 174))
        st = st.resize((W, W), Image.NEAREST)
        img.paste(st, (0, STAGE_Y))
        d = ImageDraw.Draw(img)
        ep = self.ep

        # ---- 위쪽 HUD
        text(d, (W // 2, 34), f"AI 신입 {HERO}의 직업체험 #{ep['num']:02d}", F[48], C["yellow"], "mt", 4)
        text(d, (W // 2, 100), ep["job"], F[96], C["white"], "mt", 6)
        done = [r for (at, r) in self.results if at <= t]
        hp = 3 - sum(1 for r in done if r == "fail")
        for k in range(3):
            heart(d, 48 + k * 54, 222, k < hp)
        coins = sum(1 for r in done if r == "clear") * ep.get("coin", 100)
        text(d, (W - 48, 224), f"G {coins:,}", F[48], C["yellow"], "ra", 4)
        n = len(ep["quests"])
        for k in range(n):   # 퀘스트 진행 칸
            x0 = W // 2 - (n * 60) // 2 + k * 60
            c = C["dgrey"]
            if k < len(done):
                c = C["green"] if done[k] == "clear" else C["red"]
            elif seg.q == k:
                c = C["yellow"] if int(t * 3) % 2 else C["orange"]
            d.rectangle([x0, 226, x0 + 42, 268], fill=C["black"])
            d.rectangle([x0 + 6, 232, x0 + 36, 262], fill=c)

        # ---- 무대 위 오버레이
        if seg.q is not None:
            q = ep["quests"][seg.q]
            label = f"QUEST {seg.q + 1}  {q['title']}"
            pixel_panel(d, 30, STAGE_Y + 24, W - 30, STAGE_Y + 120, C["navy"], C["yellow"])
            text(d, (W // 2, STAGE_Y + 48), label, F[48], C["white"], "mt", 4)
        if seg.kind == "result" and since < 1.6:
            ok = ep["quests"][seg.q]["result"] == "clear"
            s = "CLEAR!" if ok else "FAIL..."
            pop = 1 + 0.4 * max(0, 1 - since / 0.25)
            size = 128
            col = C["green"] if ok else C["red"]
            tmp = Image.new("RGBA", (900, 220), (0, 0, 0, 0))
            td = ImageDraw.Draw(tmp)
            td.text((458, 118), s, font=F[size], fill=C["black"] + (255,), anchor="mm")
            td.text((450, 110), s, font=F[size], fill=col + (255,), anchor="mm")
            tmp = tmp.resize((int(900 * pop), int(220 * pop)), Image.NEAREST)
            img.paste(tmp, (W // 2 - tmp.width // 2, STAGE_Y + 230 - tmp.height // 2), tmp)
        if seg.kind == "hook" and t < 2.2:
            k = ease(t / 0.35) if t < 1.8 else 1 - ease((t - 1.8) / 0.4)
            y0 = STAGE_Y + 260 + int((1 - k) * -120)
            if k > 0.02:
                pixel_panel(d, 90, y0, W - 90, y0 + 380, C["navy"], self.accent)
                text(d, (W // 2, y0 + 50), f"DAY {ep['num']:02d}", F[64], C["yellow"], "mt", 4)
                text(d, (W // 2, y0 + 140), ep["job"], F[128], C["white"], "mt", 8)
                text(d, (W // 2, y0 + 290), "체험 시작!", F[48], C["cyan"], "mt", 4)
        if seg.kind in ("data", "verdict"):
            self.data_card(img, d, seg, since)

        # ---- 대화창
        y0, y1 = 1420, 1700
        pixel_panel(d, 24, y0, W - 24, y1, (20, 22, 40), C["white"])
        speaker = HERO
        pixel_panel(d, 50, y0 - 46, 50 + 60 + 48 * len(speaker), y0 + 30, self.accent, C["white"])
        text(d, (80 + 48 * len(speaker) // 2, y0 - 22), speaker, F[48], C["white"], "mt", 3)
        dur = max(0.1, seg.end - seg.start)
        shown = seg.text if since > dur * 0.55 else seg.text[: int(len(seg.text) * since / (dur * 0.55)) + 1]
        lines = wrap(d, seg.text, F[48], W - 160)
        # 줄 바꿈 위치를 고정하려고 전체 문장 기준으로 자른 뒤 보이는 만큼만 그린다
        left = len(shown)
        for k, ln in enumerate(lines[:4]):
            part = ln[:max(0, left)]
            left -= len(ln) + 1
            text(d, (80, y0 + 60 + k * 64), part, F[48], C["white"], "la", 3)
        if since > dur * 0.6 and int(t * 3) % 2:
            d.polygon([(W - 90, y1 - 60), (W - 60, y1 - 60), (W - 75, y1 - 42)], fill=C["yellow"])

        # ---- 아래 출처(유튜브 UI가 덮는 자리라 작게)
        foot = "자료: Frey & Osborne(2013) 옥스퍼드대, 미국 702개 직업" if seg.kind in ("data", "verdict") \
            else "픽셀·음악·음성 모두 코드로 만든 AI 콘텐츠"
        text(d, (W // 2, 1730), foot, F[32], (150, 150, 170), "mt", 0)
        return img

    def data_card(self, img, d, seg, since):
        F, ep = self.F, self.ep
        p = ep["data"]["prob"]
        dark = Image.new("RGB", (W, 760), (10, 10, 20))
        region = img.crop((0, STAGE_Y + 140, W, STAGE_Y + 900))
        img.paste(Image.blend(region, dark, 0.55), (0, STAGE_Y + 140))
        x0, y0, x1 = 60, STAGE_Y + 160, W - 60
        pixel_panel(d, x0, y0, x1, y0 + 560, (24, 28, 52), C["cyan"])
        text(d, (W // 2, y0 + 40), "AI 대체 가능성", F[64], C["cyan"], "mt", 4)
        rows = [("2013 옥스퍼드 연구", p, C["orange"], 0.0)]
        if seg.kind == "verdict":
            rows.append((f"{HERO} 체감 (직접 해봄)", ep["verdict"] / 100, self.accent, 0.0))
        for k, (label, val, col, _) in enumerate(rows):
            yy = y0 + 150 + k * 190
            text(d, (x0 + 50, yy), label, F[48], C["white"], "la", 3)
            grow = ease(since / 0.9) if (seg.kind == "data" or k == 1) else 1.0
            blocks = 20
            lit = int(round(val * blocks * grow))
            bx, bw = x0 + 50, (x1 - x0 - 100) // blocks
            for b in range(blocks):
                c = col if b < lit else C["dgrey"]
                d.rectangle([bx + b * bw, yy + 66, bx + b * bw + bw - 8, yy + 116], fill=c)
            shown = val * 100 * grow
            label_v = pct(shown / 100) if grow >= 1 else f"{shown:.0f}%"
            text(d, (x1 - 50, yy), label_v, F[64], col, "ra", 4)
        if seg.kind == "data":
            text(d, (W // 2, y0 + 470), ep["data"]["label"], F[32], (180, 180, 200), "mt", 0)


def render(ep: dict, segs: list[Seg], audio: list[Path], out: Path, work: Path, seed: int) -> float:
    total = timeline(segs, audio)
    voice = work / "voice.wav"
    mix_voice(segs, audio, total, voice)
    cues = [(0.05, "title")]
    for s in segs:
        if s.kind == "say" and s.start == min(x.start for x in segs if x.q == s.q):
            cues.append((s.start, "quest"))
        elif s.kind == "result":
            cues.append((s.start, "clear" if ep["quests"][s.q]["result"] == "clear" else "fail"))
        elif s.kind == "data":
            cues.append((s.start, "reveal"))
        elif s.kind == "outro":
            cues.append((s.start, "levelup"))
    bgm = work / "bgm.wav"
    chiptune.write_track(bgm, total, seed, cues, ep.get("mood", "happy"))
    r = Renderer(ep, segs, seed)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(voice), "-i", str(bgm),
         "-filter_complex", "[2:a]volume=0.32[m];[1:a][m]amix=inputs=2:normalize=0:duration=first[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
         "-tune", "animation", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", "-t", f"{total:.2f}", str(out)],
        stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        proc.stdin.write(r.frame(i / FPS).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 인코딩 실패")
    return total


# ---------------------------------------------------------------- 실행

def load_episodes() -> list[dict]:
    return yaml.safe_load((ROOT / "config" / "jobs.yaml").read_text())["episodes"]


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def pick(episodes: list[dict], history: list[dict]) -> dict | None:
    done = {h["job"] for h in history}
    todo = [e for e in episodes if e["id"] not in done and not e.get("draft")]
    return min(todo, key=lambda e: e["num"]) if todo else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job")
    ap.add_argument("--tts", choices=["edge", "silent"])
    ap.add_argument("--out", type=Path, default=ROOT / "out")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--frames", help="영상 대신 지정한 시각(초, 쉼표)의 정지 화면만 PNG로 저장")
    args = ap.parse_args(argv)

    episodes = load_episodes()
    history = load_history()
    if args.list:
        done = {h["job"] for h in history}
        for e in sorted(episodes, key=lambda e: e["num"]):
            print(f"#{e['num']:02d} {e['id']:<14} {e['job']:<10} {'완료' if e['id'] in done else ''}")
        return 0
    ep = next(e for e in episodes if e["id"] == args.job) if args.job else pick(episodes, history)
    if ep is None:
        print("[jobs] 남은 에피소드가 없어요. config/jobs.yaml에 새 직업을 추가하세요.")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    seed = (ep["num"] * 7919 + len(history)) & 0xFFFF
    segs = build_segments(ep, seed)
    print(f"[jobs] #{ep['num']:02d} {ep['job']} ({len(segs)}줄)")

    work = args.out / f"work-jobs-{stamp}"
    audio, engine = synthesize([s.text for s in segs], work / "tts", args.tts)
    print(f"[jobs] 음성 엔진: {engine}")
    args.out.mkdir(parents=True, exist_ok=True)

    if args.frames:
        timeline(segs, audio)
        r = Renderer(ep, segs, seed)
        for ts in args.frames.split(","):
            p = args.out / f"jobs-{ep['id']}-{float(ts):05.1f}s.png"
            r.frame(float(ts)).save(p)
            print(f"[jobs] {p}")
        shutil.rmtree(work, ignore_errors=True)
        return 0

    video = args.out / f"{stamp}-job-{ep['id']}.mp4"
    secs = render(ep, segs, audio, video, work, seed)
    meta = metadata(ep, seed)
    (args.out / f"{stamp}-job-{ep['id']}.json").write_text(json.dumps(
        {**meta, "script": [s.text for s in segs], "seconds": round(secs, 1), "tts": engine},
        ensure_ascii=False, indent=2))
    shutil.rmtree(work, ignore_errors=True)
    print(f"[jobs] 영상: {video} ({secs:.1f}초, {video.stat().st_size / 1e6:.1f}MB)")

    video_id = None
    if not args.no_upload and upload_make.configured():
        video_id = f"make:{upload_make.upload(video, meta)}"
        print(f"[jobs] Make.com으로 전송 완료 ({video_id})")
    elif not args.no_upload and upload_youtube.configured():
        video_id = upload_youtube.upload(video, meta)
        print(f"[jobs] 업로드 완료: https://youtu.be/{video_id}")
    elif not args.no_upload:
        print("[jobs] 업로드 설정이 없어 건너뜀")

    if not args.no_upload:
        history.append({"job": ep["id"], "at": stamp, "video_id": video_id})
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
