"""Más objetos de primer plano y sucesos animados. Se añaden a PROPS/EVENTS al final de props.py."""
from __future__ import annotations

import math
import random

import skia

from .draw import INK, blur, fill, linear, oval, poly, radial, rrect, shade, stroke, toon


# ---------------- objetos (centrados en (0,0), ~600 px) ----------------

def globo(c, t):
    """Globo aerostático con barquilla."""
    sway = math.sin(t * 1.2) * 4
    c.save()
    c.rotate(sway)
    env = poly([(0, -330), (190, -250), (230, -80), (150, 70), (60, 130), (-60, 130), (-150, 70), (-230, -80), (-190, -250)], smooth=True)
    toon(c, env, "#d9c38a", light=(-1, -0.6))
    c.save()
    c.clipPath(env, doAntiAlias=True)
    for k in range(-3, 4):
        c.drawLine(k * 70, -340, k * 40, 140, stroke("#8a6a3a", 5))
    for y in (-180, -40):
        c.drawLine(-260, y, 260, y + 20, stroke("#8a6a3a", 4))
    c.restore()
    for x0, x1 in ((-60, -45), (60, 45), (-20, -15), (20, 15)):
        c.drawLine(x0, 130, x1, 230, stroke(INK, 4))
    toon(c, rrect(-60, 220, 120, 80, 10), "#8a5a2a")
    for k in range(4):
        c.drawLine(-60 + k * 40, 220, -60 + k * 40, 300, stroke(shade("#8a5a2a", -0.35), 4))
    c.restore()


def camara(c, t):
    """Cámara de fotos antigua; dispara un flash de vez en cuando."""
    toon(c, rrect(-250, -140, 500, 300, 30), "#2b2b2f", light=(-1, -1))
    toon(c, rrect(-170, -200, 140, 70, 14), "#2b2b2f")
    c.drawRect(skia.Rect.MakeXYWH(-250, -40, 500, 90), fill("#5a3a24"))
    toon(c, oval(30, 10, 120, 120), "#1d1d22")
    c.drawCircle(30, 10, 80, linear(fill("#3a5a8a"), (-50, -70), (110, 90), ["#6a8ac0", "#0d1a2e"]))
    c.drawCircle(5, -20, 22, fill("#ffffff", 0.6))
    toon(c, rrect(150, -120, 70, 50, 10), "#d9dde2", outline=4)
    if (t % 2.4) < 0.12:
        c.drawCircle(185, -95, 260, radial(fill("#ffffff"), (185, -95), 260, ["#ffffff", "#ffffff"], [0.9, 0.0]))


def foto(c, t):
    """Fotografía antigua en blanco y negro con siluetas (pruebas, recuerdos, desaparecidos)."""
    c.rotate(-4)
    toon(c, rrect(-240, -300, 480, 560, 6), "#f4efe2", light=(-1, -1))
    c.drawRect(skia.Rect.MakeXYWH(-200, -260, 400, 400), linear(fill("#a8a29a"), (0, -260), (0, 140), ["#c9c3b8", "#6e6a64"]))
    for x, h in ((-90, 1.0), (0, 1.1), (90, 0.95)):
        c.drawCircle(x, 10 - 60 * h, 34, fill("#3a3632"))
        c.drawPath(poly([(x - 60, 140), (x - 45, 40 - 30 * h), (x + 45, 40 - 30 * h), (x + 60, 140)], smooth=True), fill("#3a3632"))
    c.drawRect(skia.Rect.MakeXYWH(-200, -260, 400, 400), stroke(INK, 5))
    c.drawLine(-160, 200, 120, 200, stroke("#5a4a3a", 5))  # dedicatoria
    toon(c, rrect(-60, -330, 120, 50, 6), "#e8d9a0", outline=3)  # cinta adhesiva


def telefono(c, t):
    """Teléfono antiguo de disco que suena (el auricular tiembla)."""
    ring = (t % 1.6) < 0.8
    shake = math.sin(t * 60) * 6 if ring else 0
    toon(c, poly([(-230, 200), (230, 200), (170, -60), (-170, -60)], smooth=False), "#1f1f24", light=(-1, -1))
    toon(c, oval(0, 60, 120, 120), "#e9e4d8")
    for k in range(10):
        a = k * math.tau / 12 - 1.3
        c.drawCircle(math.cos(a) * 85, 60 + math.sin(a) * 85, 18, fill("#1f1f24"))
    c.save()
    c.translate(shake, -abs(shake))
    toon(c, rrect(-260, -170, 520, 80, 40), "#1f1f24")
    toon(c, oval(-210, -110, 70, 50), "#1f1f24")
    toon(c, oval(210, -110, 70, 50), "#1f1f24")
    c.restore()
    if ring:
        for k in range(3):
            r = 280 + k * 40
            c.drawArc(skia.Rect.MakeLTRB(-r, -r - 100, r, r - 100), -150, 40, False, stroke(INK, 7))
            c.drawArc(skia.Rect.MakeLTRB(-r, -r - 100, r, r - 100), -30, 40, False, stroke(INK, 7))


