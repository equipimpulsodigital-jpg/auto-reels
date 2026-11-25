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


_VOWEL = {"a": (1.0, 0.0), "á": (1.0, 0.0), "e": (0.6, -0.5), "é": (0.6, -0.5), "i": (0.4, -0.8), "í": (0.4, -0.8),
          "o": (0.75, 0.75), "ó": (0.75, 0.75), "u": (0.45, 1.0), "ú": (0.45, 1.0), "ü": (0.45, 1.0)}
_CLOSED = set("mbp")
_LIP = set("fv")


def visemes_for(words: list, scene: int, start: float, fps: int, frames: int) -> list:
    """Forma de la boca en cada fotograma según la letra que suena (aproximada por el tiempo de cada palabra)."""
    out = [None] * frames
    for w in words:
        if w.scene != scene:
            continue
        letters = [ch for ch in w.text.lower() if ch.isalpha()]
        if not letters:
            continue
        a, b = w.start - start, max(w.end - start, w.start - start + 0.05)
        for f in range(max(0, int(a * fps)), min(frames, int(b * fps) + 1)):
            k = (f / fps - a) / (b - a)
            ch = letters[min(len(letters) - 1, max(0, int(k * len(letters))))]
            if ch in _VOWEL:
                out[f] = _VOWEL[ch]
            elif ch in _CLOSED:
                out[f] = (0.0, 0.0)
            elif ch in _LIP:
                out[f] = (0.15, -0.3)
            else:
                out[f] = (0.35, 0.0)
    return out


REVEAL_LABELS = ("PAYOFF", "REVELACI", "CLÍMAX", "CLIMAX", "GIRO FINAL", "DESENLACE")


def key_moments(blocks) -> tuple[int, int | None]:
    """(bloque de la revelación final, bloque del primer giro). Sirven para la música y los planos de reacción."""
    reveal = None
    for i, b in enumerate(blocks):
        if any(k in (b.label or "").upper() for k in REVEAL_LABELS):
            reveal = i
    if reveal is None:
        reveal = max(0, len(blocks) - 2)  # el penúltimo (el último lo cierra el presentador)
    turn = next((i for i, b in enumerate(blocks) if "GIRO" in (b.label or "").upper() and i != reveal and i > 1), None)
    return reveal, turn


def music_envelope(blocks, durations: list[float]) -> list[tuple[float, float]]:
    """Volumen de la música a lo largo del vídeo: algo más baja en la tensión, casi en silencio justo antes de
    la revelación y con fuerza en el giro (luego vuelve a su nivel)."""
    reveal, _ = key_moments(blocks)
    starts = [sum(durations[:i]) for i in range(len(durations))]
    pts = [(0.0, 1.0)]
    for i, b in enumerate(blocks):
        lab = (b.label or "").upper()
        g = 0.78 if ("TENSI" in lab or "SUSPENSE" in lab) else 1.0
        pts.append((starts[i] + 0.25, g))
    r = starts[reveal]
    pts = [p for p in pts if not (r - 1.0 <= p[0] <= r + 2.6)]
    pts += [(r - 1.0, 0.9), (r - 0.15, 0.22), (r + 0.05, 1.35), (r + 2.6, 1.0)]
    return sorted(pts)


def _reaction_shot(shot, react_id: str, dur: float):
    """Plano de reacción: la cara de otro personaje durante un segundo (la voz sigue sonando por encima)."""
    from dataclasses import replace
    em = "horrorizado" if shot.mood in ("noche", "tormenta") or shot.brow < -0.4 else "sorprendido"
    if shot.smile > 0.4:
        em = "contento"
    if shot.worry > 0.6 and shot.smile < -0.3:
        em = "triste"
    brow, smile, worry, extra = K.emotion(em)
    return replace(shot, duration=dur, framing="personaje", cast=[react_id], speaker=None, event=None, action="",
                   held="", camera="push_in", punches=[0.04], mouth=[], visemes=[], sfx=[], whip=False,
                   brow=brow, smile=smile, worry=worry, extra=extra)


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(ch for ch in s if ch.isalnum() or ch == " ").strip()


def host_character(cfg: dict):
    """Presentador fijo de la marca (config: channels.<id>.host)."""
    h = cfg["channel"].get("host")
    if not h:
        return None, None
    return K.make_character(h.get("name", "Presentador"), h.get("look", {}), seed=77), h


def render_typo_episode(part, durations: list[float], workdir: Path, cfg: dict,
                        words: list | None = None) -> tuple[list[Path], Path]:
    """Modo tipografía: cada bloque es una palabra clave enorme sobre fondo oscuro (sin personajes)."""
    from .typo import render_typo_shot
    v = cfg["video"]
    W, H, fps = v["width"], v["height"], v["fps"]
    accent = cfg["channel"].get("accent_color", "#E2A84B")
    files, shots = [], []
    reveal, _ = key_moments(part.blocks)
    for i, (b, dur) in enumerate(zip(part.blocks, durations)):
        start = sum(durations[:i])
        punches = [max(0.0, w.start - start) for w in (words or []) if w.scene == i and w.emph]
        sfx = [("whoosh", 0.0)] + [("hit", p - 0.03) for p in punches]
        if i == 0 or i == reveal:
            sfx.append(("hit", 0.0))
        shots.append(Shot(location="casa", duration=dur, framing="objeto", mood="noche", sfx=sfx,
                          ambience="", punches=punches))  # sin ambiente: solo voz, música y golpes
        print(f"  plano {i + 1}/{len(part.blocks)} · tipografía · {b.on_screen or b.emphasis or ''}", flush=True)
        files.append(render_typo_shot(b, dur, workdir / f"shot_{i}.mp4", W, H, fps, accent, seed=i * 13 + 5,
                                      punches=punches))
    fx = build_track(shots, durations, sum(durations), workdir / "sfx.wav")
    return files, fx


