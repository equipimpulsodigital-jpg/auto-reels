"""Más escenarios: hielo polar, desierto, calle moderna, carretera de noche, hospital, juzgado, aula,
cementerio y caserón abandonado. Se añaden a LOCATIONS al final de locations.py."""
from __future__ import annotations

import math
import random

import skia

from . import scenes as S
from .draw import INK, blur, fill, linear, mix, oval, poly, radial, rrect, shade, stroke, toon
from .locations import FLOOR, Loc, big_window, floor, lamp_glow, night_tint, plant, skyline, street_lamp, wall


def _moon(c, x, y, r=70):
    c.drawCircle(x, y, r * 3.5, radial(fill("#dfe6ff"), (x, y), r * 3.5, ["#dfe6ff", "#dfe6ff"], [0.35, 0.0]))
    c.drawCircle(x, y, r, fill("#f2f4ff"))
    c.drawCircle(x - r * 0.3, y - r * 0.2, r * 0.18, fill("#d5dbef"))
    c.drawCircle(x + r * 0.25, y + r * 0.3, r * 0.12, fill("#d5dbef"))


def _fog(c, W, y, t, a=0.1, n=18):
    for k in range(n):
        x = (k * 150 + t * 30 * (1 + k % 3)) % (W + 400) - 200
        c.drawCircle(x, y + (k % 4) * 40, 180 + (k % 3) * 50, blur(fill("#dfe6ee", a), 40))


def _dead_tree(c, x, base, s, col="#1d1a22"):
    c.drawPath(poly([(x - 22 * s, base), (x + 22 * s, base), (x + 10 * s, base - 380 * s), (x - 10 * s, base - 380 * s)]), fill(col))
    for k, (dx, dy, ang) in enumerate(((0, -200, -0.9), (0, -260, 0.8), (0, -330, -0.5), (0, -350, 0.4))):
        x0, y0 = x + dx * s, base + dy * s
        x1, y1 = x0 + math.sin(ang) * 170 * s, y0 - math.cos(ang) * 150 * s
        c.drawLine(x0, y0, x1, y1, stroke(col, 16 * s))
        c.drawLine(x1, y1, x1 + math.sin(ang * 1.6) * 70 * s, y1 - 60 * s, stroke(col, 8 * s))


class Hielo(Loc):
    key, desc, ambience = "hielo", "hielo polar o glaciar: banquisa blanca con grietas, icebergs y cielo frío (Ártico, Antártida, expediciones)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.55
        S.sky(c, W, H, g.mood, hz, g.t, sun=g.mood != "tormenta")
        if g.mood == "noche":  # aurora boreal
            for k in range(4):
                p = skia.Path()
                p.moveTo(-50, H * (0.12 + k * 0.05))
                for j in range(7):
                    p.quadTo(j * W / 6 + W / 12, H * (0.08 + k * 0.05) + math.sin(g.t * 0.8 + j + k) * 60,
                             (j + 1) * W / 6, H * (0.12 + k * 0.05))
                c.drawPath(p, stroke(["#5cf2b0", "#7ad7ff", "#9cff9c", "#c58cff"][k], 46, 0.18))
        S.clouds(c, W, g.t, H * 0.06, H * 0.25, g.mood, n=3, seed=31, speed=6)
        rnd = random.Random(6)
        for k in range(5):  # icebergs al fondo
            x, w, h = rnd.uniform(-100, W), rnd.uniform(160, 340), rnd.uniform(90, 230)
            berg = poly([(x, hz + 10), (x + w * 0.2, hz - h * 0.7), (x + w * 0.45, hz - h), (x + w * 0.7, hz - h * 0.6), (x + w, hz + 10)])
            toon(c, berg, "#e8f4fb", outline=5, light=(-1, -0.3))
        ice = "#eef6fb" if g.mood != "noche" else "#9fb2cf"
        c.drawRect(skia.Rect.MakeLTRB(0, hz, W, H), linear(fill(ice), (0, hz), (0, H), [shade(ice, -0.12), ice]))
        for k in range(9):  # grietas
            x0 = rnd.uniform(0, W)
            y0 = rnd.uniform(hz + 60, H)
            p = skia.Path()
            p.moveTo(x0, y0)
            for j in range(4):
                p.lineTo(x0 + rnd.uniform(-90, 90) * (j + 1), y0 + rnd.uniform(-20, 20) * (j + 1))
            c.drawPath(p, stroke("#7fa7c4", 5))
        for k in range(30):  # nieve que levanta el viento
            x = (rnd.uniform(0, W) + g.t * 260) % W
            c.drawCircle(x, rnd.uniform(hz, H * 0.95), rnd.uniform(3, 7), fill("#ffffff", 0.7))
        night_tint(c, g, 0.15)


