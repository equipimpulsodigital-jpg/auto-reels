"""Objetos en primer plano (planos de detalle del narrador) y sucesos animados que se superponen a un
escenario (explosiones, disparos, fuego, lluvia, multitudes...)."""
from __future__ import annotations

import math
import random

import skia

from . import scenes as S
from .draw import INK, fill, oval, poly, rrect, shade, stroke, toon
from .locations import flame, lamp_glow

# ---------------- objetos (centrados en (0,0), tamaño ~600 px) ----------------


def _scribble(c, x, y, w, rows, color="#5a4a3a", gap=34):
    """Líneas onduladas que sugieren texto manuscrito (sin letras legibles)."""
    for r in range(rows):
        p = skia.Path()
        yy = y + r * gap
        p.moveTo(x, yy)
        n = int(w / 18)
        for k in range(n):
            p.quadTo(x + k * 18 + 9, yy + (-7 if k % 2 else 7), x + (k + 1) * 18, yy)
        c.drawPath(p, stroke(color, 4))


def carta(c, t):
    toon(c, poly([(-260, -320), (260, -320), (260, 320), (-260, 320)]), "#f3ead2", light=(-1, -1))
    _scribble(c, -200, -230, 380, 11)
    toon(c, oval(150, 250, 54, 54), "#a8242c")
    c.drawPath(oval(150, 250, 30, 30), stroke(shade("#a8242c", -0.3), 5))


def documento(c, t):
    carta(c, t)
    toon(c, poly([(-260, -320), (260, -320), (260, -250), (-260, -250)]), "#e2d6b4", outline=0)


def mapa(c, t):
    toon(c, poly([(-330, -260), (-110, -300), (110, -260), (330, -300), (330, 280), (110, 320), (-110, 280), (-330, 320)]), "#e9d9a6", light=(-1, -1))
    toon(c, poly([(-250, -150), (-120, -220), (40, -170), (150, -60), (90, 120), (-60, 170), (-210, 80)], smooth=True), "#cdb987", outline=4)
    p = skia.Path()
    p.moveTo(-200, 160)
    p.cubicTo(-80, 40, 40, 200, 180, -40)
    dash = stroke("#a8242c", 8)
    dash.setPathEffect(skia.DashPathEffect.Make([24, 16], (-(t * 60)) % 40))
    c.drawPath(p, dash)
    for d in (-1, 1):
        c.drawLine(180 - 26, -40 - 26 * d, 180 + 26, -40 + 26 * d, stroke("#a8242c", 12))


def bomba(c, t):
    toon(c, poly([(-90, -300), (90, -300), (110, 220), (0, 320), (-110, 220)], smooth=True), "#7f8a93", light=(-1, -0.3))
    for k in (-1, 1):
        toon(c, poly([(k * 30, -300), (k * 150, -380), (k * 140, -260), (k * 60, -250)]), "#5a636b")
    c.drawLine(-100, -100, 100, -100, stroke(shade("#7f8a93", -0.4), 6))


def corona(c, t):
    pts = [(-260, 160), (-280, -140), (-150, 20), (-80, -220), (0, 0), (80, -220), (150, 20), (280, -140), (260, 160)]
    toon(c, poly(pts), "#e3b23c", light=(-1, -0.5))
    toon(c, rrect(-270, 110, 540, 90, 20), "#d4a02a")
    for k, colr in zip((-160, 0, 160), ("#c0262d", "#2e5aa8", "#3f8a4a")):
        toon(c, oval(k, 155, 30, 30), colr, outline=4)
    for k in range(5):  # destellos
        ph = (t * 0.8 + k * 0.2) % 1
        if ph < 0.3:
            x, y = (-250 + k * 120), (-100 + (k % 2) * 160)
            r = 30 * math.sin(ph / 0.3 * math.pi)
            c.drawPath(poly([(x - r, y), (x, y - r * 0.3), (x + r, y), (x, y + r * 0.3)]), fill("#ffffff"))
            c.drawPath(poly([(x, y - r), (x + r * 0.3, y), (x, y + r), (x - r * 0.3, y)]), fill("#ffffff"))


def pistola(c, t):
    toon(c, poly([(-300, -60), (220, -60), (240, -10), (-300, 10)]), "#3d4148", light=(0, -1))
    toon(c, poly([(-300, -80), (-120, -80), (-110, 40), (-300, 40)]), "#2f3238")
    toon(c, poly([(-240, 30), (-140, 30), (-120, 300), (-250, 300)], smooth=True), "#6b4a2f", light=(-1, 0))
    c.drawPath(oval(-80, 70, 50, 36), stroke(INK, 12))


