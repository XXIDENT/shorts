"""실시간 트렌드 순위: 구글 급상승 검색어, 유튜브 인기 급상승 영상 (한국).

둘 다 무료로 쓸 수 있는 공식 데이터만 사용한다.
- 구글 트렌드 RSS: API 키 불필요
- YouTube Data API videos.list(chart=mostPopular): 업로드용 OAuth로 호출, 1회 1점
"""
from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .data import Entry, Ranking

KST = timezone(timedelta(hours=9))
GOOGLE_RSS = "https://trends.google.com/trending/rss"
NS = {"ht": "https://trends.google.com/trending/rss"}


def today_label() -> str:
    now = datetime.now(KST)
    return f"{now.month}월 {now.day}일"


def short(text: str, limit: int = 14) -> str:
    """화면과 음성에 쓰기 좋게 줄인다: 괄호·해시태그·특수문자 제거 후 단어 단위로 자름."""
    text = re.sub(r"\[.*?\]|\(.*?\)|【.*?】|#\S+", " ", text)
    text = re.sub(r"[|/:~!?\"'“”‘’…·•ㅣ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    out = ""
    for word in text.split(" "):
        if len((out + " " + word).strip()) > limit:
            break
        out = (out + " " + word).strip()
    return out or text[:limit]


def parse_traffic(raw: str) -> float:
    """'2,000+', '20K+', '1M+', '5만+' 같은 표기를 숫자로."""
    s = raw.replace(",", "").replace("+", "").strip().upper()
    m = re.match(r"([\d.]+)\s*([KM만]?)", s)
    if not m:
        return 0.0
    n = float(m.group(1))
    return n * {"K": 1e3, "M": 1e6, "만": 1e4}.get(m.group(2), 1)


def _retry_get(url: str, **kw) -> requests.Response:
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=60, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            print(f"[trends] 재시도 {attempt + 1}/4: {e}")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"트렌드 데이터 실패: {url}: {last}")


def google_trending(xml_text: str, top_n: int = 10) -> list[Entry]:
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        traffic = parse_traffic(it.findtext("ht:approx_traffic", default="0", namespaces=NS))
        if title:
            items.append((short(title), traffic))
    # 같은 이름(줄인 뒤 겹침)은 하나만
    seen, uniq = set(), []
    for name, v in sorted(items, key=lambda x: x[1], reverse=True):
        if name not in seen:
            seen.add(name)
            uniq.append((name, v))
    return [Entry("", n, v, i + 1) for i, (n, v) in enumerate(uniq[:top_n])]


def youtube_trending(top_n: int = 10) -> list[Entry]:
    from googleapiclient.discovery import build

    from .upload_youtube import credentials

    yt = build("youtube", "v3", credentials=credentials(), cache_discovery=False)
    resp = yt.videos().list(part="snippet,statistics", chart="mostPopular",
                            regionCode="KR", maxResults=25).execute()
    vids = []
    for v in resp.get("items", []):
        views = float(v.get("statistics", {}).get("viewCount", 0))
        vids.append((short(v["snippet"]["title"]), views))
    vids.sort(key=lambda x: x[1], reverse=True)
    return [Entry("", n, v, i + 1) for i, (n, v) in enumerate(vids[:top_n])]


def get_trend_ranking(topic: dict, fixture_dir: Path | None = None) -> Ranking:
    src = topic["source"]
    if src == "google_trends":
        if fixture_dir:
            xml_text = (fixture_dir / "google_trends_kr.xml").read_text()
        else:
            xml_text = _retry_get(GOOGLE_RSS, params={"geo": "KR"}).text
        top = google_trending(xml_text)
        source = "Google 트렌드 (한국 급상승 검색어)"
    elif src == "youtube_trending":
        if fixture_dir:
            raise RuntimeError("youtube_trending은 오프라인 테스트를 지원하지 않아요")
        top = youtube_trending()
        source = "YouTube 인기 급상승 (한국)"
    else:
        raise ValueError(src)
    if len(top) < 5:
        raise RuntimeError(f"{topic['id']}: 트렌드 항목이 너무 적어요 ({len(top)}개)")
    now = datetime.now(KST)
    return Ranking(topic, now.year, top, None, len(top), label=today_label(), source=source)