class Desierto(Loc):
    key, desc, ambience = "desierto", "desierto: dunas de arena, sol abrasador, rocas y cactus (expediciones, calor extremo)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.56
        S.sky(c, W, H, g.mood, hz, g.t)
        for layer, (col, amp, y) in enumerate((("#e8b86a", 60, hz), ("#d9a050", 90, hz + 160), ("#c98a3e", 120, hz + 400))):
            col = mix(col, "#2a2a4a", 0.5) if g.mood == "noche" else col
            p = skia.Path()
            p.moveTo(0, H)
            p.lineTo(0, y)
            for k in range(7):
                p.quadTo(k * W / 6 + W / 12, y - amp * (1 if (k + layer) % 2 else -0.3), (k + 1) * W / 6, y)
            p.lineTo(W, H)
            p.close()
            c.drawPath(p, fill(col))
            c.drawPath(p, stroke(shade(col, -0.3), 5))
        for x, s in ((W * 0.15, 1.0), (W * 0.86, 0.7)):  # cactus
            base = H * 0.86 if s == 1.0 else H * 0.74
            green = "#4f8a4a"
            toon(c, rrect(x - 30 * s, base - 300 * s, 60 * s, 300 * s, 30 * s), green)
            toon(c, rrect(x - 110 * s, base - 220 * s, 40 * s, 120 * s, 20 * s), green)
            toon(c, rrect(x - 110 * s, base - 120 * s, 100 * s, 36 * s, 18 * s), green)
            toon(c, rrect(x + 70 * s, base - 260 * s, 40 * s, 110 * s, 20 * s), green)
            toon(c, rrect(x + 10 * s, base - 170 * s, 100 * s, 36 * s, 18 * s), green)
        if g.mood in ("dia", "atardecer"):  # calima
            for k in range(6):
                y = hz + 40 + k * 18
                c.drawLine(0, y + math.sin(g.t * 3 + k) * 4, W, y + math.sin(g.t * 3 + k + 1) * 4, stroke("#fff3c4", 4, 0.12))


