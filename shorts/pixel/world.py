"""모니 세계여행용 복셀 세계: 거리, 건물, 국기, 랜드마크, 모니, 행인.

좌표: x(좌우) y(위) z(앞). 길은 z 방향으로 뻗고 끝(z가 큰 쪽)에 랜드마크가 있다.
"""
from __future__ import annotations

import math
import random

import numpy as np

from .voxel import Palette, box

GX, GY, GZ = 72, 64, 240
ROAD_X0, ROAD_X1 = 28, 44           # 차도
SIDE_W = 5                          # 인도 폭
CENTER = (ROAD_X0 + ROAD_X1) / 2
LANDMARK_Z = 196

GROUND = {"grass": (96, 168, 84), "sand": (222, 196, 140), "snow": (236, 240, 246), "dry": (186, 160, 110)}


def base_palette() -> Palette:
    p = Palette()
    for name, rgb in {
        "road": (62, 64, 74), "line": (240, 230, 200), "side": (176, 176, 182), "curb": (140, 140, 150),
        "white": (242, 240, 232), "cream": (226, 216, 196), "screen": (24, 36, 54), "face": (120, 255, 170),
        "dgrey": (70, 74, 88), "grey": (130, 134, 146), "black": (24, 22, 30), "red": (214, 52, 52),
        "yellow": (250, 206, 60), "green": (40, 140, 70), "blue": (40, 80, 180), "orange": (240, 130, 40),
        "window": (250, 222, 130), "glass": (140, 196, 230), "trunk": (110, 76, 50), "leaf": (60, 150, 70),
        "leaf2": (90, 180, 80), "skin1": (246, 206, 170), "skin2": (210, 156, 116), "skin3": (140, 96, 66),
        "hair1": (40, 30, 26), "hair2": (120, 80, 40), "hair3": (230, 200, 120), "pole": (190, 190, 200),
        "lamp": (255, 240, 180), "rock": (130, 120, 112), "rock2": (160, 150, 140), "snowcap": (250, 250, 255),
        "gold": (230, 180, 60), "teal": (64, 176, 168), "accent": (64, 176, 168),
    }.items():
        p(name, rgb)
    for i, c in enumerate([(220, 70, 70), (60, 110, 210), (60, 170, 90), (240, 160, 60), (150, 90, 200),
                           (240, 240, 240), (40, 40, 60), (230, 120, 170)]):
        p(f"shirt{i}", c)
    return p


# ---------------------------------------------------------------- 국기

