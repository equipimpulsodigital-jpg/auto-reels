"""Render de planos animados: escenarios + personajes con sincronía labial + cámara."""
from __future__ import annotations

import math
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import skia

from . import scenes as S
from .locations import LOCATIONS, G
from .more_props import BEHIND_EVENTS
from .props import EVENT_AMBIENCE, EVENT_SFX, EVENTS, draw_prop
from .character import Character, Pose
from . import finish as F
from .draw import STYLE, ease, noise1, set_style


def mouth_envelope(wav_path: Path, fps: int, frames: int) -> list[float]:
    """Apertura de la boca por fotograma a partir del volumen de la voz (sincronía labial)."""
    with wave.open(str(wav_path), "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        data = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32)
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    hop = sr / fps
    rms = []
    for i in range(frames):
        a, b = int(i * hop), int((i + 1) * hop)
        seg = data[a:b]
        rms.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    rms = np.array(rms)
    ref = np.percentile(rms[rms > 0], 90) if np.any(rms > 0) else 1.0
    lvl = np.clip(rms / (ref + 1e-6), 0, 1.3)
    out, cur = [], 0.0
    for i, v in enumerate(lvl):
        v = 0.0 if v < 0.12 else min(1.0, (v - 0.12) / 0.8)
        # la boca abre rápido y cierra algo más despacio; añade «sílabas» para que no quede fija
        cur = cur + (v - cur) * (0.75 if v > cur else 0.45)
        syll = 0.65 + 0.35 * abs(math.sin(i * 1.9))
        out.append(cur * syll if cur > 0.05 else 0.0)
    return out


def ease_back(t: float) -> float:
    """Entrada con rebote (sobrepasa un poco y vuelve): gestos con vida."""
    t = max(0.0, min(1.0, t))
    c1 = 1.9
    return 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2


def darts(t: float, seed: int) -> float:
    """Mirada que salta de punto en punto cada ~1,3 s (los ojos nunca están quietos)."""
    k = int((t + seed * 0.37) / 1.3)
    return math.sin(k * 12.9898 + seed) * 0.5


def blink(t: float, seed: int) -> float:
    period = 2.6 + (seed % 5) * 0.45
    ph = (t + seed * 0.77) % period
    return max(0.0, 1 - abs(ph - 0.07) / 0.07) if ph < 0.14 else 0.0


@dataclass
class Shot:
    location: str                           # clave de LOCATIONS
    duration: float = 0.0
    framing: str = "general"                # general | personaje | dos | objeto
    speaker: Optional[str] = None           # id del personaje que habla (None = narrador)
    cast: list[str] = field(default_factory=list)  # personajes en plano
    gesture: str = "explain"
    brow: float = 0.0
    smile: float = 0.0
    listener_brow: float = 0.0
    worry: float = 0.0                      # cejas de pena/preocupación (extremo interior arriba)
    extra: str = ""                         # lágrimas, sudor, rubor, furia, shock... (ver catalog.EMOTIONS)
    listener_smile: float = 0.0
    listener_worry: float = 0.0
    listener_extra: str = ""
    mood: str = "dia"
    era: str = "1900"
    event: Optional[str] = None             # suceso animado (EVENTS)
    prop: Optional[str] = None              # objeto en primer plano (PROPS), para framing="objeto"
    walk: bool = False                      # en plano general, los personajes caminan
    action: str = ""                        # acción del protagonista del plano (ver catalog.ACTIONS)
    held: str = ""                          # objeto en la mano del protagonista
    camera: str = "push_in"                 # push_in | pull_back | shake | static
    punches: list = field(default_factory=list)  # segundos (dentro del plano) con golpe de zoom
    mouth: list[float] = field(default_factory=list)
    sfx: list[tuple[str, float]] = field(default_factory=list)  # efectos (nombre, segundo dentro del plano)
    ambience: str = ""                      # sonido de fondo: mar | viento | avion | "" (por defecto, el del lugar)

    def resolved_ambience(self) -> str:
        return self.ambience or EVENT_AMBIENCE.get(self.event or "", "") or LOCATIONS[self.location].ambience

    def resolved_sfx(self) -> list[tuple[str, float]]:
        return self.sfx + EVENT_SFX.get(self.event or "", [])


@dataclass
class Ctx:
    W: int
    H: int
    fps: int
    chars: dict[str, Character]
    sides: dict[str, float] = field(default_factory=dict)  # lado fijo de cada personaje: -1 izquierda, 1 derecha
    style: str = "caricatura"               # estilo visual de la marca (draw.STYLES)

    def side(self, cid: str) -> float:
        if cid not in self.sides:
            self.sides[cid] = -1.0 if len(self.sides) % 2 == 0 else 1.0
        return self.sides[cid]


PAIR_ACTIONS = ("abrazar", "golpear", "empujar")


def _actor(shot: Shot) -> Optional[str]:
    """Protagonista del plano: el que habla o, si habla el narrador, el primero del reparto."""
    if shot.speaker and shot.speaker in shot.cast:
        return shot.speaker
    return shot.cast[0] if shot.cast else None


def _pose(ctx: Ctx, shot: Shot, cid: str, t: float, frame: int, facing: float) -> Pose:
    p = _base_pose(ctx, shot, cid, t, frame, facing)
    actor = _actor(shot)
    if cid == actor:
        p.action, p.held = shot.action, shot.held
    elif shot.action in ("abrazar", "sentado") and cid in shot.cast:
        p.action = shot.action  # abrazo mutuo; si uno se sienta, se sientan todos (una mesa, una cita...)
    return p


def _base_pose(ctx: Ctx, shot: Shot, cid: str, t: float, frame: int, facing: float) -> Pose:
    speaking = cid == shot.speaker
    seed = ctx.chars[cid].look.seed
    if speaking:
        mo = shot.mouth
        m = mo[frame] if frame < len(mo) else 0.0
        # cabeceo en los golpes de voz (subidas bruscas de volumen)
        nod = 0.0
        for k in range(1, 7):
            j = frame - k
            if 0 < j < len(mo) and mo[j] - mo[j - 1] > 0.35:
                nod = max(nod, math.sin(math.pi * k / 7))
        amt = ease_back(t / 0.5) * (1 - ease((t - (shot.duration - 0.45)) / 0.45))
        return Pose(t=t, mouth=m, facing=facing, look=0.3 + darts(t, seed) * 0.4, look_up=0.1, blink=blink(t, seed),
                    brow=shot.brow + 0.3 * m * (1 - shot.worry), smile=shot.smile, gesture=shot.gesture, gesture_amt=amt,
                    worry=shot.worry, extra=shot.extra,
                    talking=True, nod=nod)
    # el que escucha reacciona: asiente de vez en cuando y sigue con la mirada
    nod = max(0.0, math.sin(t * 2.1 + seed)) ** 8
    narrated = shot.speaker is None  # habla el narrador: los que salen ponen la cara de la escena (`emotion`)
    return Pose(t=t, facing=facing, look=0.5 + darts(t, seed + 7) * 0.3, blink=blink(t, seed),
                brow=shot.brow if narrated else shot.listener_brow,
                smile=shot.smile if narrated else shot.listener_smile,
                worry=shot.worry if narrated else shot.listener_worry,
                extra=shot.extra if narrated else shot.listener_extra, gesture="idle", gesture_amt=0.0, nod=nod * 0.6,
                walk=1.0 if shot.walk else 0.0)



def _blurred(c, draw, sigma: float, zoom: float, cx: float, cy: float) -> None:
    c.save()
    c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(sigma, sigma)) if sigma > 0 else None)
    c.translate(cx, cy)
    c.scale(zoom, zoom)
    c.translate(-cx, -cy)
    draw()
    c.restore()
    c.restore()


