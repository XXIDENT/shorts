"""하루 한 편 지키기: GitHub 예약이 몇 시간씩 늦게 돌면 대신 실행한 것과 겹쳐서
같은 시리즈가 하루 두 번 올라갈 수 있다. 최근 12시간 안에 올렸으면 건너뛴다.
(날짜 기준이 아니라 시간 기준이라, 늦게 올라간 편 때문에 그날 정시 편이 빠지지 않는다.)"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

WINDOW = timedelta(hours=12)


def stamp_time(stamp: str) -> datetime:
    """history의 at 값(UTC, 'YYYYmmdd-HHMMSS')."""
    return datetime.strptime(stamp, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)


def uploaded_recently(history: list[dict], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return any(h.get("at") and now - stamp_time(h["at"]) < WINDOW for h in history)
