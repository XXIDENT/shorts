from PIL import Image, ImageDraw

from shorts import jobs as J
from shorts import trip as T
from shorts.pixel import art
from shorts.pixel.scenes import SCENES


def test_trips_valid_and_unique():
    trips = T.load_trips()
    assert len({t["id"] for t in trips}) == len(trips) and len({t["num"] for t in trips}) == len(trips)
    F = J.Fonts()
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = []
    for t in trips:
        assert len(t["quests"]) == 3, t["id"]
        assert any(q["result"] == "fail" for q in t["quests"]), t["id"]   # 실패 장면(콜드 오픈용) 하나는 꼭
        for q in t["quests"]:
            sc = SCENES[q["scene"]]
            assert q.get("spot", "center") in sc["spots"], (t["id"], q["title"])
            for fx in q.get("fx", []) + q.get("fx_after", []):
                assert fx in art.FX, fx
            lines += q["say"] + [q["after"]]
        lines += [t["tease"], t["hook"], t["answer_say"]]
        segs = T.build_segments(t, 1)
        assert sum(len(s.text.replace(" ", "")) for s in segs if s.kind not in ("tease", "outro")) <= 210, t["id"]
        for s in segs:
            assert len(J.wrap(d, s.text, F[48], J.W - 160)) <= 3, s.text
    assert len(lines) == len(set(lines))


def test_trip_frames(tmp_path):
    t = next(x for x in T.load_trips() if x["id"] == "japan")
    segs = T.build_segments(t, 1)
    audio, _ = J.synthesize([s.text for s in segs], tmp_path, "silent")
    total = J.timeline(segs, audio)
    r = T.TripRenderer(t, segs, 1)
    for x in (0.2, segs[3].start + 0.5, next(s for s in segs if s.kind == "data").start + 1, total - 0.1):
        assert r.frame(x).size == (J.W, J.H)
    assert r.cover().size == (J.W, J.H)
    meta = T.metadata(t, 1)
    assert "#AI" not in meta["description"] and "AI가 만들" not in meta["description"]