def calavera(c, t):
    toon(c, poly([(-200, -40), (-190, -200), (-90, -290), (90, -290), (190, -200), (200, -40), (130, 60), (110, 160),
                  (-110, 160), (-130, 60)], smooth=True), "#efe9da", light=(-1, -1))
    glow = 0.5 + 0.5 * math.sin(t * 3)
    for sx in (-80, 80):
        c.drawPath(oval(sx, -60, 62, 70), fill("#1d1a22"))
        c.drawCircle(sx, -55, 14, fill("#ff4040", 0.25 + 0.4 * glow))
    c.drawPath(poly([(0, 10), (30, 70), (-30, 70)]), fill("#1d1a22"))
    for k in range(6):
        x = -100 + k * 40
        c.drawRect(skia.Rect.MakeXYWH(x, 110, 30, 50), fill("#ffffff"))
        c.drawRect(skia.Rect.MakeXYWH(x, 110, 30, 50), stroke(INK, 4))


def lupa(c, t):
    """Lupa que se mueve sobre un papel con una huella dactilar (investigar, pistas)."""
    toon(c, rrect(-260, -200, 520, 420, 8), "#f3ead2", light=(-1, -1))
    for k in range(9):  # huella
        c.drawPath(oval(-40, 20, 30 + k * 12, 40 + k * 15), stroke("#8a6a5a", 4))
    mx, my = math.sin(t * 1.3) * 90, math.cos(t * 1.1) * 50
    c.drawLine(mx + 110, my + 110, mx + 260, my + 260, stroke("#5a3a24", 44))
    c.drawLine(mx + 110, my + 110, mx + 260, my + 260, stroke(INK, 6))
    c.drawCircle(mx, my, 150, fill("#cfe8ff", 0.35))
    c.drawCircle(mx, my, 150, stroke("#2b2f36", 26))
    c.drawCircle(mx - 50, my - 50, 30, fill("#ffffff", 0.5))


def libro(c, t):
    """Libro abierto con las páginas pasando."""
    toon(c, poly([(-300, -180), (0, -150), (300, -180), (300, 200), (0, 230), (-300, 200)]), "#7a2a2a")
    toon(c, poly([(-280, -170), (0, -140), (0, 210), (-280, 180)]), "#f6efdc", outline=5)
    toon(c, poly([(280, -170), (0, -140), (0, 210), (280, 180)]), "#f6efdc", outline=5)
    for side in (-1, 1):
        for r in range(7):
            y = -100 + r * 40
            c.drawLine(side * 40, y + 6, side * 240, y, stroke("#7a6a5a", 4))
    ph = (t * 0.8) % 1.0  # página que pasa
    x = 260 - 520 * ph
    c.drawPath(poly([(0, -140), (x, -170 + 40 * math.sin(ph * math.pi)), (x, 180 - 40 * math.sin(ph * math.pi)), (0, 210)]),
               fill("#fffaf0", 0.95))
    c.drawPath(poly([(0, -140), (x, -170 + 40 * math.sin(ph * math.pi)), (x, 180 - 40 * math.sin(ph * math.pi)), (0, 210)]),
               stroke(INK, 4))


def billetes(c, t):
    """Fajo de billetes con algunos que vuelan (dinero, sobornos, rescates)."""
    for k in range(5):
        toon(c, rrect(-250, 60 - k * 34, 500, 220, 10), "#7fb069", outline=5)
        c.drawPath(oval(0, 170 - k * 34, 60, 60), stroke("#4a7a3a", 6))
    c.drawRect(skia.Rect.MakeXYWH(-40, -80, 80, 300), fill("#e9dcb8"))
    for k in range(3):
        ph = (t * 0.6 + k / 3) % 1.0
        x, y = -200 + k * 200 + math.sin(ph * 6) * 40, -100 - ph * 300
        c.save()
        c.translate(x, y)
        c.rotate(math.sin(ph * 8 + k) * 40)
        toon(c, rrect(-80, -40, 160, 80, 6), "#8fc079", outline=4)
        c.restore()


def pastillas(c, t):
    """Bote de pastillas volcado (medicamentos, venenos lentos, ansiedad)."""
    c.rotate(-18)
    toon(c, rrect(-120, -260, 240, 380, 30), "#f0a43a", light=(-1, -0.5))
    c.drawRect(skia.Rect.MakeXYWH(-120, -140, 240, 150), fill("#ffffff"))
    for k in range(3):
        c.drawLine(-90, -110 + k * 40, 90, -110 + k * 40, stroke("#7a7a7a", 6))
    toon(c, rrect(-135, -320, 270, 80, 20), "#ffffff")
    c.rotate(18)
    for k, (x, y) in enumerate(((200, 180), (260, 120), (150, 240), (300, 220), (220, 280))):
        c.save()
        c.translate(x, y + math.sin(t * 2 + k) * 4)
        c.rotate(k * 37)
        toon(c, rrect(-34, -16, 68, 32, 16), "#ffffff", outline=4)
        c.drawRect(skia.Rect.MakeXYWH(0, -16, 34, 32), fill("#e74c3c"))
        c.restore()


