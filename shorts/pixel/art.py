"""저해상도(180x180) 픽셀아트 무대: 로봇 '모니', 손님 NPC, 소품, 효과, 배경.

모든 그림은 코드로 그린다(외부 이미지 없음 = 저작권 걱정 없음, 무료).
화면에 낼 때는 6배 최근접 확대해서 1080x1080이 된다.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

SW = SH = 180
FLOOR = 128          # 바닥 시작 y
OUT = (24, 20, 37)   # 외곽선

C = {
    "out": OUT, "white": (244, 240, 230), "cream": (232, 224, 204), "shade": (186, 176, 158),
    "screen": (22, 34, 52), "face": (124, 255, 178), "red": (232, 72, 72), "yellow": (255, 210, 64),
    "green": (92, 200, 108), "blue": (72, 132, 232), "cyan": (96, 220, 232), "pink": (255, 140, 180),
    "brown": (140, 92, 60), "dbrown": (96, 60, 40), "grey": (130, 136, 150), "dgrey": (72, 76, 92),
    "lgrey": (196, 200, 210), "orange": (240, 140, 60), "black": (16, 14, 24), "skin1": (248, 208, 172),
    "skin2": (214, 160, 118), "skin3": (150, 100, 70), "teal": (64, 176, 168), "purple": (150, 100, 220),
    "glass": (150, 210, 240), "steel": (170, 178, 190), "wood": (176, 122, 76), "lwood": (214, 164, 108),
    "navy": (40, 52, 96), "fire1": (255, 220, 80), "fire2": (255, 130, 40), "fire3": (220, 50, 40),
}


def R(d: ImageDraw.ImageDraw, x, y, w, h, c):
    if w > 0 and h > 0:
        d.rectangle([int(x), int(y), int(x + w - 1), int(y + h - 1)], fill=c)


def box(d, x, y, w, h, c, outline=OUT):
    R(d, x, y, w, h, outline)
    R(d, x + 1, y + 1, w - 2, h - 2, c)


def pat(d, x, y, rows: list[str], cmap: dict):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in cmap:
                d.point((int(x + i), int(y + j)), fill=cmap[ch])


# ---------------------------------------------------------------- 로봇 '모니'

FACES = {
    "normal": [".##....##.", ".##....##.", "..........", "...####...", ".........."],
    "happy":  [".#.#..#.#.", "#...##...#", "..........", "..#....#..", "...####..."],
    "sad":    [".##....##.", "..........", "...####...", "..#....#..", ".........."],
    "shock":  ["###....###", "#.#....#.#", "###....###", "....##....", "....##...."],
    "focus":  ["####..####", "..........", "..........", "...####...", ".........."],
    "dizzy":  ["#.#....#.#", ".#......#.", "#.#....#.#", "...#..#...", "....##...."],
    "love":   ["##.#..##.#", "####..####", ".##....##.", "...####...", ".........."],
    "smug":   ["..........", "####..####", "..........", "....####..", ".......#.."],
}


def draw_bot(d, cx, by, t, pose="idle", face="normal", accent=C["teal"]):
    """cx: 중심 x, by: 발바닥 y."""
    bob = 0
    lift = 0
    if pose in ("idle", "work", "sad", "wave"):
        bob = 1 if int(t * 3) % 2 else 0
    if pose == "jump":
        lift = int(abs(math.sin(t * 7)) * 10)
    if pose == "shake":
        cx += 1 if int(t * 20) % 2 else -1
    y0 = by - lift
    # 다리
    step = int(t * 8) % 2 if pose == "walk" else 0
    R(d, cx - 5, y0 - 5 + step, 3, 5 - step, OUT)
    R(d, cx + 2, y0 - 5 + (1 - step if pose == "walk" else 0), 3, 5 - (1 - step if pose == "walk" else 0), OUT)
    R(d, cx - 6, y0 - 1 + step * 0, 5, 2, C["dgrey"])
    R(d, cx + 1, y0 - 1, 5, 2, C["dgrey"])
    # 몸
    top = y0 - 5 - 10 + bob
    box(d, cx - 7, top, 14, 10, C["cream"])
    R(d, cx - 6, top + 7, 12, 2, C["shade"])
    blink = int(t * 2) % 2
    R(d, cx - 2, top + 3, 4, 3, accent if blink else C["face"])
    # 팔
    def arm(x, y, w, h):
        R(d, x, y, w, h, OUT)
        R(d, x + 1 if w > 2 else x, y + 1 if h > 2 else y, max(1, w - 2), max(1, h - 2), C["shade"])
    if pose in ("idle", "walk", "shake"):
        arm(cx - 10, top + 1, 3, 7)
        arm(cx + 7, top + 1, 3, 7)
    elif pose == "sad":
        arm(cx - 9, top + 3, 3, 7)
        arm(cx + 6, top + 3, 3, 7)
    elif pose == "work":
        k = int(t * 6) % 2
        arm(cx + 6, top + 2 + k * 2, 9, 3)
        arm(cx - 10, top + 1, 3, 7)
        R(d, cx + 14, top + 1 + k * 2, 3, 4, C["dgrey"])
    elif pose == "wave":
        k = int(t * 5) % 2
        arm(cx - 10, top + 1, 3, 7)
        arm(cx + 7 + k, top - 7, 3, 9)
    elif pose == "jump":
        arm(cx - 10, top - 7, 3, 9)
        arm(cx + 7, top - 7, 3, 9)
    # 목, 머리(모니터)
    R(d, cx - 1, top - 2, 3, 2, OUT)
    htop = top - 2 - 15
    box(d, cx - 10, htop, 20, 15, C["white"])
    R(d, cx - 9, htop + 12, 18, 2, C["cream"])
    R(d, cx - 8, htop + 2, 16, 10, C["screen"])
    # 화면 빛 반사
    R(d, cx - 7, htop + 3, 2, 1, (60, 80, 110))
    f = FACES.get(face, FACES["normal"])
    if face in ("normal", "focus") and int(t * 10) % 37 == 0:   # 가끔 눈 깜빡
        f = ["..........", "####..####", "..........", "...####...", ".........."]
    pat(d, cx - 5, htop + 4, f, {"#": C["face"]})
    # 안테나
    R(d, cx, htop - 4, 1, 4, OUT)
    R(d, cx - 1, htop - 6, 3, 3, C["red"] if int(t * 2) % 2 else C["yellow"])
    return htop  # 머리 꼭대기 y (효과 위치용)


# ---------------------------------------------------------------- 손님 NPC

HAIR = [C["black"], C["dbrown"], C["brown"], C["yellow"], C["grey"], C["purple"], C["orange"]]
SHIRT = [C["blue"], C["red"], C["green"], C["pink"], C["purple"], C["orange"], C["navy"], C["teal"]]
SKIN = [C["skin1"], C["skin2"], C["skin3"]]


def npc_look(rnd: random.Random) -> dict:
    return {"hair": rnd.choice(HAIR), "shirt": rnd.choice(SHIRT), "skin": rnd.choice(SKIN),
            "pants": rnd.choice([C["navy"], C["dgrey"], C["dbrown"], C["black"]]),
            "long": rnd.random() < 0.5, "hat": rnd.random() < 0.2}


def draw_npc(d, cx, by, t, look, mood="normal", flip=False):
    bob = 1 if int(t * 2.5 + cx) % 2 else 0
    R(d, cx - 4, by - 6, 3, 6, look["pants"])
    R(d, cx + 1, by - 6, 3, 6, look["pants"])
    top = by - 6 - 10 + bob
    box(d, cx - 6, top, 12, 10, look["shirt"])
    if mood == "angry":
        k = int(t * 6) % 2
        R(d, cx - 9, top - 2 + k, 3, 7, look["skin"])
        R(d, cx + 6, top - 2 + (1 - k), 3, 7, look["skin"])
    elif mood == "happy":
        R(d, cx - 9, top - 4, 3, 7, look["skin"])
        R(d, cx + 6, top - 4, 3, 7, look["skin"])
    else:
        R(d, cx - 8, top + 1, 2, 8, look["skin"])
        R(d, cx + 6, top + 1, 2, 8, look["skin"])
    htop = top - 11
    box(d, cx - 6, htop, 12, 11, look["skin"])
    R(d, cx - 6, htop, 12, 3, look["hair"])
    if look["long"]:
        R(d, cx - 7, htop + 1, 2, 9, look["hair"])
        R(d, cx + 5, htop + 1, 2, 9, look["hair"])
    if look["hat"]:
        R(d, cx - 7, htop - 2, 14, 3, C["red"])
        R(d, cx + (-10 if flip else 4), htop + 1, 6, 1, C["red"])
    ex = -1 if flip else 1
    R(d, cx - 3 + ex, htop + 5, 1, 2, OUT)
    R(d, cx + 2 + ex, htop + 5, 1, 2, OUT)
    if mood == "happy":
        R(d, cx - 2 + ex, htop + 8, 4, 1, OUT)
        R(d, cx - 3 + ex, htop + 7, 1, 1, OUT)
        R(d, cx + 2 + ex, htop + 7, 1, 1, OUT)
    elif mood == "angry":
        R(d, cx - 4 + ex, htop + 3, 2, 1, OUT)
        R(d, cx + 2 + ex, htop + 3, 2, 1, OUT)
        R(d, cx - 2 + ex, htop + 8, 4, 1, OUT)
        R(d, cx - 3 + ex, htop + 9, 1, 1, OUT)
        R(d, cx + 2 + ex, htop + 9, 1, 1, OUT)
    else:
        R(d, cx - 1 + ex, htop + 8, 3, 1, OUT)
    return htop


# ---------------------------------------------------------------- 소품 (x: 왼쪽, y: 바닥 기준선)

def p_counter(d, x, y, t, w=60, c=None):
    c = c or C["wood"]
    box(d, x, y - 22, w, 22, c)
    R(d, x + 1, y - 21, w - 2, 3, C["lwood"])
    for i in range(x + 8, x + w - 4, 14):
        R(d, i, y - 15, 1, 12, C["dbrown"])


def p_coffee(d, x, y, t):
    box(d, x, y - 22, 18, 22, C["steel"])
    R(d, x + 2, y - 20, 14, 5, C["dgrey"])
    R(d, x + 4, y - 18, 2, 2, C["red"])
    R(d, x + 8, y - 18, 2, 2, C["green"])
    R(d, x + 7, y - 13, 4, 2, OUT)
    box(d, x + 6, y - 8, 6, 6, C["white"])


def p_cup(d, x, y, t, c=None):
    box(d, x, y - 6, 5, 6, c or C["white"])
    R(d, x + 5, y - 5, 2, 3, OUT)


def p_oven(d, x, y, t, on=True):
    box(d, x, y - 30, 30, 30, C["steel"])
    box(d, x + 3, y - 22, 24, 16, C["dgrey"])
    glow = C["fire2"] if on and int(t * 3) % 2 else C["orange"]
    R(d, x + 5, y - 20, 20, 12, glow if on else C["black"])
    for i in range(3):
        R(d, x + 6 + i * 8, y - 28, 3, 3, C["black"])


def p_bread(d, x, y, t):
    box(d, x, y - 34, 26, 34, C["wood"])
    for k in range(3):
        yy = y - 30 + k * 10
        R(d, x + 1, yy + 7, 24, 1, C["dbrown"])
        for i in range(3):
            box(d, x + 3 + i * 7, yy + 2, 6, 5, C["lwood"] if (i + k) % 2 else C["orange"])


def p_desk_pc(d, x, y, t, screen=None):
    box(d, x, y - 16, 40, 4, C["wood"])
    R(d, x + 3, y - 12, 3, 12, C["dbrown"])
    R(d, x + 34, y - 12, 3, 12, C["dbrown"])
    box(d, x + 10, y - 34, 22, 16, C["dgrey"])
    sc = screen or C["blue"]
    R(d, x + 12, y - 32, 18, 12, sc)
    for i in range(3):   # 화면 속 글줄이 흘러감
        w = 4 + (int(t * 5) + i * 3) % 12
        R(d, x + 13, y - 30 + i * 3, w, 1, C["white"])
    R(d, x + 20, y - 18, 2, 2, OUT)
    R(d, x + 14, y - 17, 14, 1, C["lgrey"])


def p_phone(d, x, y, t, ring=False):
    off = (1 if int(t * 12) % 2 else -1) if ring else 0
    box(d, x + off, y - 6, 10, 6, C["red"])
    R(d, x + 1 + off, y - 9, 8, 3, OUT)
    R(d, x + 2 + off, y - 8, 6, 1, C["red"])


def p_shelf(d, x, y, t, w=40, h=46, seed=1):
    rnd = random.Random(seed)
    box(d, x, y - h, w, h, C["lgrey"])
    for k in range(3):
        yy = y - h + 4 + k * 14
        R(d, x + 1, yy + 10, w - 2, 2, C["grey"])
        cx = x + 3
        while cx < x + w - 6:
            iw = rnd.randint(3, 6)
            ih = rnd.randint(5, 9)
            R(d, cx, yy + 10 - ih, iw, ih, rnd.choice(SHIRT + [C["yellow"], C["white"]]))
            cx += iw + 1


def p_books(d, x, y, t, w=40, h=56, seed=2):
    rnd = random.Random(seed)
    box(d, x, y - h, w, h, C["dbrown"])
    for k in range(4):
        yy = y - h + 3 + k * 13
        R(d, x + 1, yy + 10, w - 2, 2, C["wood"])
        cx = x + 3
        while cx < x + w - 4:
            iw = rnd.randint(2, 4)
            ih = rnd.randint(7, 10)
            R(d, cx, yy + 10 - ih, iw, ih, rnd.choice([C["red"], C["blue"], C["green"], C["yellow"],
                                                        C["purple"], C["navy"], C["teal"]]))
            cx += iw + 1


def p_register(d, x, y, t):
    box(d, x, y - 10, 16, 10, C["dgrey"])
    box(d, x + 3, y - 18, 10, 8, C["green"] if int(t * 2) % 2 else C["teal"])
    R(d, x + 5, y - 15, 6, 2, C["black"])


def p_chair_mirror(d, x, y, t):
    box(d, x + 2, y - 60, 26, 30, C["glass"])
    R(d, x + 5, y - 57, 4, 12, C["white"])
    R(d, x + 1, y - 61, 28, 1, C["wood"])
    box(d, x + 6, y - 24, 18, 6, C["red"])
    box(d, x + 20, y - 34, 5, 16, C["red"])
    R(d, x + 13, y - 18, 3, 14, C["steel"])
    R(d, x + 8, y - 4, 14, 4, C["dgrey"])


def p_bed(d, x, y, t):
    box(d, x, y - 14, 44, 6, C["white"])
    box(d, x + 2, y - 18, 10, 5, C["lgrey"])
    R(d, x + 2, y - 8, 2, 8, C["steel"])
    R(d, x + 40, y - 8, 2, 8, C["steel"])
    R(d, x, y - 24, 2, 16, C["steel"])


def p_iv(d, x, y, t):
    R(d, x + 4, y - 44, 1, 44, C["steel"])
    R(d, x, y - 2, 10, 2, C["steel"])
    box(d, x + 1, y - 46, 7, 10, C["glass"])
    drip = int(t * 3) % 6
    R(d, x + 4, y - 35 + drip, 1, 1, C["cyan"])


def p_monitor(d, x, y, t):   # 심박 모니터
    R(d, x + 6, y - 28, 2, 28, C["steel"])
    box(d, x, y - 42, 16, 14, C["dgrey"])
    R(d, x + 2, y - 40, 12, 10, C["black"])
    k = int(t * 10) % 12
    for i in range(12):
        hh = 4 if i == k else (2 if i == (k + 1) % 12 else 0)
        R(d, x + 2 + i, y - 35 - hh, 1, 1 + hh, C["green"])


def p_plant(d, x, y, t):
    box(d, x, y - 8, 10, 8, C["orange"])
    for i, (dx, dy) in enumerate([(-2, -16), (3, -20), (7, -15), (1, -12), (5, -13)]):
        R(d, x + 2 + dx, y - 8 + dy + 4, 4, 8, C["green"])


def p_taxi(d, x, y, t, c=None):
    c = c or C["yellow"]
    sh = 1 if int(t * 10) % 2 else 0
    box(d, x, y - 18 - sh, 60, 12, c)
    box(d, x + 12, y - 28 - sh, 32, 11, c)
    R(d, x + 15, y - 26 - sh, 12, 7, C["glass"])
    R(d, x + 29, y - 26 - sh, 12, 7, C["glass"])
    R(d, x + 24, y - 32 - sh, 10, 4, C["red"] if c == C["yellow"] else C["white"])
    for wx in (x + 8, x + 42):
        box(d, wx, y - 9, 11, 9, C["black"])
        R(d, wx + 4, y - 6, 3, 3, C["lgrey"])
    R(d, x + 56, y - 16 - sh, 3, 3, C["fire1"])


def p_mailbox(d, x, y, t):
    R(d, x + 5, y - 14, 3, 14, C["dgrey"])
    box(d, x, y - 30, 14, 16, C["red"])
    R(d, x + 3, y - 26, 8, 2, OUT)


def p_fire(d, x, y, t, size=1.0):
    rnd = random.Random(int(t * 10))
    for i in range(int(10 * size)):
        fx = x + rnd.randint(0, int(24 * size))
        fh = rnd.randint(6, int(22 * size))
        R(d, fx, y - fh, 4, fh, C["fire3"])
        R(d, fx + 1, y - fh * 0.7, 2, fh * 0.7, C["fire2"])
        R(d, fx + 1, y - fh * 0.35, 2, fh * 0.35, C["fire1"])


def p_house(d, x, y, t):
    box(d, x, y - 50, 50, 50, C["lgrey"])
    d.polygon([(x - 4, y - 50), (x + 25, y - 70), (x + 54, y - 50)], fill=C["dbrown"], outline=OUT)
    for wx in (x + 6, x + 30):
        box(d, wx, y - 40, 14, 12, C["black"])
    box(d, x + 19, y - 22, 12, 22, C["wood"])


def p_hydrant(d, x, y, t):
    box(d, x, y - 14, 8, 14, C["red"])
    R(d, x - 2, y - 10, 12, 3, C["red"])
    R(d, x + 1, y - 17, 6, 3, C["red"])


def p_tripod(d, x, y, t):
    d.line([(x + 8, y - 22), (x, y)], fill=OUT)
    d.line([(x + 8, y - 22), (x + 16, y)], fill=OUT)
    R(d, x + 8, y - 22, 1, 22, OUT)
    box(d, x + 2, y - 32, 14, 10, C["dgrey"])
    box(d, x + 12, y - 30, 6, 6, C["black"])
    R(d, x + 4, y - 34, 4, 2, C["dgrey"])
    if int(t * 1.5) % 4 == 0:
        R(d, x + 4, y - 31, 3, 2, C["white"])


def p_softbox(d, x, y, t):
    R(d, x + 9, y - 40, 2, 40, C["dgrey"])
    R(d, x + 3, y - 2, 14, 2, C["dgrey"])
    box(d, x, y - 58, 20, 18, C["white"])
    R(d, x + 2, y - 56, 16, 14, (255, 250, 220))


def p_backdrop(d, x, y, t, c=None):
    R(d, x, 14, 2, y - 14, C["dgrey"])
    R(d, x + 78, 14, 2, y - 14, C["dgrey"])
    R(d, x + 2, 16, 76, y - 14, c or (200, 220, 240))


def p_board(d, x, y, t, lines=3):
    box(d, x, y - 64, 64, 34, C["wood"])
    R(d, x + 2, y - 62, 60, 30, (40, 84, 64))
    for i in range(lines):
        R(d, x + 6, y - 58 + i * 7, 20 + (i * 13) % 30, 2, C["white"])


def p_desk(d, x, y, t, w=26):
    box(d, x, y - 14, w, 4, C["lwood"])
    R(d, x + 2, y - 10, 2, 10, C["dgrey"])
    R(d, x + w - 4, y - 10, 2, 10, C["dgrey"])


def p_stove(d, x, y, t, flame=True):
    box(d, x, y - 24, 34, 24, C["steel"])
    R(d, x + 2, y - 18, 30, 1, C["dgrey"])
    box(d, x + 6, y - 14, 22, 10, C["dgrey"])
    box(d, x + 4, y - 30, 20, 6, C["black"])
    R(d, x + 24, y - 28, 10, 2, C["black"])
    if flame:
        k = int(t * 8) % 2
        R(d, x + 6, y - 25, 16, 1, C["fire2"] if k else C["fire1"])


def p_sink(d, x, y, t):
    box(d, x, y - 22, 30, 22, C["lgrey"])
    R(d, x + 3, y - 20, 24, 5, C["glass"])
    R(d, x + 20, y - 30, 2, 10, C["steel"])
    R(d, x + 16, y - 30, 6, 2, C["steel"])


def p_dishes(d, x, y, t, n=6):
    for i in range(n):
        R(d, x, y - 2 - i * 3, 14, 2, C["white"] if i % 2 else C["lgrey"])
        R(d, x, y - 1 - i * 3, 14, 1, OUT)


def p_easel(d, x, y, t, art=None):
    d.line([(x + 12, y - 50), (x + 2, y)], fill=C["dbrown"], width=2)
    d.line([(x + 12, y - 50), (x + 22, y)], fill=C["dbrown"], width=2)
    box(d, x, y - 48, 26, 24, C["white"])
    if art:
        R(d, x + 3, y - 45, 20, 8, C["cyan"])
        R(d, x + 3, y - 37, 20, 10, C["green"])
        R(d, x + 14, y - 44, 5, 5, C["yellow"])


def p_table(d, x, y, t, w=30):
    box(d, x, y - 18, w, 4, C["white"])
    R(d, x + w // 2 - 1, y - 14, 3, 14, C["dgrey"])
    R(d, x + w // 2 - 6, y - 2, 13, 2, C["dgrey"])


def p_plate(d, x, y, t, food=None):
    R(d, x, y - 2, 12, 2, C["white"])
    R(d, x + 1, y - 1, 10, 1, OUT)
    if food:
        R(d, x + 3, y - 5, 6, 3, food)


def p_bottles(d, x, y, t, w=50):
    box(d, x, y - 48, w, 34, C["dbrown"])
    rnd = random.Random(7)
    for k in range(2):
        yy = y - 46 + k * 16
        R(d, x + 1, yy + 13, w - 2, 2, C["wood"])
        for i in range(x + 3, x + w - 5, 6):
            c = rnd.choice([C["green"], C["glass"], C["orange"], C["purple"], C["red"]])
            R(d, i, yy + 4, 4, 9, c)
            R(d, i + 1, yy + 1, 2, 3, c)


def p_boxes(d, x, y, t):
    box(d, x, y - 14, 18, 14, C["lwood"])
    box(d, x + 18, y - 12, 14, 12, C["wood"])
    box(d, x + 4, y - 26, 14, 12, C["wood"])
    for bx, by_, bw in ((x, y - 14, 18), (x + 18, y - 12, 14), (x + 4, y - 26, 14)):
        R(d, bx + bw // 2, by_ + 1, 1, 4, C["dbrown"])


def p_dog(d, x, y, t, c=None, sick=False):
    c = c or C["lwood"]
    wag = int(t * 6) % 2
    box(d, x, y - 12, 18, 8, c)
    R(d, x + 2, y - 4, 2, 4, c)
    R(d, x + 13, y - 4, 2, 4, c)
    box(d, x + 14, y - 18, 9, 8, c)
    R(d, x + 15, y - 20, 3, 3, C["dbrown"])
    R(d, x + 20, y - 15, 1, 1, OUT)
    R(d, x + 22, y - 13, 2, 2, OUT)
    R(d, x - 3, y - 13 - wag * 2, 4, 2, c)
    if sick:
        R(d, x + 4, y - 11, 6, 3, C["white"])


def p_cat(d, x, y, t, c=None):
    c = c or C["grey"]
    box(d, x, y - 9, 13, 7, c)
    R(d, x + 1, y - 2, 2, 2, c)
    R(d, x + 9, y - 2, 2, 2, c)
    box(d, x + 9, y - 15, 8, 7, c)
    R(d, x + 9, y - 17, 2, 2, c)
    R(d, x + 15, y - 17, 2, 2, c)
    R(d, x + 11, y - 12, 1, 1, C["green"])
    R(d, x + 14, y - 12, 1, 1, C["green"])
    k = int(t * 3) % 2
    R(d, x - 3, y - 12 - k * 3, 2, 6, c)


def p_streetlamp(d, x, y, t, night=False):
    R(d, x + 3, y - 60, 2, 60, C["dgrey"])
    box(d, x, y - 66, 8, 7, C["yellow"] if night else C["lgrey"])


def p_building(d, x, y, t, w=40, h=90, c=None, night=False):
    c = c or C["grey"]
    box(d, x, y - h, w, h, c)
    rnd = random.Random(x * 7 + h)
    for wy in range(y - h + 6, y - 10, 10):
        for wx in range(x + 4, x + w - 6, 9):
            lit = rnd.random() < (0.6 if night else 0.2)
            R(d, wx, wy, 5, 6, C["yellow"] if lit else C["navy"])


def p_tree(d, x, y, t):
    R(d, x + 6, y - 20, 4, 20, C["dbrown"])
    d.ellipse([x - 4, y - 46, x + 20, y - 18], fill=C["green"], outline=OUT)


def p_fridge(d, x, y, t):
    box(d, x, y - 50, 24, 50, C["white"])
    R(d, x + 1, y - 30, 22, 1, OUT)
    R(d, x + 19, y - 46, 2, 10, C["lgrey"])
    R(d, x + 19, y - 26, 2, 14, C["lgrey"])


def p_mic(d, x, y, t):
    R(d, x + 4, y - 40, 1, 40, C["dgrey"])
    R(d, x, y - 2, 10, 2, C["dgrey"])
    box(d, x + 1, y - 48, 7, 9, C["lgrey"])


def p_door(d, x, y, t):
    box(d, x, y - 60, 28, 60, C["wood"])
    R(d, x + 22, y - 32, 3, 3, C["yellow"])
    R(d, x + 4, y - 54, 20, 20, C["dbrown"])


def p_clock(d, x, y, t):
    d.ellipse([x, y, x + 14, y + 14], fill=C["white"], outline=OUT)
    a = t * 0.8
    d.line([(x + 7, y + 7), (x + 7 + 5 * math.cos(a), y + 7 + 5 * math.sin(a))], fill=OUT)
    d.line([(x + 7, y + 7), (x + 7, y + 3)], fill=OUT)


def p_poster(d, x, y, t, c=None):
    box(d, x, y, 18, 24, c or C["pink"])
    R(d, x + 3, y + 4, 12, 8, C["white"])
    R(d, x + 3, y + 15, 12, 2, C["white"])
    R(d, x + 3, y + 19, 8, 2, C["white"])


def p_field_lines(d, x, y, t):
    R(d, 0, FLOOR + 10, SW, 2, C["white"])
    d.ellipse([60, FLOOR + 16, 120, FLOOR + 40], outline=C["white"])


def p_goal(d, x, y, t):
    R(d, x, y - 40, 3, 40, C["white"])
    R(d, x + 33, y - 40, 3, 40, C["white"])
    R(d, x, y - 40, 36, 3, C["white"])
    for i in range(x + 4, x + 33, 4):
        R(d, i, y - 37, 1, 37, C["lgrey"])


def p_whistle_flag(d, x, y, t):
    R(d, x, y - 30, 2, 30, C["dgrey"])
    k = int(t * 4) % 2
    R(d, x + 2, y - 30 + k, 12, 8, C["yellow"])


def p_sofa(d, x, y, t):
    box(d, x, y - 16, 40, 12, C["purple"])
    box(d, x, y - 26, 40, 10, C["purple"])
    R(d, x + 2, y - 4, 3, 4, C["dbrown"])
    R(d, x + 35, y - 4, 3, 4, C["dbrown"])


PROPS = {k[2:]: v for k, v in globals().items() if k.startswith("p_")}


# ---------------------------------------------------------------- 효과

def fx_steam(d, x, y, t):
    for i in range(3):
        k = (t * 1.5 + i / 3) % 1
        R(d, x + i * 3 + int(math.sin(k * 6 + i) * 2), y - int(k * 14), 2, 2, (230, 230, 240))


def fx_sparkle(d, x, y, t, c=C["yellow"]):
    rnd = random.Random(int(x * 13 + y))
    for i in range(6):
        px, py = x + rnd.randint(-20, 20), y + rnd.randint(-22, 6)
        if int(t * 6 + i) % 3:
            R(d, px, py - 2, 1, 5, c)
            R(d, px - 2, py, 5, 1, c)


def fx_smoke(d, x, y, t):
    for i in range(5):
        k = (t * 0.8 + i / 5) % 1
        s = 3 + int(k * 6)
        R(d, x - 10 + i * 5, y - int(k * 24), s, s, (110, 110, 120) if i % 2 else (80, 80, 90))


def fx_sweat(d, x, y, t):
    k = int(t * 4) % 6
    R(d, x, y + k, 2, 3, C["cyan"])


def fx_hearts(d, x, y, t):
    for i in range(3):
        k = (t * 0.9 + i / 3) % 1
        hx, hy = x - 10 + i * 9, y - int(k * 20)
        pat(d, hx, hy, [".#.#.", "#####", ".###.", "..#.."], {"#": C["pink"]})


def fx_notes(d, x, y, t):
    for i in range(3):
        k = (t * 0.8 + i / 3) % 1
        nx, ny = x - 10 + i * 10, y - int(k * 22)
        pat(d, nx, ny, [".##", ".#.", ".#.", "##."], {"#": C["white"]})


def fx_zzz(d, x, y, t):
    for i in range(3):
        k = (t * 0.6 + i / 3) % 1
        pat(d, x + i * 5, y - int(k * 20), ["###", "..#", ".#.", "###"], {"#": C["white"]})


def fx_coins(d, x, y, t):
    for i in range(4):
        k = (t * 1.2 + i / 4) % 1
        R(d, x - 12 + i * 8, y - int(k * 18), 4, 4, C["yellow"])
        R(d, x - 11 + i * 8, y - int(k * 18) + 1, 2, 2, C["orange"])


def fx_bubble(d, x, y, t, mark="!"):
    box(d, x, y, 11, 11, C["white"])
    R(d, x + 2, y + 11, 2, 2, C["white"])
    if mark == "!":
        R(d, x + 5, y + 2, 1, 5, C["red"])
        R(d, x + 5, y + 8, 1, 1, C["red"])
    elif mark == "?":
        pat(d, x + 3, y + 2, ["###.", "...#", ".##.", ".#..", "....", ".#.."], {"#": C["blue"]})
    elif mark == "...":
        for i in range(3):
            R(d, x + 2 + i * 3, y + 5, 1, 1, OUT)


def fx_confetti(d, x, y, t):
    rnd = random.Random(3)
    for i in range(30):
        px = rnd.randint(0, SW)
        speed = rnd.uniform(20, 50)
        py = int((rnd.randint(0, SH) + t * speed) % SH)
        R(d, px, py, 2, 2, rnd.choice([C["red"], C["yellow"], C["cyan"], C["pink"], C["green"]]))


def fx_water(d, x, y, t):
    for i in range(10):
        k = (t * 3 + i / 10) % 1
        R(d, x + int(k * 40), y - int(math.sin(k * math.pi) * 14), 2, 2, C["cyan"])


def fx_ring(d, x, y, t):
    if int(t * 6) % 2:
        R(d, x - 4, y - 2, 2, 1, C["yellow"])
        R(d, x + 12, y - 2, 2, 1, C["yellow"])
        R(d, x - 5, y - 5, 1, 2, C["yellow"])
        R(d, x + 14, y - 5, 1, 2, C["yellow"])


def fx_flash(d, x, y, t):
    if (t * 2) % 1 < 0.15:
        R(d, 0, 0, SW, SH, (255, 255, 255))


FX = {k[3:]: v for k, v in globals().items() if k.startswith("fx_")}


# ---------------------------------------------------------------- 배경과 무대

SKY = {"morning": (150, 200, 240), "day": (110, 180, 245), "evening": (240, 150, 110), "night": (30, 36, 80)}


def background(scene: dict, t: float) -> Image.Image:
    img = Image.new("RGB", (SW, SH), scene["wall"])
    d = ImageDraw.Draw(img)
    sky = SKY.get(scene.get("time", "day"), SKY["day"])
    if scene.get("outdoor"):
        R(d, 0, 0, SW, FLOOR, sky)
        if scene.get("time") == "night":
            rnd = random.Random(5)
            for _ in range(25):
                R(d, rnd.randint(0, SW), rnd.randint(0, 70), 1, 1, C["white"])
            d.ellipse([140, 12, 156, 28], fill=C["cream"])
        else:
            d.ellipse([140, 12, 158, 30], fill=C["yellow"] if scene.get("time") != "evening" else C["orange"])
            for cx0 in (20, 90):   # 구름이 천천히 흐름
                cx = int((cx0 + t * 4) % (SW + 40)) - 20
                R(d, cx, 24, 26, 6, C["white"])
                R(d, cx + 6, 20, 14, 4, C["white"])
        R(d, 0, FLOOR, SW, SH - FLOOR, scene["floor"])
        R(d, 0, FLOOR, SW, 3, scene.get("floor2", C["dgrey"]))
        if scene.get("road"):
            for i in range(0, SW, 24):
                R(d, (i - int(t * 30)) % (SW + 24) - 12, FLOOR + 30, 12, 2, C["white"])
    else:
        R(d, 0, 0, SW, 8, scene.get("wall2", scene["wall"]))
        for i in range(0, SW, 12):   # 벽지 무늬
            R(d, i, 8, 1, FLOOR - 8, scene.get("wall2", scene["wall"]))
        if scene.get("window", True):
            wx = scene.get("window_x", 12)
            box(d, wx, 22, 40, 30, sky)
            R(d, wx + 19, 22, 2, 30, OUT)
            R(d, wx, 36, 40, 2, OUT)
            if scene.get("time") == "night":
                R(d, wx + 6, 26, 1, 1, C["white"])
                R(d, wx + 28, 30, 1, 1, C["white"])
        R(d, 0, FLOOR - 4, SW, 4, scene.get("trim", C["dbrown"]))
        f1, f2 = scene["floor"], scene.get("floor2", tuple(max(0, v - 18) for v in scene["floor"]))
        for j, yy in enumerate(range(FLOOR, SH, 8)):
            for i, xx in enumerate(range(0, SW, 16)):
                R(d, xx, yy, 16, 8, f1 if (i + j) % 2 else f2)
    for name, x, *rest in scene.get("decor", []):
        kw = dict(rest[0]) if rest else {}
        y = kw.pop("y", 0)
        PROPS[name](d, x, y, t, **kw)
    return img


def draw_props(d, scene: dict, t: float, overrides: dict | None = None):
    for name, x, *rest in scene.get("props", []):
        kw = dict(rest[0]) if rest else {}
        kw.update((overrides or {}).get(name, {}))
        y = kw.pop("y", FLOOR + 20)
        PROPS[name](d, x, y, t, **kw)