class CalleModerna(Loc):
    key, desc, ambience = "calle", "calle de una ciudad actual: tiendas con letreros, acera, semáforo y coches que pasan (vida diaria, quedar con alguien)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        night = g.mood == "noche"
        hz = H * 0.6
        S.sky(c, W, H, g.mood, hz, g.t, sun=False)
        skyline(c, -40, W + 40, hz - 200, night, seed=12, s=1.3)
        cols = ["#c96f53", "#e2c290", "#7d9bb8", "#b76e8f"]
        signs = ["#ffcf3a", "#3ad1ff", "#ff5c7a", "#7dff8a"]
        for k in range(4):  # fachadas con escaparates
            x = k * W / 4
            toon(c, poly([(x, hz + 30), (x + W / 4, hz + 30), (x + W / 4, hz - 380), (x, hz - 380)]), cols[k], outline=5)
            c.drawRect(skia.Rect.MakeXYWH(x + 26, hz - 200, W / 4 - 52, 200), fill("#ffe9b0" if night else "#bcd7e6", 0.9))
            c.drawRect(skia.Rect.MakeXYWH(x + 26, hz - 200, W / 4 - 52, 200), stroke(INK, 5))
            glow = 0.9 if not night else 0.75 + 0.25 * math.sin(g.t * 4 + k)
            toon(c, rrect(x + 30, hz - 290, W / 4 - 60, 60, 12), signs[k] if night else shade(signs[k], -0.15), outline=4)
            if night:
                lamp_glow(c, x + W / 8, hz - 260, 160, signs[k], 0.3 * glow)
            for r in range(2):
                c.drawRect(skia.Rect.MakeXYWH(x + 40 + r * (W / 8), hz - 360, 60, 50), fill("#2c3442" if not night else "#ffd77a"))
        c.drawRect(skia.Rect.MakeLTRB(0, hz + 30, W, hz + 110), fill("#b7b2aa"))  # acera
        c.drawLine(0, hz + 110, W, hz + 110, stroke(INK, 6))
        c.drawRect(skia.Rect.MakeLTRB(0, hz + 110, W, H), fill("#4a4d55"))  # calzada
        for k in range(6):
            x = (k * 260 - g.t * 200) % (W + 260) - 130
            c.drawRect(skia.Rect.MakeXYWH(x, H * 0.8, 140, 18), fill("#f2f2f2"))
        cx = (g.t * 420) % (W + 900) - 450  # coche que pasa
        toon(c, rrect(cx - 220, hz + 150, 440, 120, 40), "#c0392b")
        toon(c, poly([(cx - 130, hz + 150), (cx - 80, hz + 70), (cx + 90, hz + 70), (cx + 150, hz + 150)]), "#c0392b")
        c.drawPath(poly([(cx - 105, hz + 145), (cx - 70, hz + 85), (cx + 80, hz + 85), (cx + 120, hz + 145)]), fill("#bfe3f5"))
        for wx in (cx - 130, cx + 130):
            toon(c, oval(wx, hz + 270, 46, 46), "#1d1f24")
            c.drawCircle(wx, hz + 270, 18, fill("#b0b5bd"))
        if night:
            lamp_glow(c, cx + 220, hz + 210, 200, "#fff3c4", 0.5)
        x = W * 0.9  # semáforo
        c.drawLine(x, hz + 100, x, hz - 260, stroke("#2f2f33", 18))
        toon(c, rrect(x - 36, hz - 400, 72, 170, 16), "#2f2f33")
        on = int(g.t / 2) % 2
        c.drawCircle(x, hz - 360, 22, fill("#ff4040" if on == 0 else "#5a2020"))
        c.drawCircle(x, hz - 300, 22, fill("#40ff70" if on == 1 else "#1f4a2a"))
        night_tint(c, g, 0.12)


class Carretera(Loc):
    key, desc, ambience = "carretera", "carretera solitaria que se pierde en el horizonte, con postes y quitamiedos (viajes, desapariciones, huidas)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.52
        S.sky(c, W, H, g.mood, hz, g.t, sun=g.mood == "atardecer")
        if g.mood == "noche":
            _moon(c, W * 0.78, H * 0.14)
        S.mountains(c, W, hz + 4, S.MOODS[g.mood][4], seed=19, height=120)
        ground = "#6f7a4a" if g.mood != "noche" else "#1f2630"
        c.drawRect(skia.Rect.MakeLTRB(0, hz, W, H), fill(ground))
        vx = W * 0.5
        road = poly([(vx - 20, hz), (vx + 20, hz), (W * 0.95, H), (W * 0.05, H)])
        c.drawPath(road, fill("#3d3f45"))
        c.drawPath(road, stroke(INK, 5))
        for k in range(8):  # rayas que se acercan
            ph = ((k / 8) + g.t * 0.35) % 1.0
            y0, y1 = hz + (H - hz) * ph ** 2, hz + (H - hz) * min(1.0, (ph + 0.05) ** 2)
            w0, w1 = 3 + 30 * ph ** 2, 3 + 30 * min(1.0, (ph + 0.05)) ** 2
            c.drawPath(poly([(vx - w0 / 2, y0), (vx + w0 / 2, y0), (vx + w1 / 2, y1), (vx - w1 / 2, y1)]), fill("#f2e9a0"))
        for k in range(6):  # postes
            ph = ((k / 6) + g.t * 0.35) % 1.0
            y = hz + (H - hz) * ph ** 2
            x = vx + (W * 0.55) * ph ** 2 + 30
            h = 20 + 380 * ph ** 2
            c.drawLine(x, y, x, y - h, stroke("#5a4632", 4 + 14 * ph ** 2))
        if g.mood == "noche":
            c.drawPath(poly([(vx, hz + 10), (W * 0.2, H), (W * 0.8, H)]), fill("#fff3c4", 0.07))