def vela(c, t):
    """Vela encendida que parpadea en la oscuridad."""
    c.drawCircle(0, -240, 340, radial(fill("#ffcf7a"), (0, -240), 340, ["#ffcf7a", "#ffcf7a"], [0.35, 0.0]))
    toon(c, rrect(-70, -150, 140, 330, 14), "#f3ead2", light=(-1, 0))
    c.drawPath(poly([(-70, -150), (70, -150), (70, -110), (40, -80), (20, -130), (-30, -90), (-70, -120)]), fill("#fffaf0"))
    c.drawLine(0, -150, 0, -185, stroke(INK, 6))
    fl = 1 + 0.12 * math.sin(t * 13) + 0.08 * math.sin(t * 7.3)
    c.drawPath(poly([(0, -330 * fl), (46, -215), (0, -175), (-46, -215)], smooth=True), fill("#ffb347"))
    c.drawPath(poly([(0, -270 * fl), (22, -205), (0, -185), (-22, -205)], smooth=True), fill("#fff6c9"))
    toon(c, oval(0, 190, 170, 34), "#c9a227")


def portatil(c, t):
    """Portátil abierto con una pantalla que cambia (redes, trabajo, búsquedas)."""
    toon(c, poly([(-300, 120), (300, 120), (340, 200), (-340, 200)]), "#b0b5bd")
    toon(c, rrect(-260, -240, 520, 360, 20), "#2b2f36")
    c.drawRect(skia.Rect.MakeXYWH(-235, -215, 470, 310), fill("#eef3f8"))
    c.drawRect(skia.Rect.MakeXYWH(-235, -215, 470, 50), fill("#3a7bd5"))
    for k in range(4):
        w = 180 + (k * 71 + int(t * 2) * 37) % 200
        c.drawRect(skia.Rect.MakeXYWH(-205, -140 + k * 55, w, 26), fill("#c3ccd6"))
    if int(t * 2) % 2 == 0:
        c.drawRect(skia.Rect.MakeXYWH(-205 + 180, -140 + 3 * 55, 6, 26), fill(INK))


def brujula(c, t):
    toon(c, oval(0, 0, 250, 250), "#c9a227", light=(-1, -1))
    c.drawCircle(0, 0, 210, fill("#f3ead2"))
    c.drawCircle(0, 0, 210, stroke(INK, 5))
    for k in range(16):
        a = k * math.tau / 16
        r0 = 170 if k % 4 else 140
        c.drawLine(math.cos(a) * r0, math.sin(a) * r0, math.cos(a) * 200, math.sin(a) * 200, stroke(INK, 5 if k % 4 else 8))
    a = math.sin(t * 2.3) * 0.5 + math.sin(t * 5.1) * 0.15  # la aguja no para quieta
    c.save()
    c.rotate(math.degrees(a))
    c.drawPath(poly([(0, -180), (26, 0), (-26, 0)]), fill("#c0392b"))
    c.drawPath(poly([(0, 180), (26, 0), (-26, 0)]), fill("#2b2f36"))
    c.restore()
    c.drawCircle(0, 0, 16, fill("#c9a227"))


EXTRA_PROPS = {"globo": globo, "camara": camara, "foto": foto, "telefono": telefono, "calavera": calavera,
               "lupa": lupa, "libro": libro, "billetes": billetes, "pastillas": pastillas, "vela": vela,
               "portatil": portatil, "brujula": brujula}
EXTRA_PROP_DESC = {
    "globo": "globo aerostático con barquilla", "camara": "cámara de fotos antigua que dispara el flash",
    "foto": "fotografía antigua en blanco y negro con siluetas de personas", "telefono": "teléfono antiguo sonando",
    "calavera": "calavera con un brillo rojo en los ojos", "lupa": "lupa examinando una huella dactilar",
    "libro": "libro o diario abierto pasando páginas", "billetes": "fajo de billetes con algunos volando",
    "pastillas": "bote de pastillas volcado", "vela": "vela encendida en la oscuridad",
    "portatil": "ordenador portátil con una web abierta", "brujula": "brújula con la aguja temblando",
}


# ---------------- sucesos (encima del escenario) ----------------

def ev_globo(c, W, H, t, dur):
    """Globo aerostático que cruza el cielo."""
    c.save()
    c.translate(W * 0.15 + t * 70, H * 0.3 + math.sin(t * 0.9) * 20)
    c.scale(0.55, 0.55)
    globo(c, t)
    c.restore()


