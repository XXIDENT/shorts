from pathlib import Path

from shorts import jobs
from shorts.pixel import art
from shorts.pixel.scenes import SCENES


def _check_props(items):
    for name, _x, *rest in items:
        assert name in art.PROPS, name


def test_episodes_are_valid_and_unique():
    eps = jobs.load_episodes()
    assert len({e["id"] for e in eps}) == len(eps)
    assert len({e["num"] for e in eps}) == len(eps)
    lines = []
    for e in eps:
        sc = SCENES[e["scene"]]
        assert 0 < e["data"]["prob"] < 1 and e["data"]["occupation"] and e["data"]["label"]
        assert 0 <= e["verdict"] <= 100
        assert 2 <= len(e["quests"]) <= 3
        _check_props(e.get("props", []))
        for q in e["quests"]:
            assert q["result"] in ("clear", "fail")
            assert q.get("spot", "center") in sc["spots"], (e["id"], q.get("spot"))
            for fx in q.get("fx", []) + q.get("fx_after", []):
                assert fx in art.FX, fx
            _check_props(q.get("props", []))
            lines += q["say"] + [q["after"]]
        lines += [e["hook"], e["verdict_say"]]
        # 쇼츠 완주율을 위해 한 편 40~50초: 음성 글자 수(공백 제외) 제한.
        # 끝인사(구독·좋아요 부탁)는 모든 편 공통이라 따로 센다.
        segs = jobs.build_segments(e, seed=1)
        assert sum(len(x.text.replace(" ", "")) for x in segs if x.kind != "outro") <= 210, e["id"]
    # 같은 문장을 여러 편에 재사용하지 않는다(대량생산 템플릿 방지)
    assert len(lines) == len(set(lines))


def test_scene_props_exist():
    for sc in SCENES.values():
        _check_props(sc.get("props", []))
        _check_props(sc.get("decor", []))


def test_josa_and_pct():
    assert jobs.josa("간호사") == "가" and jobs.josa("셰프") == "가" and jobs.josa("집배원") == "이"
    assert jobs.pct(0.96) == "96%" and jobs.pct(0.009) == "0.9%" and jobs.pct(0.0044) == "0.4%"


def test_segments_and_frame(tmp_path: Path):
    ep = next(e for e in jobs.load_episodes() if e["id"] == "barista")
    segs = jobs.build_segments(ep, seed=1)
    assert segs[0].kind == "hook" and segs[-1].kind == "outro"
    assert sum(1 for s in segs if s.kind == "result") == len(ep["quests"])
    audio, eng = jobs.synthesize([s.text for s in segs], tmp_path, "silent")
    total = jobs.timeline(segs, audio)
    assert total > 20
    r = jobs.Renderer(ep, segs, seed=1)
    for t in (0.5, segs[2].start + 0.5, segs[-3].start + 1, total - 0.1):
        assert r.frame(t).size == (jobs.W, jobs.H)
    meta = jobs.metadata(ep, 1)
    assert "Frey" in meta["description"] and len(meta["title"]) <= 100