def render_episode(series, part, durations: list[float], workdir: Path, cfg: dict,
                   words: list | None = None) -> tuple[list[Path], Path]:
    if cfg["channel"].get("render") == "tipografia":
        return render_typo_episode(part, durations, workdir, cfg, words)
    v = cfg["video"]
    W, H, fps = v["width"], v["height"], v["fps"]
    chars, sides = build_cast(series)
    host, host_cfg = host_character(cfg)
    if host:
        chars["_host"], sides["_host"] = host, -1.0
        # si el guionista mete a la presentadora como personaje («La Cabeza», «Presentadora»...), siempre con su cara fija
        alias = {_norm(host_cfg.get("name", "")), _norm(cfg["channel"].get("name", ""))}
        for c in series.characters:
            n = _norm(c.name)
            if n in alias or "presentador" in n or (len(n) > 4 and any(n in a or a in n for a in alias if len(a) > 4)):
                chars[c.id] = host
    ctx = Ctx(W, H, fps, chars, dict(sides), style=cfg["channel"].get("style", "caricatura"))
    shots, files = [], []
    reveal, turn = key_moments(part.blocks)
    seated_at = None  # lugar donde los personajes se han sentado (siguen sentados mientras no cambie)
    for i, (b, dur) in enumerate(zip(part.blocks, durations)):
        shot = block_to_shot(b, series, chars, dur)
        if shot.action == "sentado":
            seated_at = shot.location
        elif shot.location != seated_at or shot.action:
            seated_at = None  # cambian de sitio o hacen otra cosa: ya no están sentados
        elif shot.framing == "general" and not shot.action:
            shot.action = "sentado"  # continuidad: si estaban sentados en este sitio, siguen sentados
        last = i == len(part.blocks) - 1
        if host and last and b.speaker not in chars:
            # el presentador de la marca cierra el vídeo mirando a cámara (dice la última frase del narrador)
            shot.framing, shot.cast, shot.speaker = "personaje", ["_host"], "_host"
            shot.location, shot.mood = host_cfg.get("location", "despacho"), host_cfg.get("mood", "dia")
            shot.event, shot.action, shot.held, shot.gesture = None, "", "", host_cfg.get("gesture", "explain")
            if abs(shot.brow) < 0.05 and abs(shot.smile) < 0.05:
                shot.smile, shot.brow = 0.5, 0.2
        if i == 0 and shot.framing == "general" and not shot.event:
            # primer segundo: nada de planos generales tranquilos; de cerca, a la cara o al objeto clave
            if shot.cast:
                shot.framing = "personaje"
            elif shot.prop:
                shot.framing = "objeto"
        if i == 0:  # el gancho: arranque con impacto (zoom, destello y golpe de sonido)
            shot.camera = "shake" if shot.camera == "shake" else "golpe"
            if not any(name in ("hit", "boom") for name, _ in shot.sfx):
                shot.sfx.append(("hit", 0.0))
        start = sum(durations[:i])
        if i > 0 and shots and shot.location != shots[-1].location:  # cambio de lugar: barrido de cámara con «whoosh»
            shot.sfx.append(("whoosh", 0.0))
            shot.whip = True
        for w in words or []:  # palabra clave: golpe de zoom y de sonido justo cuando se dice
            if w.scene == i and w.emph:
                shot.punches.append(max(0.0, w.start - start))
                shot.sfx.append(("hit", max(0.0, w.start - start - 0.03)))
        if shot.speaker:
            shot.mouth = mouth_envelope(workdir / f"voice_{i}.wav", fps, round(dur * fps))
            shot.visemes = visemes_for(words or [], i, start, fps, round(dur * fps))
        if i == reveal:
            shot.sfx.append(("hit", 0.0))  # golpe de la revelación (la música entra con fuerza a la vez)
        print(f"  plano {i + 1}/{len(part.blocks)} · {shot.location} · {shot.framing}"
              + (f" · {shot.event}" if shot.event else "") + (f" · {shot.prop}" if shot.framing == "objeto" else ""), flush=True)
        react = None
        if i in (reveal, turn) and dur >= 2.6 and shot.framing != "objeto":
            who = [c for c in list(shot.cast) + list(chars) if c not in (shot.speaker, "_host")]
            react = who[0] if who else None
        if react:  # plano de reacción al final del bloque (montaje en «J»: la frase sigue sonando)
            from dataclasses import replace
            cut = dur - 0.9
            n = round(cut * fps)
            main = replace(shot, duration=cut, mouth=shot.mouth[:n], visemes=shot.visemes[:n])
            a = render_shot(ctx, main, workdir / f"shot_{i}_a.mp4")
            b = render_shot(ctx, _reaction_shot(shot, react, 0.9), workdir / f"shot_{i}_b.mp4")
            lst = workdir / f"shot_{i}_list.txt"
            lst.write_text(f"file '{a.resolve()}'\nfile '{b.resolve()}'\n")
            from ..media import run_ffmpeg
            out = workdir / f"shot_{i}.mp4"
            run_ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
            files.append(out)
            print(f"    + reacción de {react}", flush=True)
        else:
            files.append(render_shot(ctx, shot, workdir / f"shot_{i}.mp4"))
        shots.append(shot)
    fx = build_track(shots, durations, sum(durations), workdir / "sfx.wav")
    return files, fx