def ev_niebla(c, W, H, t, dur):
    for k in range(26):
        x = (k * 120 + t * (40 + (k % 4) * 15)) % (W + 500) - 250
        y = H * (0.35 + (k % 7) * 0.09)
        c.drawCircle(x, y, 200 + (k % 3) * 60, blur(fill("#e6ecf2", 0.14), 50))


def ev_relampago(c, W, H, t, dur):
    """Un rayo enorme y la pantalla se ilumina."""
    for at in (0.3, 1.8):
        a = t - at
        if 0 <= a < 0.35:
            c.drawRect(skia.Rect.MakeWH(W, H), fill("#ffffff", max(0.0, 0.7 - a * 2)))
            rnd = random.Random(int(at * 10))
            x, y = W * rnd.uniform(0.3, 0.7), 0.0
            p = skia.Path()
            p.moveTo(x, y)
            while y < H * 0.6:
                x += rnd.uniform(-70, 70)
                y += rnd.uniform(50, 110)
                p.lineTo(x, y)
            c.drawPath(p, stroke("#ffffff", 16, 1 - a * 2))
            c.drawPath(p, stroke("#bfe0ff", 34, 0.4 * (1 - a * 2)))


def ev_sirenas(c, W, H, t, dur):
    """Luces de policía o ambulancia (rojo y azul) que barren la escena."""
    red = (t * 3) % 1.0 < 0.5
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#ff2a2a" if red else "#2a6bff", 0.14))
    for k, col in ((0, "#ff2a2a"), (1, "#2a6bff")):
        on = (red and k == 0) or (not red and k == 1)
        x = W * (0.1 if k == 0 else 0.9)
        c.drawCircle(x, H * 0.08, 400, radial(fill(col), (x, H * 0.08), 400, [col, col], [0.55 if on else 0.1, 0.0]))


def ev_notificaciones(c, W, H, t, dur):
    """Notificaciones del móvil que van apareciendo en pantalla."""
    for k in range(5):
        at = 0.2 + k * 0.45
        if t < at:
            break
        pop = min(1.0, (t - at) / 0.15)
        x, y = W * (0.12 + (k % 2) * 0.3), H * (0.12 + k * 0.1)
        c.save()
        c.translate(x + 200, y + 50)
        c.scale(pop, pop)
        toon(c, rrect(-200, -50, 400, 100, 24), "#ffffff", outline=4)
        c.drawCircle(-150, 0, 30, fill(["#25d366", "#e1306c", "#1da1f2", "#ff0000", "#ffcc00"][k]))
        c.drawRect(skia.Rect.MakeXYWH(-100, -22, 230, 16), fill("#5a6270"))
        c.drawRect(skia.Rect.MakeXYWH(-100, 6, 160, 14), fill("#a5adb8"))
        c.drawCircle(185, -45, 22, fill("#ff3b30"))
        c.restore()


def ev_billetes(c, W, H, t, dur):
    rnd = random.Random(3)
    for k in range(18):
        x = rnd.uniform(0, W) + math.sin(t * 2 + k) * 50
        y = (rnd.uniform(-H, 0) + t * rnd.uniform(220, 360)) % (H + 200) - 100
        c.save()
        c.translate(x, y)
        c.rotate(math.sin(t * 3 + k) * 50)
        toon(c, rrect(-70, -34, 140, 68, 6), "#8fc079", outline=4)
        c.drawPath(oval(0, 0, 20, 20), stroke("#4a7a3a", 4))
        c.restore()


def ev_sombra(c, W, H, t, dur):
    """Una figura oscura aparece y desaparece al fondo (alguien vigila)."""
    a = min(1.0, t / 1.0) * (1 - max(0.0, (t - (dur - 0.6)) / 0.6)) * (0.7 + 0.3 * math.sin(t * 2))
    x, base, s = W * 0.82, H * 0.82, 1.3
    col = "#0b0a10"
    c.drawCircle(x, base - 520 * s, 60 * s, fill(col, a))
    c.drawPath(poly([(x - 120 * s, base), (x - 90 * s, base - 440 * s), (x + 90 * s, base - 440 * s), (x + 120 * s, base)],
                    smooth=True), fill(col, a))
    c.drawPath(poly([(x - 85 * s, base - 560 * s), (x + 85 * s, base - 560 * s), (x + 60 * s, base - 600 * s), (x - 60 * s, base - 600 * s)]),
               fill(col, a))
    for sx in (-18, 18):  # ojos
        c.drawCircle(x + sx * s, base - 520 * s, 6 * s, fill("#ffdf6b", a * (0.6 + 0.4 * math.sin(t * 5))))


