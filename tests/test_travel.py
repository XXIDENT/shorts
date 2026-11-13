import json
from pathlib import Path

from shorts import travel as T
from shorts.pixel import world as Wd

FX = Path(__file__).parent / "fixtures" / "travel.json"


def test_countries_valid_and_unique():
    cs = T.load_countries()
    assert len({c["id"] for c in cs}) == len(cs) and len({c["num"] for c in cs}) == len(cs)
    lines = []
    for c in cs:
        assert c["landmark"] in Wd.LANDMARKS, c["id"]
        pal = Wd.base_palette()
        for name, rgb in c.get("flag_colors", {}).items():
            pal(name, tuple(rgb))
        for row in Wd.flag_pixels(c["flag"]):
            for name in row:
                pal(name)          # 정의되지 않은 국기 색이면 KeyError
        lines += [c["hook"], c["landmark_say"], c["culture_say"], c["closing"]]
    assert len(lines) == len(set(lines))     # 나라끼리 같은 문장 재사용 금지


def test_segments_and_frame(tmp_path):
    ct = next(c for c in T.load_countries() if c["id"] == "france")
    facts = T.fetch_facts("FR", FX)
    segs = T.build_segments(ct, facts, seed=3)
    assert [s.kind for s in segs][0] == "hook" and segs[-1].kind == "outro"
    assert sum(1 for s in segs if s.kind == "fact") == 3
    audio, _ = T.synthesize([s.text for s in segs], tmp_path, "silent")
    total = T.timeline(segs, audio)
    fr = T.Frames(ct, segs, facts, total, seed=3)
    for t in (0.2, segs[3].start + 1, total - 0.2):
        assert fr.frame(t).size == (T.W, T.H)
    meta = T.metadata(ct, segs, facts, 3)
    assert "세계은행" in meta["description"]


def test_fmt():
    assert T.fmt(83.46, "years") == "83.5세"
    assert T.fmt(44000, "usd") == "4.4만 달러"
    assert T.fmt(1.43e9, "people") == "14.3억 명"
