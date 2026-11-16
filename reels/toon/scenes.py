"""Escenarios y objetos animados (todo vectorial, en movimiento continuo)."""
from __future__ import annotations

import math
import random

import skia

from .draw import INK, fill, linear, mix, oval, poly, radial, shade, stroke, toon

# Paletas de ambiente (cielo arriba, cielo horizonte, sol, mar, tierra lejana)
MOODS = {
    "dia":       ("#5fa8d3", "#cfe8ef", "#fff3c4", "#2f7fa6", "#9db7a0"),
    "atardecer": ("#2e3a6b", "#f2a65a", "#ffd27a", "#264a73", "#6b5a7a"),
    "noche":     ("#0b1230", "#2a3a6e", "#e9eefc", "#0f2340", "#1e2747"),
    "tormenta":  ("#2c3440", "#7b8794", "#d9dde2", "#2a3b47", "#4a5560"),
}


def sky(c: skia.Canvas, W: int, H: int, mood: str, horizon: float, t: float, sun: bool = True) -> None:
    top, hor, sun_c, _, _ = MOODS[mood]
    c.drawRect(skia.Rect.MakeWH(W, H), linear(fill(top), (0, 0), (0, horizon), [top, hor]))
    if mood == "noche":
        rnd = random.Random(4)
        for _ in range(90):
            x, y = rnd.uniform(0, W), rnd.uniform(0, horizon * 0.8)
            tw = 0.5 + 0.5 * math.sin(t * rnd.uniform(1, 3) + x)
            c.drawCircle(x, y, rnd.uniform(1.5, 3.5), fill("#ffffff", 0.4 + 0.5 * tw))
    if sun:
        sx, sy = W * 0.72, horizon - (H * 0.12 if mood != "atardecer" else H * 0.05)
        if mood != "noche":  # rayos de sol que giran despacio
            for k in range(12):
                a = math.radians(k * 30 + t * 4)
                ray = poly([(sx, sy), (sx + math.cos(a - 0.06) * 1400, sy + math.sin(a - 0.06) * 1400),
                            (sx + math.cos(a + 0.06) * 1400, sy + math.sin(a + 0.06) * 1400)])
                c.drawPath(ray, fill(sun_c, 0.07))
        c.drawCircle(sx, sy, 260, radial(fill(sun_c), (sx, sy), 260, [sun_c, sun_c], [0.55, 0.0]))
        c.drawCircle(sx, sy, 85 if mood != "noche" else 60, fill(sun_c))


def clouds(c: skia.Canvas, W: int, t: float, y0: float, y1: float, mood: str, n: int = 6, seed: int = 1,
           speed: float = 12.0) -> None:
    rnd = random.Random(seed)
    base = {"dia": "#ffffff", "atardecer": "#f6c9a0", "noche": "#3a4778", "tormenta": "#5d6670"}[mood]
    for i in range(n):
        y = rnd.uniform(y0, y1)
        s = rnd.uniform(0.7, 1.5)
        x = (rnd.uniform(0, W + 600) + t * speed * s) % (W + 600) - 300
        puffs = [(x + dx * s, y + dy * s, r * s) for dx, dy, r in ((0, 0, 70), (70, -25, 85), (150, 0, 65), (80, 20, 70), (-60, 15, 50))]
        path = skia.Path()
        for px, py, r in puffs:
            path.addCircle(px, py, r)
        path = skia.Op(path, skia.Path(), skia.PathOp.kUnion_PathOp) or path
        c.drawPath(path, fill(base, 0.92))
        c.drawPath(path, stroke(shade(base, -0.25), 4, 0.6))