def espada(c, t):
    c.save()
    c.rotate(-35)
    toon(c, poly([(-24, -380), (0, -440), (24, -380), (24, 160), (-24, 160)]), "#dfe5ea", light=(-1, 0))
    toon(c, rrect(-150, 160, 300, 40, 18), "#c9a227")
    toon(c, rrect(-20, 200, 40, 170, 12), "#5a3a24")
    toon(c, oval(0, 385, 34, 34), "#c9a227")
    sh = (t * 0.7) % 1.4
    if sh < 1:
        y = -380 + sh * 540
        c.drawLine(-10, y, 10, y - 80, stroke("#ffffff", 10, 0.8))
    c.restore()


def monedas(c, t):
    rnd = random.Random(2)
    for k in range(12):
        x, y = rnd.uniform(-260, 260), rnd.uniform(-60, 260)
        toon(c, oval(x, y, 70, 26), "#d4a02a", outline=5)
        toon(c, oval(x, y - 12, 70, 26), "#f0c24a", outline=5)
        c.drawPath(oval(x, y - 12, 44, 15), stroke("#b5871d", 4))
    for k in range(3):  # monedas cayendo
        ph = (t * 0.9 + k * 0.33) % 1
        x = -120 + k * 120
        toon(c, oval(x, -380 + ph * 520, 60, 60 * abs(math.cos(t * 6 + k))), "#f0c24a", outline=5)


def reloj(c, t):
    toon(c, oval(0, 0, 280, 280), "#e3b23c", light=(-1, -0.5))
    toon(c, oval(0, 0, 235, 235), "#f7f1e1")
    for k in range(12):
        a = math.radians(k * 30)
        c.drawLine(math.sin(a) * 190, -math.cos(a) * 190, math.sin(a) * 220, -math.cos(a) * 220, stroke(INK, 10 if k % 3 == 0 else 5))
    sec = math.radians(int(t * 2) * 6 * 3)
    mn = math.radians(300 + t * 2)
    c.drawLine(0, 0, math.sin(mn) * 120, -math.cos(mn) * 120, stroke(INK, 16))
    c.drawLine(0, 0, math.sin(mn * 0.08 + 2) * 80, -math.cos(mn * 0.08 + 2) * 80, stroke(INK, 20))
    c.drawLine(0, 0, math.sin(sec) * 190, -math.cos(sec) * 190, stroke("#a8242c", 6))
    c.drawCircle(0, 0, 14, fill(INK))
    toon(c, rrect(-30, -330, 60, 60, 12), "#d4a02a")


def llave(c, t):
    c.save()
    c.rotate(math.sin(t * 2) * 8)
    toon(c, oval(-200, 0, 110, 110), "#c9a227", light=(-1, -0.5))
    c.drawPath(oval(-200, 0, 50, 50), fill("#2a2420"))
    toon(c, rrect(-100, -26, 380, 52, 20), "#c9a227")
    toon(c, poly([(200, 20), (260, 20), (260, 130), (230, 130), (230, 80), (200, 80)]), "#c9a227")
    c.restore()


def veneno(c, t):
    toon(c, poly([(-140, 300), (140, 300), (170, 0), (60, -110), (60, -260), (-60, -260), (-60, -110), (-170, 0)], smooth=True), "#3f8a4a", light=(-1, -0.3))
    toon(c, rrect(-70, -330, 140, 80, 14), "#6b4a2f")
    toon(c, poly([(-110, 40), (110, 40), (110, 200), (-110, 200)]), "#f3ead2")
    c.drawCircle(0, 100, 36, fill(INK))
    c.drawLine(-50, 160, 50, 120, stroke(INK, 12))
    c.drawLine(-50, 120, 50, 160, stroke(INK, 12))
    for k in range(4):  # vapores
        ph = (t * 0.5 + k / 4) % 1
        c.drawCircle(math.sin(ph * 6 + k) * 40, -340 - ph * 300, 20 + 30 * ph, fill("#9fe08a", 0.5 * (1 - ph)))


def periodico(c, t):
    toon(c, poly([(-300, -330), (300, -330), (300, 330), (-300, 330)]), "#ece6d6", light=(-1, -1))
    toon(c, rrect(-250, -290, 500, 70, 6), "#2b2f3a", outline=0)
    toon(c, poly([(-250, -190), (-20, -190), (-20, 40), (-250, 40)]), "#b9b2a1", outline=4)
    _scribble(c, 10, -170, 240, 7, "#4a4a4a", 30)
    _scribble(c, -250, 90, 500, 7, "#4a4a4a", 30)


def cuchillo(c, t):
    c.save()
    c.rotate(20)
    toon(c, poly([(-40, -380), (40, -300), (40, 80), (-40, 80)], smooth=False), "#dfe5ea", light=(-1, 0))
    toon(c, rrect(-60, 80, 120, 30, 10), "#4a4a4a")
    toon(c, rrect(-34, 110, 68, 230, 22), "#5a3a24")
    c.drawPath(poly([(-30, -200), (10, -150), (0, -60), (-20, -120)], smooth=True), fill("#a8242c", 0.85))
    c.restore()


