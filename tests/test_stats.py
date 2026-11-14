import json
from datetime import datetime, timezone
from pathlib import Path

from shorts import stats

VIDEOS = json.loads((Path(__file__).parent / "fixtures" / "views.json").read_text())
NOW = datetime(2026, 11, 13, 14, 0, tzinfo=timezone.utc)


def test_first_report():
    md = stats.report(VIDEOS, {}, "2026-11-13", NOW)
    assert "1.6만회" in md and "첫 집계" in md
    assert "세계여행" in md and "직업체험" in md
    assert md.index("aaa") < md.index("bbb")          # TOP5는 조회수 순


def test_gain_and_90days():
    hist = {"2026-11-12": {"aaa": 15000, "bbb": 800}}
    md = stats.report(VIDEOS, hist, "2026-11-13", NOW)
    assert "+669회" in md                              # 320+20+230+99
    assert "1.6만회 / 수익화" in md                     # 90일 밖 영상(ddd)은 빠짐


def test_series_slot():
    assert stats.series_of("2026-11-12T23:10:00Z") == "직업체험"
    assert stats.series_of("2026-11-13T05:00:00Z") == "기타(수동)"


def test_series_by_title():
    assert stats.series_of("2026-11-14T11:55:00Z", "태국에서 이거 하면 안 돼?! #Shorts") == "세계여행"
    assert stats.series_of("2026-11-14T03:26:00Z", "바리스타, AI가 하면 몇 점? #Shorts") == "직업체험"
    assert stats.series_of("2026-11-13T05:00:00Z", "모니의 프랑스 여행, 한국이랑 이렇게 달라 #Shorts") == "세계여행"