class Hospital(Loc):
    key, desc, ambience = "hospital", "habitación de hospital: cama, monitor del corazón que pita, gotero y cortina (enfermedad, médicos, experimentos)", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#cfe3dc")
        c.drawRect(skia.Rect.MakeLTRB(0, fy - 140, W, fy), fill("#b5d1c7"))
        big_window(c, W * 0.06, H * 0.1, W * 0.3, H * 0.22, g.mood == "noche", g.t, seed=5)
        # monitor con electrocardiograma
        mx, my = W * 0.62, H * 0.14
        toon(c, rrect(mx, my, 300, 210, 18), "#2b2f36")
        c.drawRect(skia.Rect.MakeXYWH(mx + 18, my + 18, 264, 150), fill("#0b1a14"))
        p = skia.Path()
        for i in range(60):
            x = mx + 20 + i * 4.4
            ph = (i / 60 * 2 + g.t * 1.2) % 1.0
            y = my + 95 - (70 if 0.48 < ph < 0.52 else -25 if 0.52 < ph < 0.55 else 0)
            p.moveTo(x, y) if i == 0 else p.lineTo(x, y)
        c.drawPath(p, stroke("#4dff88", 5))
        c.drawCircle(mx + 260, my + 190, 8, fill("#ff4040", 0.5 + 0.5 * math.sin(g.t * 7)))
        # gotero
        gx = W * 0.9
        c.drawLine(gx, fy + 40, gx, H * 0.14, stroke("#9aa3ab", 9))
        toon(c, rrect(gx - 40, H * 0.15, 80, 120, 20), "#e8f4f8", outline=4)
        c.drawRect(skia.Rect.MakeXYWH(gx - 32, H * 0.2, 64, 60), fill("#bfe6ff", 0.8))
        # cortina
        for k in range(6):
            x = W * 0.38 + k * 40
            toon(c, rrect(x, 40, 44, fy - 80, 20), "#8fc1d4", outline=3)
        floor(c, W, H, fy, "#d9dee0", "ajedrez")
        y = fy + 120  # cama al fondo, junto a la pared
        toon(c, rrect(W * 0.52, y - 220, 40, 300, 12), "#9aa3ab")
        toon(c, rrect(W * 0.54, y - 60, W * 0.44, 120, 20), "#ffffff")
        toon(c, rrect(W * 0.54, y - 20, W * 0.44, 90, 20), "#8fb4e0")
        toon(c, rrect(W * 0.56, y - 110, 160, 70, 30), "#ffffff")


class Tribunal(Loc):
    key, desc, ambience = "tribunal", "sala de un juzgado: estrado del juez, paneles de madera, balanza de la justicia y banquillo (juicios, sentencias)", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#8a5a3a", "madera")
        # balanza
        bx, by = W * 0.5, H * 0.13
        c.drawLine(bx, by, bx, by + 170, stroke("#d4af37", 10))
        tilt = math.sin(g.t * 1.2) * 8
        c.drawLine(bx - 130, by + 30 + tilt, bx + 130, by + 30 - tilt, stroke("#d4af37", 10))
        for sx, dy in ((-130, tilt), (130, -tilt)):
            c.drawLine(bx + sx, by + 30 + dy, bx + sx - 40, by + 110 + dy, stroke("#d4af37", 4))
            c.drawLine(bx + sx, by + 30 + dy, bx + sx + 40, by + 110 + dy, stroke("#d4af37", 4))
            toon(c, poly([(bx + sx - 60, by + 110 + dy), (bx + sx + 60, by + 110 + dy), (bx + sx, by + 150 + dy)]), "#d4af37", outline=4)
        # estrado
        toon(c, rrect(W * 0.18, fy - 360, W * 0.64, 360, 10), "#5a3a24", light=(0, -1))
        for k in range(4):
            c.drawRect(skia.Rect.MakeXYWH(W * 0.22 + k * W * 0.15, fy - 320, W * 0.11, 260), stroke(shade("#5a3a24", -0.35), 6))
        toon(c, rrect(W * 0.46, fy - 420, 90, 60, 10), "#3a2618")  # mazo
        c.drawLine(W * 0.46 + 45, fy - 420, W * 0.46 + 110, fy - 470, stroke("#3a2618", 14))
        floor(c, W, H, fy, "#6b4a2f", "madera")
    def front(self, c, g, close):
        W, H = g.W, g.H
        y = H * (0.9 if close else 0.84)
        c.drawRect(skia.Rect.MakeLTRB(-20, y, W + 20, y + 26), fill("#5a3a24"))
        c.drawLine(-20, y, W + 20, y, stroke(INK, 6))
        for k in range(14):
            x = k * W / 13
            toon(c, rrect(x - 12, y + 26, 24, H - y, 8), "#6b4a2f", outline=4)