def draw_frame(c, ctx: Ctx, shot: Shot, t: float, frame: int) -> None:
    W, H = ctx.W, ctx.H
    loc = LOCATIONS[shot.location]
    g = G(W, H, t, shot.mood, shot.era)
    fr = shot.framing
    ev = EVENTS.get(shot.event or "")
    if fr == "objeto":
        _blurred(c, lambda: loc.back(c, g), 12, 1.8, W / 2, H * 0.45)
        F.mood_light(c, W, H, shot.mood)  # la luz de ambiente tiñe el fondo; a los personajes, solo un poco
        draw_prop(c, W, H, shot.prop or "carta", t)
        return
    if fr == "general":
        loc.back(c, g)
        F.mood_light(c, W, H, shot.mood)
        behind = ev is not None and shot.event in BEHIND_EVENTS
        if behind:  # los vehículos pasan por detrás de los personajes
            ev(c, W, H, t, shot.duration)
        feet = H * loc.floor_y
        n = len(shot.cast)
        actor = _actor(shot)
        order = sorted(shot.cast, key=lambda c_: ctx.side(c_)) if n > 1 else list(shot.cast)
        for i, cid in enumerate(order):
            s = 0.6
            side = ctx.side(cid)
            x = W * (0.5 + (i - (n - 1) / 2) * 0.36) if n > 1 else W * 0.5
            facing = -side if n > 1 else 1.0
            if shot.action == "correr" and cid == actor:  # cruza la pantalla corriendo
                facing = 1.0 if n == 1 else side
                x = W * 0.5 + (t - shot.duration / 2) * 300 * facing
            elif shot.action in PAIR_ACTIONS and n > 1 and i < 2:  # se acercan el uno al otro
                k = ease(min(1.0, t / 0.6))
                gap = {"abrazar": 0.1, "golpear": 0.115, "empujar": 0.11}[shot.action]
                x = W * (0.5 + (i - 0.5) * 2 * (0.18 + (gap - 0.18) * k))
            elif shot.walk:
                x += (t - shot.duration / 2) * 70 * facing
            if behind and n == 1 and shot.action != "correr":  # deja sitio al vehículo que pasa
                x = W * 0.24
            p = _pose(ctx, shot, cid, t, frame, facing)
            p.full_body = True
            ctx.chars[cid].draw(c, x, feet - 440 * s, s, p)
        if ev and not behind:
            ev(c, W, H, t, shot.duration)
        return
    zoom, sigma = (1.45, 7) if fr == "personaje" else (1.15, 3)
    _blurred(c, lambda: loc.back(c, g), sigma, zoom, W / 2, H * 0.42)
    F.mood_light(c, W, H, shot.mood)
    if ev:
        ev(c, W, H, t, shot.duration)
    if fr == "personaje":
        cid = shot.speaker or (shot.cast[0] if shot.cast else None)
        if cid:
            side = ctx.side(cid)
            facing = -side
            S.light_glow(c, W, H, shot.mood, facing)
            ctx.chars[cid].draw(c, W * (0.5 + side * 0.1), H * 1.02, 1.7, _pose(ctx, shot, cid, t, frame, facing))
        loc.front(c, g, True)
        others = [o for o in shot.cast if o != cid]
        if others:  # plano por encima del hombro del que escucha
            o = others[0]
            c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(14, 14)))
            ctx.chars[o].draw_back(c, W * (0.5 + ctx.side(o) * 0.48), H * 1.12, 1.55, -ctx.side(o), t)
            c.restore()
        return
    # plano de dos
    for cid in shot.cast[:2]:
        side = ctx.side(cid)
        p = _pose(ctx, shot, cid, t, frame, -side)
        p.relative_height = True  # en el plano de dos se nota quién es más alto o más bajo
        ctx.chars[cid].draw(c, W * (0.5 + side * 0.24), H * 0.95, 0.92, p)
    c.save()
    c.translate(0, H * 0.07)  # en el plano de dos, la mesa/barra queda más baja
    loc.front(c, g, True)
    c.restore()


