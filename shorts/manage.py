"""채널 영상 관리: 목록 보기, 삭제, 공개 상태 변경, 제목 수정.

사용법 (GitHub Actions '채널 관리' 워크플로에서 실행):
  python -m shorts.manage list
  python -m shorts.manage delete VIDEO_ID [VIDEO_ID ...]
  python -m shorts.manage privacy VIDEO_ID public|unlisted|private
  python -m shorts.manage title VIDEO_ID "새 제목"
  python -m shorts.manage branding        (채널 설명·키워드·배너 적용)
  python -m shorts.manage info VIDEO_ID [VIDEO_ID ...]   (처리 상태·제한 사유 확인)
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


CHANNEL_DESCRIPTION = """세계 순위와 오늘의 트렌드를 1분 안에 보여 드려요.

매일 오전 8시, 낮 12시, 저녁 7시에 새 TOP 10이 올라와요.
- 세계은행 공식 통계로 보는 나라별 순위 (한국은 몇 위?)
- 오늘 한국 급상승 검색어, 유튜브 인기 급상승

궁금한 순위가 있으면 댓글로 알려 주세요."""
CHANNEL_KEYWORDS = '랭킹 순위 TOP10 세계순위 통계 데이터 트렌드 급상승 "1분 랭킹"'


def branding(yt, banner: str = "assets/banner.png") -> None:
    from googleapiclient.http import MediaFileUpload
    ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
    bs = ch["brandingSettings"]
    bs.setdefault("channel", {})
    bs["channel"]["description"] = CHANNEL_DESCRIPTION
    bs["channel"]["keywords"] = CHANNEL_KEYWORDS
    bs["channel"]["defaultLanguage"] = "ko"
    url = yt.channelBanners().insert(media_body=MediaFileUpload(banner, mimetype="image/png")).execute()["url"]
    bs.setdefault("image", {})["bannerExternalUrl"] = url
    yt.channels().update(part="brandingSettings", body={"id": ch["id"], "brandingSettings": bs}).execute()
    print("채널 설명·키워드·배너 적용 완료")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    yt, cmd, args = client(), argv[0], argv[1:]
    if cmd == "list":
        list_videos(yt)
    elif cmd == "branding":
        branding(yt)
    elif cmd == "info":
        import json
        resp = yt.videos().list(part="status,processingDetails,contentDetails,snippet", id=",".join(args)).execute()
        for v in resp.get("items", []):
            print(json.dumps({"id": v["id"], "title": v["snippet"]["title"], "status": v.get("status"),
                              "processing": v.get("processingDetails"),
                              "duration": v["contentDetails"].get("duration"),
                              "regionRestriction": v["contentDetails"].get("regionRestriction"),
                              "contentRating": v["contentDetails"].get("contentRating")},
                             ensure_ascii=False, indent=1))
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
