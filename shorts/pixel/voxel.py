"""아주 작은 복셀(3D 픽셀) 레이캐스터. numpy만 쓴다(GPU, 3D 프로그램 불필요, 0원).

세계는 uint8 격자(0=빈칸, 1~255=팔레트 색 번호). 카메라에서 화면 픽셀마다 광선을 쏴서
처음 맞는 복셀의 색을 칠하고, 면 방향과 거리로 명암과 안개를 준다.
저해상도(예: 180x320)로 그린 뒤 최근접 확대하면 '픽셀 느낌의 3D'가 된다.
"""
from __future__ import annotations

import numpy as np


class Palette:
    def __init__(self):
        self.colors = np.zeros((256, 3), np.float32)
        self.names: dict[str, int] = {}

    def __call__(self, name: str, rgb=None) -> int:
        if name not in self.names:
            if rgb is None:
                raise KeyError(name)
            i = len(self.names) + 1
            self.names[name] = i
            self.colors[i] = rgb
        elif rgb is not None:
            self.colors[self.names[name]] = rgb
        return self.names[name]


def look_at(pos, target, up=(0.0, 1.0, 0.0)):
    f = np.asarray(target, np.float64) - np.asarray(pos, np.float64)
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return f, r, u


def render(grid: np.ndarray, pal: Palette, pos, target, w: int, h: int, fov=62.0,
           sky_top=(90, 150, 230), sky_bottom=(190, 220, 245), fog=(200, 220, 240),
           fog_dist=110.0, light=(0.45, 0.85, 0.3), max_steps=400) -> np.ndarray:
    """grid[x, y, z]. 반환: (h, w, 3) uint8."""
    X, Y, Z = grid.shape
    f, r, u = look_at(pos, target)
    aspect = w / h
    th = np.tan(np.radians(fov) / 2)
    sx = (np.arange(w) + 0.5) / w * 2 - 1
    sy = 1 - (np.arange(h) + 0.5) / h * 2
    gx, gy = np.meshgrid(sx * th * aspect, sy * th)
    d = (f[None, None] + gx[..., None] * r[None, None] + gy[..., None] * u[None, None]).reshape(-1, 3)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    n = d.shape[0]
    o = np.asarray(pos, np.float64)

    # 하늘 배경
    sky_t = np.clip((d[:, 1] + 0.2) / 0.8, 0, 1)[:, None]
    out = (np.asarray(sky_bottom) * (1 - sky_t) + np.asarray(sky_top) * sky_t).astype(np.float32)

    d_safe = np.where(np.abs(d) < 1e-9, 1e-9, d)
    step = np.where(d > 0, 1, -1).astype(np.int64)
    idx = np.floor(np.broadcast_to(o, (n, 3))).astype(np.int64)
    tdelta = np.abs(1.0 / d_safe)
    tmax = ((idx + (step > 0)) - o) / d_safe
    axis = np.zeros(n, np.int64)
    t_hit = np.full(n, np.inf)
    col = np.zeros(n, np.int64)
    alive = np.arange(n)
    lim = np.array([X, Y, Z])

    for _ in range(max_steps):
        if alive.size == 0:
            break
        tm = tmax[alive]
        a = np.argmin(tm, axis=1)
        rows = alive
        t_now = tm[np.arange(rows.size), a]
        idx[rows, a] += step[rows, a]
        tmax[rows, a] += tdelta[rows, a]
        p = idx[rows]
        inside = np.all((p >= 0) & (p < lim), axis=1)
        # 위로 빠져나가거나 앞뒤로 나가면 하늘
        keep = inside.copy()
        pi = p[inside]
        v = grid[pi[:, 0], pi[:, 1], pi[:, 2]]
        hit = np.zeros(rows.size, bool)
        hit[np.where(inside)[0][v > 0]] = True
        if hit.any():
            hr = rows[hit]
            t_hit[hr] = t_now[hit]
            axis[hr] = a[hit]
            hp = p[hit]
            col[hr] = grid[hp[:, 0], hp[:, 1], hp[:, 2]]
        keep &= ~hit
        alive = rows[keep]

    hit = np.isfinite(t_hit)
    hi = np.where(hit)[0]
    if hi.size:
        base = pal.colors[col[hi]]
        # 면 방향 명암 (위 1.0, 옆 0.78/0.62) + 빛 방향
        nrm = np.zeros((hi.size, 3), np.float32)
        nrm[np.arange(hi.size), axis[hi]] = -np.sign(d[hi, axis[hi]])
        lv = np.asarray(light, np.float32)
        lv /= np.linalg.norm(lv)
        shade = 0.55 + 0.45 * np.clip(nrm @ lv, 0, 1)
        shade = np.where(axis[hi] == 1, np.maximum(shade, 0.92), shade)
        # 복셀마다 살짝 다른 밝기(질감)
        hp = np.floor(o + d[hi] * (t_hit[hi, None] + 1e-4)).astype(np.int64)
        hp[np.arange(hi.size), axis[hi]] -= 0  # 그대로
        noise = ((hp[:, 0] * 73856093) ^ (hp[:, 1] * 19349663) ^ (hp[:, 2] * 83492791)) % 7
        shade = shade * (0.94 + noise * 0.012)
        c = base * shade[:, None]
        fogk = np.clip(t_hit[hi] / fog_dist, 0, 1)[:, None] ** 1.6
        c = c * (1 - fogk) + np.asarray(fog, np.float32) * fogk
        out[hi] = c
    return np.clip(out, 0, 255).astype(np.uint8).reshape(h, w, 3)


def box(grid, x0, y0, z0, sx, sy, sz, c):
    X, Y, Z = grid.shape
    x1, y1, z1 = min(X, x0 + sx), min(Y, y0 + sy), min(Z, z0 + sz)
    x0, y0, z0 = max(0, x0), max(0, y0), max(0, z0)
    if x1 > x0 and y1 > y0 and z1 > z0:
        grid[x0:x1, y0:y1, z0:z1] = c
