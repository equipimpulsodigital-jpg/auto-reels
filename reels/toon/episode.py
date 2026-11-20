"""Convierte la planificación del guionista en planos animados y los renderiza."""
from __future__ import annotations

import zlib
from pathlib import Path

from . import catalog as K
from .film import Ctx, Shot, mouth_envelope, render_shot
from .locations import LOCATIONS
from .sfx import build_track


def build_cast(series) -> tuple[dict, dict]:
    base = zlib.crc32(series.series_title.encode()) % 1000
    chars, sides = {}, {}
    for i, c in enumerate(series.characters):
        chars[c.id] = K.make_character(c.name, c.look.model_dump(), seed=base + i * 7)
        sides[c.id] = -1.0 if i % 2 == 0 else 1.0  # cada personaje siempre en el mismo lado (regla de los 180°)
    return chars, sides


# sonidos que acompañan a cada acción: (efecto, segundo dentro del plano)
ACTION_SFX = {"golpear": [("hit", 0.25), ("hit", 0.95), ("hit", 1.65)], "caer": [("hit", 0.5)],
              "empujar": [("whoosh", 0.3)], "correr": [("whoosh", 0.1)], "saltar": [("whoosh", 0.2)]}


def block_to_shot(b, series, chars: dict, duration: float) -> Shot:
    speaker = b.speaker if b.speaker in chars else None
    cast = [c for c in b.cast if c in chars]
    if speaker and speaker not in cast:
        cast.insert(0, speaker)
    if speaker and cast[0] != speaker:
        cast.remove(speaker)
        cast.insert(0, speaker)
    framing = b.framing
    if framing == "general" and not cast and not b.event and b.prop:  # plano vacío: mejor el objeto de cerca
        framing = "objeto"
    if framing in ("personaje", "dos") and not cast:
        framing = "general"
    if framing == "dos" and len(cast) < 2:
        framing = "personaje"
    brow, smile, worry, extra = K.emotion(b.emotion)
    lbrow, lsmile, lworry, lextra = K.emotion(b.listener_emotion)
    return Shot(
        location=b.location if b.location in LOCATIONS else "pueblo",
        duration=duration, framing=framing, speaker=speaker, cast=cast,
        gesture=b.gesture, brow=brow, smile=smile, listener_brow=lbrow,
        worry=worry, extra=extra, listener_smile=lsmile * 0.7, listener_worry=lworry, listener_extra=lextra,
        mood=b.mood, era=series.era, event=b.event,
        prop=b.prop or ("carta" if framing == "objeto" else None),
        walk=b.walk and framing == "general", camera=b.camera,
        action="" if getattr(b, "action", "ninguna") == "ninguna" else b.action,
        held=getattr(b, "held_prop", None) or "",
        sfx=[(name, 0.0) for name in b.sfx] + ACTION_SFX.get(getattr(b, "action", ""), []),
    )


def render_episode(series, part, durations: list[float], workdir: Path, cfg: dict,
                   words: list | None = None) -> tuple[list[Path], Path]:
    v = cfg["video"]
    W, H, fps = v["width"], v["height"], v["fps"]
    chars, sides = build_cast(series)
    ctx = Ctx(W, H, fps, chars, dict(sides))
    shots, files = [], []
    for i, (b, dur) in enumerate(zip(part.blocks, durations)):
        shot = block_to_shot(b, series, chars, dur)
        if i == 0:  # el gancho: arranque con impacto (zoom, destello y golpe de sonido)
            shot.camera = "shake" if shot.camera == "shake" else "golpe"
            if not any(name in ("hit", "boom") for name, _ in shot.sfx):
                shot.sfx.append(("hit", 0.0))
        start = sum(durations[:i])
        if i > 0 and shots and shot.location != shots[-1].location:  # cambio de lugar: transición con «whoosh»
            shot.sfx.append(("whoosh", 0.0))
        for w in words or []:  # palabra clave: golpe de zoom y de sonido justo cuando se dice
            if w.scene == i and w.emph:
                shot.punches.append(max(0.0, w.start - start))
                shot.sfx.append(("hit", max(0.0, w.start - start - 0.03)))
        if shot.speaker:
            shot.mouth = mouth_envelope(workdir / f"voice_{i}.wav", fps, round(dur * fps))
        print(f"  plano {i + 1}/{len(part.blocks)} · {shot.location} · {shot.framing}"
              + (f" · {shot.event}" if shot.event else "") + (f" · {shot.prop}" if shot.framing == "objeto" else ""), flush=True)
        files.append(render_shot(ctx, shot, workdir / f"shot_{i}.mp4"))
        shots.append(shot)
    fx = build_track(shots, durations, sum(durations), workdir / "sfx.wav")
    return files, fx
