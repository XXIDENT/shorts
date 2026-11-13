"""순위 데이터로 내레이션 대본(장면 목록)을 만든다.

매 영상의 데이터가 다르고, 훅·전개·마무리 문장을 여러 변형 중 고르므로
같은 문장이 반복되는 '대량생산' 영상이 되지 않게 한다.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .data import Entry, Ranking


def fmt(value: float, topic: dict) -> str:
    f = topic.get("format", "number")
    unit = topic.get("unit", "")
    if f == "count_people":
        if value >= 1e8:
            return f"{value / 1e8:.1f}억 명"
        if value >= 1e4:
            return f"{value / 1e4:,.0f}만 명"
        return f"{value:,.0f}명"
    if f == "usd_big":
        if value >= 1e12:
            return f"{value / 1e12:.1f}조 달러"
        return f"{value / 1e8:,.0f}억 달러"
    if f == "usd":
        if value >= 1e4:
            return f"{value / 1e4:.1f}만 달러"
        return f"{value:,.0f}달러"
    if f == "years":
        return f"{value:.1f}세"
    if f == "percent":
        return f"{value:.1f}%"
    if f == "ratio2":
        return f"{value:.2f}{unit}"
    if f == "per_1000":
        return f"1천 명당 {value:.1f}명"
    return f"{value:,.1f}{unit}"


@dataclass
class Scene:
    kind: str          # hook | reveal | korea | outro
    text: str          # 읽을 문장 (자막으로도 표시)
    reveal_rank: int | None = None


HOOKS = [
    "{title}, 1위는 어디일까요?",
    "{title} TOP 10. 한국은 몇 위일까요?",
    "{title} 순위, 1위는 예상 밖일 수 있어요.",
    "{title}, 세계 순위를 알아볼게요.",
]
TOP3 = {
    3: ["3위는 {name}, {value}입니다.", "3위, {name}. {value}."],
    2: ["2위는 {name}, {value}.", "그리고 2위, {name}. {value}입니다."],
    1: ["대망의 1위는 {name}! {value}입니다.", "1위는 바로 {name}, {value}!"],
}
KOREA_IN = ["한국은 {rank}위로 톱 10에 들었어요.", "눈치채셨나요? 한국이 {rank}위예요."]
KOREA_OUT = ["그럼 한국은요? {total}개국 중 {rank}위, {value}입니다.",
             "참고로 한국은 {total}개국 중 {rank}위였어요. {value}."]
OUTROS = ["다음엔 어떤 순위가 궁금하세요? 댓글로 알려주세요.",
          "예상하신 순위와 같았나요? 댓글로 남겨주세요.",
          "더 궁금한 세계 순위는 구독하고 확인하세요."]


def build_script(r: Ranking, seed: int | None = None) -> list[Scene]:
    rnd = random.Random(seed)
    t = r.topic
    scenes = [Scene("hook", rnd.choice(HOOKS).format(title=t["title"]))]
    top = {e.rank: e for e in r.top}

    # 10위~4위는 세 개씩 묶어 빠르게 넘긴다 (쇼츠는 30초대가 완주율이 높음)
    low = [k for k in sorted(top, reverse=True) if k > 3]
    for i in range(0, len(low), 3):
        pair = low[i:i + 3]
        text = ", ".join(f"{k}위 {top[k].name}" for k in pair) + "."
        # 묶음의 장면들은 같은 문장을 공유하고, 음성 한 줄을 나눠 쓴다
        for k in pair:
            scenes.append(Scene("reveal", text, k))
    for k in (3, 2, 1):
        if k in top:
            e = top[k]
            scenes.append(Scene("reveal", rnd.choice(TOP3[k]).format(name=e.name, value=fmt(e.value, t)), k))

    if r.korea:
        if r.korea.rank <= len(r.top):
            scenes.append(Scene("korea", rnd.choice(KOREA_IN).format(rank=r.korea.rank)))
        else:
            scenes.append(Scene("korea", rnd.choice(KOREA_OUT).format(
                rank=r.korea.rank, total=r.total, value=fmt(r.korea.value, t))))
    scenes.append(Scene("outro", rnd.choice(OUTROS)))
    return scenes


def narration_lines(scenes: list[Scene]) -> list[tuple[str, list[int]]]:
    """같은 문장을 공유하는 연속 장면을 하나의 음성 줄로 묶는다.
    반환: [(문장, [장면 인덱스...]), ...]"""
    out: list[tuple[str, list[int]]] = []
    for i, s in enumerate(scenes):
        if out and out[-1][0] == s.text and s.kind == "reveal" and scenes[out[-1][1][-1]].kind == "reveal":
            out[-1][1].append(i)
        else:
            out.append((s.text, [i]))
    return out


def metadata(r: Ranking, scenes: list[Scene]) -> dict:
    t = r.topic
    first = r.top[0]
    lines = [f"{e.rank}. {e.name} - {fmt(e.value, t)}" for e in r.top]
    korea = f"\n한국: {r.korea.rank}위 ({fmt(r.korea.value, t)})" if r.korea else ""
    return {
        "title": f"{t['title']} TOP 10 (한국은 몇 위?) #Shorts",
        "description": (f"#Shorts {t['title']} 순위 ({r.year}년 기준)\n\n" + "\n".join(lines) + korea +
                        f"\n\n출처: 세계은행(World Bank) 오픈데이터, 지표 {t['indicator']}\n#세계순위 #데이터 #shorts"),
        "tags": ["세계순위", "데이터", "통계", "랭킹", t["title"]],
        "first": first.name,
    }