class Aula(Loc):
    key, desc, ambience = "aula", "aula de colegio o universidad: pizarra verde con tiza, pupitres y reloj (clases, exámenes, experimentos de psicología)", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#e8dcc0")
        c.drawRect(skia.Rect.MakeLTRB(0, fy - 150, W, fy), fill("#a8c4a0"))
        toon(c, rrect(W * 0.08, H * 0.1, W * 0.62, H * 0.24, 10), "#2f5a43")
        c.drawRect(skia.Rect.MakeXYWH(W * 0.08, H * 0.1, W * 0.62, H * 0.24), stroke("#8a6a4a", 18))
        rnd = random.Random(7)
        for k in range(4):
            x0, y = W * 0.12, H * 0.14 + k * 90
            p = skia.Path()
            p.moveTo(x0, y)
            for j in range(int(rnd.uniform(8, 16))):
                p.quadTo(x0 + j * 26 + 13, y + (-10 if j % 2 else 10), x0 + (j + 1) * 26, y)
            c.drawPath(p, stroke("#f2f2ea", 6))
        cx, cy = W * 0.84, H * 0.15  # reloj
        toon(c, oval(cx, cy, 80, 80), "#ffffff")
        a = g.t * 0.6
        c.drawLine(cx, cy, cx + math.sin(a) * 60, cy - math.cos(a) * 60, stroke(INK, 6))
        c.drawLine(cx, cy, cx + 40, cy, stroke(INK, 9))
        floor(c, W, H, fy, "#b08a5e", "madera")
        for k in range(3):  # pupitres al fondo del aula
            x = W * (0.05 + k * 0.33)
            y = fy + 90
            toon(c, rrect(x, y - 20, 260, 30, 6), "#c9a77c")
            c.drawLine(x + 30, y + 10, x + 30, y + 150, stroke("#4a4d55", 10))
            c.drawLine(x + 230, y + 10, x + 230, y + 150, stroke("#4a4d55", 10))


class Cementerio(Loc):
    key, desc, ambience = "cementerio", "cementerio antiguo: lápidas, cruces, verja de hierro, árbol seco y niebla (muertes, entierros, misterios)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.6
        S.sky(c, W, H, g.mood, hz, g.t, sun=False)
        if g.mood in ("noche", "tormenta"):
            _moon(c, W * 0.25, H * 0.15, 80)
        S.mountains(c, W, hz, shade(S.MOODS[g.mood][4], -0.2), seed=23, height=90)
        grass = "#3c4a34" if g.mood == "dia" else "#1f2a22"
        c.drawRect(skia.Rect.MakeLTRB(0, hz, W, H), fill(grass))
        _dead_tree(c, W * 0.82, hz + 80, 1.6)
        for k in range(16):  # verja
            x = k * W / 15
            c.drawLine(x, hz + 20, x, hz - 140, stroke("#1d1a22", 8))
            c.drawPath(poly([(x - 10, hz - 140), (x + 10, hz - 140), (x, hz - 170)]), fill("#1d1a22"))
        c.drawLine(0, hz - 100, W, hz - 100, stroke("#1d1a22", 8))
        rnd = random.Random(9)
        stone = "#9a9aa3" if g.mood == "dia" else "#6a6f80"
        for row, (y, s) in enumerate(((hz + 120, 0.6), (hz + 330, 0.85), (H * 0.94, 1.1))):
            for k in range(4 - row):
                x = W * (0.12 + k * 0.28 + row * 0.08) + rnd.uniform(-30, 30)
                if (k + row) % 3 == 1:  # cruz
                    c.drawRect(skia.Rect.MakeXYWH(x - 16 * s, y - 230 * s, 32 * s, 230 * s), fill(stone))
                    c.drawRect(skia.Rect.MakeXYWH(x - 70 * s, y - 180 * s, 140 * s, 30 * s), fill(stone))
                    c.drawRect(skia.Rect.MakeXYWH(x - 16 * s, y - 230 * s, 32 * s, 230 * s), stroke(INK, 4))
                else:
                    tomb = rrect(x - 80 * s, y - 200 * s, 160 * s, 220 * s, 70 * s)
                    toon(c, tomb, stone, light=(-1, -0.5))
                    c.drawLine(x - 40 * s, y - 120 * s, x + 40 * s, y - 120 * s, stroke(shade(stone, -0.4), 6 * s))
                    c.drawLine(x - 30 * s, y - 90 * s, x + 30 * s, y - 90 * s, stroke(shade(stone, -0.4), 6 * s))
        _fog(c, W, H * 0.8, g.t, 0.09)


