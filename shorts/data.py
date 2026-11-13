"""세계은행 API에서 지표 데이터를 받아 국가 순위를 만든다 (API 키 불필요)."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import time

import requests
from babel import Locale

API = "https://api.worldbank.org/v2"
KO = Locale("ko")
# 세계은행 국가명이 babel에 없거나 어색한 경우 보정
NAME_FIX = {"KR": "한국", "KP": "북한", "US": "미국", "GB": "영국", "XK": "코소보"}


@dataclass
class Entry:
    iso2: str
    name: str
    value: float
    rank: int


@dataclass
class Ranking:
    topic: dict
    year: int
    top: list[Entry]          # 1위부터 순서대로
    korea: Entry | None       # 한국 순위 (데이터가 있을 때)
    total: int                # 순위에 포함된 국가 수
    label: str = ""           # 화면에 표시할 기준 시점 (예: "2025년", "11월 13일")
    source: str = "세계은행 오픈데이터"


def _get(path: str, **params) -> list:
    """세계은행 API는 가끔 느리거나 끊겨서, 최대 4번까지 간격을 늘려가며 다시 시도한다."""
    params = {"format": "json", "per_page": 20000, **params}
    last: Exception | None = None
    for attempt in range(4):
        try:
            r = requests.get(f"{API}/{path}", params=params, timeout=120)
            r.raise_for_status()
            body = r.json()
            break
        except (requests.RequestException, ValueError) as e:
            last = e
            print(f"[data] {path} 재시도 {attempt + 1}/4: {e}")
            time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError(f"World Bank API 실패: {path}: {last}")
    if not isinstance(body, list) or len(body) < 2 or body[1] is None:
        raise RuntimeError(f"World Bank 응답 이상: {path} {str(body)[:200]}")
    return body[1]


def korean_name(iso2: str, fallback: str) -> str:
    if iso2 in NAME_FIX:
        return NAME_FIX[iso2]
    return KO.territories.get(iso2, fallback)


def fetch_countries() -> set[str]:
    """지역 묶음(Aggregates)을 뺀 실제 국가의 iso2 코드."""
    return {c["iso2Code"] for c in _get("country") if c["region"]["id"] != "NA"}


def fetch_indicator(indicator: str, years: str = "2014:2025") -> list[dict]:
    return _get(f"country/all/indicator/{indicator}", date=years)


def latest_population() -> dict[str, float]:
    pop: dict[str, tuple[int, float]] = {}
    for row in fetch_indicator("SP.POP.TOTL"):
        if row["value"] is None:
            continue
        iso, year = row["country"]["id"], int(row["date"])
        if iso not in pop or year > pop[iso][0]:
            pop[iso] = (year, row["value"])
    return {k: v for k, (_, v) in pop.items()}


def build_ranking(topic: dict, rows: list[dict], countries: set[str],
                  population: dict[str, float] | None = None, top_n: int = 10) -> Ranking:
    rows = [r for r in rows if r["value"] is not None and r["country"]["id"] in countries]
    min_pop = topic.get("min_pop")
    if min_pop and population is not None:
        rows = [r for r in rows if population.get(r["country"]["id"], 0) >= min_pop]
    # 가장 최근이면서 국가 100개 이상 데이터가 있는 연도를 고른다
    per_year = Counter(int(r["date"]) for r in rows)
    good = [y for y, n in per_year.items() if n >= 100] or list(per_year)
    if not good:
        raise RuntimeError(f"{topic['id']}: 데이터 없음")
    year = max(good)
    rows = [r for r in rows if int(r["date"]) == year]
    rows.sort(key=lambda r: r["value"], reverse=topic.get("order", "desc") == "desc")
    entries = [Entry(r["country"]["id"], korean_name(r["country"]["id"], r["country"]["value"]),
                     float(r["value"]), i + 1) for i, r in enumerate(rows)]
    korea = next((e for e in entries if e.iso2 == "KR"), None)
    return Ranking(topic, year, entries[:top_n], korea, len(entries), label=f"{year}년")


def get_ranking(topic: dict, fixture_dir: Path | None = None) -> Ranking:
    """fixture_dir가 있으면 저장된 JSON으로 (오프라인 테스트용), 없으면 API로."""
    if topic.get("source") in ("google_trends", "youtube_trending"):
        from .trends import get_trend_ranking
        return get_trend_ranking(topic, fixture_dir)
    if fixture_dir:
        fx = json.loads((fixture_dir / f"{topic['indicator']}.json").read_text())
        return build_ranking(topic, fx["rows"], set(fx["countries"]), fx.get("population"))
    countries = fetch_countries()
    population = latest_population() if topic.get("min_pop") else None
    return build_ranking(topic, fetch_indicator(topic["indicator"]), countries, population)
