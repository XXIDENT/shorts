"""채널 언어. SHORTS_LANG=en이면 영어 채널용으로 만든다(기본 ko).

영어판 대본은 config/en/*.yaml에 글자(대사·제목)만 쓰고, 무대·소품·효과·데이터는
같은 id의 한국어 대본에서 가져온다. 기록은 data/en/에 따로 남긴다.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LANG = (os.environ.get("SHORTS_LANG") or "ko").lower()
EN = LANG == "en"

# 텍스트 키: (한국어, 영어)
S = {
    "hero": ("모니", "Moni"),
    "subscribe": ("구독", "SUB"),
    "like": ("좋아요", "LIKE"),
    "answer_end": ("정답은 마지막에!", "Answer at the end!"),
    "start_job": ("체험 시작!", "Let's work!"),
    "start_trip": ("여행 퀘스트 시작!", "Quest start!"),
    "tired": ("피곤", "Tired"),
    "reveal": ("정답 공개!", "The answer!"),
    "reveal_ai": ("정답 공개! AI 대체 확률", "The answer! AI takeover odds"),
    "ai_chance": ("AI 대체 가능성", "Can AI replace it?"),
    "study": ("2013 옥스퍼드 연구", "2013 Oxford study"),
    "felt": ("{hero} 체감 (직접 해봄)", "{hero}'s verdict (tried it)"),
    "can_ai": ("AI가 대신할 수 있을까?", "Can AI do this job?"),
    "three_quests": ("여행 퀘스트 3개!", "3 travel quests!"),
    "ep": ("{name}편", "{name}"),
    "job_series": ("AI 신입 {hero}의 직업체험 #{num:02d}", "AI Rookie {hero}'s Job Day #{num:02d}"),
    "trip_series": ("모니의 세계여행 #{num:02d}", "Moni's World Trip #{num:02d}"),
    "job_source": ("자료: Frey & Osborne(2013) 옥스퍼드대, 미국 702개 직업",
                   "Source: Frey & Osborne (2013), Oxford, 702 US jobs"),
    "quest_line": ("퀘스트 {i}. {title} - {res}", "Quest {i}. {title} - {res}"),
    "clear": ("성공", "CLEAR"),
    "fail": ("실패", "FAIL"),
}


def t(key: str, **kw) -> str:
    return S[key][1 if EN else 0].format(**kw)


HERO = t("hero")


def money(v: float) -> str:
    """화면용 돈 표시. 한국어는 원, 영어는 달러."""
    if EN:
        return f"${v:,.0f}" if v >= 100 or float(v).is_integer() else f"${v:,.2f}"
    return f"{int(v):,}원"


def config_path(name: str) -> Path:
    return ROOT / "config" / ("en" if EN else "") / name


def data_path(name: str) -> Path:
    return ROOT / "data" / ("en" if EN else "") / name


def merge_text(base: list[dict], name: str, key: str = "id") -> list[dict]:
    """영어판: config/en/<name>의 글자만 같은 id의 한국어 대본 위에 덮는다.
    영어 대본이 없는 편은 빠진다(번역 안 된 편이 한국어로 나가지 않게)."""
    if not EN:
        return base
    doc = yaml.safe_load(config_path(name).read_text())
    over = next(iter(doc.values()))
    by_id = {b[key]: b for b in base}
    out = []
    for o in over:
        b = dict(by_id.get(o[key], {}))
        for k, v in o.items():
            if k == "quests" and b.get("quests"):
                qs = []
                for i, q in enumerate(v):
                    bq = dict(b["quests"][i]) if i < len(b["quests"]) else {}
                    bq.update(q)
                    qs.append(bq)
                b["quests"] = qs
            elif k == "data" and isinstance(v, dict):
                b["data"] = {**b.get("data", {}), **v}
            else:
                b[k] = v
        out.append(b)
    return out