class Caseron(Loc):
    key, desc, ambience = "caseron", "caserón o mansión abandonada en una colina, con una sola ventana encendida y árboles secos (casas encantadas, crímenes)", "viento"
    def back(self, c, g):
        W, H = g.W, g.H
        hz = H * 0.62
        mood = g.mood if g.mood != "dia" else "atardecer"
        S.sky(c, W, H, mood, hz, g.t, sun=False)
        _moon(c, W * 0.8, H * 0.12, 75)
        S.clouds(c, W, g.t, H * 0.05, H * 0.2, mood, n=3, seed=41, speed=10)
        hill = poly([(-50, H), (-50, hz), (W * 0.3, hz - 150), (W * 0.7, hz - 160), (W + 50, hz), (W + 50, H)], smooth=True)
        c.drawPath(hill, fill("#1d2420"))
        dark, x0, base = "#2a2433", W * 0.18, hz - 120
        toon(c, poly([(x0, base), (x0 + W * 0.64, base), (x0 + W * 0.64, base - 420), (x0, base - 420)]), dark, outline=6)
        toon(c, poly([(x0 - 40, base - 420), (x0 + W * 0.68, base - 420), (x0 + W * 0.32, base - 680)]), "#1d1826", outline=6)
        toon(c, poly([(x0 + W * 0.48, base - 520), (x0 + W * 0.56, base - 520), (x0 + W * 0.56, base - 640), (x0 + W * 0.48, base - 640)]), dark)
        for r in range(2):
            for k in range(4):
                wx, wy = x0 + 50 + k * W * 0.15, base - 360 + r * 190
                lit = (r, k) == (0, 2)
                flick = 0.75 + 0.25 * math.sin(g.t * 11) * math.sin(g.t * 3.7)
                c.drawRect(skia.Rect.MakeXYWH(wx, wy, 90, 130), fill("#ffcf6b" if lit else "#11101a", flick if lit else 1))
                c.drawRect(skia.Rect.MakeXYWH(wx, wy, 90, 130), stroke(INK, 5))
                c.drawLine(wx + 45, wy, wx + 45, wy + 130, stroke(INK, 4))
                if lit:
                    lamp_glow(c, wx + 45, wy + 65, 220, "#ffcf6b", 0.3 * flick)
                elif (r + k) % 3 == 0:  # tablones
                    c.drawLine(wx - 10, wy + 20, wx + 100, wy + 100, stroke("#4a3a2a", 14))
        toon(c, poly([(x0 + W * 0.28, base), (x0 + W * 0.36, base), (x0 + W * 0.36, base - 160), (x0 + W * 0.28, base - 160)]), "#3a2618")
        _dead_tree(c, W * 0.08, H * 0.9, 1.8)
        _dead_tree(c, W * 0.95, H * 0.84, 1.3)
        c.drawRect(skia.Rect.MakeLTRB(0, H * 0.86, W, H), fill("#141a16"))
        _fog(c, W, H * 0.84, g.t, 0.08)


