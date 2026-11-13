"""인스타그램 릴스에 같은 영상을 올린다 (Make.com 경유, 0원).

인스타 API는 파일을 직접 받지 않고 '공개 주소의 영상'을 가져가서 올린다. 그래서
1) 영상을 이 저장소(공개)의 GitHub 릴리스 'reels-media'에 첨부해 공개 주소를 만들고
2) 그 주소와 캡션을 Make.com 두 번째 웹훅(MAKE_IG_WEBHOOK_URL)으로 보낸다.
   Make 시나리오: Webhooks > Custom webhook → Instagram for Business > Create a Reel Post

환경변수: MAKE_IG_WEBHOOK_URL (없으면 인스타는 건너뜀), GITHUB_TOKEN, GITHUB_REPOSITORY (Actions가 넣어 줌)
인스타 실패는 유튜브 업로드에 영향을 주지 않는다.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

TAG = "reels-media"
KEEP = 40          # 릴리스에 남겨 둘 영상 수 (인스타가 가져간 뒤엔 필요 없음)
API = "https://api.github.com"


def configured() -> bool:
    return bool(os.environ.get("MAKE_IG_WEBHOOK_URL") and os.environ.get("GITHUB_TOKEN")
                and os.environ.get("GITHUB_REPOSITORY"))


def _gh() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                      "Accept": "application/vnd.github+json"})
    return s


def _release(s: requests.Session, repo: str) -> dict:
    r = s.get(f"{API}/repos/{repo}/releases/tags/{TAG}", timeout=30)
    if r.status_code == 200:
        return r.json()
    r = s.post(f"{API}/repos/{repo}/releases", json={
        "tag_name": TAG, "name": "릴스 업로드용 영상 (자동)", "prerelease": True,
        "body": "인스타그램 릴스 업로드에 쓰는 임시 영상 보관소예요. 자동으로 정리돼요."}, timeout=30)
    r.raise_for_status()
    return r.json()


def host_video(video: Path) -> str:
    """영상을 공개 릴리스에 올리고 내려받기 주소를 돌려준다."""
    repo = os.environ["GITHUB_REPOSITORY"]
    s = _gh()
    rel = _release(s, repo)
    assets = sorted(rel.get("assets", []), key=lambda a: a["created_at"])
    for a in assets[: max(0, len(assets) - KEEP + 1)]:
        s.delete(f"{API}/repos/{repo}/releases/assets/{a['id']}", timeout=30)
    up = rel["upload_url"].split("{")[0]
    with video.open("rb") as f:
        r = s.post(up, params={"name": video.name}, data=f,
                   headers={"Content-Type": "video/mp4"}, timeout=300)
    r.raise_for_status()
    return r.json()["browser_download_url"]


def caption(meta: dict) -> str:
    title = meta["title"].replace("#Shorts", "").strip()
    body = meta["description"].split("\n\n#")[0]
    tags = " ".join(t for t in meta["description"].split() if t.startswith("#") and t != "#Shorts")
    return f"{title}\n\n{body}\n\n{tags} #릴스".strip()[:2150]


def upload(video: Path, meta: dict) -> str:
    url = host_video(video)
    print(f"[instagram] 영상 주소: {url}")
    data = {"video_url": url, "caption": caption(meta)}
    last = None
    for attempt in range(3):
        try:
            r = requests.post(os.environ["MAKE_IG_WEBHOOK_URL"], json=data, timeout=120)
            r.raise_for_status()
            return r.text.strip() or "accepted"
        except requests.RequestException as e:
            last = e
            print(f"[instagram] 재시도 {attempt + 1}/3: {e}")
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"인스타 웹훅 전송 실패: {last}")


def try_upload(video: Path, meta: dict, tag: str) -> str | None:
    if not configured():
        return None
    try:
        res = upload(video, meta)
        print(f"[{tag}] 인스타 릴스로 전송 완료 ({res})")
        return res
    except Exception as e:      # 인스타가 실패해도 유튜브 기록은 남긴다
        print(f"[{tag}] 인스타 전송 실패(유튜브는 정상): {e}")
        return None