def mountains(c: skia.Canvas, W: int, y: float, color: str, seed: int, height: float = 160, jag: int = 7,
              offset: float = 0.0) -> None:
    rnd = random.Random(seed)
    pts = [(-50, y + 400)]
    for i in range(jag + 1):
        x = -50 + (W + 100) * i / jag + offset
        pts.append((x, y - rnd.uniform(0.3, 1.0) * height))
    pts.append((W + 50 + offset, y + 400))
    path = poly(pts, smooth=True)
    c.drawPath(path, fill(color))
    # bruma: las montañas se aclaran hacia la base (perspectiva atmosférica)
    c.save()
    c.clipPath(path, doAntiAlias=True)
    c.drawRect(skia.Rect.MakeLTRB(-60, y - height, W + 60, y + 60),
               linear(skia.Paint(AntiAlias=True), (0, y - height * 0.2), (0, y + 30), [color, shade(color, 0.35)]))
    c.restore()


def village(c: skia.Canvas, x0: float, y: float, s: float, seed: int, n: int = 9, night: bool = False, t: float = 0) -> None:
    """Pueblo mediterráneo: casas blancas encaladas de tejado plano."""
    rnd = random.Random(seed)
    x = x0
    for i in range(n):
        w, h = rnd.uniform(60, 110) * s, rnd.uniform(45, 95) * s
        yy = y - rnd.uniform(0, 40) * s
        wall = "#f4efe4" if not night else "#8f97b8"
        house = poly([(x, yy), (x + w, yy), (x + w, yy - h), (x, yy - h)])
        toon(c, house, wall, outline=4)
        for k in range(rnd.randint(1, 2)):
            wx = x + w * (0.25 + 0.4 * k)
            lit = night and math.sin(t * 0.5 + i) > -0.3
            c.drawRect(skia.Rect.MakeXYWH(wx, yy - h * 0.6, 12 * s, 16 * s), fill("#ffcf6b" if lit else "#3d4a5c"))
        x += w * rnd.uniform(0.7, 1.0)


def sea(c: skia.Canvas, W: int, H: int, y0: float, t: float, mood: str) -> None:
    col = MOODS[mood][3]
    c.drawRect(skia.Rect.MakeLTRB(0, y0, W, H), linear(fill(col), (0, y0), (0, H), [shade(col, 0.15), shade(col, -0.35)]))
    rnd = random.Random(9)
    for i in range(26):
        depth = i / 26
        yy = y0 + 10 + (H - y0) * depth ** 1.6
        x = (rnd.uniform(0, W) + t * (20 + 60 * depth) * (1 if i % 2 else -1)) % (W + 200) - 100
        w = 40 + 160 * depth
        p = skia.Path()
        p.moveTo(x - w / 2, yy)
        p.quadTo(x, yy - 8 - 10 * depth + math.sin(t * 2 + i) * 4, x + w / 2, yy)
        c.drawPath(p, stroke(shade(col, 0.35), 3 + 4 * depth, 0.7))
    # destellos que titilan
    rnd2 = random.Random(5)
    for i in range(40):
        x, yy = rnd2.uniform(0, W), y0 + (H - y0) * rnd2.random() ** 1.8
        tw = max(0.0, math.sin(t * rnd2.uniform(2, 5) + i * 1.3)) ** 6
        if tw > 0.05:
            r = 6 + 10 * tw
            c.drawPath(poly([(x - r, yy), (x, yy - r * 0.35), (x + r, yy), (x, yy + r * 0.35)]), fill("#ffffff", 0.8 * tw))
    # brillo del sol en el agua
    sx = W * 0.72
    for k in range(10):
        yy = y0 + 20 + k * 22
        ww = 120 - k * 6 + math.sin(t * 3 + k) * 20
        c.drawRect(skia.Rect.MakeXYWH(sx - ww / 2, yy, ww, 5), fill(MOODS[mood][2], 0.5))


def boat_front(c: skia.Canvas, W: int, H: int, y: float, t: float) -> None:
    """Borda de una barca de pesca en primer plano (tapa la cintura del personaje)."""
    roll = math.sin(t * 1.4) * 10
    hull = poly([(-40, y + roll), (W + 40, y - roll), (W + 40, H + 40), (-40, H + 40)])
    toon(c, hull, "#a4532f", light=(0, -1))
    for k in range(1, 4):
        c.drawLine(-40, y + roll + k * 70, W + 40, y - roll + k * 70, stroke(shade("#a4532f", -0.35), 5))
    rail = poly([(-40, y + roll - 26), (W + 40, y - roll - 26), (W + 40, y - roll + 8), (-40, y + roll + 8)])
    toon(c, rail, "#e8dcc2")
    # cuerda enrollada y red
    c.drawPath(oval(W * 0.82, y - roll + 120, 90, 38), stroke("#d9b26b", 14))
    c.drawPath(oval(W * 0.82, y - roll + 120, 55, 22), stroke("#c99d55", 12))


