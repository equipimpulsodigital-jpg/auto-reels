"""Vida en los fondos de los planos generales: gente que pasa a lo lejos, clientes en la cafetería, compañeros en la
oficina, polvo en el aire de los interiores, hojas en el bosque, luciérnagas de noche. Todo pequeño y apagado para
que no robe protagonismo."""
from __future__ import annotations

import math
import random

import skia

from .draw import fill, mix, oval, rrect

FLOOR = 0.62


def _person(c, x, y, s, color, t, walk=0.0, seed=0, sitting=False):
    """Figura lejana sencilla (cabeza, cuerpo y piernas), sin contorno."""
    rnd = random.Random(seed)
    skin = rnd.choice(["#c9926b", "#e0b08a", "#8a5a3c", "#b07a55"])
    bob = abs(math.sin(t * 6 + seed)) * 4 * s if walk else 0
    if not sitting:
        sw = math.sin(t * 6 + seed) * 14 * s if walk else 0
        for d in (-1, 1):
            c.drawLine(x + d * 6 * s, y - 40 * s - bob, x + d * 6 * s + d * sw, y - bob * 0.2,
                       skia.Paint(Color=_c(mix(color, "#222222", 0.5)), StrokeWidth=9 * s, AntiAlias=True,
                                  StrokeCap=skia.Paint.kRound_Cap))
    top = y - (95 if not sitting else 70) * s - bob
    c.drawPath(rrect(x - 17 * s, top, 34 * s, 58 * s, 14 * s), fill(color))
    c.drawPath(oval(x, top - 16 * s, 14 * s, 15 * s), fill(skin))
    c.drawPath(oval(x, top - 25 * s, 14 * s, 8 * s), fill(rnd.choice(["#2a1d16", "#5a3b22", "#c9a25a", "#1f1a17"])))


def _c(h):
    h = h.lstrip("#")
    return skia.ColorSetRGB(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _muted(color: str, mood: str) -> str:
    base = {"noche": "#1c2236", "tormenta": "#4a5262", "atardecer": "#8a6a5a"}.get(mood, "#9aa4ae")
    return mix(color, base, 0.45)


def _walkers(c, W, H, t, mood, y, n=4, seed=1, s=2.0):
    rnd = random.Random(seed)
    for k in range(n):
        speed = rnd.uniform(40, 80) * rnd.choice([-1, 1])
        x = (rnd.uniform(0, W) + t * speed) % (W + 120) - 60
        col = _muted(rnd.choice(["#c0392b", "#2e5aa8", "#3f8a4f", "#d4a017", "#6b4a8a", "#444444"]), mood)
        _person(c, x, y + rnd.uniform(-8, 8), s * rnd.uniform(0.85, 1.1), col, t, walk=1, seed=seed * 10 + k)


def _particles(c, W, H, t, kind, seed=3):
    rnd = random.Random(seed)
    for k in range(26 if kind != "fireflies" else 14):
        x0, y0 = rnd.uniform(0, W), rnd.uniform(0, H * 0.8)
        if kind == "dust":  # polvo flotando en la luz de un interior
            x = x0 + math.sin(t * 0.4 + k) * 30
            y = (y0 - t * 12) % (H * 0.8)
            c.drawCircle(x, y, rnd.uniform(1.5, 3.5), fill("#fff4d6", 0.35 + 0.25 * math.sin(t * 2 + k)))
        elif kind == "leaves":  # hojas que caen
            x = (x0 + math.sin(t * 1.2 + k) * 50 + t * 20) % W
            y = (y0 + t * rnd.uniform(40, 90)) % H
            c.save()
            c.translate(x, y)
            c.rotate(math.sin(t * 3 + k) * 60)
            c.drawPath(oval(0, 0, 9, 4), fill(rnd.choice(["#c9822a", "#a85a1f", "#d9b23a", "#6b8a2f"]), 0.85))
            c.restore()
        else:  # luciérnagas
            x = x0 + math.sin(t * 0.7 + k * 2) * 40
            y = H * 0.5 + (y0 % (H * 0.35)) + math.cos(t * 0.9 + k) * 25
            a = max(0.0, math.sin(t * 2.5 + k * 1.7))
            c.drawCircle(x, y, 10, fill("#fff27a", 0.18 * a))
            c.drawCircle(x, y, 3, fill("#fffbd0", 0.9 * a))


def draw_life(c, W, H, t, location: str, mood: str) -> None:
    night = mood == "noche"
    if location in ("calle", "ciudad", "pueblo", "estacion"):
        _walkers(c, W, H, t, mood, H * (0.68 if location == "calle" else 0.7), n=2 if night else 4, seed=len(location))
    elif location in ("cafeteria", "taberna"):
        rnd = random.Random(7)
        for k, x in enumerate((W * 0.12, W * 0.88)):  # clientes sentados al fondo, que hablan y beben
            col = _muted(rnd.choice(["#2e5aa8", "#8a3a3a", "#3f6a4f", "#6b4a8a"]), mood)
            _person(c, x, H * FLOOR + 120, 2.0, col, t, seed=40 + k, sitting=True)
            c.drawPath(rrect(x - 110, H * FLOOR + 110, 220, 26, 10), fill(_muted("#5a3b2a", mood)))
            c.drawPath(rrect(x + 30, H * FLOOR + 80, 26, 32, 6), fill(_muted("#ffffff", mood)))
    elif location == "oficina":
        for k, x in enumerate((W * 0.18, W * 0.84)):
            _person(c, x, H * FLOOR - 20, 1.6, _muted("#40506a", mood), t, seed=60 + k, sitting=True)
    elif location == "hospital":
        _walkers(c, W, H, t * 0.6, mood, H * FLOOR + 140, n=1, seed=9, s=1.9)
    if location in ("despacho", "salon", "palacio", "iglesia", "aula", "carcel", "tribunal", "taberna"):
        _particles(c, W, H, t, "dust")
    elif location in ("bosque", "campo") and not night:
        _particles(c, W, H, t, "leaves")
    if night and location in ("bosque", "campo", "pueblo", "cementerio", "caseron", "carretera"):
        _particles(c, W, H, t, "fireflies")