def ev_estrellas(c, W, H, t, dur):
    """Estrellas fugaces."""
    for k in range(4):
        ph = (t * 0.7 + k * 0.27) % 1.0
        x0, y0 = W * (0.2 + k * 0.22), H * (0.05 + (k % 2) * 0.08)
        x, y = x0 + ph * 500, y0 + ph * 300
        for j in range(10):
            c.drawCircle(x - j * 22, y - j * 13, 9 - j * 0.8, fill("#ffffff", max(0.0, (1 - ph) * (1 - j / 10))))


def ev_terremoto(c, W, H, t, dur):
    """El suelo se agrieta y cae polvo (terremotos, derrumbes)."""
    rnd = random.Random(8)
    grow = min(1.0, t / 1.5)
    for k in range(4):
        x, y = W * (0.15 + k * 0.23), H * 0.86
        p = skia.Path()
        p.moveTo(x, y)
        for j in range(int(6 * grow) + 1):
            x += rnd.uniform(-60, 60)
            y += rnd.uniform(-10, 30)
            p.lineTo(x, y)
        c.drawPath(p, stroke(INK, 10))
    for k in range(30):
        ph = (t * 0.8 + k / 30) % 1.0
        c.drawCircle(rnd.uniform(0, W), ph * H * 0.8, rnd.uniform(4, 10), fill("#b9a88f", 0.5 * (1 - ph)))
    for k in range(5):
        c.drawCircle(rnd.uniform(0, W), H * 0.86, 120 + 80 * grow, fill("#c9b89f", 0.12))


EXTRA_EVENTS = {"globo": ev_globo, "niebla": ev_niebla, "relampago": ev_relampago, "sirenas": ev_sirenas,
                "notificaciones": ev_notificaciones, "billetes": ev_billetes, "sombra": ev_sombra,
                "estrellas": ev_estrellas, "terremoto": ev_terremoto}
EXTRA_EVENT_DESC = {
    "globo": "globo aerostático cruzando el cielo (lugares al aire libre)", "niebla": "niebla espesa que avanza",
    "relampago": "rayo enorme que ilumina toda la pantalla", "sirenas": "luces de policía o ambulancia, rojo y azul",
    "notificaciones": "notificaciones del móvil que no paran de llegar", "billetes": "lluvia de billetes",
    "sombra": "una figura oscura con ojos que aparece al fondo y vigila", "estrellas": "estrellas fugaces (de noche)",
    "terremoto": "el suelo se agrieta y cae polvo (con la cámara temblando)",
}
EXTRA_EVENT_SFX = {"relampago": [("boom", 0.35), ("boom", 1.85)], "terremoto": [("boom", 0.1)],
                   "sombra": [("whoosh", 0.4)]}
EXTRA_EVENT_AMBIENCE = {"niebla": "viento", "relampago": "viento", "globo": "viento"}


# ---------------- vehículos (cruzan la escena por detrás de los personajes) ----------------

def _wheel(c, x, y, r, t, spokes=True, color="#1d1f24", rim="#b0b5bd"):
    toon(c, oval(x, y, r, r), color, outline=5)
    c.drawCircle(x, y, r * 0.55, fill(rim))
    if spokes:
        for k in range(6):
            a = t * 8 + k * math.pi / 3
            c.drawLine(x, y, x + math.cos(a) * r * 0.85, y + math.sin(a) * r * 0.85, stroke(INK, 4))
    c.drawCircle(x, y, r * 0.15, fill(INK))


def _window(c, pts, night=False):
    c.drawPath(poly(pts), fill("#bfe3f5"))
    c.drawPath(poly(pts), stroke(INK, 5))


def coche(c, x, y, s, t, f=1.0, color="#c0392b"):
    """Coche moderno."""
    c.save(); c.translate(x, y); c.scale(s * f, s)
    toon(c, rrect(-230, -130, 460, 100, 40), color)
    toon(c, poly([(-140, -130), (-90, -210), (95, -210), (160, -130)]), color)
    _window(c, [(-115, -135), (-78, -195), (0, -195), (0, -135)])
    _window(c, [(15, -135), (15, -195), (88, -195), (135, -135)])
    c.drawCircle(215, -95, 16, fill("#fff3c4"))
    c.drawRect(skia.Rect.MakeXYWH(-232, -80, 30, 14), fill("#ff4040"))
    c.restore()
    for wx in (-140, 140):
        _wheel(c, x + wx * s * f, y - 30 * s, 48 * s, t * f)


