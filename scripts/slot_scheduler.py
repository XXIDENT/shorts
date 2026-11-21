"""정시 업로드 스케줄러: GitHub 예약(cron)이 4~8시간씩 늦게 돌아서(2026-11-18~21 실측),
예약 시각에 직접 업로드하지 않고, 이 스크립트가 다음 정시까지 기다렸다가 workflow_dispatch로 실행한다.

slots.yml이 매시간 깨우고(늦어도 됨), 실행 하나가 최대 약 5시간 45분 동안 살아 있으면서
- 지난 3시간 안의 정시 편이 아직 안 올라갔으면 바로 실행(따라잡기)
- 다음 정시가 그 안에 오면 그때까지 기다렸다가 실행한다.
같은 편이 두 번 실행돼도 업로드 워크플로의 동시 실행 그룹 + 4시간 중복 방지(shorts/once.py)가 막는다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# (UTC 시, 분, 워크플로, 언어)  = KST 07:52 한국 직업, 08:52 영어 직업, 10:52 영어 여행, 11:52·18:52 한국 여행, 20:52 한국 직업
SLOTS = [(22, 52, "jobs.yml", "ko"), (23, 52, "jobs.yml", "en"), (1, 52, "travel.yml", "en"),
         (2, 52, "travel.yml", "ko"), (9, 52, "travel.yml", "ko"), (11, 52, "jobs.yml", "ko")]
HISTORY = {("jobs.yml", "ko"): "data/jobs_history.json", ("jobs.yml", "en"): "data/en/jobs_history.json",
           ("travel.yml", "ko"): "data/trip_history.json", ("travel.yml", "en"): "data/en/trip_history.json"}
CATCH_UP = timedelta(hours=3)
LIFETIME = timedelta(hours=5, minutes=45)


def occurrences(now: datetime) -> list[tuple[datetime, str, str]]:
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for d in (-1, 0, 1):
        for h, m, wf, lang in SLOTS:
            out.append((base + timedelta(days=d, hours=h, minutes=m), wf, lang))
    return sorted(out)


def done(at: datetime, wf: str, lang: str, root: Path = ROOT) -> bool:
    """그 정시(20분 전부터) 이후에 같은 시리즈·언어 기록이 있으면 이미 올라간 것."""
    p = root / HISTORY[(wf, lang)]
    if not p.exists():
        return False
    for h in json.loads(p.read_text()):
        t = datetime.strptime(h["at"], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        if t >= at - timedelta(minutes=20):
            return True
    return False


def due(now: datetime, sent: set, root: Path = ROOT) -> list[tuple[datetime, str, str]]:
    return [o for o in occurrences(now) if now - CATCH_UP <= o[0] <= now and o not in sent and not done(*o, root=root)]


def dispatch(wf: str, lang: str) -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    subprocess.run(["gh", "api", "-X", "POST", f"repos/{repo}/actions/workflows/{wf}/dispatches",
                    "-f", "ref=main", "-f", "inputs[no_upload]=false", "-f", f"inputs[lang]={lang}"], check=True)


def main() -> int:
    start = datetime.now(timezone.utc)
    sent: set = set()
    while True:
        now = datetime.now(timezone.utc)
        subprocess.run(["git", "pull", "-q", "--ff-only"], cwd=ROOT, check=False)   # 다른 실행이 남긴 기록 반영
        for o in due(now, sent):
            print(f"[slots] {o[0]:%m-%d %H:%M} UTC {o[1]} {o[2]} 실행")
            dispatch(o[1], o[2])
            sent.add(o)
        nxt = [o for o in occurrences(now) if o[0] > now and o not in sent]
        if not nxt or nxt[0][0] > start + LIFETIME:
            print("[slots] 이번 실행 안에 남은 정시 없음, 끝")
            return 0
        wait = (nxt[0][0] - now).total_seconds()
        print(f"[slots] 다음 정시 {nxt[0][0]:%m-%d %H:%M} UTC ({nxt[0][1]} {nxt[0][2]})까지 {wait / 60:.0f}분 대기")
        time.sleep(max(1, wait) + 5)


if __name__ == "__main__":
    sys.exit(main())
