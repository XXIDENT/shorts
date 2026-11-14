"""채널 조회수 리포트.

매일 한 번 채널의 모든 영상 조회수를 받아 data/views.json에 날짜별로 쌓고,
어제 대비 늘어난 조회수, 최근 90일 조회수(수익화 기준 참고용), 인기 영상을 정리한다.
결과 마크다운은 out/views.md와 GitHub Actions 요약에 쓰고, 워크플로가 이슈 댓글로 남긴다.

  python -m shorts.stats            # 실제 채널에서 받기
  python -m shorts.stats --fixture tests/fixtures/views.json
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "views.json"
OUT = ROOT / "out" / "views.md"
KST = timezone(timedelta(hours=9))
GOAL_90D = 10_000_000          # 현재 쇼츠 수익화 기준 (2027-02-01부터 2천만)
# 제목은 편마다 달라서, 올라간 시각(KST)으로 시리즈를 나눈다.
SLOTS = [(8, "직업체험"), (12, "세계여행"), (19, "세계여행"), (21, "직업체험")]  # 2026-11-14부터


def fetch_videos() -> list[dict]:
    from .manage import client

    yt = client()
    ch = yt.channels().list(part="contentDetails,statistics", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50,
                                    pageToken=token).execute()
        ids += [it["contentDetails"]["videoId"] for it in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    videos = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,status", id=",".join(ids[i:i + 50])).execute()
        for v in r.get("items", []):
            s = v.get("statistics", {})
            videos.append({
                "id": v["id"], "title": v["snippet"]["title"],
                "published": v["snippet"]["publishedAt"],
                "privacy": v.get("status", {}).get("privacyStatus", ""),
                "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            })
    return videos


def fetch_retention(ids: list[str], since: str, until: str) -> dict[str, dict]:
    """YouTube Analytics: 영상별 평균 시청 비율·시간, 참여 조회수(engagedViews).

    refresh token에 yt-analytics.readonly 권한이 없으면 빈 dict(리포트에서 안내만 한다).
    '계속 시청' 비율은 API에 없어서 engagedViews / views를 대신 쓴다.
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token")
    ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    out: dict[str, dict] = {}
    for metrics in ("views,engagedViews,averageViewDuration,averageViewPercentage",
                    "views,averageViewDuration,averageViewPercentage"):
        try:
            for i in range(0, len(ids), 200):
                r = ya.reports().query(ids="channel==MINE", startDate=since, endDate=until, metrics=metrics,
                                       dimensions="video", filters="video==" + ",".join(ids[i:i + 200])).execute()
                cols = [h["name"] for h in r.get("columnHeaders", [])]
                for row in r.get("rows", []):
                    d = dict(zip(cols, row))
                    out[d.pop("video")] = d
            return out
        except Exception as e:  # noqa: BLE001 - 권한 없음/지표 없음
            print(f"[stats] 분석 API 실패({metrics.split(',')[1]}): {str(e)[:200]}")
            out = {}
    return out


def retention_lines(videos: list[dict], ret: dict[str, dict]) -> list[str]:
    if not ret:
        return ["**시청 유지율**: 분석 권한이 없어서 못 가져왔어요 (scripts/get_refresh_token.py로 토큰을 다시 받으면 보여요)", ""]
    lines = ["**시청 유지율 (최근 영상)**", "", "| 영상 | 조회 | 계속 시청* | 평균 시청 | 평균 비율 |", "|---|---:|---:|---:|---:|"]
    for v in sorted(videos, key=lambda v: v["published"], reverse=True)[:12]:
        d = ret.get(v["id"])
        if not d:
            continue
        views = d.get("views") or 0
        eng = f"{d['engagedViews'] / views * 100:.0f}%" if views and "engagedViews" in d else "-"
        lines.append(f"| {v['title'][:28]} | {fmt(int(views))} | {eng} | {d.get('averageViewDuration', 0):.0f}초 | "
                     f"{d.get('averageViewPercentage', 0):.0f}% |")
    lines += ["", "*계속 시청 = 참여 조회수 ÷ 조회수 (스튜디오의 '계속 시청'과 비슷한 값). 분석 숫자는 1~2일 늦게 들어와요.", ""]
    return lines