def coche_antiguo(c, x, y, s, t, f=1.0, color="#1d1f24"):
    """Coche de los años 20-50: guardabarros curvos, faros redondos y estribo."""
    c.save(); c.translate(x, y); c.scale(s * f, s)
    toon(c, poly([(-240, -60), (-200, -120), (60, -120), (90, -170), (180, -170), (230, -110), (250, -60)], smooth=False), color)
    toon(c, poly([(-70, -120), (-60, -250), (60, -250), (70, -120)]), color)
    _window(c, [(-48, -130), (-40, -232), (48, -232), (56, -130)])
    for gx in (-170, 160):  # guardabarros
        toon(c, poly([(gx - 80, -40), (gx - 60, -100), (gx + 60, -100), (gx + 80, -40)], smooth=True), shade(color, 0.1))
    c.drawRect(skia.Rect.MakeXYWH(-110, -55, 200, 14), fill(shade(color, 0.2)))  # estribo
    toon(c, oval(235, -130, 20, 20), "#e8e2c8", outline=4)
    for k in range(5):
        c.drawLine(200 + k * 8, -165, 200 + k * 8, -115, stroke("#c9ced6", 3))
    c.restore()
    for wx in (-170, 160):
        _wheel(c, x + wx * s * f, y - 38 * s, 46 * s, t * f, rim="#d9d2c4")


def caballo(c, x, y, s, t, f=1.0, color="#6b4423", rider=True):
    """Caballo al galope (con jinete opcional)."""
    gal = t * 9
    c.save(); c.translate(x, y - abs(math.sin(gal)) * 18 * s); c.scale(s * f, s)
    for k, (lx, ph) in enumerate(((-120, 0), (-90, 1.5), (110, 3.0), (140, 4.5))):  # patas
        a = math.sin(gal + ph) * 0.6
        kx, ky = lx + math.sin(a) * 70, -140 + math.cos(a) * 70
        c.drawLine(lx, -190, kx, ky, stroke(INK, 30))
        c.drawLine(lx, -190, kx, ky, stroke(shade(color, -0.1 if k % 2 else 0), 18))
        c.drawLine(kx, ky, kx + math.sin(a * 1.4) * 60, ky + 70, stroke(INK, 24))
        c.drawLine(kx, ky, kx + math.sin(a * 1.4) * 60, ky + 70, stroke(color, 13))
    toon(c, oval(0, -230, 190, 80), color, light=(-1, -0.6))
    toon(c, poly([(130, -270), (200, -380), (260, -390), (300, -340), (240, -310), (190, -220)], smooth=True), color)
    c.drawPath(poly([(140, -280), (195, -385), (170, -300)], smooth=True), fill("#2a1d16"))  # crin
    c.drawCircle(262, -358, 7, fill(INK))
    tail = skia.Path(); tail.moveTo(-185, -250); tail.quadTo(-260, -230 + math.sin(gal) * 20, -250, -150)
    c.drawPath(tail, stroke("#2a1d16", 22))
    if rider:  # jinete en silueta con sombrero
        toon(c, poly([(-40, -300), (40, -300), (30, -420), (-30, -420)], smooth=True), "#3a2a20")
        toon(c, oval(0, -460, 40, 44), "#dda177")
        toon(c, poly([(-70, -480), (70, -480), (40, -500), (25, -540), (-25, -540), (-40, -500)]), "#1d1f24")
        c.drawLine(20, -380, 150, -330, stroke(INK, 5))  # riendas
    c.restore()


def carruaje(c, x, y, s, t, f=1.0, color="#3a2618"):
    """Carruaje tirado por un caballo (siglos XVIII-XIX)."""
    caballo(c, x + 330 * s * f, y, s * 0.85, t, f, rider=False)
    c.save(); c.translate(x, y); c.scale(s * f, s)
    c.drawLine(120, -150, 260, -170, stroke(INK, 10))
    toon(c, poly([(-200, -80), (130, -80), (150, -320), (-210, -320)], smooth=True), color, light=(-1, -0.4))
    toon(c, rrect(-220, -350, 380, 40, 14), shade(color, -0.2))
    _window(c, [(-140, -290), (-20, -290), (-20, -170), (-140, -170)])
    c.drawPath(oval(70, -200, 30, 50), stroke("#d4af37", 6))
    toon(c, oval(150, -360, 22, 22), "#ffcf6b", outline=4)
    c.restore()
    for wx, r in ((-150, 70), (90, 60)):
        _wheel(c, x + wx * s * f, y - r * s, r * s, t * f, color="#5a3a24", rim="#8a6a4a")


def tractor(c, x, y, s, t, f=1.0, color="#2e8b3e"):
    c.save(); c.translate(x, y); c.scale(s * f, s)
    toon(c, rrect(-60, -230, 280, 120, 16), color)
    toon(c, poly([(-180, -110), (-180, -330), (-20, -330), (-20, -110)]), color)
    _window(c, [(-160, -310), (-40, -310), (-40, -220), (-160, -220)])
    c.drawLine(180, -230, 180, -330, stroke("#2b2b2f", 18))
    c.drawCircle(180 - math.sin(t * 4) * 6, -350 - (t * 60) % 60, 18, fill("#8a8a8a", 0.5))
    c.restore()
    _wheel(c, x - 120 * s * f, y - 110 * s, 110 * s, t * f, color="#1d1f24", rim="#e2b93b")
    _wheel(c, x + 160 * s * f, y - 60 * s, 60 * s, t * f, color="#1d1f24", rim="#e2b93b")


