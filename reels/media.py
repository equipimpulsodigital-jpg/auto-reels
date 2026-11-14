from __future__ import annotations

import subprocess
from pathlib import Path


def run_ffmpeg(args: list) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *[str(a) for a in args]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falló:\n{' '.join(cmd)}\n{proc.stderr[-3000:]}")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)
