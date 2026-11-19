"""Montaje final con FFmpeg: planos animados + voz + música + efectos + subtítulos."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from .config import ASSETS
from .media import run_ffmpeg

def join_shots(shot_files: list[Path], durations: list[float], fade: float, out: Path, workdir: Path) -> Path:
    """Une los planos. Con fade > 0, cada plano (salvo el último) dura `fade` s de más y se funde con
    el siguiente, que empieza justo cuando arranca su frase."""
    if fade <= 0 or len(shot_files) == 1:
        listfile = workdir / "shots.txt"
        listfile.write_text("".join(f"file '{p.resolve()}'\n" for p in shot_files))
        run_ffmpeg(["-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", out])
        return out
    inputs: list = []
    for p in shot_files:
        inputs += ["-i", p]
    chain, prev, start = [], "[0:v]", 0.0
    for i in range(1, len(shot_files)):
        start += durations[i - 1]
        label = f"[x{i}]"
        chain.append(f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={start:.3f}{label}")
        prev = label
    run_ffmpeg([*inputs, "-filter_complex", ";".join(chain), "-map", prev,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out])
    return out


def pick_music(names: Optional[list[str]] = None) -> Optional[Path]:
    """Pista al azar entre las de la marca (o entre todas si no tiene lista)."""
    tracks = [p for p in (ASSETS / "music").glob("*") if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg"}]
    if names:
        tracks = [p for p in tracks if p.stem in names] or tracks
    return random.choice(tracks) if tracks else None


def assemble(shot_files: list[Path], durations: list[float], voice: Path, captions_list: Path, total: float,
             out: Path, workdir: Path, music_volume: float, fade: float = 0.0,
             sfx: Optional[Path] = None, progress_color: Optional[str] = None,
             music_names: Optional[list[str]] = None) -> Path:
    bg = join_shots(shot_files, durations, fade, workdir / "background.mp4", workdir)

    music = pick_music(music_names)
    inputs = ["-i", bg, "-f", "concat", "-safe", "0", "-i", captions_list, "-i", voice]
    # Barra de progreso fina abajo: ver que «ya casi acaba» hace que más gente llegue al final.
    if progress_color:  # una franja del color de la marca que entra desde la izquierda al ritmo del vídeo
        fc = (f"color=c=0x{progress_color.lstrip('#')}:s=1080x14:r=30[bar];"
              "[1:v]format=rgba[cap];[0:v][cap]overlay=0:0:eof_action=pass[base];"
              f"[base][bar]overlay=x='-w+w*t/{total:.3f}':y=H-14:eof_action=pass:shortest=1,format=yuv420p[v];")
    else:
        fc = "[1:v]format=rgba[cap];[0:v][cap]overlay=0:0:eof_action=pass,format=yuv420p[v];"
    mix = ["[vo]"]
    idx = 3
    if music:
        print(f"  música: {music.name}")
        inputs += ["-stream_loop", "-1", "-i", music]
        fade_start = max(0.0, total - 1.5)
        # La música baja automáticamente mientras habla el narrador (sidechain) y sube en las pausas.
        fc += ("[2:a]apad,asplit=2[vo][sc];"
               f"[{idx}:a]volume={music_volume},afade=t=out:st={fade_start:.2f}:d=1.5[mraw];"
               "[mraw][sc]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=500[m];")
        mix.append("[m]")
        idx += 1
    else:
        fc += "[2:a]apad[vo];"
    if sfx:  # efectos de sonido (explosiones, olas, motores...)
        inputs += ["-i", sfx]
        fc += f"[{idx}:a]aformat=channel_layouts=mono,apad[fx];"
        mix.append("[fx]")
    fc += f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0[a]"

    run_ffmpeg([
        *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "10M", "-bufsize", "20M", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out,
    ])
    return out