def camion(c, x, y, s, t, f=1.0, color="#2e5aa8"):
    c.save(); c.translate(x, y); c.scale(s * f, s)
    toon(c, rrect(-320, -300, 420, 240, 10), "#d9d2c4")
    toon(c, poly([(110, -60), (110, -250), (230, -250), (290, -160), (290, -60)]), color)
    _window(c, [(130, -235), (215, -235), (262, -165), (130, -165)])
    c.restore()
    for wx in (-230, -120, 220):
        _wheel(c, x + wx * s * f, y - 45 * s, 50 * s, t * f)


def tren(c, x, y, s, t, f=1.0):
    """Locomotora de vapor con dos vagones."""
    c.save(); c.translate(x, y); c.scale(s * f, s)
    for k, vx in enumerate((-900, -520)):  # vagones
        toon(c, rrect(vx, -300, 340, 230, 12), "#7e1c28")
        for w in range(3):
            c.drawRect(skia.Rect.MakeXYWH(vx + 30 + w * 105, -260, 75, 70), fill("#ffe9b0"))
            c.drawRect(skia.Rect.MakeXYWH(vx + 30 + w * 105, -260, 75, 70), stroke(INK, 4))
    toon(c, rrect(-150, -260, 360, 190, 30), "#1d1f24")
    toon(c, rrect(-170, -380, 150, 320, 10), "#2b2f36")
    toon(c, poly([(150, -260), (190, -400), (230, -400), (230, -260)]), "#2b2f36")
    c.drawLine(-150, -150, 210, -150, stroke("#c0262d", 10))
    c.restore()
    for k in range(5):  # humo
        ph = (t * 0.8 + k * 0.2) % 1.0
        c.drawCircle(x + (210 - ph * 300) * s * f, y + (-420 - ph * 260) * s, (40 + ph * 70) * s, fill("#e6e6e6", 0.6 * (1 - ph)))
    for wx in (-850, -620, -470, -240, -60, 120):
        _wheel(c, x + wx * s * f, y - 40 * s, 45 * s, t * f, color="#2b2b2f", rim="#c0262d")


def bicicleta(c, x, y, s, t, f=1.0):
    for wx in (-90, 90):
        _wheel(c, x + wx * s * f, y - 70 * s, 70 * s, t * f * 1.4, color="#2b2b2f", rim="#e9eef2")
    c.save(); c.translate(x, y); c.scale(s * f, s)
    for a, b in (((-90, -70), (0, -70)), ((0, -70), (60, -190)), ((-90, -70), (-30, -190)), ((-30, -190), (60, -190)),
                 ((60, -190), (90, -70)), ((60, -190), (50, -240))):
        c.drawLine(a[0], a[1], b[0], b[1], stroke("#c0392b", 10))
    toon(c, poly([(-60, -200), (0, -200), (-10, -185), (-50, -185)]), "#2b2b2f", outline=3)
    c.restore()


def helicoptero(c, x, y, s, t, f=1.0, color="#c9302c"):
    c.save(); c.translate(x, y + math.sin(t * 2) * 10 * s); c.scale(s * f, s)
    toon(c, oval(0, 0, 180, 100), color, light=(-1, -0.6))
    toon(c, poly([(-160, -20), (-420, -10), (-420, 20), (-160, 40)]), color)
    _window(c, [(40, -80), (170, -30), (150, 20), (40, 20)])
    c.drawLine(-80, 110, 120, 110, stroke(INK, 10))
    c.drawLine(0, -100, 0, -140, stroke(INK, 10))
    w = 300 * abs(math.cos(t * 30))
    c.drawLine(-w, -140, w, -140, stroke("#2b2b2f", 12))
    c.drawCircle(-420, 0, 40 * abs(math.sin(t * 30)) + 6, stroke("#2b2b2f", 6))
    c.restore()


def _cross(draw, ground=0.84, scale=1.4, speed=420, f=1.0, **kw):
    """Suceso: el vehículo cruza la pantalla por detrás de los personajes."""
    def ev(c, W, H, t, dur):
        x = W * 0.5 + (t - dur / 2) * speed * f  # pasa por el centro a mitad del plano
        draw(c, x, H * ground, scale, t, f, **kw)
    return ev


