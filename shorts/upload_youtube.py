"""YouTube Data API로 쇼츠를 업로드한다.

필요한 환경변수 (GitHub 저장소 Secrets에 저장):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
선택:
  YT_PRIVACY = private(기본) | unlisted | public
    Google API 감사(audit)를 통과하기 전에는 API로 올린 영상이 비공개로만 올라간다.
    그래서 기본값은 private이고, YouTube Studio에서 확인 후 '공개'로 바꾸는 게 검수 단계다.
"""
from __future__ import annotations

import os
from pathlib import Path

# 업로드·수정·삭제 등 채널 관리 전체 권한
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def configured() -> bool:
    return all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def upload(video: Path, meta: dict) -> str:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta["description"][:4900],
            "tags": meta["tags"],
            "categoryId": "27",  # 교육
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": os.environ.get("YT_PRIVACY", "private"),
            "selfDeclaredMadeForKids": False,
            # 실제 데이터를 그린 차트라 '사실적인 합성 콘텐츠'에 해당하지 않음
            "containsSyntheticMedia": False,
        },
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True,
                                                        mimetype="video/mp4"))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]
