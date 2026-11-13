"""쇼츠 한 편을 만든다: 주제 선택 → 데이터 → 대본 → 음성 → 영상 → (선택) 업로드.

사용법:
  python -m shorts.main                  # 다음 주제로 영상 생성 (+ Secrets가 있으면 업로드)
  python -m shorts.main --topic gdp      # 특정 주제
  python -m shorts.main --fixtures tests/fixtures --tts silent --no-upload   # 오프라인 테스트
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import upload_youtube
from .data import get_ranking
from .render import render
from .script import build_script, metadata, narration_lines
from .tts import synthesize

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history.json"


def load_topics() -> list[dict]:
    return yaml.safe_load((ROOT / "config" / "topics.yaml").read_text())["topics"]


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def pick_topic(topics: list[dict], history: list[dict]) -> dict:
    """가장 오래전에 만든(또는 아직 안 만든) 주제를 고른다."""
    last = {h["topic"]: h["at"] for h in history}
    return min(topics, key=lambda t: last.get(t["id"], ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic")
    ap.add_argument("--fixtures", type=Path)
    ap.add_argument("--tts", choices=["google", "edge", "silent"])
    ap.add_argument("--out", type=Path, default=ROOT / "out")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args(argv)

    topics = load_topics()
    history = load_history()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if args.topic:
        candidates = [next(t for t in topics if t["id"] == args.topic)]
    else:
        # 데이터를 못 받은 주제는 건너뛰고 다음 주제로 (최대 3개 시도)
        last = {h["topic"]: h["at"] for h in history}
        candidates = sorted(topics, key=lambda t: last.get(t["id"], ""))[:3]
    ranking = None
    for topic in candidates:
        print(f"[main] 주제: {topic['id']} ({topic['title']})")
        try:
            ranking = get_ranking(topic, args.fixtures)
            break
        except Exception as e:
            print(f"[main] 데이터 실패, 다음 주제로: {e}")
    if ranking is None:
        raise SystemExit("[main] 모든 후보 주제의 데이터를 받지 못했어요")
    scenes = build_script(ranking, seed=hash((topic["id"], stamp)) & 0xFFFF)
    groups = narration_lines(scenes)

    work = args.out / f"work-{stamp}"
    audio, engine = synthesize([g[0] for g in groups], work / "tts", args.tts)
    print(f"[main] 음성 엔진: {engine}")

    args.out.mkdir(parents=True, exist_ok=True)
    video = args.out / f"{stamp}-{topic['id']}.mp4"
    secs = render(ranking, scenes, groups, audio, video, work)
    meta = metadata(ranking, scenes)
    (args.out / f"{stamp}-{topic['id']}.json").write_text(
        json.dumps({**meta, "script": [g[0] for g in groups], "seconds": round(secs, 1),
                    "year": ranking.year, "tts": engine}, ensure_ascii=False, indent=2))
    shutil.rmtree(work, ignore_errors=True)
    print(f"[main] 영상: {video} ({secs:.1f}초)")

    video_id = None
    if not args.no_upload and upload_youtube.configured():
        video_id = upload_youtube.upload(video, meta)
        print(f"[main] 업로드 완료: https://youtu.be/{video_id}")
    elif not args.no_upload:
        print("[main] YouTube Secrets가 없어 업로드는 건너뜀")

    if not args.fixtures:
        history.append({"topic": topic["id"], "at": stamp, "year": ranking.year, "video_id": video_id})
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
