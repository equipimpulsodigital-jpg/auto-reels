"""Montaje con FFmpeg: imágenes con movimiento de cámara + grano + voz + música + subtítulos."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from .config import ASSETS
from .media import run_ffmpeg

ZOOM = 0.14  # cuánto se acerca/aleja la cámara a lo largo del plano


def _motion(camera: str, frames: int) -> tuple[str, str, str]:
    """Expresiones de zoompan (z, x, y) para cada movimiento. 'on' = nº de frame de salida."""
    t = f"(on/{max(frames - 1, 1)})"
    cx, cy = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    zmax = f"{1 + ZOOM:.3f}"
    return {
        "push_in":   (f"1+{ZOOM}*{t}", cx, cy),
        "pull_back": (f"{zmax}-{ZOOM}*{t}", cx, cy),
        "pan_right": (zmax, f"(iw-iw/zoom)*{t}", cy),
        "pan_left":  (zmax, f"(iw-iw/zoom)*(1-{t})", cy),
        "tilt_down": (zmax, cx, f"(ih-ih/zoom)*{t}"),
        "tilt_up":   (zmax, cx, f"(ih-ih/zoom)*(1-{t})"),
    }.get(camera, (f"1+{ZOOM}*{t}", cx, cy))


def shot_clip(image: Optional[Path], camera: str, seconds: float, out: Path, w: int, h: int, fps: int) -> Path:
    frames = max(1, round(seconds * fps))
    film = "eq=contrast=1.06:saturation=0.85,noise=alls=5:allf=t,vignette=PI/4.5,format=yuv420p"
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an"]
    if image is None:
        run_ffmpeg(["-f", "lavfi", "-i", f"color=c=0x15110d:s={w}x{h}:r={fps}", "-t", f"{seconds:.3f}",
                    "-vf", film, *enc, out])
        return out
    z, x, y = _motion(camera, frames)
    # Se escala al doble antes de zoompan para que el movimiento sea suave (sin temblores).
    vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps},setsar=1,{film}")
    run_ffmpeg(["-loop", "1", "-i", image, "-vf", vf, "-frames:v", frames, *enc, out])
    return out


def pick_music() -> Optional[Path]:
    tracks = [p for p in (ASSETS / "music").glob("*") if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg"}]
    return random.choice(tracks) if tracks else None


def assemble(shot_files: list[Path], voice: Path, captions_list: Path, total: float,
             out: Path, workdir: Path, music_volume: float) -> Path:
    listfile = workdir / "shots.txt"
    listfile.write_text("".join(f"file '{p.resolve()}'\n" for p in shot_files))
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
        "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-maxrate", "10M", "-bufsize", "20M", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out,
    ])
    return out