def render_shot(ctx: Ctx, shot: Shot, out: Path) -> Path:
    W, H, fps = ctx.W, ctx.H, ctx.fps
    set_style(ctx.style)
    frames = max(1, round(shot.duration * fps))
    info = skia.ImageInfo.Make(W, H, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
    surface = skia.Surface.MakeRaster(info)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
         "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    shaky = shot.camera == "shake" or shot.event in ("explosion", "bombardeo", "cañonazos", "terremoto") \
        or shot.action in ("golpear", "caer")
    for i in range(frames):
        t = i / fps
        c = surface.getCanvas()
        c.clear(skia.ColorBLACK)
        c.save()
        k = t / max(shot.duration, 0.01)
        z = {"push_in": 1 + 0.06 * ease(k), "pull_back": 1.08 - 0.08 * ease(k),
             # golpe: zoom de impacto al arrancar el vídeo (frena el scroll) y luego acercamiento lento
             "golpe": 1.0 + 0.24 * (1 - ease(t / 0.32)) + 0.07 * ease(k)}.get(shot.camera, 1.0)
        for pt in shot.punches:  # golpe de zoom en la palabra clave
            d = t - pt
            if -0.05 < d < 0.5:
                z *= 1 + 0.09 * math.exp(-max(d, 0) * 9)
        c.translate(W / 2, H * 0.5)
        c.scale(z, z)
        if shaky:
            amp = 14 * max(0.0, 1 - abs(t - 0.8) / 1.2)
            c.translate(noise1(t * 30, 1) * amp, noise1(t * 30, 2) * amp)
        elif shot.camera == "golpe" and t < 0.45:
            amp = 18 * (1 - t / 0.45)
            c.translate(noise1(t * 40, 3) * amp, noise1(t * 40, 4) * amp)
        c.translate(-W / 2, -H * 0.5)
        draw_frame(c, ctx, shot, t, i)
        c.restore()
        # acabado del estilo: luz de ambiente, brillo de las luces, grano/papel y viñeta
        F.mood_light(c, W, H, shot.mood, 0.3)
        F.bloom(c, surface, W, H)
        F.texture(c, W, H, i)
        S.vignette(c, W, H, STYLE["vignette"])
        arr = surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
        proc.stdin.write(arr.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg falló renderizando {out}")
    return out