def dock_front(c: skia.Canvas, W: int, H: int, y: float) -> None:
    toon(c, poly([(-40, y), (W + 40, y), (W + 40, H + 40), (-40, H + 40)]), "#8a6a48", light=(0, -1))
    for k in range(-1, 9):
        x = k * 150
        c.drawLine(x, y, x - 60, H + 40, stroke(shade("#8a6a48", -0.35), 5))


def plane(c: skia.Canvas, x: float, y: float, s: float, kind: str = "b52", color: str = "#c8ced6", tilt: float = 0) -> None:
    """Silueta de avión de perfil (mira a la derecha)."""
    c.save()
    c.translate(x, y)
    c.rotate(tilt)
    c.scale(s, s)
    body = poly([(-260, -10), (-230, -30), (200, -30), (270, -12), (280, 0), (200, 22), (-230, 22), (-265, 10)], smooth=True)
    tail = poly([(-250, -20), (-300, -120), (-255, -120), (-180, -25)])
    toon(c, tail, shade(color, -0.1), outline=5)
    wing_far = poly([(-20, -10), (-110, -70), (-70, -70), (60, -12)])
    toon(c, wing_far, shade(color, -0.25), outline=5)
    toon(c, body, color, light=(0, -1), outline=5)
    wing = poly([(-30, 8), (-150, 110), (-95, 110), (70, 10)])
    toon(c, wing, shade(color, -0.08), outline=5)
    if kind == "b52":
        for k, (px, py) in enumerate(((-75, 55), (-120, 92))):
            toon(c, poly([(px - 30, py - 9), (px + 30, py - 9), (px + 34, py + 9), (px - 30, py + 9)], smooth=True), shade(color, -0.3), outline=4)
    for k in range(8):
        c.drawCircle(150 - k * 34, -8, 6, fill("#33404f"))
    c.drawPath(poly([(200, -26), (250, -20), (236, -4), (200, -6)]), fill("#33404f"))
    c.restore()


def fireball(c: skia.Canvas, x: float, y: float, age: float, size: float = 1.0) -> None:
    """Explosión: destello, bola de fuego que crece y humo que sube."""
    if age < 0:
        return
    rnd = random.Random(21)
    if age < 0.35:
        r = 900 * age / 0.35
        c.drawCircle(x, y, r, radial(fill("#ffffff"), (x, y), r, ["#ffffff", "#fff2b0"], [0.9 * (1 - age / 0.35), 0.0]))
    for i in range(18):  # humo negro
        a = rnd.uniform(0, 2 * math.pi)
        d = (60 + rnd.uniform(0, 160)) * min(1, age * 1.4) * size
        rr = (60 + rnd.uniform(0, 70)) * min(1, 0.3 + age) * size
        sx, sy = x + math.cos(a) * d, y + math.sin(a) * d * 0.7 - age * 70 * size
        c.drawCircle(sx, sy, rr, fill(mix("#2b2626", "#5b5555", rnd.random()), min(0.95, age * 2)))
    core = max(0.0, 1 - max(0, age - 0.6) / 1.5)
    for i, (colr, k) in enumerate((("#e2471f", 1.0), ("#f7931e", 0.75), ("#ffd23f", 0.5))):
        pts = []
        for j in range(14):
            a = 2 * math.pi * j / 14
            r = (150 + 50 * math.sin(age * 12 + j * 2.1 + i)) * k * min(1, age * 3) * core * size
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r * 0.85))
        if core > 0.02:
            c.drawPath(poly(pts, smooth=True), fill(colr))
    for i in range(14):  # restos en llamas
        a = rnd.uniform(-math.pi, 0.3)
        v = rnd.uniform(250, 600) * size
        px = x + math.cos(a) * v * age
        py = y + math.sin(a) * v * age + 260 * age * age
        c.drawCircle(px, py, 10 * size, fill("#ffb13b"))
        c.drawLine(px, py, px - math.cos(a) * 50, py - math.sin(a) * 50 + 30 * age, stroke("#3a3333", 7, 0.7))