def flag_pixels(spec: dict, w=9, h=6) -> list[list[str]]:
    """국기를 w x h 색 이름 격자로. 위쪽 행이 먼저."""
    kind, cols = spec["type"], spec["colors"]
    g = [[cols[0]] * w for _ in range(h)]
    if kind == "h":            # 가로 줄무늬 (비율 지정 가능)
        weights = spec.get("weights", [1] * len(cols))
        total = sum(weights)
        rows = []
        for c, wgt in zip(cols, weights):
            rows += [c] * round(h * wgt / total)
        rows = (rows + [cols[-1]] * h)[:h]
        g = [[rows[j]] * w for j in range(h)]
    elif kind == "v":          # 세로 줄무늬 (비율 지정 가능)
        weights = spec.get("weights", [1] * len(cols))
        total = sum(weights)
        colsx = []
        for c, wgt in zip(cols, weights):
            colsx += [c] * round(w * wgt / total)
        colsx = (colsx + [cols[-1]] * w)[:w]
        g = [list(colsx) for _ in range(h)]
    elif kind == "circle":     # 바탕 + 가운데 원
        for j in range(h):
            for i in range(w):
                if (i - (w - 1) / 2 + spec.get("dx", 0)) ** 2 + (j - (h - 1) / 2) ** 2 <= 2.3:
                    g[j][i] = cols[1]
    elif kind == "cross":      # 북유럽 십자 (바탕, 십자, 안쪽 십자)
        cx = 3
        for j in range(h):
            for i in range(w):
                if i in (cx - 1, cx, cx + 1) or j in (h // 2 - 1, h // 2):
                    g[j][i] = cols[1]
        if len(cols) > 2:
            for j in range(h):
                g[j][cx] = cols[2]
            for i in range(w):
                g[h // 2 - (1 if h % 2 == 0 else 0)][i] = cols[2] if h % 2 else g[h // 2 - 1][i]
                g[h // 2][i] = cols[2] if h % 2 else g[h // 2][i]
    elif kind == "plus":       # 스위스형 가운데 십자
        for j in range(1, h - 1):
            g[j][w // 2] = cols[1]
        for i in range(w // 2 - 2, w // 2 + 3):
            g[h // 2][i] = cols[1]
            g[h // 2 - 1][i] = cols[1] if h % 2 == 0 else g[h // 2 - 1][i]
    if spec.get("dot"):        # 가운데 문장(紋章)을 점 하나로 단순화
        g[h // 2][w // 2] = spec["dot"]
    if spec.get("canton"):     # 왼쪽 위 사각형 (미국·칠레·말레이시아형)
        cn = spec["canton"]
        cw, ch = cn.get("w", w // 2), cn.get("h", h // 2)
        for j in range(ch):
            for i in range(cw):
                g[j][i] = cn["color"]
        if cn.get("dot"):
            g[(ch - 1) // 2][(cw - 1) // 2] = cn["dot"]
    if spec.get("tri"):        # 깃대 쪽 삼각형 (필리핀·체코·쿠바형)
        tr = spec["tri"]
        depth = tr.get("w", 4)
        for j in range(h):
            dist = abs(j - (h - 1) / 2)
            for i in range(max(1, round(depth * (1 - dist / (h / 2))))):
                g[j][i] = tr["color"]
        if tr.get("dot"):
            g[h // 2][max(0, depth // 2 - 1)] = tr["dot"]
    return g


def flagpole(grid, pal, x, z, spec, height=16, t=0.0):
    """깃대와 펄럭이는 국기(매 프레임 다시 찍는다)."""
    box(grid, x, 1, z, 1, height, 1, pal("pole"))
    for j, row in enumerate(flag_pixels(spec)):
        for i, name in enumerate(row):
            xx = x + int(round(math.sin(t * 4 - i * 0.8) * 0.7 * (i / 8)))
            zz = z + 1 + i
            if 0 <= xx < grid.shape[0] and zz < grid.shape[2]:
                grid[xx, height - j, zz] = pal(name)


# ---------------------------------------------------------------- 건물과 소품

def building(grid, pal, x0, z0, w, d, h, wall, rnd, roof=None, facing=1):
    box(grid, x0, 1, z0, w, h, d, wall)
    win = pal("window") if rnd.random() < 0.5 else pal("glass")
    face_x = x0 + w - 1 if facing > 0 else x0
    for y in range(3, h - 1, 3):
        for z in range(z0 + 1, z0 + d - 1, 2):
            if rnd.random() < 0.8:
                grid[face_x, y, z] = win
    if roof is not None:
        box(grid, x0, h + 1, z0, w, 1, d, roof)
        if rnd.random() < 0.4:
            box(grid, x0 + 1, h + 2, z0 + 1, w - 2, 1, d - 2, roof)
    # 1층 문
    dz = z0 + d // 2
    box(grid, face_x, 1, dz, 1, 3, 2, pal("dgrey"))


def tree(grid, pal, x, z, h=6, kind="round"):
    box(grid, x, 1, z, 1, h, 1, pal("trunk"))
    if kind == "palm":
        for dx, dz in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (1, -1), (-1, 1)):
            box(grid, x + dx, h, z + dz, 1, 1, 1, pal("leaf"))
        box(grid, x, h + 1, z, 1, 1, 1, pal("leaf2"))
    elif kind == "pine":
        for k, r in enumerate((3, 2, 2, 1, 1, 0)):
            box(grid, x - r, h - 3 + k, z - r, 2 * r + 1, 1, 2 * r + 1, pal("leaf" if k % 2 else "leaf2"))
    else:
        box(grid, x - 2, h - 1, z - 2, 5, 3, 5, pal("leaf"))
        box(grid, x - 1, h + 2, z - 1, 3, 1, 3, pal("leaf2"))


def lamp(grid, pal, x, z, toward):
    box(grid, x, 1, z, 1, 9, 1, pal("pole"))
    box(grid, x + toward, 9, z, 1, 1, 1, pal("pole"))
    box(grid, x + toward * 2, 8, z, 1, 1, 1, pal("lamp"))


# ---------------------------------------------------------------- 랜드마크 (길 끝, 중앙)

def lm_lattice_tower(g, p, cx, cz, c):
    col = p("lm", c)
    H = 58
    for y in range(1, H):
        half = max(1, int(11 * (1 - y / H) ** 1.7) + 1)
        for sx in (-1, 1):
            for sz in (-1, 1):
                box(g, cx + sx * half - (1 if sx < 0 else 0), y, cz + sz * half - (1 if sz < 0 else 0), 2, 1, 2, col)
        if y in (12, 24, 40):
            box(g, cx - half, y, cz - half, 2 * half + 1, 1, 2 * half + 1, col)
        if y < 10 and y % 3 == 0:
            for k in range(-half, half + 1):
                box(g, cx + k, y, cz - half, 1, 1, 1, col)
                box(g, cx + k, y, cz + half, 1, 1, 1, col)
    box(g, cx, H, cz, 1, 4, 1, col)


def lm_pyramid(g, p, cx, cz, c, steps=False):
    col, col2 = p("lm", c), p("lm2", tuple(max(0, v - 25) for v in c))
    H = 26 if not steps else 22
    for y in range(H):
        r = H - y if not steps else (H - y) // 1
        if steps and y % 3 == 2:
            r -= 1
        box(g, cx - r, 1 + y, cz - r, 2 * r + 1, 1, 2 * r + 1, col if y % 2 else col2)
    if steps:
        box(g, cx - 2, H + 1, cz - 2, 5, 4, 5, col2)
        box(g, cx - 1, 1, cz - H - 1, 3, H, H, col)   # 계단


def lm_pagoda(g, p, cx, cz, c):
    wall, roof = p("lm", c), p("lm2", (60, 60, 70))
    y = 1
    for k, r in enumerate((9, 8, 7, 6, 5)):
        box(g, cx - r + 2, y, cz - r + 2, 2 * r - 3, 5, 2 * r - 3, wall)
        box(g, cx - r, y + 5, cz - r, 2 * r + 1, 1, 2 * r + 1, roof)
        y += 7
    box(g, cx, y, cz, 1, 7, 1, p("gold"))


def lm_colosseum(g, p, cx, cz, c):
    col, dark = p("lm", c), p("lm2", tuple(int(v * 0.6) for v in c))
    R, r = 22, 15
    for y in range(1, 22):
        for a in range(0, 360, 2):
            for rr in range(r, R):
                x = int(cx + rr * math.cos(math.radians(a)))
                z = int(cz + rr * math.sin(math.radians(a)) * 0.8)
                if rr == R - 1 and y % 6 in (2, 3, 4) and a % 12 < 6:
                    g[x, y, z] = dark
                elif rr in (R - 1, r):
                    g[x, y, z] = col
        # 한쪽이 무너진 모양
    box(g, cx - R, 15, cz - R, R, 8, 2 * R, 0)


def lm_dome(g, p, cx, cz, c, minarets=True, top=(240, 240, 245)):
    col, top = p("lm", c), p("lm2", tuple(top))
    box(g, cx - 14, 1, cz - 10, 29, 14, 20, col)
    R = 10
    for y in range(R + 1):
        rr = int(math.sqrt(max(0, R * R - y * y)))
        box(g, cx - rr, 15 + y, cz - rr, 2 * rr + 1, 1, 2 * rr + 1, top)
    box(g, cx, 26, cz, 1, 4, 1, p("gold"))
    if minarets:
        for sx in (-18, 18):
            box(g, cx + sx, 1, cz - 8, 2, 34, 2, col)
            box(g, cx + sx, 35, cz - 8, 2, 4, 2, top)


def lm_windmill(g, p, cx, cz, c, t=0.0):
    col, roof, sail = p("lm", c), p("lm2", (80, 60, 50)), p("sail", (240, 236, 220))
    for y in range(1, 24):
        r = 6 - y // 6
        box(g, cx - r, y, cz - r, 2 * r + 1, 1, 2 * r + 1, col)
    box(g, cx - 3, 24, cz - 3, 7, 3, 7, roof)
    hub = (cx, 22, cz - 6)
    for k in range(4):
        a = t * 1.2 + k * math.pi / 2
        for s in range(2, 18):
            x = int(round(hub[0] + math.cos(a) * s))
            y = int(round(hub[1] + math.sin(a) * s))
            if 0 < y < g.shape[1] and 0 <= x < g.shape[0]:
                g[x, y, hub[2]] = sail
                if s > 6:
                    xx = int(round(hub[0] + math.cos(a) * s - math.sin(a) * 2))
                    yy = int(round(hub[1] + math.sin(a) * s + math.cos(a) * 2))
                    if 0 < yy < g.shape[1] and 0 <= xx < g.shape[0]:
                        g[xx, yy, hub[2]] = sail


def lm_needle(g, p, cx, cz, c):
    col, pod = p("lm", c), p("lm2", (240, 240, 245))
    box(g, cx - 2, 1, cz - 2, 5, 44, 5, col)
    box(g, cx - 5, 34, cz - 5, 11, 4, 11, pod)
    box(g, cx - 4, 38, cz - 4, 9, 1, 9, col)
    box(g, cx, 45, cz, 1, 14, 1, col)
    box(g, cx, 59, cz, 1, 1, 1, p("red"))


def lm_mountain(g, p, cx, cz, c, snow=True, green=False):
    rock = p("lm", c)
    rock2 = p("lm2", tuple(min(255, v + 22) for v in c))
    cap, grass = p("snowcap"), p("lm3", (70, 140, 70))
    rnd = random.Random(4)
    for peak, (dx, H, R) in enumerate([(-14, 40, 30), (14, 32, 26), (0, 50, 34)]):
        for y in range(1, H):
            r = int(R * (1 - y / H)) + rnd.randint(0, 1)
            colr = rock if (y // 3) % 2 else rock2
            if snow and y > H * 0.72:
                colr = cap
            elif green and y < H * 0.75 and (y // 2) % 2 == 0:
                colr = grass                      # 계단식 밭
            box(g, cx + dx - r, y, cz + 6 - r // 2, 2 * r + 1, 1, r + 1, colr)


def lm_rock(g, p, cx, cz, c):
    """하나로 우뚝 선 둥근 바위산."""
    rock, rock2 = p("lm", c), p("lm2", tuple(max(0, v - 25) for v in c))
    H, R = 44, 22
    for y in range(1, H):
        k = y / H
        r = int(R * math.sqrt(max(0.0, 1 - k ** 3)))
        box(g, cx - r, y, cz - r // 2, 2 * r + 1, 1, r + 2, rock if (y // 4) % 2 else rock2)


def lm_temple(g, p, cx, cz, c):
    col, roof = p("lm", c), p("lm2", tuple(int(v * 0.85) for v in c))
    box(g, cx - 16, 1, cz - 8, 33, 3, 16, col)
    for x in range(cx - 14, cx + 15, 4):
        box(g, x, 4, cz - 7, 2, 14, 2, col)
    box(g, cx - 16, 18, cz - 8, 33, 3, 16, roof)
    for k in range(6):
        box(g, cx - 15 + k * 2, 21 + k, cz - 8, 31 - k * 4, 1, 16, roof)


def lm_arch(g, p, cx, cz, c):
    col = p("lm", c)
    box(g, cx - 14, 1, cz - 4, 9, 30, 8, col)
    box(g, cx + 6, 1, cz - 4, 9, 30, 8, col)
    box(g, cx - 14, 30, cz - 4, 29, 10, 8, col)
    for x in range(cx - 13, cx + 14, 3):
        box(g, x, 40, cz - 4, 1, 1, 8, col)


def lm_spires(g, p, cx, cz, c):
    col, dark = p("lm", c), p("lm2", tuple(int(v * 0.7) for v in c))
    box(g, cx - 12, 1, cz - 6, 25, 22, 14, col)
    for k, (dx, H) in enumerate([(-10, 46), (-4, 54), (4, 54), (10, 46)]):
        for y in range(22, H):
            r = max(0, 2 - (y - 22) // 9)
            box(g, cx + dx - r, y, cz - r, 2 * r + 1, 1, 2 * r + 1, dark if y % 4 == 0 else col)
    box(g, cx - 3, 1, cz - 7, 7, 10, 1, p("glass"))


def lm_gate(g, p, cx, cz, c):
    col, roof = p("lm", c), p("lm2", (60, 64, 76))
    box(g, cx - 16, 1, cz - 5, 33, 12, 10, p("rock2"))
    box(g, cx - 4, 1, cz - 6, 9, 8, 1, p("dgrey"))
    box(g, cx - 13, 13, cz - 4, 27, 8, 8, col)
    for k in range(4):
        box(g, cx - 16 + k, 21 + k, cz - 6, 33 - 2 * k, 1, 12, roof)


def lm_stupa(g, p, cx, cz, c):
    col, gold = p("lm", c), p("gold")
    for k in range(4):
        r = 14 - k * 3
        box(g, cx - r, 1 + k * 3, cz - r, 2 * r + 1, 3, 2 * r + 1, col)
    R = 6
    for y in range(R + 1):
        rr = int(math.sqrt(max(0, R * R - y * y)))
        box(g, cx - rr, 13 + y, cz - rr, 2 * rr + 1, 1, 2 * rr + 1, gold)
    for y in range(20, 36):
        r = max(0, 2 - (y - 20) // 5)
        box(g, cx - r, y, cz - r, 2 * r + 1, 1, 2 * r + 1, gold)


LANDMARKS = {k[3:]: v for k, v in globals().items() if k.startswith("lm_")}


# ---------------------------------------------------------------- 사람과 모니 (매 프레임 다시 찍음)

def person(grid, pal, x, z, t, look, facing=1):
    step = int(t * 6 + x) % 2
    sh = pal(look["shirt"])
    box(grid, x, 1, z + (step if facing > 0 else -step), 1, 2, 1, pal("dgrey"))
    box(grid, x + 1, 1, z + (1 - step if facing > 0 else step - 1), 1, 2, 1, pal("dgrey"))
    box(grid, x, 3, z, 2, 3, 1, sh)
    box(grid, x, 6, z, 2, 2, 1, pal(look["skin"]))
    box(grid, x, 8, z, 2, 1, 1, pal(look["hair"]))


def moni(grid, pal, x, z, t, walking=True, face="happy", facing=1):
    """facing=1: +z를 봄(카메라는 뒤에서 따라감)."""
    x, z = int(x), int(z)
    step = int(t * 6) % 2 if walking else 0
    bob = 1 if walking and int(t * 6) % 2 else 0
    dg, wh, cr = pal("dgrey"), pal("white"), pal("cream")
    box(grid, x - 2, 1, z + step * facing, 1, 2, 1, dg)
    box(grid, x + 2, 1, z + (1 - step) * facing if walking else z, 1, 2, 1, dg)
    box(grid, x - 2, 3 + bob, z - 1, 5, 4, 3, cr)
    box(grid, x - 3, 3 + bob, z, 1, 3, 1, pal("grey"))
    box(grid, x + 3, 3 + bob, z, 1, 3, 1, pal("grey"))
    box(grid, x - 3, 7 + bob, z - 2, 7, 6, 4, wh)
    # 앞면 화면
    fz = z + 2 if facing > 0 else z - 2
    box(grid, x - 2, 8 + bob, fz, 5, 4, 1, pal("screen"))
    eyes = {"happy": [(-1, 10), (1, 10)], "shock": [(-1, 10), (1, 10), (-1, 11), (1, 11)]}.get(face, [(-1, 10), (1, 10)])
    for ex, ey in eyes:
        grid[x + ex, ey + bob, fz] = pal("face")
    grid[x, 8 + bob, fz] = pal("face")
    box(grid, x, 13 + bob, z, 1, 2, 1, pal("dgrey"))
    grid[x, 15 + bob, z] = pal("red") if int(t * 2) % 2 else pal("yellow")
    # 뒤통수 통풍구 줄무늬
    hz = z - 2 if facing > 0 else z + 1
    for yy in (9, 11):
        box(grid, x - 2, yy + bob, hz, 5, 1, 1, pal("grey"))
    # 등 쪽 배낭(여행 느낌)
    bz = z - 2 if facing > 0 else z + 2
    box(grid, x - 1, 3 + bob, bz, 3, 3, 1, pal("accent"))


# ---------------------------------------------------------------- 세계 만들기

def build_world(country: dict, seed: int) -> tuple[np.ndarray, Palette, dict]:
    rnd = random.Random(seed)
    pal = base_palette()
    g = np.zeros((GX, GY, GZ), np.uint8)
    ground = pal("ground", GROUND.get(country.get("ground", "grass")))
    box(g, 0, 0, 0, GX, 1, GZ, ground)
    box(g, ROAD_X0, 0, 0, ROAD_X1 - ROAD_X0, 1, LANDMARK_Z - 24, pal("road"))
    for z in range(2, LANDMARK_Z - 26, 8):
        box(g, int(CENTER), 0, z, 1, 1, 4, pal("line"))
    for sx in (ROAD_X0 - SIDE_W, ROAD_X1):
        box(g, sx, 0, 0, SIDE_W, 2, LANDMARK_Z - 24, pal("side"))
    # 광장
    box(g, ROAD_X0 - SIDE_W, 0, LANDMARK_Z - 24, ROAD_X1 - ROAD_X0 + 2 * SIDE_W, 1, 50, pal("side"))
    walls = [pal(f"wall{i}", tuple(c)) for i, c in enumerate(country["walls"])]
    roof = pal("roof", tuple(country.get("roof", (120, 70, 60))))
    z = 0
    while z < LANDMARK_Z - 30:
        d = rnd.randint(9, 15)
        for side in (-1, 1):
            w = rnd.randint(9, 14)
            h = rnd.randint(*country.get("heights", (10, 26)))
            x0 = ROAD_X0 - SIDE_W - w - 1 if side < 0 else ROAD_X1 + SIDE_W + 1
            building(g, pal, x0, z, w, d, h, rnd.choice(walls), rnd,
                     roof if rnd.random() < country.get("roof_ratio", 0.5) else None, facing=-side)
        z += d + rnd.randint(1, 3)
    trees = country.get("tree", "round")
    for z in range(6, LANDMARK_Z - 30, 18):
        tree(g, pal, ROAD_X0 - 3, z, rnd.randint(6, 8), trees)
        tree(g, pal, ROAD_X1 + 2, z + 9, rnd.randint(6, 8), trees)
    for z in range(14, LANDMARK_Z - 30, 36):
        lamp(g, pal, ROAD_X0 - 1, z, 1)
        lamp(g, pal, ROAD_X1, z + 18, -1)
    lm = country["landmark"]
    LANDMARKS[lm](g, pal, int(CENTER), LANDMARK_Z + 12, tuple(country.get("landmark_color", (200, 190, 170))),
                  **country.get("landmark_args", {}))
    flags = [(ROAD_X0 - 4, LANDMARK_Z - 22), (ROAD_X1 + 3, LANDMARK_Z - 22)]
    info = {"flags": flags, "pal": pal}
    return g, pal, info