class Hemiciclo(Loc):
    key, desc, ambience = "hemiciclo", "el Congreso: hemiciclo con escaños rojos en gradas, tribuna de oradores con micrófono y bandera de España (debates, votaciones, sesión de control)", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        wall(c, W, H, fy, "#7a5a3c", "madera")
        # cúpula / vidriera y lámparas
        c.drawPath(oval(W * 0.5, H * 0.02, W * 0.42, H * 0.1), fill("#d9c48a", 0.55))
        for k in range(7):
            x = W * (0.2 + k * 0.1)
            c.drawLine(W * 0.5, -H * 0.05, x, H * 0.1, stroke("#8a6a3a", 4, 0.6))
        for x in (W * 0.2, W * 0.8):
            lamp_glow(c, x, H * 0.14, 160, "#ffe2a0", 0.35)
            c.drawCircle(x, H * 0.14, 26, fill("#f0d58a"))
        # gradas de escaños rojos (en arco)
        for row in range(5):
            y = H * 0.2 + row * 62
            n = 9 + row * 2
            for k in range(n):
                f = (k + 0.5) / n
                x = W * (0.04 + 0.92 * f)
                dy = abs(f - 0.5) * -90 * (1 - row * 0.12)
                toon(c, rrect(x - 30, y + dy, 60, 46, 12), "#a3262a", outline=3)
                c.drawRect(skia.Rect.MakeXYWH(x - 34, y + dy + 40, 68, 14), fill("#5a3a24"))
                if (k * 7 + row * 3) % 4 == 0:  # diputados lejanos
                    c.drawCircle(x, y + dy - 10, 13, fill(mix("#c9926b", "#7a5a3c", 0.25)))
                    c.drawPath(rrect(x - 17, y + dy + 2, 34, 30, 10), fill(mix("#2a2f3a", "#7a5a3c", 0.2)))
        # bandera de España al fondo
        bx, by = W * 0.86, H * 0.2
        c.drawLine(bx, by, bx, fy - 10, stroke("#d4af37", 8))
        wav = math.sin(g.t * 2) * 6
        for i, col in enumerate(("#c60b1e", "#ffc400", "#ffc400", "#c60b1e")):
            c.drawPath(poly([(bx, by + i * 30), (bx - 150, by + i * 30 + wav), (bx - 150, by + (i + 1) * 30 + wav), (bx, by + (i + 1) * 30)]), fill(col))
        floor(c, W, H, fy, "#8a3a2a", "madera")
    def front(self, c, g, close):
        W, H = g.W, g.H
        y = H * (0.9 if close else 0.82)
        # tribuna de oradores con micrófono
        toon(c, poly([(W * 0.36, y), (W * 0.64, y), (W * 0.61, H + 20), (W * 0.39, H + 20)]), "#6b4a2f", light=(0, -1))
        c.drawRect(skia.Rect.MakeXYWH(W * 0.36, y - 12, W * 0.28, 18), fill("#4a3220"))
        c.drawLine(W * 0.5, y - 12, W * 0.47, y - 110, stroke("#222222", 6))
        c.drawPath(oval(W * 0.47, y - 118, 12, 16), fill("#333333"))


class PlatoDebate(Loc):
    key, desc, ambience = "plato_debate", "plató de televisión de un debate electoral: fondo azul oscuro con pantallas y luces, atriles enfrentados y focos (debates, entrevistas, tertulias)", ""
    interior = True
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        c.drawRect(skia.Rect.MakeWH(W, fy), linear(fill("#0f1d3a"), (0, 0), (0, fy), ["#070d1c", "#14285a"]))
        # pantallas de vídeo con barras de luz
        for k in range(3):
            x = W * (0.08 + k * 0.31)
            c.drawPath(rrect(x, H * 0.12, W * 0.24, H * 0.2, 10), fill("#1d3f8a"))
            for j in range(6):
                a = 0.25 + 0.2 * math.sin(g.t * 2 + j + k)
                c.drawRect(skia.Rect.MakeXYWH(x + 14, H * 0.12 + 16 + j * 34, W * 0.24 - 28, 14), fill("#5aa0ff", a))
        # rótulo «DEBATE» y cuenta atrás
        c.drawPath(rrect(W * 0.3, H * 0.36, W * 0.4, 70, 14), fill("#c0392b"))
        for k in range(12):  # tiras de led en el suelo del decorado
            x = k * W / 11
            c.drawLine(x, fy - 6, W * 0.5 + (x - W * 0.5) * 1.6, H, stroke("#5aa0ff", 3, 0.25))
        for x in (W * 0.15, W * 0.85):  # focos
            c.drawPath(poly([(x - 20, 0), (x + 20, 0), (x + 220 * (1 if x < W / 2 else -1) + 120, fy), (x + 220 * (1 if x < W / 2 else -1) - 120, fy)]), fill("#cfe0ff", 0.06))
        floor(c, W, H, fy, "#101a30", "madera")
    def front(self, c, g, close):
        W, H = g.W, g.H
        y = H * (0.9 if close else 0.8)
        for x in (W * 0.16, W * 0.84):  # atriles a los lados
            toon(c, poly([(x - 110, y), (x + 110, y), (x + 80, H + 20), (x - 80, H + 20)]), "#e8ecf4", light=(0, -1))
            c.drawRect(skia.Rect.MakeXYWH(x - 110, y + 40, 220, 18), fill("#c0392b"))
            c.drawLine(x, y, x - 20, y - 90, stroke("#222222", 5))
            c.drawPath(oval(x - 20, y - 96, 10, 13), fill("#333333"))


