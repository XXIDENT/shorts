"""문장별 음성 파일을 만든다.

우선순위: Google Cloud TTS(무료 한도, GOOGLE_TTS_API_KEY) → edge-tts(무료, 키 불필요) → 무음.
"""
from __future__ import annotations

import asyncio
import base64
import os
import subprocess
from pathlib import Path

import requests

GOOGLE_VOICE = os.environ.get("GOOGLE_TTS_VOICE", "ko-KR-Neural2-C")
EDGE_VOICE = os.environ.get("EDGE_TTS_VOICE", "ko-KR-InJoonNeural")


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _google(text: str, out: Path, key: str) -> None:
    r = requests.post(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        params={"key": key}, timeout=60,
        json={"input": {"text": text},
              "voice": {"languageCode": "ko-KR", "name": GOOGLE_VOICE},
              "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.3}})
    r.raise_for_status()
    out.write_bytes(base64.b64decode(r.json()["audioContent"]))


def _edge(text: str, out: Path) -> None:
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, EDGE_VOICE, rate="+28%").save(str(out)))


def _silence(text: str, out: Path) -> None:
    secs = max(1.6, len(text) * 0.11)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=mono", "-t", f"{secs:.2f}", "-q:a", "9", str(out)], check=True)


def synthesize(lines: list[str], workdir: Path, engine: str | None = None) -> tuple[list[Path], str]:
    """각 문장을 mp3로 만든다. 반환: (파일 목록, 사용한 엔진)."""
    workdir.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("GOOGLE_TTS_API_KEY")
    order = [engine] if engine else (["google"] if key else []) + ["edge", "silent"]
    last_err: Exception | None = None
    for eng in order:
        try:
            paths = []
            for i, text in enumerate(lines):
                p = workdir / f"line{i:02d}.mp3"
                if eng == "google":
                    _google(text, p, key)
                elif eng == "edge":
                    _edge(text, p)
                else:
                    _silence(text, p)
                if p.stat().st_size == 0:
                    raise RuntimeError("빈 음성 파일")
                paths.append(p)
            return paths, eng
        except Exception as e:  # 다음 엔진으로 넘어간다
            last_err = e
            print(f"[tts] {eng} 실패: {e}")
    raise RuntimeError(f"모든 TTS 실패: {last_err}")
