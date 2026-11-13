"""칩튠 배경음악과 효과음을 코드로 합성한다 (무료, 저작권 걱정 없음).

에피소드마다 seed로 템포, 조, 코드 진행, 멜로디가 달라진다.
"""
from __future__ import annotations

import random
import wave
from pathlib import Path

import numpy as np

SR = 22050
PROGRESSIONS = [
    [0, 5, 3, 4],    # I vi IV V
    [0, 4, 5, 3],    # I V vi IV
    [5, 3, 0, 4],    # vi IV I V
    [0, 3, 4, 3],    # I IV V IV
    [0, 5, 1, 4],    # I vi ii V
]
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _pulse(f: float, n: int, duty=0.5, vol=0.3) -> np.ndarray:
    if f <= 0 or n <= 0:
        return np.zeros(max(n, 0))
    ph = (np.arange(n) * f / SR) % 1.0
    return np.where(ph < duty, vol, -vol)


def _tri(f: float, n: int, vol=0.35) -> np.ndarray:
    ph = (np.arange(n) * f / SR) % 1.0
    return (4 * np.abs(ph - 0.5) - 1) * vol


def _env(n: int, a=0.005, r=0.6) -> np.ndarray:
    e = np.ones(n)
    na, nr = int(SR * a), int(n * r)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def _noise(n: int, vol=0.2, seed=0) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-vol, vol, n) * np.linspace(1, 0, n) ** 3


def _chord_root(key: int, degree: int) -> int:
    return key + MAJOR[degree % 7]


def music(seconds: float, seed: int, mood="happy") -> np.ndarray:
    rnd = random.Random(seed)
    bpm = rnd.randint(112, 140) if mood == "happy" else rnd.randint(92, 110)
    key = 48 + rnd.choice([0, 2, 4, 5, 7, 9])
    prog = rnd.choice(PROGRESSIONS)
    duty = rnd.choice([0.125, 0.25, 0.5])
    beat = 60 / bpm
    step = beat / 2                       # 8분음표
    n_steps = int(seconds / step) + 2
    out = np.zeros(int(SR * seconds) + SR)
    # 2마디짜리 멜로디 모티프를 만들고 변주한다
    motif = [rnd.choice([None, 0, 2, 4, 4, 7, 9, 7]) for _ in range(16)]
    arp = rnd.choice([[0, 4, 7, 12], [0, 7, 4, 7], [0, 4, 7, 4], [12, 7, 4, 0]])
    for s in range(n_steps):
        t0 = int(s * step * SR)
        n = int(step * SR)
        bar = s // 8
        root = _chord_root(key, prog[bar % 4])
        minor = prog[bar % 4] in (1, 2, 5)
        third = 3 if minor else 4
        # 베이스: 4분음표
        if s % 2 == 0:
            b = _tri(_freq(root - 12), n * 2, 0.28) * _env(n * 2, r=0.3)
            out[t0:t0 + len(b)] += b[: len(out) - t0]
        # 아르페지오(작은 소리)
        iv = arp[s % 4]
        iv = third if iv == 4 else (third + 12 if iv == 16 else iv)
        a = _pulse(_freq(root + 12 + iv), n, 0.25, 0.06) * _env(n, r=0.7)
        out[t0:t0 + n] += a[: len(out) - t0]
        # 멜로디: 4마디마다 한 번 쉬어서 목소리가 잘 들리게
        m = motif[(s + (bar // 4) * 3) % 16]
        if m is not None and (bar % 4) != 3:
            deg = MAJOR[(m // 2) % 7] if m < 12 else m
            mm = _pulse(_freq(key + 24 + deg), n, duty, 0.08) * _env(n, r=0.5)
            out[t0:t0 + n] += mm[: len(out) - t0]
        # 드럼: 킥(1,3) 하이햇(8분)
        if s % 4 == 0:
            k = np.sin(2 * np.pi * np.cumsum(np.linspace(150, 40, int(0.12 * SR))) / SR) * 0.35
            k *= np.linspace(1, 0, len(k))
            out[t0:t0 + len(k)] += k[: len(out) - t0]
        if s % 4 == 2:
            sn = _noise(int(0.1 * SR), 0.18, s)
            out[t0:t0 + len(sn)] += sn[: len(out) - t0]
        hh = _noise(int(0.03 * SR), 0.05, s + 999)
        out[t0:t0 + len(hh)] += hh[: len(out) - t0]
    return out[: int(SR * seconds)]


def sfx(kind: str) -> np.ndarray:
    def seq(notes, dur, duty=0.5, vol=0.25):
        parts = [_pulse(_freq(n), int(dur * SR), duty, vol) * _env(int(dur * SR), r=0.4) for n in notes]
        return np.concatenate(parts)
    if kind == "clear":
        return seq([72, 76, 79, 84, 88], 0.07, 0.25)
    if kind == "fail":
        n = int(0.5 * SR)
        f = np.linspace(330, 110, n)
        ph = np.cumsum(f) / SR % 1
        return np.where(ph < 0.5, 0.25, -0.25) * np.linspace(1, 0, n)
    if kind == "quest":
        return seq([67, 74], 0.08, 0.5, 0.2)
    if kind == "coin":
        return seq([83, 88], 0.06, 0.5, 0.2)
    if kind == "reveal":
        n = int(0.6 * SR)
        f = np.linspace(200, 900, n)
        ph = np.cumsum(f) / SR % 1
        return np.where(ph < 0.25, 0.15, -0.15) * np.linspace(0.3, 1, n)
    if kind == "title":
        return seq([60, 64, 67, 72, 67, 72], 0.09, 0.25, 0.22)
    if kind == "levelup":
        return seq([72, 74, 76, 77, 79, 81, 83, 84], 0.05, 0.125, 0.22)
    return np.zeros(1)


def write_track(path: Path, seconds: float, seed: int, cues: list[tuple[float, str]], mood="happy",
                music_vol=0.55) -> None:
    track = music(seconds, seed, mood) * music_vol
    for at, kind in cues:
        s = sfx(kind)
        i = int(at * SR)
        if i < len(track):
            track[i:i + len(s)] += s[: len(track) - i]
    # 1초 페이드아웃
    fo = min(len(track), SR)
    track[-fo:] *= np.linspace(1, 0, fo)
    pcm = (np.clip(track, -1, 1) * 32767 * 0.8).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