def parachute(c: skia.Canvas, x: float, y: float, s: float, t: float, seed: int = 0, load: str = "bomba") -> None:
    sway = math.sin(t * 1.6 + seed) * 8
    c.save()
    c.translate(x, y)
    c.rotate(sway)
    c.scale(s, s)
    canopy = poly([(-160, 0), (-150, -90), (-80, -150), (0, -165), (80, -150), (150, -90), (160, 0),
                   (110, -18), (55, 0), (0, -18), (-55, 0), (-110, -18)], smooth=True)
    toon(c, canopy, "#eef0ee", light=(-1, -0.5))
    for k in (-110, -55, 0, 55, 110):
        c.drawLine(k * 1.3, -10, 0, 230, stroke(INK, 3, 0.8))
    if load == "bomba":
        b = poly([(-28, 230), (28, 230), (32, 380), (0, 420), (-32, 380)], smooth=True)
        toon(c, b, "#7f8a93", light=(-1, -0.3))
        c.drawPath(poly([(-40, 230), (40, 230), (30, 205), (-30, 205)]), fill("#5a636b"))
    c.restore()


def splash(c: skia.Canvas, x: float, y: float, age: float) -> None:
    if age < 0 or age > 2.5:
        return
    for k in range(3):
        r = (age * 220) + k * 60
        a = max(0.0, 1 - age / 2.5 - k * 0.15)
        c.drawPath(oval(x, y, r, r * 0.22), stroke("#e8f6ff", 8, a))
    for i in range(10):
        a = math.pi + math.pi * i / 9
        h = 260 * math.sin(min(math.pi, age * 2.5))
        c.drawLine(x + math.cos(a) * 30, y, x + math.cos(a) * (60 + i * 8), y - h * (0.5 + 0.5 * math.sin(i)), stroke("#e8f6ff", 10, max(0.0, 1 - age / 1.3)))


def vignette(c: skia.Canvas, W: int, H: int, strength: float = 0.45) -> None:
    p = fill("#000000")
    p.setShader(skia.GradientShader.MakeRadial(center=(W / 2, H * 0.45), radius=H * 0.75,
                                               colors=[skia.ColorSetARGB(0, 0, 0, 0), skia.ColorSetARGB(int(255 * strength), 0, 0, 0)],
                                               positions=[0.55, 1.0]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)


def gulls(c: skia.Canvas, W: int, H: int, t: float, seed: int = 0, n: int = 3) -> None:
    rnd = random.Random(seed)
    for i in range(n):
        sp = rnd.uniform(40, 90)
        x = (rnd.uniform(0, W) + t * sp) % (W + 200) - 100
        y = rnd.uniform(H * 0.12, H * 0.3) + math.sin(t * 0.8 + i) * 20
        s = rnd.uniform(0.6, 1.1)
        flap = math.sin(t * 7 + i * 2) * 18 * s
        p = skia.Path()
        p.moveTo(x - 34 * s, y - flap)
        p.quadTo(x - 14 * s, y - 14 * s - flap * 0.3, x, y)
        p.quadTo(x + 14 * s, y - 14 * s - flap * 0.3, x + 34 * s, y - flap)
        c.drawPath(p, stroke("#2a2f38", 5 * s))


def light_glow(c: skia.Canvas, W: int, H: int, mood: str, facing: float) -> None:
    """Luz cálida que baña al personaje desde el lado al que mira."""
    sun_c = MOODS[mood][2]
    cx = W * (0.95 if facing > 0 else 0.05)
    c.drawCircle(cx, H * 0.45, H * 0.6, radial(fill(sun_c), (cx, H * 0.45), H * 0.6, [sun_c, sun_c], [0.22, 0.0]))