class Mitin(Loc):
    key, desc, ambience = "mitin", "mitin de campaña: escenario con atril y pantalla gigante, focos y un público con banderas y pancartas (actos electorales, discursos)", ""
    def back(self, c, g):
        W, H = g.W, g.H
        fy = H * FLOOR
        c.drawRect(skia.Rect.MakeWH(W, fy), linear(fill("#1a1430"), (0, 0), (0, fy), ["#0a0814", "#2a1f4a"]))
        # pantalla gigante y focos de colores
        c.drawPath(rrect(W * 0.12, H * 0.08, W * 0.76, H * 0.24, 12), fill("#2b4c8f"))
        c.drawPath(rrect(W * 0.14, H * 0.09, W * 0.72, H * 0.22, 10), linear(fill("#3d6fd1"), (0, H * 0.09), (0, H * 0.31), ["#4f86f0", "#24448a"]))
        for k, col in enumerate(("#ff5a5a", "#ffd23f", "#5ab0ff", "#7dff9a")):
            x = W * (0.1 + k * 0.27)
            a = 0.08 + 0.05 * math.sin(g.t * 3 + k)
            c.drawPath(poly([(x - 15, 0), (x + 15, 0), (x + 140, fy), (x - 140, fy)]), fill(col, a))
        # escenario
        c.drawRect(skia.Rect.MakeLTRB(0, fy - 40, W, fy), fill("#2a2a3a"))
        floor(c, W, H, fy, "#22222e", "madera")
        # público con banderas genéricas (sin partidos)
        rnd = random.Random(29)
        for row in range(2):
            for k in range(14):
                x = (k + 0.5) * W / 14 + rnd.uniform(-20, 20)
                y = H * (0.78 + row * 0.08)
                bob = math.sin(g.t * 4 + k + row) * 6
                c.drawCircle(x, y - 60 + bob, 26, fill("#141020"))
                c.drawPath(rrect(x - 36, y - 38 + bob, 72, 90, 22), fill("#141020"))
                if rnd.random() < 0.3:
                    col = rnd.choice(["#c60b1e", "#ffc400", "#ffffff", "#5ab0ff", "#7dd37d"])
                    hx = x + 30
                    c.drawLine(hx, y - 50 + bob, hx + 10, y - 170 + bob, stroke("#aaaaaa", 4))
                    w = math.sin(g.t * 5 + k) * 8
                    c.drawPath(poly([(hx + 10, y - 170 + bob), (hx + 90, y - 165 + bob + w), (hx + 85, y - 120 + bob + w), (hx + 8, y - 125 + bob)]), fill(col, 0.9))
    def front(self, c, g, close):
        W, H = g.W, g.H
        y = H * (0.9 if close else 0.82)
        toon(c, poly([(W * 0.4, y), (W * 0.6, y), (W * 0.58, H + 20), (W * 0.42, H + 20)]), "#e8ecf4", light=(0, -1))
        c.drawLine(W * 0.5, y, W * 0.48, y - 90, stroke("#222222", 5))
        c.drawPath(oval(W * 0.48, y - 96, 10, 13), fill("#333333"))



EXTRA_LOCATIONS = {cls.key: cls() for cls in (Hielo, Desierto, CalleModerna, Carretera, Hospital, Tribunal, Aula,
                                               Cementerio, Caseron, Hemiciclo, PlatoDebate, Mitin)}
