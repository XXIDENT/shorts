"""Make.com 웹훅으로 영상을 보내 공개 업로드한다.

Google 감사 전에는 우리 앱(YouTube Data API)으로 올린 영상이 '비공개 잠김'이 되어 공개할 수 없다.
Make.com의 YouTube 연동은 Google 검증을 받은 앱이라 공개 업로드가 가능하다.

환경변수: MAKE_WEBHOOK_URL (GitHub Secrets에 저장, 이 주소를 아는 사람은 채널에 업로드할 수 있으니 공유 금지)
Make 시나리오: Webhooks > Custom webhook → YouTube > Upload a Video (README 참고)
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests


def configured() -> bool:
    return bool(os.environ.get("MAKE_WEBHOOK_URL"))


def upload(video: Path, meta: dict) -> str:
    url = os.environ["MAKE_WEBHOOK_URL"]
    data = {
        "title": meta["title"][:100],
        "description": meta["description"][:4900],
        "tags": ",".join(meta["tags"]),
        "privacy": os.environ.get("MAKE_PRIVACY", "public"),
    }
    last = None
    for attempt in range(3):
        try:
            with video.open("rb") as f:
                r = requests.post(url, data=data, files={"video": (video.name, f, "video/mp4")}, timeout=300)
            r.raise_for_status()
            return r.text.strip() or "accepted"
        except requests.RequestException as e:
            last = e
            print(f"[make] 재시도 {attempt + 1}/3: {e}")
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"Make.com 웹훅 전송 실패: {last}")
