"""영어 채널(SHORTS_LANG=en) 대본과 화면 검사. 언어는 import 때 정해지므로 별도 프로세스에서 돈다."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHECK = r'''
import re, tempfile
from pathlib import Path
from PIL import Image, ImageDraw
from shorts import jobs as J, trip as T, lang as L
assert L.EN
hangul = re.compile("[가-힣]")
F = J.Fonts()
d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
ko_jobs = {e["id"] for e in __import__("yaml").safe_load((L.ROOT / "config/jobs.yaml").read_text())["episodes"]}
eps, trips = J.load_episodes(), T.load_trips()
assert eps and trips
lines = []
for mod, items in ((J, eps), (T, trips)):
    for e in items:
        if mod is J:
            assert e["id"] in ko_jobs and e.get("scene"), e["id"]
        segs = mod.build_segments(e, 1)
        meta = mod.metadata(e, 1)
        for s in segs:
            assert not hangul.search(s.text), s.text
            assert len(J.wrap(d, s.text, F[48], J.W - 160)) <= 3, s.text
            if s.kind not in ("outro", "data"):
                lines.append(s.text)
        for q in e["quests"]:
            assert not hangul.search(q["title"]), q["title"]
        assert not hangul.search(meta["title"] + meta["description"] + " ".join(meta["tags"])), e["id"]
        assert "#AI" not in meta["description"] and "AI" not in meta["tags"]
        assert sum(len(s.text) for s in segs if s.kind != "outro") <= 640, e["id"]
assert len(lines) == len(set(lines)), [x for x in lines if lines.count(x) > 1][:3]
with tempfile.TemporaryDirectory() as tmp:
    for mod, R, e in ((J, J.Renderer, eps[0]), (T, T.TripRenderer, trips[0])):
        segs = mod.build_segments(e, 1)
        audio, _ = J.synthesize([s.text for s in segs], Path(tmp) / e["id"], "silent")
        total = J.timeline(segs, audio)
        r = R(e, segs, 1)
        for x in (0.2, segs[3].start + 0.5, next(s for s in segs if s.kind == "data").start + 1, total - 0.1):
            assert r.frame(x).size == (J.W, J.H)
        assert r.cover().size == (J.W, J.H)
assert str(J.HISTORY).endswith("data/en/jobs_history.json") and str(T.HISTORY).endswith("data/en/trip_history.json")
print("ok")
'''


def test_english_scripts_and_frames():
    env = dict(os.environ, SHORTS_LANG="en", SHORTS_CUT="")
    r = subprocess.run([sys.executable, "-c", CHECK], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and "ok" in r.stdout, r.stdout + r.stderr
