from shorts import upload_instagram as IG


def test_caption_and_config(monkeypatch):
    meta = {"title": "AI가 바리스타 하루 해봤더니 #Shorts",
            "description": "AI 신입 '모니'의 직업체험 #01\n\n퀘스트 1. 아메리카노\n\n#Shorts #직업체험 #AI"}
    cap = IG.caption(meta)
    assert cap.startswith("AI가 바리스타 하루 해봤더니") and "#Shorts" not in cap
    assert "#직업체험" in cap and "#릴스" in cap and len(cap) <= 2200
    monkeypatch.delenv("MAKE_IG_WEBHOOK_URL", raising=False)
    assert not IG.configured() and IG.try_upload(None, meta, "t") is None
