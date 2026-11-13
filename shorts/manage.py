"""채널 영상 관리: 목록 보기, 삭제, 공개 상태 변경, 제목 수정.

사용법 (GitHub Actions '채널 관리' 워크플로에서 실행):
  python -m shorts.manage list
  python -m shorts.manage delete VIDEO_ID [VIDEO_ID ...]
  python -m shorts.manage privacy VIDEO_ID public|unlisted|private
  python -m shorts.manage title VIDEO_ID "새 제목"
"""
from __future__ import annotations

import sys

from googleapiclient.discovery import build

from .upload_youtube import credentials


def client():
    return build("youtube", "v3", credentials=credentials(), cache_discovery=False)


def list_videos(yt) -> None:
    ch = yt.channels().list(part="contentDetails,snippet", mine=True).execute()["items"][0]
    print(f"채널: {ch['snippet']['title']}")
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="snippet,status", playlistId=uploads, maxResults=50).execute()
    for it in items.get("items", []):
        vid = it["snippet"]["resourceId"]["videoId"]
        print(f"{vid}  [{it['status']['privacyStatus']}]  {it['snippet']['title']}")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    yt, cmd, args = client(), argv[0], argv[1:]
    if cmd == "list":
        list_videos(yt)
    elif cmd == "delete":
        for vid in args:
            yt.videos().delete(id=vid).execute()
            print(f"삭제 완료: {vid}")
    elif cmd == "privacy":
        vid, status = args
        v = yt.videos().list(part="status", id=vid).execute()["items"][0]
        v["status"]["privacyStatus"] = status
        yt.videos().update(part="status", body={"id": vid, "status": v["status"]}).execute()
        print(f"공개 상태 변경: {vid} → {status}")
    elif cmd == "title":
        vid, title = args[0], " ".join(args[1:])
        v = yt.videos().list(part="snippet", id=vid).execute()["items"][0]
        v["snippet"]["title"] = title[:100]
        yt.videos().update(part="snippet", body={"id": vid, "snippet": v["snippet"]}).execute()
        print(f"제목 변경: {vid} → {title}")
    else:
        print(f"알 수 없는 명령: {cmd}\n{__doc__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
