"""채널 영상 관리: 목록 보기, 삭제, 공개 상태 변경, 제목 수정.

사용법 (GitHub Actions '채널 관리' 워크플로에서 실행):
  python -m shorts.manage list
  python -m shorts.manage delete VIDEO_ID [VIDEO_ID ...]
  python -m shorts.manage privacy VIDEO_ID public|unlisted|private
  python -m shorts.manage title VIDEO_ID "새 제목"
  python -m shorts.manage branding "채널 이름"   # 배너(assets/brand/banner.png)·채널 설명 바꾸고 이름 변경 시도
  python -m shorts.manage audit               # 채널 설정·재생목록·영상 태그를 출력(읽기만)
  python -m shorts.manage fix_settings        # 채널 키워드·기본 언어를 '모니의 하루'에 맞게 바꾸기
  python -m shorts.manage clean_desc          # 설명란에서 '코드로 만들었어요(AI 음성)' 줄 지우기(전체 영상)
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


CHANNEL_DESC = (
    "픽셀 로봇 모니의 하루 🤖\n\n"
    "💼 직업체험: 모니가 하루 동안 직업을 체험해요. 연구로 본 그 직업의 자동화 확률도 함께!\n"
    "🌍 세계여행: 모니가 나라를 여행하며 한국이랑 숫자로 비교해요.\n\n"
    "매일 08시·12시·19시·21시(한국 시간) 업로드\n"
    "다음 직업이나 나라는 댓글로 추천해 주세요!"
)


CHANNEL_KEYWORDS = ["모니의 하루", "모니", "픽셀아트", "픽셀 로봇", "직업체험", "직업 체험", "AI 직업",
                    "세계여행", "나라 비교", "한국 비교", "자동화", "쇼츠", "도트", "칩튠"]


def keyword_string(words: list[str]) -> str:
    """유튜브 채널 키워드는 공백으로 나누고, 띄어쓰기가 있는 말은 따옴표로 묶는다."""
    return " ".join(f'"{w}"' if " " in w else w for w in words)


def clean_description(desc: str) -> str:
    """'코드로 만들었어요' 줄과 #AI 해시태그를 뺀다(사용자 요청 2026-11-14)."""
    out = "\n".join(ln for ln in desc.split("\n") if "코드로 만들었어요" not in ln)
    return out.replace(" #AI", "")


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
    elif cmd == "branding":
        from pathlib import Path
        from googleapiclient.http import MediaFileUpload
        name = " ".join(args) or "모니의 하루"
        banner = Path(__file__).resolve().parent.parent / "assets" / "brand" / "banner.png"
        up = yt.channelBanners().insert(media_body=MediaFileUpload(str(banner), mimetype="image/png")).execute()
        ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
        bs = ch["brandingSettings"]
        bs.setdefault("channel", {})
        bs["channel"]["description"] = CHANNEL_DESC
        bs["channel"]["title"] = name
        bs.setdefault("image", {})["bannerExternalUrl"] = up["url"]
        res = yt.channels().update(part="brandingSettings", body={"id": ch["id"], "brandingSettings": bs}).execute()
        print("배너·설명 변경 완료")
        now = yt.channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]
        print(f"채널 이름: {now}" + ("" if now == name else f"  (API로는 이름이 안 바뀜 → 유튜브 스튜디오에서 '{name}'로 직접 변경 필요)"))
    elif cmd == "audit":
        ch = yt.channels().list(part="snippet,brandingSettings,status,contentDetails", mine=True).execute()["items"][0]
        bc = ch["brandingSettings"].get("channel", {})
        print(f"이름: {ch['snippet']['title']}  핸들: {ch['snippet'].get('customUrl')}")
        for k in ("keywords", "country", "defaultLanguage", "unsubscribedTrailer", "trackingAnalyticsAccountId"):
            print(f"{k}: {bc.get(k)}")
        print(f"madeForKids: {ch['status'].get('madeForKids')}  selfDeclared: {ch['status'].get('selfDeclaredMadeForKids')}")
        print("--- 재생목록")
        for pl in yt.playlists().list(part="snippet,status", mine=True, maxResults=50).execute().get("items", []):
            print(f"{pl['id']} [{pl['status']['privacyStatus']}] {pl['snippet']['title']}")
        print("--- 영상")
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        items = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute()
        ids = [it["contentDetails"]["videoId"] for it in items.get("items", [])]
        for v in yt.videos().list(part="snippet,status", id=",".join(ids)).execute().get("items", []) if ids else []:
            sn = v["snippet"]
            print(f"{v['id']} [{v['status']['privacyStatus']}] cat={sn.get('categoryId')} lang={sn.get('defaultLanguage')}"
                  f"/{sn.get('defaultAudioLanguage')} {sn['title']}\n   tags={sn.get('tags')}")
    elif cmd == "fix_settings":
        ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
        bs = ch["brandingSettings"]
        c = bs.setdefault("channel", {})
        print(f"이전 키워드: {c.get('keywords')}")
        c["keywords"] = keyword_string(CHANNEL_KEYWORDS)
        c["defaultLanguage"] = "ko"
        c["description"] = CHANNEL_DESC
        yt.channels().update(part="brandingSettings", body={"id": ch["id"], "brandingSettings": bs}).execute()
        print(f"새 키워드: {c['keywords']}")
    elif cmd == "clean_desc":
        ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        items = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute()
        ids = [it["contentDetails"]["videoId"] for it in items.get("items", [])]
        for v in yt.videos().list(part="snippet", id=",".join(ids)).execute().get("items", []) if ids else []:
            sn = v["snippet"]
            new = clean_description(sn.get("description", ""))
            if new != sn.get("description", ""):
                sn["description"] = new
                yt.videos().update(part="snippet", body={"id": v["id"], "snippet": sn}).execute()
                print(f"설명 정리: {v['id']} {sn['title']}")
    else:
        print(f"알 수 없는 명령: {cmd}\n{__doc__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
