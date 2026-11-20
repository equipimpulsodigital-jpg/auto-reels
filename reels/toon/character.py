"""Personajes caricatura: cabeza grande, nariz exagerada, boca sincronizada con la voz, ojos que
parpadean y miran, cejas expresivas y brazos que gesticulan. Todo vectorial: el mismo personaje es
siempre idéntico en todos los planos."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import skia

from .draw import INK, fill, limb, mix, noise1, oval, poly, shade, stroke, toon

SKIN = {"clara": "#f1c7a3", "media": "#dda177", "morena": "#b9784f", "oscura": "#7b4b30"}


@dataclass
class Look:
    """Aspecto de un personaje (lo elige el guionista a partir de opciones cerradas)."""
    skin: str = "media"
    hair: str = "#3b2a20"                 # color de pelo, cejas y bigote
    hair_style: str = "corto"             # corto | calvo | largo | moño | rapado
    hat: str = "ninguno"                  # ninguno | gorra_plana | gorra_militar | boina | sombrero | casco | tricornio | corona | mantilla | chistera | bombin | toca | pañuelo
    hat_color: str = "#2b2f3a"
    beard: str = "ninguna"                # ninguna | barba_corta | barba | bigote | bigotazo | perilla
    beard_color: str | None = None
    outfit: str = "jersey"                # jersey | uniforme | traje | camisa | vestido | sotana | armadura | capa | noble | levita | campesino
    pants_color: str = "#3a3a42"
    shoes_color: str = "#2a1d16"
    outfit_color: str = "#2d3d5c"
    accent_color: str = "#c9a227"         # botones, galones, corbata, joyas
    nose: str = "patata"                  # patata | aguileña | pequeña | gancho
    jaw: str = "redonda"                  # redonda | cuadrada | fina
    age: str = "adulto"                   # joven | adulto | mayor
    glasses: bool = False
    female: bool = False
    eyes: str = "#5b3a22"                 # color del iris
    seed: int = 1

    @property
    def skin_color(self) -> str:
        return SKIN.get(self.skin, self.skin if self.skin.startswith("#") else SKIN["media"])


@dataclass
class Pose:
    """Estado del personaje en un fotograma."""
    t: float = 0.0
    mouth: float = 0.0        # apertura de la boca 0-1 (de la voz)
    facing: float = 1.0       # 1 = mira a la derecha de la pantalla, -1 = a la izquierda
    look: float = 0.0         # pupilas: -1 izquierda … 1 derecha (relativo a facing)
    look_up: float = 0.0
    blink: float = 0.0        # 0 abiertos … 1 cerrados
    brow: float = 0.0         # -1 enfadado … 0 neutro … 1 sorprendido
    smile: float = 0.0        # -1 triste … 1 sonrisa (también curva las comisuras al hablar)
    worry: float = 0.0        # 0-1 cejas de pena/miedo (extremo interior hacia arriba)
    extra: str = ""           # lagrimas | sudor | rubor | furia | shock | abierta | brillo | entorna | enamorado ...
    gesture: str = "idle"     # idle | point | explain | chest | shrug | fist | wave | think
    gesture_amt: float = 1.0  # 0-1 (para entrar/salir del gesto)
    talking: bool = False
    nod: float = 0.0          # cabeceo (énfasis al hablar o al escuchar)
    full_body: bool = False   # dibuja piernas (planos generales)
    walk: float = 0.0         # 0 = quieto; >0 = caminando (velocidad del paso)


@dataclass
class Character:
    name: str
    look: Look
    _stubble: list = field(default_factory=list, repr=False)

    def __post_init__(self):
        rnd = random.Random(self.look.seed)
        self._stubble = [(rnd.uniform(-130, 130), rnd.uniform(-400, -280), rnd.uniform(2, 3.6)) for _ in range(160)]

    # ---------- geometría de la cabeza ----------
    def _head_path(self, f: float, mouth: float = 0.0) -> skia.Path:
        L = self.look
        jaw = {"redonda": 128, "cuadrada": 150, "fina": 100}[L.jaw]
        chin = {"redonda": -275, "cuadrada": -270, "fina": -262}[L.jaw] + mouth * 24
        w = 160 if not L.female else 150
        pts = [
            (0, -640), (w * 0.85, -615), (w, -520), (w * 0.98, -420),
            (jaw, -330 + mouth * 8), (jaw * 0.55 + f * 10, chin + 4), (f * 12, chin - 6),
            (-jaw * 0.55 + f * 10, chin + 4), (-jaw, -330 + mouth * 8), (-w * 0.98, -420), (-w, -520), (-w * 0.85, -615),
        ]
        return poly(pts, smooth=True)

    def draw(self, canvas: skia.Canvas, x: float, y: float, scale: float, p: Pose) -> None:
        """Dibuja el personaje con la cintura en (x, y)."""
        L = self.look
        f = 1.0 if p.facing >= 0 else -1.0
        canvas.save()
        canvas.translate(x, y)
        canvas.scale(scale, scale)
        # respiración y balanceo
        breathe = math.sin(p.t * 2.2) * 4
        bob = -abs(math.sin(p.t * 7.5)) * 10 * p.mouth if p.talking else 0
        lean = noise1(p.t * 0.6, L.seed) * 2.0 + (3.0 * f if p.talking else 0)
        canvas.rotate(lean * 0.4)

        if p.walk:
            canvas.translate(0, -abs(math.sin(p.t * p.walk * 6)) * 12)
        if p.full_body:
            self._legs(canvas, p, f)
        self._arms(canvas, p, f, back=True)
        self._torso(canvas, f, breathe)
        canvas.save()
        canvas.translate(0, bob + breathe * 0.5 + p.nod * 14)
        canvas.rotate(lean + p.nod * 5 * f + (noise1(p.t * 1.3, L.seed + 3) * 3 * p.mouth if p.talking else 0), 0, -300)
        # squash & stretch: la cabeza se estira un poco al abrir mucho la boca
        st = 1 + 0.03 * p.mouth
        canvas.scale(1 / st ** 0.5, st)
        self._head(canvas, p, f)
        canvas.restore()
        self._arms(canvas, p, f, back=False)
        canvas.restore()

    def draw_back(self, canvas: skia.Canvas, x: float, y: float, scale: float, f: float, t: float) -> None:
        """Personaje de espaldas (nuca y hombro) para los planos por encima del hombro."""
        L = self.look
        canvas.save()
        canvas.translate(x, y + math.sin(t * 2.2) * 4)
        canvas.scale(scale, scale)
        body = poly([(-190, -230), (190, -230), (230, 200), (-230, 200)], smooth=True)
        toon(canvas, body, shade(L.outfit_color, -0.25))
        toon(canvas, oval(f * 150, -440, 30, 44), shade(L.skin_color, -0.2))
        head = oval(0, -450, 165, 185)
        toon(canvas, head, shade(L.skin_color, -0.2))
        if L.hair_style != "calvo":
            toon(canvas, poly([(-168, -470), (-150, -600), (0, -650), (150, -600), (168, -470), (120, -330), (-120, -330)], smooth=True),
                 shade(L.hair, -0.15))
        if L.hat in ("gorra_plana", "gorra_militar", "boina", "sombrero", "casco", "tricornio"):
            toon(canvas, poly([(-200, -560), (-160, -660), (0, -700), (160, -660), (200, -560), (0, -585)], smooth=True),
                 shade(L.hat_color, -0.2))
        canvas.restore()

    # ---------- cuerpo ----------
    def _torso(self, c: skia.Canvas, f: float, breathe: float) -> None:
        L = self.look
        top = -250 - breathe
        sh = 150 if not L.female else 130
        body = poly([(-sh, top + 30), (-sh + 30, top), (sh - 30, top), (sh, top + 30),
                     (sh + 25, 120), (-sh - 25, 120)], smooth=False)
        # hombros redondeados
        body = skia.Op(body, poly([(-sh - 10, top + 40), (-sh + 40, top - 6), (sh - 40, top - 6), (sh + 10, top + 40),
                                   (sh + 10, top + 80), (-sh - 10, top + 80)], smooth=True), skia.PathOp.kUnion_PathOp) or body
        color = L.outfit_color
        toon(c, body, color, light=(-f, -0.3), shade_amt=0.25)
        # cuello
        neck = poly([(-48 + f * 10, -300), (48 + f * 10, -300), (52 + f * 10, top + 10), (-52 + f * 10, top + 10)])
        toon(c, neck, L.skin_color, light=(-f, 0))
        o = L.outfit
        if o == "jersey":
            collar = poly([(-70 + f * 8, top - 18), (70 + f * 8, top - 18), (78 + f * 8, top + 26), (-78 + f * 8, top + 26)], smooth=True)
            toon(c, collar, shade(color, -0.12))
            for k in range(-3, 4):
                c.drawLine(k * 18 + f * 8, top - 8, k * 18 + f * 8, top + 18, stroke(shade(color, -0.35), 4))
        elif o in ("uniforme", "traje", "camisa"):
            shirt = "#efe6d2" if o != "camisa" else shade(color, 0.5)
            v = poly([(-62 + f * 8, top - 8), (62 + f * 8, top - 8), (f * 8, top + 120)])
            toon(c, v, shirt)
            if o in ("uniforme", "traje"):
                tie = poly([(-14 + f * 8, top + 8), (14 + f * 8, top + 8), (20 + f * 8, top + 110), (f * 8, top + 135), (-20 + f * 8, top + 110)])
                toon(c, tie, L.accent_color if o == "traje" else "#1f2633")
                for side in (-1, 1):  # solapas / cuello de la camisa
                    lap = poly([(side * 62 + f * 8, top - 8), (side * 18 + f * 8, top + 40), (side * 90 + f * 8, top + 70)])
                    toon(c, lap, shade(color, 0.08))
            if o == "uniforme":
                for side in (-1, 1):  # galones en los hombros
                    c.drawPath(poly([(side * 100, top + 4), (side * 140, top + 14), (side * 140, top + 30), (side * 100, top + 20)]), fill(L.accent_color))
                for k in range(3):  # botones
                    c.drawCircle(f * 8 + 0, top + 160 + k * 45, 7, fill(L.accent_color))
                pocket = poly([(-120, top + 90), (-55, top + 90), (-55, top + 150), (-120, top + 150)])
                c.drawPath(pocket, stroke(shade(color, -0.4), 5))
        elif o in ("sotana", "capa", "vestido"):
            c.drawPath(poly([(-60 + f * 8, top - 6), (60 + f * 8, top - 6), (40 + f * 8, top + 30), (-40 + f * 8, top + 30)], smooth=True),
                       fill("#f5f0e6" if o == "sotana" else L.accent_color))
        elif o == "armadura":
            for k in range(3):
                c.drawLine(-sh + 20, top + 60 + k * 50, sh - 20, top + 60 + k * 50, stroke(shade(color, -0.4), 5))
            for k in range(-2, 3):
                c.drawCircle(k * 55, top + 35, 6, fill(shade(color, 0.4)))
        elif o == "noble":  # jubón con gorguera (cuello de lechuguilla) y botonadura
            for k in range(5):
                c.drawCircle(f * 8, top + 70 + k * 42, 8, fill(L.accent_color))
            c.drawLine(-sh + 30, top + 120, sh - 30, top + 120, stroke(L.accent_color, 6, 0.7))
            ruff = skia.Path()
            for k in range(16):
                a = 2 * math.pi * k / 16
                ruff.addCircle(f * 8 + math.cos(a) * 82, top - 4 + math.sin(a) * 26, 22)
            ruff = skia.Op(ruff, skia.Path(), skia.PathOp.kUnion_PathOp) or ruff
            toon(c, ruff, "#f7f3ea", outline=5)
        elif o == "levita":  # levita del XIX: camisa blanca, pañuelo al cuello y solapas
            v = poly([(-70 + f * 8, top - 8), (70 + f * 8, top - 8), (f * 8, top + 150)])
            toon(c, v, "#f4efe3")
            toon(c, poly([(-38 + f * 8, top), (38 + f * 8, top), (f * 8, top + 50)], smooth=True), L.accent_color)
            for side in (-1, 1):
                toon(c, poly([(side * 70 + f * 8, top - 8), (side * 24 + f * 8, top + 70), (side * 100 + f * 8, top + 110)]), shade(color, 0.12))
            for k in range(2):
                c.drawCircle(f * 8 + 40, top + 180 + k * 50, 8, fill(shade(color, 0.5)))
        elif o == "campesino":  # camisa clara con chaleco oscuro
            toon(c, poly([(-sh + 20, top + 10), (-30 + f * 8, top + 10), (-20 + f * 8, 120), (-sh - 10, 120)]), shade(color, -0.35))
            toon(c, poly([(sh - 20, top + 10), (30 + f * 8, top + 10), (20 + f * 8, 120), (sh + 10, 120)]), shade(color, -0.35))
            c.drawLine(-55 + f * 8, top - 10, f * 8, top + 40, stroke(INK, 5))
            c.drawLine(55 + f * 8, top - 10, f * 8, top + 40, stroke(INK, 5))

    def _legs(self, c: skia.Canvas, p: Pose, f: float) -> None:
        L = self.look
        skirt = L.outfit in ("vestido", "sotana", "capa") or L.female and L.outfit != "uniforme"
        sw = math.sin(p.t * p.walk * 6) if p.walk else 0.0
        if skirt:
            hem = 430
            for side in (-1, 1):
                sx = side * 50 + sw * side * 25
                toon(c, oval(sx + f * 20, hem + 8, 42, 20), L.shoes_color, outline=5)
            color = L.outfit_color if L.outfit != "capa" else shade(L.outfit_color, -0.1)
            sk = poly([(-150, 60), (150, 60), (210 + sw * 15, hem), (-210 + sw * 15, hem)], smooth=False)
            toon(c, sk, color, light=(-f, -0.2))
            for k in (-1, 0, 1):
                c.drawLine(k * 60, 120, k * 85 + sw * 10, hem - 10, stroke(shade(color, -0.3), 4))
            return
        for side in (-1, 1):
            hip = (side * 62, 90)
            swing = sw * side * 22
            knee = (side * 66 + swing * 0.6, 260)
            foot = (side * 64 + swing, 410 - max(0.0, sw * side) * 20)
            limb(c, [hip, knee, foot], 88, L.pants_color)
            toon(c, oval(foot[0] + f * 26, foot[1] + 20, 56, 26), L.shoes_color, outline=5)

    def _arm_points(self, side: float, th: float, ph: float, top: float) -> list[tuple[float, float]]:
        sx, sy = side * 132, top + 45
        a1, a2 = math.radians(th), math.radians(th + ph)
        ex, ey = sx + side * math.sin(a1) * 135, sy + math.cos(a1) * 135
        hx, hy = ex + side * math.sin(a2) * 125, ey + math.cos(a2) * 125
        return [(sx, sy), (ex, ey), (hx, hy)]

    def _gesture(self, p: Pose, side: float, f: float) -> tuple[float, float]:
        """Ángulos (hombro, codo) en grados: 0 = brazo colgando; positivo = hacia fuera."""
        t, a = p.t, p.gesture_amt
        near = side == f  # brazo del lado hacia el que mira
        idle = (12 + math.sin(t * 2.2 + side) * 3, 12)
        g = p.gesture
        if g == "point" and near:
            tgt = (118 + math.sin(t * 3) * 4, -8)
        elif g == "explain":
            osc = math.sin(t * 5.5 + (0 if near else 1.8)) * 18 * (0.4 + p.mouth)
            tgt = (22 + osc * 0.4, -118 + osc)
        elif g == "chest" and near:
            tgt = (16, -150)
        elif g == "shrug":
            tgt = (38 + math.sin(t * 2) * 4, 92)
        elif g == "fist" and near:
            tgt = (150 + math.sin(t * 9) * 8, -40)
        elif g == "wave" and near:
            tgt = (150, -30 + math.sin(t * 10) * 35)
        elif g == "think" and near:
            tgt = (20, -160)
        else:
            tgt = idle
        return (idle[0] + (tgt[0] - idle[0]) * a, idle[1] + (tgt[1] - idle[1]) * a)

    def _arms(self, c: skia.Canvas, p: Pose, f: float, back: bool) -> None:
        L = self.look
        top = -250 - math.sin(p.t * 2.2) * 4
        sleeve = shade(L.outfit_color, -0.06)
        for side in (-1.0, 1.0):
            th, ph = self._gesture(p, side, f)
            raised = ph < -60 or th > 60
            # los brazos levantados por delante se dibujan delante del cuerpo
            if back == raised:
                continue
            pts = self._arm_points(side, th, ph, top)
            limb(c, pts, 62, sleeve)
            hx, hy = pts[-1]
            ux, uy = hx - pts[1][0], hy - pts[1][1]
            un = math.hypot(ux, uy) or 1
            ux, uy = ux / un, uy / un
            # pulgar hacia el centro del cuerpo
            tx, ty = hx - side * 26 + ux * 6, hy - 8 + uy * 6
            thumb = oval(tx, ty, 13, 20)
            toon(c, thumb, L.skin_color, outline=5)
            hand = poly([(hx - 30, hy - 24), (hx + 28, hy - 26), (hx + 34 + ux * 14, hy + 8 + uy * 14),
                         (hx + ux * 26, hy + 30 + uy * 20), (hx - 32 + ux * 10, hy + 10 + uy * 14)], smooth=True)
            toon(c, hand, L.skin_color, light=(-f, -0.5))
            for k in (-1, 0, 1):  # dedos
                c.drawLine(hx + k * 12 + ux * 12, hy + 4 + uy * 12, hx + k * 13 + ux * 26, hy + 8 + uy * 26,
                           stroke(shade(L.skin_color, -0.4), 3.5))
            if p.gesture == "point" and side == f:
                dx, dy = hx - pts[1][0], hy - pts[1][1]
                n = math.hypot(dx, dy) or 1
                fx, fy = hx + dx / n * 46, hy + dy / n * 46
                c.drawLine(hx, hy, fx, fy, stroke(INK, 24))
                c.drawLine(hx, hy, fx, fy, stroke(L.skin_color, 12))

    # ---------- cabeza ----------
    def _head(self, c: skia.Canvas, p: Pose, f: float) -> None:
        L = self.look
        skin = L.skin_color
        hair = L.hair
        # oreja (la del lado contrario a donde mira)
        ear = oval(-f * 150, -440, 32, 46)
        toon(c, ear, skin, light=(f, 0))
        c.drawPath(oval(-f * 150, -440, 14, 24), stroke(shade(skin, -0.35), 5))
        # pelo largo por detrás
        if L.hair_style in ("largo", "moño") or L.female:
            back = poly([(-185, -560), (185, -560), (195, -330), (120, -250), (-120, -250), (-195, -330)], smooth=True)
            toon(c, back, hair, light=(-f, -0.5))
        if L.hat == "toca":  # velo por detrás de la cabeza, enmarcando la cara
            toon(c, poly([(-215, -620), (0, -700), (215, -620), (240, -230), (-240, -230)], smooth=True), L.hat_color, light=(-f, -0.4))
        head = self._head_path(f, p.mouth)
        toon(c, head, skin, light=(-f, -0.4), shade_amt=0.16)
        c.save()
        c.clipPath(head, doAntiAlias=True)
        rim = skia.Path(head)
        rim.offset(f * 14, 6)
        edge = skia.Op(head, rim, skia.PathOp.kDifference_PathOp)
        if edge is not None:  # luz de contorno (contraluz) en el borde de la nuca
            c.drawPath(edge, fill("#fff1d6", 0.45))
        if L.hat not in ("ninguno", "corona", "mantilla"):  # sombra de la gorra en la frente
            c.drawRect(skia.Rect.MakeLTRB(-200, -600, 200, -545), fill("#000000", 0.16))
        if L.beard in ("barba_corta", "barba") or L.age == "mayor" and L.beard == "ninguna" and not L.female:
            bc = L.beard_color or hair
            a = 0.55 if L.beard == "barba_corta" else 0.35
            for sx, sy, r in self._stubble:
                if sy > -380 or abs(sx) > 90:
                    c.drawCircle(sx + f * 10, sy, r, fill(bc, a))
        if L.age == "mayor":  # arrugas de la frente
            for k in range(3):
                pth = skia.Path()
                pth.moveTo(-60 + f * 20, -570 + k * 16)
                pth.quadTo(f * 20, -580 + k * 16, 60 + f * 20, -570 + k * 16)
                c.drawPath(pth, stroke(shade(skin, -0.3), 4))
        # mejillas
        for side in (-1, 1):
            c.drawPath(oval(side * 92 + f * 22, -380, 34, 22), fill("#e0705a", 0.22))
        self._emotion_tint(c, p, f)
        c.restore()
        if L.beard == "barba":
            bc = L.beard_color or hair
            beard = poly([(-150, -420), (-120, -330), (-70, -255), (f * 10, -230), (70, -255), (120, -330), (150, -420),
                          (95, -360), (f * 25, -335), (-95, -360)], smooth=True)
            toon(c, beard, bc, light=(-f, -0.3))
        self._hair(c, f)
        self._eyes(c, p, f)
        self._nose(c, f)
        self._mouth(c, p, f)
        self._facial_hair(c, f)
        self._emotion_fx(c, p, f, head)
        if L.glasses:
            for side in (-1, 1):
                c.drawPath(oval(side * 60 + f * 26, -468, 46, 40), stroke(INK, 8))
            c.drawLine(-14 + f * 26, -470, 14 + f * 26, -470, stroke(INK, 7))
        self._hat(c, f)

    def _emotion_tint(self, c: skia.Canvas, p: Pose, f: float) -> None:
        """Color de la piel según la emoción (se dibuja debajo de ojos y boca, ya recortado a la cabeza)."""
        e, t = p.extra, p.t
        if e == "furia":  # rojo que sube desde la frente, en degradado
            pulse = 0.06 * math.sin(t * 9)
            for k in range(12):
                y0 = -660 + k * 24
                c.drawRect(skia.Rect.MakeLTRB(-220, y0, 220, y0 + 24), fill("#d4322c", max(0.0, 0.5 - k * 0.04 + pulse)))
        elif e == "shock":  # palidez azulada que baja desde la frente
            for k in range(10):
                y0 = -660 + k * 22
                c.drawRect(skia.Rect.MakeLTRB(-220, y0, 220, y0 + 22), fill("#7d8db8", max(0.0, 0.4 - k * 0.04)))
            for k in range(4):
                x = -70 + k * 45 + f * 20
                c.drawLine(x, -630, x, -585, stroke("#4a5a88", 6, 0.55))
        elif e in ("rubor", "enamorado"):  # colorado
            for side in (-1, 1):
                c.drawPath(oval(side * 92 + f * 22, -385, 52, 30), fill("#ff4f6d", 0.42))
                for k in range(3):
                    x = side * 92 + f * 22 - 24 + k * 22
                    c.drawLine(x, -398, x - 10, -372, stroke("#c2304a", 4, 0.6))

    def _emotion_fx(self, c: skia.Canvas, p: Pose, f: float, head: skia.Path) -> None:
        """Detalles que hacen legible la emoción a la primera: lágrimas, sudor, rubor, ira, palidez..."""
        e, t = p.extra, p.t
        if e == "furia":  # vena de cómic en la frente
            vx, vy = -f * 85, -585
            for a in range(4):
                ang = a * math.pi / 2 + math.pi / 4
                c.drawLine(vx + math.cos(ang) * 8, vy + math.sin(ang) * 8, vx + math.cos(ang) * 30, vy + math.sin(ang) * 30,
                           stroke("#c01f1f", 10))
        if e == "sudor":  # gota que resbala por la sien
            k = (t * 0.6) % 1.0
            sx, sy = -f * 140, -560 + k * 120
            drop = poly([(sx, sy - 34), (sx + 18, sy + 2), (sx, sy + 20), (sx - 18, sy + 2)], smooth=True)
            c.drawPath(drop, fill("#9fd8ff", 0.95))
            c.drawPath(drop, stroke(INK, 4))
            c.drawCircle(sx - 5, sy, 4, fill("#ffffff"))
        if e == "lagrimas":  # regueros y gotas que caen
            for side in (-1, 1):
                ex = side * 58 + f * 26
                c.drawLine(ex, -440, ex + side * 6, -330, stroke("#7fc8ff", 14, 0.75))
                k = (t * 1.3 + (0.5 if side > 0 else 0)) % 1.0
                yy = -440 + k * 170
                d = poly([(ex + side * 6, yy - 20), (ex + side * 6 + 13, yy + 4), (ex + side * 6, yy + 16), (ex + side * 6 - 13, yy + 4)], smooth=True)
                c.drawPath(d, fill("#7fc8ff"))
                c.drawPath(d, stroke(INK, 3))
        if e == "enamorado":  # corazoncitos que suben junto a la cabeza
            for k in range(3):
                ph = (t * 0.5 + k / 3) % 1.0
                hx, hy, sz = f * 200 + math.sin(ph * 6 + k) * 20, -560 - ph * 220, 0.18 + 0.05 * k
                hp = skia.Path()
                hp.moveTo(hx, hy + 90 * sz)
                hp.cubicTo(hx - 170 * sz, hy - 10 * sz, hx - 90 * sz, hy - 150 * sz, hx, hy - 60 * sz)
                hp.cubicTo(hx + 90 * sz, hy - 150 * sz, hx + 170 * sz, hy - 10 * sz, hx, hy + 90 * sz)
                c.drawPath(hp, fill("#ff4f6d", 1 - ph * 0.7))
        if e == "suspiro":  # bocanada de aire
            k = (t * 0.7) % 1.0
            c.drawCircle(f * (90 + k * 90), -330 - k * 30, 14 + k * 22, fill("#ffffff", 0.55 * (1 - k)))
        if e == "shock":  # líneas de impacto alrededor de la cabeza
            for k in range(6):
                ang = -math.pi * (0.15 + k * 0.14)
                r0 = 250 + 10 * math.sin(t * 12 + k)
                c.drawLine(math.cos(ang) * r0, -450 + math.sin(ang) * r0, math.cos(ang) * (r0 + 60),
                           -450 + math.sin(ang) * (r0 + 60), stroke(INK, 7))

    def _hair(self, c: skia.Canvas, f: float) -> None:
        L = self.look
        if L.hair_style == "calvo" or L.hat in ("casco", "tricornio"):
            if L.hair_style != "calvo":
                return
            for side in (-1, 1):  # coronilla calva con pelo a los lados
                toon(c, oval(side * 150, -500, 26, 60), L.hair, light=(-f, 0))
            return
        if L.hair_style == "rapado":
            cap = poly([(-160, -540), (-150, -610), (0, -652), (150, -610), (160, -540), (0, -600)], smooth=True)
            toon(c, cap, L.hair)
            return
        top = poly([(-168, -470), (-170, -590), (-90, -660), (30, -672), (140, -630), (172, -560), (165, -470),
                    (140, -560), (40 * f, -600), (-120, -570)], smooth=True)
        toon(c, top, L.hair, light=(-f, -0.6))
        if L.hair_style == "moño":
            toon(c, oval(-f * 60, -680, 62, 50), L.hair)

    def _eyes(self, c: skia.Canvas, p: Pose, f: float) -> None:
        L = self.look
        lid = 0.25 if L.age == "mayor" else 0.0
        if p.extra == "suspiro":
            lid = max(lid, 0.45)
        open_amt = max(0.05, 1 - p.blink)
        big = 1.18 if p.extra in ("shock", "abierta") else 1.0
        pupil = 11 if p.extra == "shock" else 18
        look_up = {"mira_arriba": 0.9, "rubor": -0.8}.get(p.extra, p.look_up)
        for side in (-1, 1):
            ex, ey = side * 58 + f * 26, -468
            rx, ry = (30, 36) if side == f else (27, 34)  # el ojo lejano un poco más pequeño
            rx, ry = rx * big, ry * big
            white = oval(ex, ey, rx, ry * open_amt)
            c.drawPath(white, fill("#fbf8f2"))
            c.save()
            c.clipPath(white, doAntiAlias=True)
            px = ex + (p.look * 0.6 + f * 0.6) * 12
            py = ey - look_up * 12 + 3
            c.drawCircle(px, py, pupil, fill(L.eyes))
            c.drawCircle(px, py, pupil, stroke(shade(L.eyes, -0.5), 3))
            c.drawCircle(px, py, pupil / 2, fill("#141111"))
            if p.extra == "brillo":  # ojos brillantes de emoción
                c.drawCircle(px + 6, py - 6, 9, fill("#ffffff"))
                c.drawCircle(px - 7, py + 6, 5, fill("#ffffff"))
            else:
                c.drawCircle(px + 6, py - 7, 6 * pupil / 18, fill("#ffffff"))
                c.drawCircle(px - 5, py + 6, 2.5, fill("#ffffff", 0.8))
            squint = 0.42 if p.extra == "entorna" else 0.0
            if lid > 0 or p.brow < -0.3 or squint:  # párpado: cansado, enfadado o desconfiado
                amt = max(lid, -p.brow * 0.35, squint)
                c.drawRect(skia.Rect.MakeLTRB(ex - rx - 2, ey - ry - 2, ex + rx + 2, ey - ry + 2 * ry * amt), fill(shade(L.skin_color, -0.08)))
            c.restore()
            c.drawPath(white, stroke(INK, 5))
            lash = skia.Path()  # párpado superior marcado
            lash.addArc(skia.Rect.MakeLTRB(ex - rx, ey - ry * open_amt, ex + rx, ey + ry * open_amt), 200, 140)
            c.drawPath(lash, stroke(INK, 10 if not L.female else 12))
            if L.female:
                c.drawLine(ex + side * rx * 0.85, ey - ry * open_amt * 0.6, ex + side * (rx + 14), ey - ry * open_amt - 6, stroke(INK, 6))
            # ceja
            by = ey - 52 * big - p.brow * 14
            tilt = (-p.brow * 10 if p.brow < 0 else p.brow * 4) * side
            w = 16 if L.female else 20 if L.age == "mayor" else 17
            y_l, y_r = by + tilt * -side, by - tilt * -side
            if p.worry > 0:  # pena o miedo: el extremo de dentro (hacia la nariz) sube, el de fuera baja
                inner_left = side < 0  # en el ojo izquierdo el extremo interior es el derecho
                up, down = p.worry * 24, p.worry * 8
                y_l, y_r = (y_l + down, y_r - up) if inner_left else (y_l - up, y_r + down)
            bpath = skia.Path()
            bpath.moveTo(ex - 30, y_l)
            bpath.quadTo(ex, min(y_l, y_r) - 8 * (1 - p.worry), ex + 30, y_r)
            c.drawPath(bpath, stroke(INK, w + 6))
            c.drawPath(bpath, stroke(L.hair if L.age != "mayor" else mix(L.hair, "#dddddd", 0.5), w))

    def _nose(self, c: skia.Canvas, f: float) -> None:
        L = self.look
        skin = shade(L.skin_color, -0.06)
        nx = f * 48
        if L.nose == "patata":
            path = poly([(nx - 10, -470), (nx + f * 30, -440), (nx + f * 48, -395), (nx + f * 20, -372), (nx - f * 28, -380), (nx - f * 18, -420)], smooth=True)
        elif L.nose == "aguileña":
            path = poly([(nx - f * 5, -480), (nx + f * 40, -420), (nx + f * 56, -385), (nx + f * 10, -378), (nx - f * 14, -400)], smooth=True)
        elif L.nose == "gancho":
            path = poly([(nx - f * 4, -485), (nx + f * 36, -440), (nx + f * 60, -380), (nx + f * 28, -368), (nx - f * 6, -390)], smooth=True)
        else:
            path = poly([(nx, -440), (nx + f * 22, -400), (nx + f * 4, -388), (nx - f * 12, -400)], smooth=True)
        toon(c, path, skin, light=(-f, -0.5), shade_amt=0.2)
        c.drawPath(oval(nx + f * 22, -385, 7, 5), fill(shade(L.skin_color, -0.45)))

    def _mouth(self, c: skia.Canvas, p: Pose, f: float) -> None:
        L = self.look
        mx, my = f * 30, -332
        o = max(0.0, min(1.0, p.mouth))
        if o < 0.08 and p.extra in ("shock", "abierta"):  # boca en O (susto, sorpresa)
            r = 22 if p.extra == "abierta" else 28
            m = oval(mx, my + 6, r * 0.8, r)
            c.drawPath(m, fill("#4a1414"))
            c.drawPath(m, stroke(INK, 6))
            return
        if o < 0.08 and p.smile > 0.85:  # gran sonrisa con dientes
            m = poly([(mx - 44, my - 10), (mx + 44, my - 10), (mx + 30, my + 22), (mx, my + 32), (mx - 30, my + 22)], smooth=True)
            c.drawPath(m, fill("#4a1414"))
            c.save()
            c.clipPath(m, doAntiAlias=True)
            c.drawRect(skia.Rect.MakeLTRB(mx - 50, my - 14, mx + 50, my + 6), fill("#fbf6ee"))
            c.restore()
            c.drawPath(m, stroke(INK, 6))
            return
        if o < 0.08:
            path = skia.Path()
            path.moveTo(mx - 34, my - p.smile * 6)
            path.quadTo(mx, my + p.smile * 16, mx + 34, my - p.smile * 6)
            c.drawPath(path, stroke(INK, 7))
            return
        w, h = 36 + o * 10 + max(0.0, p.smile) * 8, 8 + o * 40
        cy = my - 4 - p.smile * 14  # comisuras: arriba si sonríe, abajo si está triste o enfadado
        m = poly([(mx - w, cy), (mx - w * 0.5, my - h * 0.35), (mx + w * 0.5, my - h * 0.35), (mx + w, cy),
                  (mx + w * 0.6, my + h * 0.7), (mx, my + h), (mx - w * 0.6, my + h * 0.7)], smooth=True)
        c.drawPath(m, fill("#4a1414"))
        c.save()
        c.clipPath(m, doAntiAlias=True)
        c.drawPath(oval(mx, my + h * 0.95, w * 0.65, h * 0.45), fill("#d8655f"))
        c.drawRect(skia.Rect.MakeLTRB(mx - w, my - h, mx + w, my - h * 0.35 + 9), fill("#fbf6ee"))
        c.restore()
        c.drawPath(m, stroke(INK, 6))
        if L.female:
            c.drawPath(m, stroke("#b0383c", 3))

    def _facial_hair(self, c: skia.Canvas, f: float) -> None:
        L = self.look
        bc = L.beard_color or L.hair
        mx, my = f * 30, -350
        if L.beard in ("bigote", "bigotazo", "barba", "perilla"):
            big = 1.35 if L.beard == "bigotazo" else 1.0
            for side in (-1, 1):
                must = poly([(mx, my - 12 * big), (mx + side * 30 * big, my - 22 * big), (mx + side * 62 * big, my - 6 * big),
                             (mx + side * 70 * big, my + 14 * big), (mx + side * 34 * big, my + 2), (mx, my + 2)], smooth=True)
                toon(c, must, bc, light=(-f, -0.6))
        if L.beard == "perilla":
            toon(c, poly([(mx - 22, -300), (mx + 22, -300), (mx + 6, -248), (mx - 6, -248)], smooth=True), bc)

    def _hat(self, c: skia.Canvas, f: float) -> None:
        L = self.look
        hc = L.hat_color
        h = L.hat
        if h == "gorra_plana":  # boina/gorra plana de pescador
            crown = poly([(-178, -560), (-172, -625), (-80, -685), (60, -690), (170, -642), (186, -575), (0, -590)], smooth=True)
            toon(c, crown, hc, light=(-f, -0.6))
            brim = poly([(f * 40, -585), (f * 190, -575), (f * 222, -560), (f * 150, -552), (f * 30, -562)], smooth=True)
            toon(c, brim, shade(hc, -0.15))
            c.drawLine(-20, -662, 30, -668, stroke(shade(hc, -0.35), 5))
        elif h == "gorra_militar":  # gorra de oficial con visera
            band = poly([(-165, -610), (165, -610), (162, -560), (-162, -560)])
            toon(c, band, "#22252b")
            crown = poly([(-205, -620), (-150, -690), (0, -715), (150, -690), (205, -620), (0, -600)], smooth=True)
            toon(c, crown, hc, light=(-f, -0.6))
            visor = poly([(f * -40, -565), (f * 150, -567), (f * 215, -545), (f * 120, -532), (f * -20, -545)], smooth=True)
            toon(c, visor, "#15171b")
            c.drawCircle(f * 20, -587, 18, fill(L.accent_color))
            c.drawCircle(f * 20, -587, 18, stroke(INK, 5))
        elif h == "boina":
            toon(c, poly([(-185, -560), (-150, -640), (20, -690), (175, -640), (185, -565), (0, -585)], smooth=True), hc, light=(-f, -0.6))
            c.drawLine(10, -690, 18, -712, stroke(INK, 10))
        elif h == "sombrero":
            toon(c, oval(0, -560, 245, 42), shade(hc, -0.1))
            toon(c, poly([(-140, -565), (-130, -690), (0, -715), (130, -690), (140, -565)], smooth=True), hc, light=(-f, -0.6))
            c.drawRect(skia.Rect.MakeLTRB(-138, -600, 138, -570), fill(L.accent_color))
        elif h == "casco":
            toon(c, poly([(-200, -470), (-185, -600), (0, -700), (185, -600), (200, -470), (0, -520)], smooth=True), hc, light=(-f, -0.6))
        elif h == "tricornio":
            toon(c, poly([(-230, -560), (-120, -650), (0, -700), (120, -650), (230, -560), (0, -610)], smooth=True), hc, light=(-f, -0.6))
            c.drawPath(poly([(-230, -560), (0, -610), (230, -560)]), stroke(L.accent_color, 8))
        elif h == "corona":
            pts = [(-140, -560), (-150, -680), (-90, -620), (-45, -710), (0, -630), (45, -710), (90, -620), (150, -680), (140, -560)]
            toon(c, poly(pts), "#e3b23c", light=(-f, -0.5))
            for x in (-90, 0, 90):
                c.drawCircle(x, -590, 12, fill("#c0262d"))
        elif h == "mantilla":
            toon(c, poly([(-60, -640), (0, -760), (60, -640)], smooth=True), "#e7c25b")
            c.drawPath(poly([(-200, -620), (0, -700), (200, -620), (220, -300), (-220, -300)], smooth=True), fill("#111111", 0.35))
        elif h == "chistera":
            toon(c, oval(0, -575, 215, 34), shade(hc, -0.1))
            toon(c, poly([(-125, -580), (-135, -820), (135, -820), (125, -580)]), hc, light=(-f, -0.3))
            c.drawRect(skia.Rect.MakeLTRB(-128, -630, 128, -598), fill(L.accent_color))
        elif h == "bombin":
            toon(c, oval(f * 10, -572, 200, 30), shade(hc, -0.1))
            toon(c, poly([(-140, -575), (-130, -680), (0, -720), (130, -680), (140, -575)], smooth=True), hc, light=(-f, -0.5))
        elif h == "toca":  # toca de monja: banda blanca en la frente y velo por arriba
            toon(c, poly([(-180, -540), (-170, -640), (0, -690), (170, -640), (180, -540), (0, -585)], smooth=True), hc, light=(-f, -0.4))
            toon(c, poly([(-160, -585), (160, -585), (165, -540), (-165, -540)], smooth=True), "#f6f3ec", outline=5)
            for side in (-1, 1):  # griñón blanco bajo la barbilla
                toon(c, poly([(side * 150, -420), (side * 130, -280), (0, -240), (side * 40, -300), (side * 120, -330)], smooth=True), "#f6f3ec", outline=4)
        elif h == "pañuelo":  # pañuelo a la cabeza (campesina)
            toon(c, poly([(-185, -480), (-175, -620), (0, -680), (175, -620), (185, -480), (0, -560)], smooth=True), hc, light=(-f, -0.5))
            toon(c, poly([(-f * 150, -380), (-f * 190, -330), (-f * 120, -330)], smooth=True), shade(hc, -0.1))
