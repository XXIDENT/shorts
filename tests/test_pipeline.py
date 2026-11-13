import json
from pathlib import Path

from shorts.data import build_ranking
from shorts.script import build_script, fmt, narration_lines

FX = Path(__file__).parent / "fixtures" / "SP.POP.TOTL.json"


def ranking(order="desc"):
    fx = json.loads(FX.read_text())
    topic = {"id": "t", "indicator": "SP.POP.TOTL", "title": "인구", "order": order, "format": "count_people"}
    return build_ranking(topic, fx["rows"], set(fx["countries"]))


def test_ranking_excludes_aggregates_and_sorts():
    r = ranking()
    assert [e.iso2 for e in r.top[:2]] == ["IN", "CN"]
    assert all(e.iso2 != "1W" for e in r.top)
    assert r.korea and r.korea.name == "한국"


def test_asc_order():
    assert ranking("asc").top[0].iso2 == "KR"


def test_script_reveals_every_rank_once():
    scenes = build_script(ranking(), seed=1)
    ranks = [s.reveal_rank for s in scenes if s.reveal_rank]
    assert sorted(ranks) == list(range(1, 11))
    assert scenes[0].kind == "hook" and scenes[-1].kind == "outro"
    groups = narration_lines(scenes)
    assert sum(len(g[1]) for g in groups) == len(scenes)


def test_fmt():
    assert fmt(1.43e9, {"format": "count_people"}) == "14.3억 명"
    assert fmt(2.74e13, {"format": "usd_big"}) == "27.4조 달러"
    assert fmt(0.72, {"format": "ratio2", "unit": "명"}) == "0.72명"
