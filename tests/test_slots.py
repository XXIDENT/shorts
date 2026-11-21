import json
from datetime import datetime, timedelta, timezone

from scripts import slot_scheduler as S


def _hist(tmp, rel, stamps):
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([{"at": s} for s in stamps]))


def test_due_and_done(tmp_path):
    for rel in S.HISTORY.values():
        _hist(tmp_path, rel, [])
    now = datetime(2026, 11, 21, 23, 0, tzinfo=timezone.utc)   # KST 08:00
    d = S.due(now, set(), root=tmp_path)
    assert [(o[1], o[2]) for o in d] == [("jobs.yml", "ko")]   # 22:52 한국 직업만 (11:52는 3시간 넘음)
    _hist(tmp_path, "data/jobs_history.json", ["20261121-225500"])
    assert S.due(now, set(), root=tmp_path) == []
    # 전날 기록은 오늘 정시를 채우지 않는다
    _hist(tmp_path, "data/jobs_history.json", ["20261120-225500"])
    assert len(S.due(now, set(), root=tmp_path)) == 1


def test_six_slots_a_day():
    occ = S.occurrences(datetime(2026, 11, 21, 12, tzinfo=timezone.utc))
    day = [o for o in occ if o[0].date() == datetime(2026, 11, 21).date()]
    assert len(day) == 6 and sum(o[2] == "en" for o in day) == 2