def series_of(published: str) -> str:
    h = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(KST).hour
    for hour, name in SLOTS:
        if hour <= h < hour + 2:
            return name
    return "기타(수동)"


def fmt(n: int) -> str:
    if n >= 10_000:
        return f"{n / 10_000:.1f}만".replace(".0만", "만")
    return f"{n:,}"


def report(videos: list[dict], history: dict, today: str, now: datetime, ret: dict | None = None) -> str:
    snap = {v["id"]: v["views"] for v in videos}
    prev_days = sorted(d for d in history if d < today)
    prev = history[prev_days[-1]] if prev_days else {}
    total = sum(snap.values())
    gain = total - sum(prev.get(k, 0) for k in snap) if prev else None

    cutoff = now - timedelta(days=90)
    recent = [v for v in videos
              if datetime.fromisoformat(v["published"].replace("Z", "+00:00")) >= cutoff]
    views_90 = sum(v["views"] for v in recent)

    lines = [f"## 📊 조회수 리포트 ({today})", ""]
    lines.append(f"- 전체 조회수: **{fmt(total)}회** (영상 {len(videos)}개)")
    if gain is not None:
        lines.append(f"- 어제보다: **+{fmt(max(gain, 0))}회** ({prev_days[-1]} 대비)")
    else:
        lines.append("- 어제보다: 첫 집계라 내일부터 나와요")
    pct = views_90 / GOAL_90D * 100
    lines.append(f"- 최근 90일 영상 조회수: {fmt(views_90)}회 / 수익화 기준 1,000만회의 {pct:.2f}%")
    lines.append("")

    by: dict[str, list[int]] = {}
    for v in videos:
        d = by.setdefault(series_of(v["published"]), [0, 0, 0])
        d[0] += 1
        d[1] += v["views"]
        d[2] += v["views"] - prev.get(v["id"], 0) if prev else 0
    lines += ["| 시리즈 | 영상 | 조회수 | 어제보다 |", "|---|---:|---:|---:|"]
    for name, (n, views, g) in sorted(by.items(), key=lambda kv: -kv[1][1]):
        lines.append(f"| {name} | {n} | {fmt(views)} | {'+' + fmt(g) if prev else '-'} |")
    lines.append("")

    lines += ["**조회수 TOP 5**", ""]
    for i, v in enumerate(sorted(videos, key=lambda v: -v["views"])[:5], 1):
        lines.append(f"{i}. [{v['title']}](https://youtu.be/{v['id']}) · {fmt(v['views'])}회 · 👍 {fmt(v['likes'])}")
    lines.append("")

    lines += retention_lines(videos, ret or {})
    new = sorted(videos, key=lambda v: v["published"], reverse=True)[:5]
    lines += ["**최근 올린 영상**", ""]
    for v in new:
        t = datetime.fromisoformat(v["published"].replace("Z", "+00:00")).astimezone(KST)
        lock = "" if v["privacy"] in ("public", "") else f" ({v['privacy']})"
        lines.append(f"- {t:%m/%d %H:%M} [{v['title']}](https://youtu.be/{v['id']}) · {fmt(v['views'])}회{lock}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", help="채널 대신 이 JSON 영상 목록을 쓴다(테스트용)")
    a = ap.parse_args(argv)

    videos = json.loads(Path(a.fixture).read_text()) if a.fixture else fetch_videos()
    now = datetime.now(timezone.utc)
    today = now.astimezone(KST).strftime("%Y-%m-%d")
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    ret = {}
    if not a.fixture and videos:
        since = min(v["published"][:10] for v in videos)
        ret = fetch_retention([v["id"] for v in videos], since, today)
    md = report(videos, history, today, now, ret)

    history[today] = {v["id"]: v["views"] for v in videos}
    for d in sorted(history)[:-120]:          # 120일치만 보관
        del history[d]
    if not a.fixture:
        HISTORY.parent.mkdir(exist_ok=True)
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=0, sort_keys=True))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(md)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
