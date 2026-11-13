from datetime import datetime, timezone

from shorts.once import uploaded_recently

HIST = [{"at": "20261113-192550"}]          # KST 11/14 04:25 (늦게 돈 예약)


def at(h, m=0, d=14):
    return datetime(2026, 11, d, h, m, tzinfo=timezone.utc)


def test_late_schedule_after_backup_is_skipped():
    assert uploaded_recently(HIST, at(21, 0, d=13))   # 1시간 반 뒤 또 돌면 건너뜀


def test_next_slot_still_runs():
    assert not uploaded_recently(HIST, at(3, 0))    # 7시간 뒤 다음 시간대 편은 올라감
    assert not uploaded_recently([], at(12, 0))
