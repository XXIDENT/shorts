"""밤 점검: 오늘(KST) 올라간 편 수를 기록과 대조하고, 빠졌으면 이유를 출력한다(종료 코드 1).

기대: 한국어 직업체험 2·세계여행 2, 영어 직업체험 1·여행 1 (예약: jobs.yml·travel.yml).
기록 파일의 at은 UTC 'YYYYMMDD-HHMMSS'.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
EXPECTED = {
    "한국어 직업체험": ("data/jobs_history.json", 2),
    "한국어 세계여행": ("data/trip_history.json", 2),
    "영어 직업체험": ("data/en/jobs_history.json", 1),
    "영어 여행": ("data/en/trip_history.json", 1),
}


def count_today(path: Path, today) -> int:
    if not path.exists():
        return 0
    n = 0
    for h in json.loads(path.read_text()):
        at = datetime.strptime(h["at"], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc).astimezone(KST)
        n += at.date() == today
    return n


def main() -> int:
    # 예약 리포트가 몇 시간 늦게(다음 날 새벽·아침) 돌 수 있어서, 정오 전이면 전날을 점검한다
    now = datetime.now(KST)
    today = (now - timedelta(days=1)).date() if now.hour < 12 else now.date()
    missing = []
    for name, (rel, want) in EXPECTED.items():
        got = count_today(ROOT / rel, today)
        print(f"{name}: {got}/{want}")
        if got < want:
            missing.append(f"- {name}: {got}/{want}편")
    if missing:
        Path(ROOT / "out").mkdir(exist_ok=True)
        (ROOT / "out" / "missing.md").write_text(
            f"{today} (KST) 업로드 편 수가 모자라요.\n\n" + "\n".join(missing) +
            "\n\n예약 실행이 늦거나 실패했을 수 있어요. Actions 실행 기록을 확인하고 빠진 편을 수동 실행(no_upload=false)으로 올려 주세요.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