VEHICLE_EVENTS = {
    "coche": _cross(coche, scale=1.45), "coche_antiguo": _cross(coche_antiguo, scale=1.45),
    "coche_policia": _cross(coche, scale=1.45, color="#2b4a8a"),
    "caballo": _cross(caballo, speed=520, scale=1.25), "carruaje": _cross(carruaje, speed=300, scale=1.2),
    "tractor": _cross(tractor, speed=160, scale=1.35), "camion": _cross(camion, speed=300, scale=1.3),
    "tren": _cross(tren, speed=520, scale=1.05, ground=0.8), "bicicleta": _cross(bicicleta, speed=260, scale=1.3),
    "helicoptero": _cross(helicoptero, speed=300, ground=0.28, scale=1.0),
}
VEHICLE_DESC = {
    "coche": "coche moderno que pasa", "coche_antiguo": "coche antiguo (años 20-50) que pasa",
    "coche_policia": "coche de policía que pasa (combínalo con sirenas si hace falta)", "caballo": "jinete a caballo al galope",
    "carruaje": "carruaje tirado por un caballo (s. XVIII-XIX)", "tractor": "tractor que avanza por el campo",
    "camion": "camión que pasa", "tren": "tren de vapor que cruza", "bicicleta": "bicicleta que pasa",
    "helicoptero": "helicóptero que cruza el cielo",
}
BEHIND_EVENTS = set(VEHICLE_EVENTS) - {"helicoptero"}  # se dibujan detrás de los personajes


# ---------------- más objetos ----------------

def maleta(c, t):
    toon(c, rrect(-260, -170, 520, 360, 30), "#8a5a2a", light=(-1, -1))
    toon(c, rrect(-80, -250, 160, 90, 30), "#5a3a1a")
    c.drawRect(skia.Rect.MakeXYWH(-50, -225, 100, 50), fill("#c9b38a"))
    for x in (-150, 150):
        c.drawRect(skia.Rect.MakeXYWH(x - 18, -170, 36, 360), fill("#5a3a1a"))
        toon(c, rrect(x - 26, -20, 52, 40, 6), "#d4af37", outline=4)


def rosa(c, t):
    sway = math.sin(t * 1.5) * 3
    c.save(); c.rotate(sway)
    stem = skia.Path(); stem.moveTo(0, 300); stem.quadTo(30, 100, 0, -80)
    c.drawPath(stem, stroke("#2e6b2e", 18))
    toon(c, poly([(10, 120), (140, 60), (60, 160)], smooth=True), "#3f8a4f")
    for k, (r, col) in enumerate(((150, "#c0392b"), (110, "#d9434f"), (70, "#e85a68"))):
        petals = poly([(-r, -150), (-r * 0.6, -150 - r), (0, -150 - r * 1.2), (r * 0.6, -150 - r), (r, -150), (0, -150 + r * 0.6)], smooth=True)
        toon(c, petals, col, outline=5)
    c.restore()


def regalo(c, t):
    toon(c, rrect(-220, -120, 440, 330, 14), "#2e86de", light=(-1, -1))
    toon(c, rrect(-240, -180, 480, 90, 14), "#3d97ef")
    c.drawRect(skia.Rect.MakeXYWH(-30, -180, 60, 390), fill("#f1c40f"))
    lift = abs(math.sin(t * 2)) * 10
    for side in (-1, 1):
        toon(c, poly([(0, -180 - lift), (side * 140, -300 - lift), (side * 160, -200 - lift)], smooth=True), "#f1c40f")


def botella(c, t):
    toon(c, poly([(-90, 280), (90, 280), (100, -20), (40, -120), (40, -280), (-40, -280), (-40, -120), (-100, -20)], smooth=True),
         "#2e6b3a", light=(-1, -0.4))
    c.drawRect(skia.Rect.MakeXYWH(-80, 40, 160, 140), fill("#f3ead2"))
    c.drawRect(skia.Rect.MakeXYWH(-80, 40, 160, 140), stroke(INK, 5))
    toon(c, rrect(-44, -320, 88, 50, 10), "#8a5a2a")
    c.drawPath(oval(-50, -40, 16, 90), fill("#ffffff", 0.3))


def dinero_maletin(c, t):
    toon(c, rrect(-280, -100, 560, 300, 20), "#2b2b2f", light=(-1, -1))
    toon(c, poly([(-280, -100), (280, -100), (250, -230), (-250, -230)]), "#3a3a40")
    for k in range(6):
        toon(c, rrect(-240 + k * 80, -150, 70, 120, 6), "#7fb069", outline=4)
    toon(c, rrect(-50, -40, 100, 50, 10), "#d4af37", outline=4)


EXTRA_PROPS_2 = {"maleta": maleta, "rosa": rosa, "regalo": regalo, "botella": botella, "maletin_dinero": dinero_maletin}
EXTRA_PROP_DESC_2 = {"maleta": "maleta de viaje antigua", "rosa": "rosa roja (amor, cita, funeral)",
                     "regalo": "caja de regalo con lazo", "botella": "botella de vino o licor",
                     "maletin_dinero": "maletín abierto lleno de billetes (rescates, sobornos)"}
