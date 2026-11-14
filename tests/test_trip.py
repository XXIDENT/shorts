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
        assert sum(len(s.text.replace(" ", "")) for s in segs if s.kind not in ("tease", "outro")) <= 195, t["id"]   # 실제 음성 기준 약 50초
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


def test_every_trip_quest_renders(tmp_path):
    """퀘스트마다 소품·무대가 달라서 모든 나라의 모든 퀘스트 장면을 한 번씩 그려 본다."""
    for t in T.load_trips():
        segs = T.build_segments(t, 1)
        audio, _ = J.synthesize([s.text for s in segs], tmp_path / t["id"], "silent")
        J.timeline(segs, audio)
        r = T.TripRenderer(t, segs, 1)
        for s in segs:
            r.frame(s.start + 0.3)


def test_consecutive_titles_differ():
    """연달아 올라가는 편은 제목 틀이 달라야 한다(같은 날 '…에서 이거 하면 안 돼?!'가 두 번 나가 노출이 약했음)."""
    for mod, items in ((T, T.load_trips()), (J, J.load_episodes())):
        eps = sorted(items, key=lambda e: e["num"])
        for a, b in zip(eps, eps[1:]):
            ta = mod.metadata(a, 1)["title"].replace(a.get("name", a["job"]), "")
            tb = mod.metadata(b, 1)["title"].replace(b.get("name", b["job"]), "")
            assert ta != tb, (a["id"], b["id"])
