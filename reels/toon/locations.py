"""Biblioteca de escenarios. Cada lugar se dibuja en plano general (1080x1920); el motor lo acerca y
desenfoca para los planos de personaje. `era` cambia detalles de época (luces, farolas...)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import skia

from . import scenes as S
from .draw import INK, fill, linear, mix, oval, poly, radial, rrect, shade, stroke, toon

FLOOR = 0.62  # línea suelo/pared en interiores (fracción de H)


@dataclass
class G:
    W: int
    H: int
    t: float
    mood: str = "dia"   # dia | atardecer | noche | tormenta
    era: str = "1900"   # medieval | 1500 | 1700 | 1800 | 1900 | 1950 | moderno


def _old(era: str) -> bool:
    return era in ("medieval", "1500", "1700", "1800")


# ---------------- piezas reutilizables ----------------

def flame(c, x, y, s, t, seed=0):
    fl = 1 + 0.15 * math.sin(t * 13 + seed) + 0.1 * math.sin(t * 21 + seed * 2)
    c.drawCircle(x, y - 10 * s, 70 * s, radial(fill("#ffb347"), (x, y - 10 * s), 70 * s, ["#ffb347", "#ffb347"], [0.35, 0.0]))
    toon(c, poly([(x - 12 * s, y), (x, y - 42 * s * fl), (x + 12 * s, y)], smooth=True), "#ff9b2f", outline=0)
    toon(c, poly([(x - 6 * s, y), (x, y - 24 * s * fl), (x + 6 * s, y)], smooth=True), "#ffe27a", outline=0)


def candle(c, x, y, s, t, seed=0):
    toon(c, rrect(x - 10 * s, y, 20 * s, 60 * s, 4 * s), "#f3ead2", outline=4)
    flame(c, x, y - 2, s, t, seed)


def lamp_glow(c, x, y, r, color="#ffd28a", a=0.45):
    c.drawCircle(x, y, r, radial(fill(color), (x, y), r, [color, color], [a, 0.0]))


def street_lamp(c, x, base, s, era, night, t):
    c.drawLine(x, base, x, base - 520 * s, stroke(INK, 22 * s))
    c.drawLine(x, base, x, base - 520 * s, stroke("#30343b", 14 * s))
    head = poly([(x - 34 * s, base - 520 * s), (x + 34 * s, base - 520 * s), (x + 22 * s, base - 600 * s), (x - 22 * s, base - 600 * s)])
    toon(c, head, "#ffe7a3" if night else "#d9dfe6", outline=5)
    if night:
        lamp_glow(c, x, base - 560 * s, 260 * s, "#ffcf6b", 0.5 if not _old(era) else 0.4)


def window(c, x, y, w, h, sky_top, sky_bot, frame="#6b4a2f", curtains=None, night=False, t=0.0):
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), linear(fill(sky_top), (0, y), (0, y + h), [sky_top, sky_bot]))
    if night:
        c.drawCircle(x + w * 0.7, y + h * 0.3, w * 0.12, fill("#eef2ff"))
    for k in (1, 2):
        c.drawLine(x + w * k / 3, y, x + w * k / 3, y + h, stroke(frame, 10))
    c.drawLine(x, y + h / 2, x + w, y + h / 2, stroke(frame, 10))
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), stroke(frame, 18))
    c.drawRect(skia.Rect.MakeXYWH(x - 9, y - 9, w + 18, h + 18), stroke(INK, 5))
    if curtains:
        for side in (0, 1):
            cx = x - 40 if side == 0 else x + w - 50
            sway = math.sin(t * 0.8 + side) * 6
            cur = poly([(cx, y - 40), (cx + 90, y - 40), (cx + 70 + sway, y + h + 40), (cx + 10 + sway, y + h + 60)], smooth=False)
            toon(c, cur, curtains, light=(1 if side else -1, 0))


def floor(c, W, H, y, color, kind="madera", vp=None):
    vx = W / 2 if vp is None else vp
    c.drawRect(skia.Rect.MakeLTRB(0, y, W, H), linear(fill(color), (0, y), (0, H), [shade(color, -0.25), color]))
    if kind == "madera":
        for k in range(-8, 9):
            c.drawLine(vx + k * 40, y, vx + k * 260, H, stroke(shade(color, -0.3), 4))
    elif kind == "ajedrez":
        rows = 7
        for r in range(rows):
            y0 = y + (H - y) * (r / rows) ** 1.5
            y1 = y + (H - y) * ((r + 1) / rows) ** 1.5
            for k in range(-8, 8):
                if (k + r) % 2:
                    continue
                def X(kk, yy):
                    return vx + kk * (60 + 240 * (yy - y) / (H - y))
                c.drawPath(poly([(X(k, y0), y0), (X(k + 1, y0), y0), (X(k + 1, y1), y1), (X(k, y1), y1)]), fill(shade(color, -0.45)))
    elif kind == "piedra":
        rnd = random.Random(3)
        for r in range(9):
            yy = y + (H - y) * (r / 9) ** 1.4
            c.drawLine(0, yy, W, yy, stroke(shade(color, -0.3), 4))
            for k in range(6):
                xx = rnd.uniform(0, W)
                c.drawLine(xx, yy, xx, yy + 30 + r * 8, stroke(shade(color, -0.3), 4))
    elif kind == "adoquin":
        for r in range(12):
            yy = y + (H - y) * (r / 12) ** 1.3
            c.drawLine(0, yy, W, yy, stroke(shade(color, -0.25), 3))
            off = (r % 2) * 30
            for k in range(-2, 30):
                xx = k * (40 + r * 9) + off
                c.drawLine(xx, yy, xx, yy + 10 + r * 4, stroke(shade(color, -0.25), 3))


def wall(c, W, H, y, color, kind="liso"):
    c.drawRect(skia.Rect.MakeLTRB(0, 0, W, y), linear(fill(color), (0, 0), (0, y), [shade(color, -0.15), color]))
    if kind == "madera":
        for k in range(0, W, 90):
            c.drawLine(k, 0, k, y, stroke(shade(color, -0.3), 5))
    elif kind == "piedra":
        rnd = random.Random(8)
        for r in range(0, int(y), 70):
            off = (r // 70 % 2) * 60
            c.drawLine(0, r, W, r, stroke(shade(color, -0.3), 4))
            for k in range(-1, W // 120 + 2):
                c.drawLine(k * 120 + off, r, k * 120 + off, r + 70, stroke(shade(color, -0.3), 4))
            for _ in range(3):
                c.drawCircle(rnd.uniform(0, W), r + rnd.uniform(10, 60), rnd.uniform(3, 8), fill(shade(color, -0.2)))
    elif kind == "papel":  # papel pintado de rayas con zócalo
        for k in range(0, W, 60):
            c.drawRect(skia.Rect.MakeXYWH(k, 0, 24, y), fill(shade(color, -0.07)))
        c.drawRect(skia.Rect.MakeLTRB(0, y - 160, W, y), fill(shade(color, -0.35)))
        c.drawLine(0, y - 160, W, y - 160, stroke(INK, 5))
    c.drawLine(0, y, W, y, stroke(INK, 6))


def painting(c, x, y, w, h, colors, frame="#c9a227"):
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), linear(fill(colors[0]), (x, y), (x, y + h), colors))
    c.drawPath(oval(x + w * 0.5, y + h * 0.55, w * 0.22, h * 0.3), fill(shade(colors[-1], -0.3)))
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), stroke(frame, 22))
    c.drawRect(skia.Rect.MakeXYWH(x - 12, y - 12, w + 24, h + 24), stroke(INK, 5))


def flag(c, x, y, s, t, colors, pole=True):
    if pole:
        c.drawLine(x, y, x, y + 520 * s, stroke(INK, 14 * s))
        c.drawLine(x, y, x, y + 520 * s, stroke("#8a6a48", 8 * s))
    n = len(colors)
    for i, col in enumerate(colors):
        pts = []
        for k in range(9):
            u = k / 8
            pts.append((x + u * 260 * s, y + 10 * s + (i / n) * 160 * s + math.sin(t * 4 - u * 5) * 18 * s * u))
        for k in range(8, -1, -1):
            u = k / 8
            pts.append((x + u * 260 * s, y + 10 * s + ((i + 1) / n) * 160 * s + math.sin(t * 4 - u * 5) * 18 * s * u))
        c.drawPath(poly(pts), fill(col))
    c.drawPath(poly([(x, y + 10 * s), (x + 260 * s, y + 10 * s + math.sin(t * 4 - 5) * 18 * s),
                     (x + 260 * s, y + 170 * s + math.sin(t * 4 - 5) * 18 * s), (x, y + 170 * s)]), stroke(INK, 4))


def house(c, x, base, w, h, wall_c="#f4efe4", roof="#b5563a", night=False, t=0.0, seed=0):
    toon(c, poly([(x, base), (x + w, base), (x + w, base - h), (x, base - h)]), wall_c, light=(-1, 0), outline=5)
    if roof:
        toon(c, poly([(x - 14, base - h), (x + w + 14, base - h), (x + w * 0.5, base - h - w * 0.28)]), roof, outline=5)
    rnd = random.Random(seed)
    for k in range(max(1, int(w // 90))):
        wx = x + 25 + k * 90
        lit = night and rnd.random() > 0.35
        c.drawRect(skia.Rect.MakeXYWH(wx, base - h * 0.62, 34, 48), fill("#ffcf6b" if lit else "#33404f"))
        c.drawRect(skia.Rect.MakeXYWH(wx, base - h * 0.62, 34, 48), stroke(INK, 4))
    c.drawRect(skia.Rect.MakeXYWH(x + w * 0.5 - 24, base - 90, 48, 90), fill("#6b4a2f"))


def olive(c, x, base, s, t, seed=0):
    rnd = random.Random(seed)
    toon(c, poly([(x - 14 * s, base), (x + 14 * s, base), (x + 8 * s, base - 120 * s), (x - 10 * s, base - 120 * s)]), "#6a4b34", outline=4)
    for k in range(5):
        dx, dy = rnd.uniform(-80, 80) * s, rnd.uniform(-220, -140) * s
        sw = math.sin(t * 1.2 + k) * 3 * s
        toon(c, oval(x + dx + sw, base + dy, rnd.uniform(55, 80) * s, rnd.uniform(40, 55) * s), "#7d8f55", outline=4)


def column(c, x, top, base, w, color="#e9e2d3"):
    toon(c, poly([(x - w / 2, top), (x + w / 2, top), (x + w / 2, base), (x - w / 2, base)]), color, light=(-1, 0))
    for k in (-0.25, 0, 0.25):
        c.drawLine(x + k * w, top + 40, x + k * w, base - 40, stroke(shade(color, -0.25), 4))
    toon(c, rrect(x - w * 0.7, top - 30, w * 1.4, 40, 6), shade(color, -0.05))
    toon(c, rrect(x - w * 0.7, base - 10, w * 1.4, 40, 6), shade(color, -0.05))


def bookshelf(c, x, y, w, h, seed=0):
    toon(c, poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), "#5a3a24")
    rnd = random.Random(seed)
    rows = 5
    for r in range(rows):
        yy = y + 20 + r * (h - 20) / rows
        c.drawLine(x, yy + (h - 20) / rows - 4, x + w, yy + (h - 20) / rows - 4, stroke("#3d2717", 10))
        xx = x + 14
        while xx < x + w - 30:
            bw = rnd.uniform(18, 34)
            bh = (h - 20) / rows - rnd.uniform(14, 34)
            colr = rnd.choice(["#7a2e2e", "#2e4a7a", "#3f6b3a", "#8a6a2a", "#5a3a6b", "#a85a32"])
            toon(c, poly([(xx, yy + (h - 20) / rows - 8), (xx + bw, yy + (h - 20) / rows - 8), (xx + bw, yy + (h - 20) / rows - 8 - bh), (xx, yy + (h - 20) / rows - 8 - bh)]), colr, outline=3)
            xx += bw + 3


def table_front(c, W, H, y, color="#7a5232"):
    toon(c, poly([(-40, y), (W + 40, y), (W + 40, H + 40), (-40, H + 40)]), color, light=(0, -1))
    c.drawLine(-40, y + 28, W + 40, y + 28, stroke(shade(color, -0.35), 6))


# ---------------- lugares ----------------

class Loc:
    key = ""
    desc = ""
    ambience = ""
    interior = False
    floor_y = 0.86          # dónde pisan los personajes en plano general (fracción de H)

    def back(self, c, g: G) -> None: ...
    def front(self, c, g: G, close: bool) -> None: ...


class Costa(Loc):
    key, desc, ambience = "costa", "orilla o puerto de un pueblo costero: mar, montañas, casas blancas y muelle de madera", "mar"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.5
        S.sky(c, W, H, g.mood, hz, g.t)
        S.clouds(c, W, g.t, H * 0.06, H * 0.3, g.mood, n=4, seed=15)
        S.mountains(c, W, hz + 5, S.MOODS[g.mood][4], seed=7, height=110)
        S.village(c, W * 0.05, hz + 6, 0.5, seed=5, n=10, night=g.mood == "noche", t=g.t)
        S.sea(c, W, H, hz, g.t, g.mood)
        S.gulls(c, W, H, g.t, seed=2)
        S.dock_front(c, W, H, H * 0.74)
        for k in range(3):
            x = 120 + k * 400
            toon(c, rrect(x, H * 0.66, 34, H * 0.12, 8), "#6b4f35")


class Barca(Loc):
    key, desc, ambience = "barca", "a bordo de una barca o barco en el mar, con la costa al fondo", "mar"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.52
        S.sky(c, W, H, g.mood, hz, g.t)
        S.clouds(c, W, g.t, H * 0.06, H * 0.32, g.mood, n=4, seed=11)
        S.mountains(c, W, hz + 5, S.MOODS[g.mood][4], seed=7, height=70, jag=5)
        S.sea(c, W, H, hz, g.t, g.mood)
        S.gulls(c, W, H, g.t, seed=4)
    def front(self, c, g, close):
        S.boat_front(c, g.W, g.H, g.H * (0.88 if close else 0.8), g.t)


class Cielo(Loc):
    key, desc, ambience = "cielo", "el cielo a gran altura con nubes y la tierra muy abajo (aviones, explosiones aéreas)", "viento"
    floor_y = 0.95
    def back(self, c, g):
        W, H = g.W, g.H
        S.sky(c, W, H, g.mood, H * 1.05, g.t)
        S.clouds(c, W, g.t, H * 0.55, H * 0.95, g.mood, n=5, seed=3, speed=-160)
        c.drawRect(skia.Rect.MakeLTRB(0, H * 0.86, W, H), fill(S.MOODS[g.mood][3]))
        S.mountains(c, W, H * 0.88, shade(S.MOODS[g.mood][4], -0.1), seed=5, height=60)
        S.village(c, W * 0.35, H * 0.9, 0.35, seed=2, n=8)
        S.clouds(c, W, g.t, H * 0.08, H * 0.4, g.mood, n=4, seed=8, speed=-90)


class Pueblo(Loc):
    key, desc, ambience = "pueblo", "plaza de un pueblo español: casas encaladas, iglesia con campanario, fuente y suelo empedrado", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        night = g.mood == "noche"
        hz = H * 0.62
        S.sky(c, W, H, g.mood, hz, g.t)
        S.clouds(c, W, g.t, H * 0.05, H * 0.25, g.mood, n=3, seed=21)
        S.mountains(c, W, hz - 120, S.MOODS[g.mood][4], seed=12, height=180)
        # iglesia con campanario
        toon(c, poly([(560, hz), (900, hz), (900, hz - 330), (560, hz - 330)]), "#efe3cc", light=(-1, 0))
        toon(c, poly([(640, hz - 330), (800, hz - 330), (800, hz - 640), (640, hz - 640)]), "#eadcc2", light=(-1, 0))
        toon(c, poly([(625, hz - 640), (815, hz - 640), (720, hz - 760)]), "#b5563a")
        c.drawPath(oval(720, hz - 560, 36, 46), fill("#2b2f3a"))
        bell = math.sin(g.t * 2) * 10
        toon(c, poly([(700 + bell, hz - 580), (740 + bell, hz - 580), (750 + bell, hz - 540), (690 + bell, hz - 540)], smooth=True), "#c9a227", outline=4)
        c.drawPath(poly([(690, hz), (770, hz), (770, hz - 140), (730, hz - 180), (690, hz - 140)]), fill("#6b4a2f"))
        house(c, -20, hz, 300, 260, night=night, t=g.t, seed=1)
        house(c, 260, hz + 10, 260, 200, roof="#a8492f", night=night, t=g.t, seed=2)
        house(c, 900, hz + 5, 240, 230, night=night, t=g.t, seed=3)
        floor(c, W, H, hz, "#c8b08a", "adoquin")
        # fuente
        fx, fy = W * 0.5, H * 0.74
        toon(c, oval(fx, fy, 170, 40), "#b9b1a3")
        toon(c, rrect(fx - 20, fy - 160, 40, 150, 10), "#b9b1a3")
        for k in range(5):
            ph = (g.t * 1.5 + k * 0.2) % 1
            c.drawCircle(fx + (k - 2) * 26 * ph, fy - 160 + 120 * ph * ph, 6, fill("#bfe6ff", 1 - ph))
        if night:
            street_lamp(c, 120, H * 0.8, 1.0, g.era, True, g.t)


class Ciudad(Loc):
    key, desc, ambience = "ciudad", "calle de una ciudad antigua (Madrid, Barcelona, Sevilla...): edificios con balcones, farolas y adoquines", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        night = g.mood == "noche"
        hz = H * 0.62
        S.sky(c, W, H, g.mood, hz, g.t, sun=False)
        # cúpula al fondo
        toon(c, oval(W * 0.5, hz - 380, 120, 110), "#8fa1ad")
        toon(c, poly([(W * 0.5 - 130, hz - 380), (W * 0.5 + 130, hz - 380), (W * 0.5 + 130, hz - 200), (W * 0.5 - 130, hz - 200)]), "#d8cdb8")
        colors = ["#d9b48f", "#c98d6b", "#e6d2a8", "#b8866a"]
        for side in (-1, 1):
            for k in range(3):
                bw, bh = 320 - k * 50, 1000 - k * 200
                x0 = -40 + k * 150 if side < 0 else W - 280 - k * 150
                col = colors[(k + (side > 0) * 2) % 4]
                toon(c, poly([(x0, hz + 20), (x0 + bw, hz + 20), (x0 + bw, hz - bh), (x0, hz - bh)]), col, light=(-side, 0))
                for r in range(4):
                    wy = hz - bh + 120 + r * 200
                    if wy > hz - 120:
                        continue
                    for q in range(2):
                        wx = x0 + 50 + q * (bw - 150)
                        lit = night and (r + q + k) % 3 == 0
                        c.drawRect(skia.Rect.MakeXYWH(wx, wy, 60, 110), fill("#ffcf6b" if lit else "#2c3442"))
                        c.drawRect(skia.Rect.MakeXYWH(wx, wy, 60, 110), stroke(INK, 4))
                        c.drawLine(wx - 18, wy + 110, wx + 78, wy + 110, stroke(INK, 7))
                        for b in range(6):
                            c.drawLine(wx - 14 + b * 18, wy + 70, wx - 14 + b * 18, wy + 110, stroke(INK, 3))
        floor(c, W, H, hz + 20, "#9a9087", "adoquin")
        street_lamp(c, 170, H * 0.84, 1.1, g.era, night, g.t)
        street_lamp(c, W - 170, H * 0.84, 1.1, g.era, night, g.t)


class Campo(Loc):
    key, desc, ambience = "campo", "campo español: olivos, colinas, un cortijo y un camino de tierra", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.55
        S.sky(c, W, H, g.mood, hz, g.t)
        S.clouds(c, W, g.t, H * 0.06, H * 0.3, g.mood, n=4, seed=31)
        S.mountains(c, W, hz, mix(S.MOODS[g.mood][4], "#a89a70", 0.4), seed=3, height=200)
        c.drawRect(skia.Rect.MakeLTRB(0, hz, W, H), linear(fill("#c9b071"), (0, hz), (0, H), ["#bfae6e", "#a88a4f"]))
        house(c, 640, hz + 60, 260, 150, night=g.mood == "noche", t=g.t, seed=9)
        c.drawPath(poly([(W * 0.45, hz + 60), (W * 0.55, hz + 60), (W * 0.9, H), (W * 0.1, H)]), fill("#d9c59a"))
        for r in range(3):
            for k in range(4):
                s = 0.5 + r * 0.35
                x = (k * 320 + r * 140) % (W + 200) - 100
                if 0.3 * W < x < 0.7 * W and r == 2:
                    continue
                olive(c, x, hz + 90 + r * 190, s, g.t, seed=r * 10 + k)


class Castillo(Loc):
    key, desc, ambience = "castillo", "castillo o fortaleza en lo alto de una colina con torres, almenas y estandartes", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.62
        S.sky(c, W, H, g.mood, hz, g.t)
        S.clouds(c, W, g.t, H * 0.05, H * 0.25, g.mood, n=4, seed=41)
        toon(c, poly([(-60, hz + 80), (W * 0.2, hz - 160), (W * 0.8, hz - 180), (W + 60, hz + 80)], smooth=True), "#8c9a6a")
        stone = "#b8ad99"
        base = hz - 150
        toon(c, poly([(150, base), (930, base), (930, base - 300), (150, base - 300)]), stone, light=(-1, 0))
        for k in range(14):
            c.drawRect(skia.Rect.MakeXYWH(160 + k * 56, base - 340, 34, 44), fill(stone))
            c.drawRect(skia.Rect.MakeXYWH(160 + k * 56, base - 340, 34, 44), stroke(INK, 4))
        for tx in (120, 860):
            toon(c, poly([(tx, base + 10), (tx + 140, base + 10), (tx + 140, base - 520), (tx, base - 520)]), shade(stone, 0.05), light=(-1, 0))
            for k in range(3):
                c.drawRect(skia.Rect.MakeXYWH(tx + 4 + k * 50, base - 560, 32, 44), fill(stone))
                c.drawRect(skia.Rect.MakeXYWH(tx + 4 + k * 50, base - 560, 32, 44), stroke(INK, 4))
            c.drawPath(oval(tx + 70, base - 380, 16, 34), fill("#2b2f3a"))
            flag(c, tx + 70, base - 860, 0.75, g.t, ["#c0262d", "#f2c230"])
        c.drawPath(poly([(470, base), (610, base), (610, base - 170), (540, base - 230), (470, base - 170)]), fill("#3a2a1e"))
        floor(c, W, H, hz + 80, "#9aa36f", "piedra")


class Batalla(Loc):
    key, desc, ambience = "batalla", "campo de batalla: humo, fuego, cráteres y colinas (guerras, bombardeos, asedios)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.6
        S.sky(c, W, H, "tormenta" if g.mood == "dia" else g.mood, hz, g.t, sun=False)
        S.mountains(c, W, hz, "#4a4f45", seed=17, height=150)
        c.drawRect(skia.Rect.MakeLTRB(0, hz, W, H), linear(fill("#5c5139"), (0, hz), (0, H), ["#5c5139", "#3b3326"]))
        for k in range(4):  # columnas de humo
            x = 150 + k * 260
            for j in range(8):
                y = hz - j * 110 - (g.t * 40 % 110)
                c.drawCircle(x + math.sin(g.t + j + k) * 30 + j * 12, y, 60 + j * 14, fill("#2e2a28", 0.55 - j * 0.05))
            flame(c, x, hz + 10, 2.2, g.t, k)
        for k in range(3):
            toon(c, oval(200 + k * 340, H * (0.72 + 0.06 * k), 170, 36), "#3a3226")
        for k in range(6):  # alambrada
            x = k * 200 + 40
            c.drawLine(x, H * 0.8, x + 10, H * 0.7, stroke("#3a2e22", 10))
        p = skia.Path()
        p.moveTo(0, H * 0.72)
        for k in range(30):
            p.lineTo(k * 40, H * 0.72 + (8 if k % 2 else -8))
        c.drawPath(p, stroke("#2a241c", 4))


class Estacion(Loc):
    key, desc, ambience = "estacion", "andén de una estación de tren con locomotora de vapor y marquesina de hierro", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.6
        S.sky(c, W, H, g.mood, hz, g.t, sun=False)
        for k in range(5):  # marquesina
            x = k * 270
            c.drawLine(x, H * 0.1, x, hz + 100, stroke("#3a4048", 22))
        c.drawPath(poly([(-40, H * 0.06), (W + 40, H * 0.06), (W + 40, H * 0.13), (-40, H * 0.13)]), fill("#4a525c"))
        # locomotora
        lx = W * 0.05
        toon(c, rrect(lx, hz - 320, 640, 260, 30), "#2d2f33", light=(0, -1))
        toon(c, poly([(lx + 460, hz - 470), (lx + 640, hz - 470), (lx + 640, hz - 300), (lx + 460, hz - 300)]), "#262829")
        toon(c, poly([(lx + 90, hz - 450), (lx + 160, hz - 450), (lx + 150, hz - 320), (lx + 100, hz - 320)]), "#1f2022")
        c.drawRect(skia.Rect.MakeXYWH(lx + 490, hz - 440, 110, 90), fill("#ffcf6b" if g.mood == "noche" else "#9fb7c9"))
        c.drawLine(lx, hz - 150, lx + 640, hz - 150, stroke("#b3262d", 14))
        for k in range(4):
            wx = lx + 90 + k * 150
            rot = g.t * 3
            toon(c, oval(wx, hz - 40, 62, 62), "#3c3f44")
            c.drawLine(wx, hz - 40, wx + math.cos(rot) * 55, hz - 40 + math.sin(rot) * 55, stroke("#b3262d", 8))
        for j in range(7):  # vapor
            ph = (g.t * 0.6 + j / 7) % 1
            c.drawCircle(lx + 125 + ph * 160, hz - 470 - ph * 480, 50 + ph * 120, fill("#f0f0f0", 0.6 * (1 - ph)))
        floor(c, W, H, hz + 30, "#a69a88", "piedra")
        c.drawLine(0, hz + 30, W, hz + 30, stroke("#e6c84b", 14))


class Palacio(Loc):
    key, desc, ambience = "palacio", "salón del trono de un palacio real: columnas, cortinas rojas, lámpara de araña y trono", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#c9a77c")
        window(c, W * 0.33, H * 0.12, W * 0.34, H * 0.3, "#2e3a6b" if g.mood == "noche" else "#8fc1dc", "#f2d7a5",
               frame="#d9b65a", curtains="#9e1f28", night=g.mood == "noche", t=g.t)
        for x in (110, W - 110):
            column(c, x, H * 0.04, fy, 110)
        # trono
        toon(c, poly([(W * 0.5 - 120, fy - 20), (W * 0.5 + 120, fy - 20), (W * 0.5 + 110, fy - 420), (W * 0.5, fy - 500), (W * 0.5 - 110, fy - 420)], smooth=True), "#d4af37")
        toon(c, poly([(W * 0.5 - 80, fy - 60), (W * 0.5 + 80, fy - 60), (W * 0.5 + 70, fy - 380), (W * 0.5 - 70, fy - 380)], smooth=True), "#9e1f28")
        floor(c, W, H, fy, "#e9e1cf", "ajedrez")
        # alfombra
        c.drawPath(poly([(W * 0.5 - 90, fy), (W * 0.5 + 90, fy), (W * 0.5 + 260, H), (W * 0.5 - 260, H)]), fill("#9e1f28"))
        # lámpara de araña
        cx, cy = W * 0.5 + math.sin(g.t * 0.7) * 6, H * 0.06
        c.drawLine(W * 0.5, 0, cx, cy, stroke(INK, 6))
        toon(c, oval(cx, cy + 40, 160, 30), "#d4af37")
        for k in range(-2, 3):
            candle(c, cx + k * 60, cy + 5, 0.7, g.t, k)


class Despacho(Loc):
    key, desc, ambience = "despacho", "despacho o ministerio: estanterías con libros, ventana, escritorio con lámpara y papeles", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#7a5a3c", "madera")
        bookshelf(c, 40, H * 0.15, 380, fy - H * 0.15, seed=2)
        window(c, W * 0.52, H * 0.14, W * 0.38, H * 0.28, "#2e3a6b" if g.mood == "noche" else "#a9d0e6", "#e9eef2",
               frame="#4a3220", curtains="#4f6b4a", night=g.mood == "noche", t=g.t)
        painting(c, W * 0.6, H * 0.47, 200, 150, ["#5a6b4a", "#c9a66b"])
        floor(c, W, H, fy, "#6b4a2f", "madera")
    def front(self, c, g, close):
        W, H = g.W, g.H
        y = H * (0.86 if close else 0.8)
        table_front(c, W, H, y, "#5e3b22")
        lx = W * 0.82
        toon(c, poly([(lx - 70, y - 10), (lx + 70, y - 10), (lx + 30, y - 120), (lx - 30, y - 120)]), "#2e6b4a")
        lamp_glow(c, lx, y - 40, 300, "#ffd28a", 0.35 if g.mood != "noche" else 0.6)
        for k in range(3):
            c.drawPath(poly([(W * 0.15 + k * 18, y - 6 - k * 4), (W * 0.35 + k * 18, y - 14 - k * 4), (W * 0.36 + k * 18, y + 6), (W * 0.16 + k * 18, y + 14)]), fill("#f4efe3"))


class Iglesia(Loc):
    key, desc, ambience = "iglesia", "interior de una iglesia o catedral: arcos de piedra, vidriera de colores, velas y bancos", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#a59b8b", "piedra")
        # vidriera
        vx, vy, vw, vh = W * 0.32, H * 0.08, W * 0.36, H * 0.38
        arch = poly([(vx, vy + vh), (vx, vy + vw * 0.5), (vx + vw * 0.5, vy), (vx + vw, vy + vw * 0.5), (vx + vw, vy + vh)], smooth=False)
        c.save()
        c.clipPath(arch, doAntiAlias=True)
        rnd = random.Random(6)
        for i in range(0, int(vw), 48):
            for j in range(0, int(vh), 60):
                colr = rnd.choice(["#c0262d", "#2e5aa8", "#e3b23c", "#3f8a4a", "#7a3e9e"])
                c.drawRect(skia.Rect.MakeXYWH(vx + i, vy + j, 48, 60), fill(colr, 0.9 if g.mood != "noche" else 0.45))
                c.drawRect(skia.Rect.MakeXYWH(vx + i, vy + j, 48, 60), stroke(INK, 5))
        c.restore()
        c.drawPath(arch, stroke(INK, 12))
        if g.mood != "noche":  # haz de luz de colores
            c.drawPath(poly([(vx, vy + vh), (vx + vw, vy + vh), (vx + vw + 260, H), (vx - 120, H)]), fill("#fff3c4", 0.12))
        for x in (90, W - 90):
            column(c, x, 0, fy, 120, "#bdb3a2")
        floor(c, W, H, fy, "#8d8475", "piedra")
        for k in range(3):  # bancos
            y = fy + 80 + k * 120
            toon(c, rrect(40, y, W * 0.36, 40, 6), "#5a3a24")
            toon(c, rrect(W * 0.64 - 40, y, W * 0.36, 40, 6), "#5a3a24")
        for k in range(7):
            candle(c, W * 0.5 - 180 + k * 60, fy - 40 - (k % 2) * 30, 1.0, g.t, k)


class Taberna(Loc):
    key, desc, ambience = "taberna", "taberna o mesón: barra de madera, barriles, botellas y lámpara de aceite", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#8a6240", "madera")
        for r in range(2):  # estanterías con botellas
            y = H * 0.18 + r * 200
            c.drawLine(80, y, W - 80, y, stroke("#3d2717", 14))
            rnd = random.Random(r)
            for k in range(10):
                x = 110 + k * 88
                colr = rnd.choice(["#2f5a3a", "#6b2a2a", "#8a6a2a", "#3a4a6b"])
                toon(c, poly([(x - 16, y - 7), (x + 16, y - 7), (x + 16, y - 80), (x + 6, y - 100), (x + 6, y - 125), (x - 6, y - 125), (x - 6, y - 100), (x - 16, y - 80)]), colr, outline=4)
        for k in range(3):  # barriles
            bx = 120 + k * 200
            toon(c, oval(bx, fy - 90, 90, 100), "#7a4e2c")
            for dy in (-50, 50):
                c.drawLine(bx - 86, fy - 90 + dy, bx + 86, fy - 90 + dy, stroke("#3a3a3a", 8))
        floor(c, W, H, fy, "#5a3f28", "madera")
        lx = W * 0.72 + math.sin(g.t * 1.1) * 14
        c.drawLine(W * 0.72, 0, lx, H * 0.1, stroke(INK, 5))
        toon(c, poly([(lx - 40, H * 0.1), (lx + 40, H * 0.1), (lx + 30, H * 0.16), (lx - 30, H * 0.16)]), "#ffcf6b", outline=5)
        lamp_glow(c, lx, H * 0.14, 420, "#ffc46b", 0.4)
    def front(self, c, g, close):
        y = g.H * (0.86 if close else 0.8)
        table_front(c, g.W, g.H, y, "#6b4529")
        x = g.W * 0.8
        toon(c, poly([(x - 30, y - 4), (x + 30, y - 4), (x + 26, y - 90), (x - 26, y - 90)]), "#e9d9a8", outline=5)


class Carcel(Loc):
    key, desc, ambience = "carcel", "celda de una cárcel o mazmorra: muros de piedra, ventanuco con barrotes y un haz de luz", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#6f6a62", "piedra")
        wx, wy = W * 0.58, H * 0.12
        c.drawRect(skia.Rect.MakeXYWH(wx, wy, 220, 170), fill("#bcd6e6" if g.mood != "noche" else "#1d2747"))
        for k in range(1, 5):
            c.drawLine(wx + k * 44, wy, wx + k * 44, wy + 170, stroke("#2a2a2a", 12))
        c.drawRect(skia.Rect.MakeXYWH(wx, wy, 220, 170), stroke(INK, 8))
        a = 0.14 + 0.03 * math.sin(g.t)
        c.drawPath(poly([(wx, wy + 170), (wx + 220, wy + 170), (wx + 40, H), (wx - 420, H)]), fill("#fff6d5", a))
        for k in range(30):  # polvo flotando en la luz
            ph = (g.t * 0.05 + k / 30) % 1
            c.drawCircle(wx - 300 + ph * 400 + math.sin(k) * 80, wy + 200 + (k * 53) % 800, 3, fill("#ffffff", 0.4))
        floor(c, W, H, fy, "#57524a", "piedra")
        for k in range(18):
            x = 120 + (k * 37) % 300
            c.drawLine(x, H * 0.82 + k % 5 * 6, x + 60, H * 0.8 + k % 7 * 5, stroke("#c9a85a", 4))
        c.drawLine(80, H * 0.3, 80, H * 0.45, stroke("#3a3a3a", 10))
        toon(c, oval(80, H * 0.46, 30, 14), "#3a3a3a")


class Salon(Loc):
    key, desc, ambience = "salon", "salón de una casa burguesa de los siglos XIX-XX: papel pintado, chimenea encendida, cuadros y sofá", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#6b8a7a", "papel")
        painting(c, W * 0.12, H * 0.14, 230, 300, ["#3a4a6b", "#d9b98a"])
        painting(c, W * 0.62, H * 0.12, 280, 210, ["#6b8a4a", "#e9d2a0"])
        # chimenea
        fx = W * 0.5
        toon(c, poly([(fx - 230, fy), (fx + 230, fy), (fx + 230, fy - 330), (fx - 230, fy - 330)]), "#d9cfbd", light=(-1, 0))
        toon(c, poly([(fx - 260, fy - 330), (fx + 260, fy - 330), (fx + 260, fy - 370), (fx - 260, fy - 370)]), "#bfb4a0")
        c.drawPath(poly([(fx - 140, fy), (fx + 140, fy), (fx + 140, fy - 220), (fx, fy - 260), (fx - 140, fy - 220)]), fill("#1b1411"))
        for k in range(4):
            flame(c, fx - 70 + k * 46, fy - 30, 2.2 - (k % 2) * 0.5, g.t, k)
        lamp_glow(c, fx, fy - 100, 500, "#ffa94d", 0.35)
        candle(c, fx - 190, fy - 372, 0.9, g.t, 1)
        candle(c, fx + 190, fy - 372, 0.9, g.t, 2)
        floor(c, W, H, fy, "#6e4a30", "madera")
        c.drawPath(oval(W * 0.5, H * 0.8, 420, 120), fill("#8a2e2e"))


class Tienda(Loc):
    key, desc, ambience = "tienda", "tienda de campaña militar: lona, mesa con mapas y lámpara colgante", "viento"
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        canvas_c = "#b8a77a"
        c.drawRect(skia.Rect.MakeLTRB(0, 0, W, fy), fill(canvas_c))
        for k in range(-1, 6):
            x = k * 240 + math.sin(g.t * 0.6 + k) * 6
            c.drawPath(poly([(x, 0), (x + 120, 0), (x + 160, fy), (x + 40, fy)]), fill(shade(canvas_c, -0.1)))
            c.drawLine(x + 120, 0, x + 160, fy, stroke(shade(canvas_c, -0.3), 4))
        c.drawLine(W / 2, 0, W / 2, fy, stroke("#6b4f35", 26))
        floor(c, W, H, fy, "#7a6a4a", "madera")
        lx = W * 0.5 + math.sin(g.t * 0.9) * 18
        c.drawLine(W * 0.5, H * 0.04, lx, H * 0.16, stroke(INK, 5))
        toon(c, poly([(lx - 34, H * 0.16), (lx + 34, H * 0.16), (lx + 26, H * 0.21), (lx - 26, H * 0.21)]), "#ffcf6b", outline=5)
        lamp_glow(c, lx, H * 0.19, 520, "#ffc46b", 0.45 if g.mood == "noche" else 0.25)
    def front(self, c, g, close):
        y = g.H * (0.86 if close else 0.8)
        table_front(c, g.W, g.H, y, "#6b5230")
        c.drawPath(poly([(g.W * 0.2, y - 4), (g.W * 0.7, y - 10), (g.W * 0.72, y + 26), (g.W * 0.18, y + 30)]), fill("#e9dcb4"))
        for k in range(5):
            c.drawLine(g.W * (0.25 + k * 0.09), y - 2, g.W * (0.28 + k * 0.08), y + 24, stroke("#7a6a4a", 3))


class Bosque(Loc):
    key, desc, ambience = "bosque", "bosque oscuro o camino entre árboles (huidas, crímenes, emboscadas)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.6
        S.sky(c, W, H, g.mood, hz, g.t, sun=False)
        if g.mood == "noche":
            c.drawCircle(W * 0.7, H * 0.15, 80, fill("#eef2ff"))
            lamp_glow(c, W * 0.7, H * 0.15, 300, "#dfe6ff", 0.3)
        for layer, (col, n, s) in enumerate((("#2f4a3a", 6, 0.8), ("#22382c", 5, 1.1), ("#18291f", 4, 1.5))):
            rnd = random.Random(layer)
            if g.mood == "noche":
                col = mix(col, "#0b1230", 0.5)
            for k in range(n):
                x = rnd.uniform(-100, W + 100)
                base = hz + 120 + layer * 260
                c.drawRect(skia.Rect.MakeLTRB(x - 18 * s, base - 500 * s, x + 18 * s, base), fill(shade(col, -0.2)))
                for j in range(3):
                    sw = math.sin(g.t * 0.8 + k + j) * 6
                    c.drawPath(poly([(x - (170 - j * 40) * s + sw, base - (220 + j * 150) * s), (x + sw, base - (420 + j * 150) * s),
                                     (x + (170 - j * 40) * s + sw, base - (220 + j * 150) * s)]), fill(col))
        c.drawRect(skia.Rect.MakeLTRB(0, H * 0.82, W, H), fill("#2a2a1e" if g.mood == "noche" else "#4a5a32"))
        for k in range(20):  # niebla baja
            x = (k * 140 + g.t * 25) % (W + 300) - 150
            c.drawCircle(x, H * 0.84 + (k % 3) * 30, 120, fill("#d9e2ea", 0.08))


LOCATIONS: dict[str, Loc] = {cls.key: cls() for cls in (
    Costa, Barca, Cielo, Pueblo, Ciudad, Campo, Castillo, Batalla, Estacion,
    Palacio, Despacho, Iglesia, Taberna, Carcel, Salon, Tienda, Bosque)}