def anillo(c, t):
    toon(c, oval(0, 60, 230, 120), "#e3b23c", light=(-1, -0.5))
    c.drawPath(oval(0, 60, 170, 74), fill("#2a2420"))
    toon(c, poly([(-70, -60), (70, -60), (110, -150), (0, -230), (-110, -150)]), "#b8e6f5", light=(-1, -0.5))
    ph = (t * 0.7) % 1
    if ph < 0.25:
        r = 60 * math.sin(ph / 0.25 * math.pi)
        c.drawPath(poly([(30 - r, -160), (30, -160 - r * 0.3), (30 + r, -160), (30, -160 + r * 0.3)]), fill("#ffffff"))


PROPS = {"carta": carta, "documento": documento, "mapa": mapa, "bomba": bomba, "corona": corona, "pistola": pistola,
         "espada": espada, "monedas": monedas, "reloj": reloj, "llave": llave, "veneno": veneno,
         "periodico": periodico, "cuchillo": cuchillo, "anillo": anillo}


def draw_prop(c, W, H, name, t, table_color="#6b4a2f"):
    """Objeto sobre una mesa, iluminado por un foco cálido, flotando un poco."""
    y0 = H * 0.66
    c.drawRect(skia.Rect.MakeLTRB(0, y0, W, H), fill(table_color))
    c.drawLine(0, y0, W, y0, stroke(INK, 6))
    lamp_glow(c, W / 2, H * 0.5, H * 0.45, "#ffe2a8", 0.35)
    c.drawPath(oval(W / 2, y0 + 140, 320, 50), fill("#000000", 0.25))
    c.save()
    c.translate(W / 2, H * 0.5 + math.sin(t * 1.6) * 10)
    c.rotate(math.sin(t * 0.9) * 2)
    PROPS.get(name, carta)(c, t)
    c.restore()


# ---------------- sucesos (se dibujan encima del escenario) ----------------

def ev_aviones(c, W, H, t, dur):
    bob = math.sin(t * 1.3) * 10
    x = W * 0.42 + t * 25
    S.plane(c, x + 60, H * 0.36 + bob, 1.05, "tanker", "#b9c2cc")
    c.drawLine(x + 30, H * 0.36 + 25 + bob, x - 40, H * 0.47 + bob, stroke("#4a525c", 10))
    S.plane(c, x - 70, H * 0.5 + bob * 1.2, 1.35, "b52", "#9aa5b1", tilt=-2)


def ev_explosion(c, W, H, t, dur):
    S.fireball(c, W * 0.5, H * 0.42, (t - 0.5) * 0.9, size=1.3)


def ev_bombardeo(c, W, H, t, dur):
    for k, (x, at) in enumerate(((0.3, 0.3), (0.7, 1.1), (0.5, 1.9))):
        S.fireball(c, W * x, H * 0.62, (t - at) * 1.1, size=0.8)


def ev_paracaidas(c, W, H, t, dur):
    for i in range(4):
        tt = t - i * 0.3
        if tt > 0:
            S.parachute(c, W * (0.2 + i * 0.2) + math.sin(tt + i) * 20, H * 0.12 + tt * 150, 0.45, t, seed=i)


def ev_hundimiento(c, W, H, t, dur):
    land = 1.6
    if t < land:
        S.parachute(c, W * 0.55, H * 0.12 + (H * 0.5) * (t / land), 0.8, t, seed=1)
    else:
        S.splash(c, W * 0.55, H * 0.62 + 330, t - land)


def ev_fuego(c, W, H, t, dur):
    for k in range(9):
        flame(c, W * (0.05 + k * 0.115), H * 0.8 + (k % 2) * 30, 4.0 + (k % 3), t, k)
    for j in range(10):
        ph = (t * 0.3 + j / 10) % 1
        c.drawCircle(W * (0.1 + (j * 0.37) % 0.8), H * 0.75 - ph * H * 0.6, 80 + ph * 160, fill("#2b2626", 0.5 * (1 - ph)))
    lamp_glow(c, W / 2, H * 0.8, H * 0.6, "#ff7a2f", 0.35)


def ev_disparos(c, W, H, t, dur):
    rnd = random.Random(int(t * 6))
    for k in range(3):
        x, y = rnd.uniform(0.1, 0.9) * W, rnd.uniform(0.55, 0.8) * H
        if rnd.random() < 0.5:
            c.drawPath(poly([(x - 60, y), (x, y - 22), (x + 70, y), (x, y + 22)]), fill("#ffe27a"))
            lamp_glow(c, x, y, 160, "#ffcf6b", 0.5)
    for j in range(12):
        ph = (t * 0.4 + j / 12) % 1
        c.drawCircle(W * ((j * 0.29) % 1), H * 0.72 - ph * 300, 50 + ph * 90, fill("#d9d4cc", 0.35 * (1 - ph)))


