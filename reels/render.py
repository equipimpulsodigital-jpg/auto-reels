"""Montaje final con FFmpeg: clips de fondo + voz + música + subtítulos."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from .config import ASSETS
from .media import probe_duration, run_ffmpeg


def scene_clip(src: Optional[Path], seconds: float, out: Path, w: int, h: int, fps: int, index: int) -> Path:
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps},"
        "eq=brightness=-0.06:saturation=1.1,format=yuv420p"
    )
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an"]
    if src is None:
        # Sin clip: fondo de color liso, con un tono distinto en cada escena.
        colors = ["0x14213d", "0x1b4332", "0x3a0ca3", "0x283618", "0x2b2d42", "0x432818"]
        run_ffmpeg(["-f", "lavfi", "-i", f"color=c={colors[index % len(colors)]}:s={w}x{h}:r={fps}",
                    "-t", f"{seconds:.3f}", "-vf", "format=yuv420p", *enc, out])
        return out
    src_dur = probe_duration(src)
    start = random.uniform(0, max(0.0, src_dur - seconds - 0.5)) if src_dur > seconds + 1 else 0
    run_ffmpeg(["-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", src, "-t", f"{seconds:.3f}",
                "-vf", vf, *enc, out])
    return out


def pick_music() -> Optional[Path]:
    tracks = [p for p in (ASSETS / "music").glob("*") if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg"}]
    return random.choice(tracks) if tracks else None


def assemble(scene_files: list[Path], voice: Path, captions_list: Path, total: float,
             out: Path, workdir: Path, music_volume: float) -> Path:
    listfile = workdir / "scenes.txt"
    listfile.write_text("".join(f"file '{p.resolve()}'\n" for p in scene_files))
    bg = workdir / "background.mp4"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", bg])

    music = pick_music()
    inputs = ["-i", bg, "-f", "concat", "-safe", "0", "-i", captions_list, "-i", voice]
    fc = "[1:v]format=rgba[cap];[0:v][cap]overlay=0:0:eof_action=pass,format=yuv420p[v];"
    if music:
        print(f"  música: {music.name}")
        inputs += ["-stream_loop", "-1", "-i", music]
        fade_start = max(0.0, total - 1.5)
        fc += (f"[3:a]volume={music_volume},afade=t=out:st={fade_start:.2f}:d=1.5[m];"
               "[2:a]apad[vo];[vo][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    else:
        fc += "[2:a]apad[a]"

    run_ffmpeg([
        *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out,
    ])
    return out
