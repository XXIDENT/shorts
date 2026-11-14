"""'모니의 세계여행' 여행 퀘스트판 (2026-11-14 개편).

통계 비교 대신, 그 나라에서 실제로 해 보는 퀘스트 3개(음식·물가·교통·예절)를 성공/실패로 보여 주고,
첫 1초에 던진 질문(대개 물가)의 정답을 마지막에 공개한다. 화면은 직업체험의 픽셀 무대를 그대로 쓰고,
퀘스트마다 무대(편의점, 전철, 식당, 시장 등)를 바꾼다.

대본: config/trips.yaml (나라 이름·국기는 config/travel.yaml에서 가져온다)
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

from . import jobs as J
from . import lang as L
from . import upload_instagram, upload_make, upload_youtube
from .jobs import C, HERO, W, Seg, big_title, ease, pixel_panel, text
from .once import uploaded_recently
from .pixel import world as Wd
from .pixel.scenes import SCENES

ROOT = Path(__file__).resolve().parent.parent
HISTORY = L.data_path("trip_history.json")
TRIP_HOURS = (9, 21)

OUTROS = ["다음 여행지는 댓글로 정해 줘! 구독이랑 좋아요도 꾹!",
          "다음엔 어느 나라 갈까? 댓글로 추천해 줘! 구독, 좋아요 부탁해!",
          "너는 이 퀘스트 성공할 수 있어? 댓글로 알려 줘! 구독이랑 좋아요도!"]
TITLES = ["AI 로봇이 {c}에서 살아남기 #Shorts", "{c} 가면 꼭 해 봐야 할 것 #Shorts",
          "{c}에서 이거 하면 안 돼?! #Shorts", "모니의 {c} 여행 퀘스트 #Shorts"]
if L.EN:
    OUTROS = ["Where should I go next? Tell me in the comments, and hit subscribe!",
              "Pick my next country in the comments! Like and subscribe!",
              "Could you pass these quests? Comment below, and subscribe for more!"]
    TITLES = ["A robot tries to survive in {c} #Shorts", "Things you must try in {c} #Shorts",
              "Don't do this in {c}! #Shorts", "Moni's {c} travel quest #Shorts"]


def load_trips() -> list[dict]:
    trips = yaml.safe_load((ROOT / "config" / "trips.yaml").read_text())["trips"]
    countries = {c["id"]: c for c in yaml.safe_load((ROOT / "config" / "travel.yaml").read_text())["countries"]}
    for t in trips:
        ct = countries[t["country"]]
        t.setdefault("name", ct["name"])
        t["flag"], t["flag_colors"] = ct["flag"], ct.get("flag_colors", {})
        # 직업체험 렌더러가 쓰는 키
        t["job"] = t["name"]
        t["scene"] = t["quests"][0].get("scene", "street")
        t.setdefault("data_face", "shock")
    if L.EN:
        trips = L.merge_text(trips, "trips.yaml")
        for t in trips:
            t["job"] = t["name"]
    return trips


def trim(ep: dict) -> dict:
    return J.trim(ep)


def build_segments(ep: dict, seed: int) -> list[Seg]:
    rnd = random.Random(seed)
    segs = [Seg("tease", ep["tease"])] + ([] if J.CUT else [Seg("hook", ep["hook"])])
    for i, q in enumerate(ep["quests"]):
        for line in q["say"]:
            segs.append(Seg("say", line, i))
        segs.append(Seg("result", q["after"], i))
    segs.append(Seg("data", ep["answer_say"]))
    segs.append(Seg("outro", rnd.choice(J.SHORT_OUTROS) if J.CUT else (ep.get("outro") or rnd.choice(OUTROS))))
    return segs


def metadata(ep: dict, seed: int) -> dict:
    rnd = random.Random(seed)
    c = ep["name"]
    title = ep.get("title") or rnd.choice(TITLES).format(c=c)
    lines = [L.t("quest_line", i=i + 1, title=q["title"], res=L.t(q["result"])) for i, q in enumerate(ep["quests"])]
    if L.EN:
        desc = (f"Moni's World Trip #{ep['num']:02d}: {c} {ep.get('city', '')}".strip() + "\n\n" + "\n".join(lines)
                + f"\n\nAnswer: {ep['answer_big']} ({ep.get('answer_sub', '')})".rstrip(" ()")
                + (f"\n{ep['source']}" if ep.get("source") else "")
                + f"\n\n#Shorts #travel #{c.replace(' ', '').lower()} #pixelart #robot")
        return {"title": title[:100], "description": desc,
                "tags": ["travel", c, f"{c} travel", "travel tips", "pixel art", "shorts"]}
    desc = (f"모니의 세계여행 #{ep['num']:02d}: {c} {ep.get('city', '')}".strip() + "\n\n" + "\n".join(lines)
            + f"\n\n정답: {ep['answer_big']} ({ep.get('answer_sub', '')})".rstrip(" ()")
            + (f"\n{ep['source']}" if ep.get("source") else "")
            + f"\n\n#Shorts #세계여행 #{c.replace(' ', '')}여행 #여행 #픽셀아트")
    return {"title": title[:100], "description": desc,
            "tags": ["세계여행", c, f"{c} 여행", "여행", "픽셀아트", "shorts"]}


class TripRenderer(J.Renderer):
    def __init__(self, ep: dict, segs: list[Seg], seed: int):
        super().__init__(ep, segs, seed)
        self.scenes = []
        for q in ep["quests"]:
            sc = dict(SCENES[q.get("scene", ep["scene"])])
            sc["props"] = list(sc.get("props", []))
            self.scenes.append(sc)
        self.pal = Wd.base_palette()
        for name, rgb in ep.get("flag_colors", {}).items():
            self.pal(name, tuple(rgb))
        self.flag = Wd.flag_pixels(ep["flag"])
        self.costs = [(next(s.start for s in segs if s.kind == "result" and s.q == i), q.get("cost", 0))
                      for i, q in enumerate(ep["quests"])]

    # 퀘스트마다 무대를 바꾼다
    def stage(self, t: float) -> Image.Image:
        seg = self.segs[self.seg_at(t)]
        if seg.q is not None:
            k = seg.q
        elif seg.kind in ("tease", "hook"):
            k = 0
        else:
            k = len(self.scenes) - 1
        self.scene = self.scenes[k]
        return super().stage(t)

    def spot(self, seg: Seg) -> int:
        sp = self.scene["spots"]
        if seg.q is not None:
            return sp.get(self.ep["quests"][seg.q].get("spot", "center"), sp["center"])
        return sp["center"]

    def series_line(self) -> str:
        return L.t("trip_series", num=self.ep["num"])

    def tease_parts(self):
        top = self.ep["tease_top"]
        return top, [" ".join(top)], self.ep.get("tease_big", "?")

    def hook_panel(self):
        return self.ep.get("city", f"TRIP {self.ep['num']:02d}"), L.t("start_trip")

    def foot(self, seg: Seg):
        return self.ep.get("source") if seg.kind == "data" else None

    def flag_icon(self, d, x, y, u=10):
        px = self.flag
        d.rectangle([x - 4, y - 4, x + len(px[0]) * u + 3, y + len(px) * u + 3], fill=C["black"])
        for j, row in enumerate(px):
            for i, name in enumerate(row):
                c = tuple(int(v) for v in self.pal.colors[self.pal(name)])
                d.rectangle([x + i * u, y + j * u, x + i * u + u - 1, y + j * u + u - 1], fill=c)

    def draw_name(self, img, d, y):
        F = self.F
        nw = d.textlength(self.name(), font=F[96])
        fx = int(W // 2 - (nw + 120) // 2)
        self.flag_icon(d, fx, y + 16, 10)
        text(d, (fx + 120, y), self.name(), F[96], C["white"], "la", 6)

    def status(self, t: float) -> dict:
        st = super().status(t)
        h0, h1 = TRIP_HOURS
        clock = h0 * 60 + int((h1 - h0) * 60 * st["p"])
        st["clock"] = f"{clock // 60:02d}:{clock % 60 // 10 * 10:02d}"
        st["spent"] = sum(c for at, c in self.costs if at <= t)
        return st

    def status_bar(self, d, stt):
        F = self.F
        y0, y1 = J.STAGE_Y + 990, J.STAGE_Y + 1072
        d.rectangle([0, y0, W, y1], fill=(16, 18, 34))
        d.rectangle([0, y0, W, y0 + 4], fill=C["white"])
        text(d, (28, y0 + 22), (f"Spent {L.money(stt['spent'])}" if L.EN else f"여행 경비 {stt['spent']:,}원"), F[32], C["yellow"], "la", 2)
        f = stt["fatigue"]
        text(d, (640, y0 + 22), L.t("tired"), F[32], C["white"], "la", 2)
        bx, bw, n = 730, 30, 10
        lit = int(round(f / 10))
        col = C["green"] if f < 45 else (C["yellow"] if f < 75 else C["red"])
        for k in range(n):
            x = bx + k * (bw + 2)
            d.rectangle([x, y0 + 24, x + bw - 1, y0 + 56], fill=col if k < lit else C["dgrey"])

    def data_card(self, img, d, seg, since):
        F, ep = self.F, self.ep
        dark = Image.new("RGB", (W, 760), (10, 10, 20))
        region = img.crop((0, J.STAGE_Y + 140, W, J.STAGE_Y + 900))
        img.paste(Image.blend(region, dark, 0.55), (0, J.STAGE_Y + 140))
        x0, y0, x1 = 60, J.STAGE_Y + 160, W - 60
        pixel_panel(d, x0, y0, x1, y0 + 560, (24, 28, 52), C["cyan"])
        text(d, (W // 2, y0 + 40), L.t("reveal"), F[64], C["yellow"], "mt", 4)
        text(d, (W // 2, y0 + 130), " ".join(ep["tease_top"]), F[48], C["white"], "mt", 3)
        pop = ease(min(1.0, since / 0.3))
        if pop > 0.05:
            big_title(img, y0 + 220, ep["answer_big"], F[128], C["yellow"], max_w=x1 - x0 - 60,
                      max_scale=1.2 + 0.4 * (1 - pop))
        if ep.get("answer_sub"):
            d2 = ImageDraw.Draw(img)
            text(d2, (W // 2, y0 + 470), ep["answer_sub"], F[48], (190, 190, 210), "mt", 3)

    def cover(self) -> Image.Image:
        if getattr(self, "_cover", None) is not None:
            return self._cover
        F, ep = self.F, self.ep
        st = self.stage(max(0.0, self.segs[0].end - 0.05)).resize((W, W), Image.NEAREST)
        img = Image.new("RGB", (W, J.H), self.bg_hi)
        img.paste(st, (0, 700))
        d = ImageDraw.Draw(img)
        text(d, (W // 2, 70), self.series_line(), F[64], C["yellow"], "mt", 4)
        y = big_title(img, 170, L.t("ep", name=ep["name"]), F[128], C["white"])
        J.badge(d, F, max(y + 30, 480), L.t("three_quests"), C["navy"], C["yellow"], C["cyan"])
        self._cover = img
        return img


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def pick(trips: list[dict], history: list[dict]) -> dict | None:
    done = {h["trip"] for h in history}
    todo = [t for t in trips if t["id"] not in done and not t.get("draft")]
    return min(todo, key=lambda t: t["num"]) if todo else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trip", "--country", dest="trip")
    ap.add_argument("--tts", choices=["edge", "silent"])
    ap.add_argument("--out", type=Path, default=ROOT / "out")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--frames")
    args = ap.parse_args(argv)

    trips, history = load_trips(), load_history()
    if not args.no_upload and not args.trip and uploaded_recently(history):
        print("[trip] 최근 4시간 안에 이미 올렸어요. 건너뜁니다.")
        return 0
    ep = next(t for t in trips if t["id"] == args.trip) if args.trip else pick(trips, history)
    if ep is None:
        print("[trip] 남은 여행 대본이 없어요. config/trips.yaml에 나라를 추가하세요.")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    seed = (ep["num"] * 6007 + len(history)) & 0xFFFF
    if J.CUT:
        ep = trim(ep)
    segs = build_segments(ep, seed)
    print(f"[trip] #{ep['num']:02d} {ep['name']} ({len(segs)}줄)")
    work = args.out / f"work-trip-{stamp}"
    audio, engine = J.synthesize([s.text for s in segs], work / "tts", args.tts)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.frames:
        J.timeline(segs, audio)
        r = TripRenderer(ep, segs, seed)
        for ts in args.frames.split(","):
            p = args.out / f"trip-{ep['id']}-{float(ts):05.1f}s.png"
            r.frame(float(ts)).save(p)
            print(f"[trip] {p}")
        shutil.rmtree(work, ignore_errors=True)
        return 0

    video = args.out / f"{stamp}-trip-{ep['id']}.mp4"
    secs = J.render(ep, segs, audio, video, work, seed, R=TripRenderer)
    cover = video.with_suffix(".jpg")
    TripRenderer(ep, segs, seed).cover().save(cover, quality=92)
    meta = metadata(ep, seed)
    (args.out / f"{stamp}-trip-{ep['id']}.json").write_text(json.dumps(
        {**meta, "script": [s.text for s in segs], "seconds": round(secs, 1), "tts": engine},
        ensure_ascii=False, indent=2))
    shutil.rmtree(work, ignore_errors=True)
    print(f"[trip] 영상: {video} ({secs:.1f}초, {video.stat().st_size / 1e6:.1f}MB, 음성 {engine})")

    video_id = None
    if not args.no_upload and upload_make.configured():
        video_id = f"make:{upload_make.upload(video, meta)}"
        print(f"[trip] Make.com으로 전송 완료 ({video_id})")
    elif not args.no_upload and upload_youtube.configured():
        video_id = upload_youtube.upload(video, meta)
        print(f"[trip] 업로드 완료: https://youtu.be/{video_id}")
    elif not args.no_upload:
        print("[trip] 업로드 설정이 없어 건너뜀")
    if not args.no_upload:
        upload_instagram.try_upload(video, meta, "trip", cover)
        history.append({"trip": ep["id"], "at": stamp, "video_id": video_id})
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