def ev_lluvia(c, W, H, t, dur):
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#1b2430", 0.25))
    rnd = random.Random(1)
    for k in range(160):
        x = (rnd.uniform(0, W) + t * 120) % W
        y = (rnd.uniform(0, H) + t * 1600 * rnd.uniform(0.8, 1.2)) % H
        c.drawLine(x, y, x - 10, y + 50, stroke("#cfe0f0", 3, 0.6))
    if int(t * 10) % 37 == 0:  # relámpago
        c.drawRect(skia.Rect.MakeWH(W, H), fill("#ffffff", 0.5))


def ev_nieve(c, W, H, t, dur):
    rnd = random.Random(2)
    for k in range(120):
        x = (rnd.uniform(0, W) + math.sin(t + k) * 30) % W
        y = (rnd.uniform(0, H) + t * 120 * rnd.uniform(0.6, 1.4)) % H
        c.drawCircle(x, y, rnd.uniform(4, 9), fill("#ffffff", 0.9))


def ev_multitud(c, W, H, t, dur):
    """Muchedumbre en silueta que agita los brazos (protestas, celebraciones, motines)."""
    rnd = random.Random(5)
    for row in range(3):
        y = H * (0.78 + row * 0.07)
        col = shade("#2a2430", 0.1 * row)
        for k in range(10):
            x = (k + 0.5 * (row % 2)) * W / 9 + rnd.uniform(-20, 20)
            s = 0.9 + row * 0.25
            bob = abs(math.sin(t * 4 + k * 1.7 + row)) * 14
            c.drawCircle(x, y - 150 * s - bob, 46 * s, fill(col))
            c.drawPath(poly([(x - 70 * s, y), (x - 55 * s, y - 110 * s - bob), (x + 55 * s, y - 110 * s - bob), (x + 70 * s, y)], smooth=True), fill(col))
            if (k + row) % 3 == 0:
                a = math.sin(t * 6 + k) * 0.4
                c.drawLine(x + 40 * s, y - 100 * s - bob, x + 70 * s + a * 40, y - 230 * s - bob, stroke(col, 26 * s))


def ev_barco(c, W, H, t, dur):
    x = -300 + t * 120
    y = H * 0.55 + math.sin(t * 1.3) * 8
    toon(c, poly([(x - 260, y), (x + 260, y), (x + 200, y + 110), (x - 200, y + 110)]), "#5a3a24")
    for k, h in ((-90, 420), (90, 360)):
        c.drawLine(x + k, y, x + k, y - h, stroke(INK, 12))
        sail = poly([(x + k - 120, y - h + 40), (x + k + 120, y - h + 40), (x + k + 130 + math.sin(t * 2) * 10, y - 80), (x + k - 110, y - 80)], smooth=True)
        toon(c, sail, "#f2ead6", light=(-1, 0))
    c.drawPath(poly([(x - 90, y - 420), (x - 90 + 110, y - 405), (x - 90, y - 390)]), fill("#c0262d"))


def ev_canon(c, W, H, t, dur):
    for k, at in enumerate((0.4, 1.4, 2.4)):
        a = t - at
        if 0 <= a < 1.2:
            x = W * (0.25 + k * 0.25)
            c.drawCircle(x, H * 0.7, 140 * min(1, a * 6), fill("#ffe27a", max(0, 0.9 - a * 2)))
            for j in range(6):
                c.drawCircle(x + j * 30 * a * 3, H * 0.7 - j * 20 * a * 2, 60 + 90 * a, fill("#d9d4cc", max(0, 0.6 - a * 0.5)))


EVENTS = {"aviones": ev_aviones, "explosion": ev_explosion, "bombardeo": ev_bombardeo,
          "paracaidas": ev_paracaidas, "hundimiento": ev_hundimiento, "fuego": ev_fuego, "disparos": ev_disparos,
          "lluvia": ev_lluvia, "nieve": ev_nieve, "multitud": ev_multitud, "barco": ev_barco, "cañonazos": ev_canon}

# efectos de sonido que acompañan a cada suceso: (nombre, segundo)
EVENT_SFX = {"explosion": [("boom", 0.5)], "bombardeo": [("boom", 0.3), ("boom", 1.1), ("boom", 1.9)],
             "paracaidas": [("whoosh", 0.2)], "hundimiento": [("whoosh", 1.0), ("splash", 1.6)],
             "disparos": [("hit", 0.2), ("hit", 0.9), ("hit", 1.5)], "cañonazos": [("boom", 0.4), ("boom", 1.4), ("boom", 2.4)]}
EVENT_AMBIENCE = {"aviones": "avion", "fuego": "viento", "lluvia": "viento", "barco": "mar"}
