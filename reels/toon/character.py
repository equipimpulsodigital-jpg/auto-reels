"""Personajes caricatura: cabeza grande, nariz exagerada, boca sincronizada con la voz, ojos que
parpadean y miran, cejas expresivas y brazos que gesticulan. Todo vectorial: el mismo personaje es
siempre idéntico en todos los planos."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import skia

from .draw import INK, OUTLINE, STYLE, ease, tube, fill, mix, noise1, oval, poly, rrect, shade, stroke, toon

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
    build: str = "normal"                 # delgado | normal | robusto
    height: str = "normal"                # bajo | normal | alto
    seed: int = 1

    @property
    def wx(self) -> float:  # anchura del cuerpo según la complexión
        return {"delgado": 0.84, "robusto": 1.22}.get(self.build, 1.0) * (0.92 if self.female else 1.0)

    @property
    def child(self) -> bool:
        return self.age == "niño"

    @property
    def hs(self) -> float:  # escala de altura (de pie, en planos generales)
        if self.child:
            return 0.7
        return {"bajo": 0.9, "alto": 1.08}.get(self.height, 1.0) * (0.96 if self.female else 1.0)

    @property
    def skin_color(self) -> str:
        return SKIN.get(self.skin, self.skin if self.skin.startswith("#") else SKIN["media"])


@dataclass
class Pose:
    """Estado del personaje en un fotograma."""
    t: float = 0.0
    mouth: float = 0.0        # apertura de la boca 0-1 (de la voz)
    mouth_round: float = 0.0  # forma de la boca: >0 redonda (o, u), <0 estirada (e, i)
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
    action: str = ""          # correr | caer | sentado | agachado | manos_cabeza | levantar_manos | brazos_cruzados |
                              # al_telefono | sostener | abrazar | golpear | empujar | saltar
    held: str = ""            # objeto en la mano (clave de PROPS)
    relative_height: bool = False  # plano de medio cuerpo con varios personajes: aplicar su estatura


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
        """Dibuja el personaje con la cintura en (x, y). Los pies quedan en y + 440·scale."""
        L = self.look
        f = 1.0 if p.facing >= 0 else -1.0
        act = p.action
        canvas.save()
        canvas.translate(x, y)
        canvas.scale(scale, scale)
        if p.full_body:
            self._ground_shadow(canvas, p, f)
            hs = L.hs
            canvas.translate(0, 440 * (1 - hs))
            canvas.scale(hs, hs)
            if act == "caer":  # cae de espaldas y se queda tendido
                k = ease(min(1.0, p.t / 0.55))
                canvas.translate(f * 420 * k, 60 * k)  # queda tendido en el centro del plano
                canvas.rotate(-84 * f * k, 0, 440)
            elif act == "sentado":
                self._chair(canvas, f)
                canvas.translate(0, 150)
            elif act == "agachado":
                canvas.translate(0, 112)
            elif act == "saltar":
                canvas.translate(0, -abs(math.sin(p.t * 4.2)) * 150)
        elif p.relative_height and L.hs != 1.0:
            # medio cuerpo: el más bajo asoma menos (la cintura queda fuera de plano, abajo)
            canvas.translate(0, 560 * (1 - L.hs))
            canvas.scale(L.hs, L.hs)
        # respiración y balanceo
        breathe = math.sin(p.t * 2.2) * 4
        bob = -abs(math.sin(p.t * 7.5)) * 10 * p.mouth if p.talking else 0
        lean = noise1(p.t * 0.6, L.seed) * 2.0 + (3.0 * f if p.talking else 0)
        if act == "correr":
            lean += 9 * f
            canvas.translate(0, -abs(math.sin(p.t * 11)) * 22)
        elif act in ("empujar", "golpear"):
            lean += 6 * f
        canvas.rotate(lean * 0.4, 0, 440 if p.full_body else 0)

        if p.walk and act != "correr":
            canvas.translate(0, -abs(math.sin(p.t * p.walk * 6)) * 12)
        if p.full_body:
            self._legs(canvas, p, f)
        self._arms(canvas, p, f, back=True)
        self._torso(canvas, f, breathe)
        canvas.save()
        canvas.translate(0, bob + breathe * 0.5 + p.nod * 14)
        canvas.rotate(lean + p.nod * 5 * f + (noise1(p.t * 1.3, L.seed + 3) * 3 * p.mouth if p.talking else 0), 0, -300)
        hk = STYLE["head"] * (1.18 if L.child else 1.0)  # tamaño de la cabeza (según estilo y edad)
        if hk != 1.0:
            canvas.translate(0, -270)
            canvas.scale(hk, hk)
            canvas.translate(0, 270)
        # squash & stretch: la cabeza se estira un poco al abrir mucho la boca
        st = 1 + 0.03 * p.mouth
        canvas.scale(1 / st ** 0.5, st)
        self._head(canvas, p, f)
        canvas.restore()
        self._arms(canvas, p, f, back=False)
        canvas.restore()

    def _ground_shadow(self, c: skia.Canvas, p: Pose, f: float) -> None:
        w = 170 * self.look.wx * self.look.hs
        if p.action == "caer":
            k = ease(min(1.0, p.t / 0.55))
            c.drawPath(oval(f * 160 * k, 452, w + 230 * k, 30), fill("#000000", 0.22))
        else:
            lift = abs(math.sin(p.t * 4.2)) if p.action == "saltar" else 0.0
            c.drawPath(oval(0, 450, w * (1 - 0.35 * lift), 28 * (1 - 0.35 * lift)), fill("#000000", 0.24))

    def _chair(self, c: skia.Canvas, f: float) -> None:
        wood = "#6b4a2f"
        toon(c, rrect(-f * 150 - 30, 40, 60, 260, 14), shade(wood, -0.15))  # respaldo
        toon(c, rrect(-150, 250, 330, 44, 12), wood)  # asiento
        for x in (-130, 150):
            toon(c, rrect(x - 14, 290, 28, 150, 8), shade(wood, -0.2))

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
    def _jacket_hem(self) -> float:
        return {"traje": 185, "uniforme": 175, "levita": 300, "noble": 150, "armadura": 160}.get(self.look.outfit, 128)

    def _torso(self, c: skia.Canvas, f: float, breathe: float) -> None:
        L = self.look
        top = -250 - breathe
        wx = L.wx
        sh = (150 if not L.female else 132) * wx
        waist = sh * (1.02 if L.build == "robusto" else 0.8 if L.female else 0.86)
        hip = sh * (0.98 if L.female else 0.9)
        hem = self._jacket_hem()
        belly = 18 if L.build == "robusto" else 0  # el robusto ensancha suavemente por delante, sin dibujar barriga
        pts = [(-sh + 26, top - 2), (-sh - 8, top + 34), (-sh * 0.97, top + 150), (-waist - belly * (f < 0), 40),
               (-hip, 120), (-hip * 1.02, hem), (hip * 1.02, hem), (hip, 120), (waist + belly * (f > 0), 40),
               (sh * 0.97, top + 150), (sh + 8, top + 34), (sh - 26, top - 2)]
        body = poly(pts, smooth=True)
        color = L.outfit_color
        toon(c, body, color, light=(-f, -0.3), shade_amt=0.25)
        # pliegues en las axilas y la cintura
        for side in (-1, 1):
            pth = skia.Path()
            pth.moveTo(side * sh * 0.86, top + 70)
            pth.quadTo(side * sh * 0.72, top + 140, side * sh * 0.8, top + 190)
            c.drawPath(pth, stroke(shade(color, -0.3), 4))
        if hem <= 130 and L.outfit not in ("vestido", "sotana", "capa"):  # cinturón
            c.drawPath(poly([(-waist * 1.02, 96), (waist * 1.02, 96), (hip, 126), (-hip, 126)], smooth=False), fill("#2a1d16"))
            c.drawRect(skia.Rect.MakeXYWH(f * 10 - 18, 98, 36, 26), stroke("#c9a227", 5))
        elif hem > 130 and L.outfit in ("traje", "levita", "uniforme"):  # abertura de la chaqueta
            c.drawLine(f * 8, 60, f * 8, hem, stroke(shade(color, -0.4), 5))
        # cuello (con sombra de la barbilla)
        neck = poly([(-44 + f * 10, -300), (44 + f * 10, -300), (50 + f * 10, top + 10), (-50 + f * 10, top + 10)])
        toon(c, neck, L.skin_color, light=(-f, 0))
        c.drawPath(oval(f * 10, -292, 48, 18), fill(shade(L.skin_color, -0.35), 0.7))
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


    # ---------- piernas ----------
    def _leg_angles(self, p: Pose, side: float) -> tuple[float, float]:
        """(muslo, rodilla) en grados: muslo > 0 = hacia delante; rodilla > 0 = el pie va hacia atrás."""
        a = p.action
        if a == "correr":
            sw = math.sin(p.t * 11) * side
            return 42 * sw, 25 + 55 * max(0.0, -sw)
        if a == "sentado":
            return 88, 88
        if a == "agachado":
            return 62 + side * 8, 122
        if a == "saltar":
            k = abs(math.sin(p.t * 4.2))
            return 20 * k + side * 6, 40 * k
        if a == "caer":
            return 12 + side * 10, 18
        if p.walk:
            sw = math.sin(p.t * p.walk * 6) * side
            return 20 * sw, 12 * max(0.0, -sw)
        return side * 1.5, 0.0

    def _legs(self, c: skia.Canvas, p: Pose, f: float) -> None:
        L = self.look
        wx = L.wx
        skirt = L.outfit in ("vestido", "sotana", "capa") or L.female and L.outfit not in ("uniforme", "traje", "camisa", "jersey")
        if skirt and p.action not in ("sentado", "agachado", "correr", "caer"):
            sw = math.sin(p.t * p.walk * 6) if p.walk else 0.0
            hem = 430
            for side in (-1, 1):
                sx = side * 50 * wx + sw * side * 25
                self._shoe(c, sx, hem - 2, f)
            color = L.outfit_color if L.outfit != "capa" else shade(L.outfit_color, -0.1)
            top_w = 135 * wx * (0.98 if L.female else 0.9)
            sk = poly([(-top_w, 90), (top_w, 90), (top_w * 1.5 + sw * 15, hem), (-top_w * 1.5 + sw * 15, hem)], smooth=False)
            toon(c, sk, color, light=(-f, -0.2))
            for k in (-1, 0, 1):
                c.drawLine(k * 55 * wx, 120, k * 85 * wx + sw * 10, hem - 10, stroke(shade(color, -0.3), 4))
            return
        pants = L.outfit_color if skirt else L.pants_color
        L1, L2 = 165.0, 150.0
        legs = []
        for side in (-1.0, 1.0):
            th, bend = self._leg_angles(p, side)
            hip = (side * 52 * wx, 120.0)
            a1, a2 = math.radians(th), math.radians(th - bend)
            knee = (hip[0] + f * math.sin(a1) * L1, hip[1] + math.cos(a1) * L1)
            foot = (knee[0] + f * math.sin(a2) * L2, knee[1] + math.cos(a2) * L2)
            legs.append((side, hip, knee, foot))
        thick = 96 * wx ** 0.7
        # la pierna de atrás primero (la del lado contrario a donde mira)
        legs.sort(key=lambda l: l[0] * f)
        for side, hip, knee, foot in legs:
            back = side * f < 0
            col = shade(pants, -0.12) if back else pants
            # la pernera acaba justo encima del zapato (el extremo redondo no asoma por debajo)
            dx, dy = foot[0] - knee[0], foot[1] - knee[1]
            dn = math.hypot(dx, dy) or 1
            ankle = (foot[0] - dx / dn * thick * 0.5, foot[1] - dy / dn * thick * 0.5)
            for seg, w in (((hip, knee), thick), ((knee, ankle), thick * 0.84)):
                pth = skia.Path()
                pth.moveTo(*seg[0])
                pth.lineTo(*seg[1])
                c.drawPath(pth, stroke(INK, w + OUTLINE * 2))
            for seg, w in (((hip, knee), thick), ((knee, ankle), thick * 0.84)):
                pth = skia.Path()
                pth.moveTo(*seg[0])
                pth.lineTo(*seg[1])
                c.drawPath(pth, stroke(col, w))
                tube(c, seg[0], seg[1], w, col)
            # bajo del pantalón
            c.drawLine(ankle[0] - thick * 0.42, ankle[1] + 8, ankle[0] + thick * 0.42, ankle[1] + 8, stroke(shade(col, -0.35), 5))
            self._shoe(c, foot[0], foot[1], f, dark=back)
        # entrepierna: une las dos perneras bajo la cadera
        seat = poly([(-62 * wx, 100), (62 * wx, 100), (58 * wx, 170), (f * 6, 186), (-58 * wx, 170)], smooth=True)
        toon(c, seat, pants, outline=0)

    def _shoe(self, c: skia.Canvas, fx: float, fy: float, f: float, dark: bool = False) -> None:
        col = shade(self.look.shoes_color, -0.15 if dark else 0.0)
        shoe = poly([(fx - f * 38, fy - 6), (fx + f * 12, fy - 18), (fx + f * 56, fy - 2), (fx + f * 64, fy + 16),
                     (fx - f * 40, fy + 18)], smooth=True)
        toon(c, shoe, col, outline=5)
        c.drawLine(fx - f * 40, fy + 16, fx + f * 62, fy + 16, stroke(shade(col, 0.25), 5))
        c.drawPath(oval(fx + f * 20, fy - 4, 14, 5), fill("#ffffff", 0.25))

    # ---------- brazos ----------
    def _shoulder(self, side: float, top: float) -> tuple[float, float]:
        return side * (132 * self.look.wx - (6 if self.look.female else 0)), top + 45

    def _arm_points(self, side: float, th: float, ph: float, top: float) -> list[tuple[float, float]]:
        sx, sy = self._shoulder(side, top)
        a1, a2 = math.radians(th), math.radians(th + ph)
        ex, ey = sx + side * math.sin(a1) * 135, sy + math.cos(a1) * 135
        hx, hy = ex + side * math.sin(a2) * 125, ey + math.cos(a2) * 125
        return [(sx, sy), (ex, ey), (hx, hy)]

    def _ik(self, side: float, target: tuple[float, float], top: float, elbow_out: float = 1.0) -> list[tuple[float, float]]:
        """Brazo que lleva la mano a un punto (cinemática inversa de dos huesos)."""
        L1, L2 = 135.0, 125.0
        sx, sy = self._shoulder(side, top)
        dx, dy = target[0] - sx, target[1] - sy
        d = max(1.0, min(math.hypot(dx, dy), L1 + L2 - 1))
        base = math.atan2(dy, dx)
        cos_a = max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)))
        a = math.acos(cos_a)
        best = None
        for sgn in (1, -1):
            ang = base + sgn * a
            ex, ey = sx + math.cos(ang) * L1, sy + math.sin(ang) * L1
            score = ey + elbow_out * side * ex * 0.6  # codo abajo y hacia fuera
            if best is None or score > best[0]:
                best = (score, (ex, ey))
        ex, ey = best[1]
        k = d / max(1.0, math.hypot(dx, dy))
        hx, hy = sx + dx * k, sy + dy * k
        return [(sx, sy), (ex, ey), (hx, hy)]

    def _action_target(self, p: Pose, side: float, f: float, top: float):
        """Dónde va la mano en cada acción (None = gesto normal)."""
        a, t, near = p.action or ("sostener" if p.held else ""), p.t, side == f
        if a == "manos_cabeza":
            return (side * 150, -400 + math.sin(t * 3 + side) * 8)
        if a == "levantar_manos":
            return (side * 250, -560 + math.sin(t * 6 + side) * 14)
        if a == "brazos_cruzados":
            return (-side * 70, -70)
        if a == "al_telefono" and near:
            return (f * 152, -430)
        if a == "sostener" and near:
            return (f * 190, -70 + math.sin(t * 1.6) * 6)
        if a == "abrazar":
            return (f * 205 + side * 30, -140 + side * 20)
        if a == "golpear" and near:
            k = max(0.0, math.sin(t * 9))
            return (f * (120 + 190 * k), -190)
        if a == "empujar":
            k = 0.5 + 0.5 * math.sin(t * 6)
            return (f * (170 + 70 * k), -150 + side * 40)
        if a == "agachado":
            return (f * 120 + side * 40, 40)
        if a == "sentado" and near:
            return (f * 150, 60)
        return None

    def _gesture(self, p: Pose, side: float, f: float) -> tuple[float, float]:
        """Ángulos (hombro, codo) en grados: 0 = brazo colgando; positivo = hacia fuera."""
        t, a = p.t, p.gesture_amt
        near = side == f  # brazo del lado hacia el que mira
        if p.action == "correr":
            sw = math.sin(p.t * 11) * side
            return (10 + 40 * sw * f * side, -70)
        if p.action == "caer":
            k = ease(min(1.0, p.t / 0.55))
            return (12 + 120 * k, -20 * k)
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
        front_actions = ("manos_cabeza", "levantar_manos", "brazos_cruzados", "al_telefono", "sostener", "abrazar",
                         "golpear", "empujar")
        for side in (-1.0, 1.0):
            tgt = self._action_target(p, side, f, top)
            if tgt is not None:
                pts = self._ik(side, tgt, top, elbow_out=-1.0 if p.action == "brazos_cruzados" else 1.0)
                raised = (p.action or "sostener") in front_actions
                if p.action == "abrazar" and side != f:
                    raised = False  # el brazo de atrás rodea por detrás
            else:
                th, ph = self._gesture(p, side, f)
                pts = self._arm_points(side, th, ph, top)
                raised = ph < -60 or th > 60
                if p.action == "correr":
                    raised = side == f
            # los brazos levantados por delante se dibujan delante del cuerpo
            if back == raised:
                continue
            w1, w2 = 66 * L.wx ** 0.6, 56 * L.wx ** 0.6
            for (a, b), w in (((pts[0], pts[1]), w1), ((pts[1], pts[2]), w2)):
                c.drawLine(a[0], a[1], b[0], b[1], stroke(INK, w + OUTLINE * 2))
            for (a, b), w in (((pts[0], pts[1]), w1), ((pts[1], pts[2]), w2)):
                c.drawLine(a[0], a[1], b[0], b[1], stroke(sleeve, w))
                tube(c, a, b, w, sleeve)
            c.drawCircle(pts[1][0], pts[1][1], w2 * 0.5, fill(shade(sleeve, -0.08)))  # codo
            hx, hy = pts[-1]
            ux, uy = hx - pts[1][0], hy - pts[1][1]
            un = math.hypot(ux, uy) or 1
            ux, uy = ux / un, uy / un
            # puño de la manga
            cx, cy = hx - ux * 18, hy - uy * 18
            c.drawLine(cx - uy * w2 * 0.52, cy + ux * w2 * 0.52, cx + uy * w2 * 0.52, cy - ux * w2 * 0.52,
                       stroke(shade(sleeve, -0.35), 9))
            held = p.held and side == f and (p.action in ("", "sostener", "al_telefono"))
            if held:
                self._held(c, p, hx, hy, f)
            self._hand(c, hx, hy, ux, uy, side, f, fist=p.action in ("golpear",) and side == f, point=p.gesture == "point" and side == f and tgt is None)

    def _hand(self, c, hx, hy, ux, uy, side, f, fist=False, point=False) -> None:
        L = self.look
        s = 1.22
        tx, ty = hx - side * 26 * s + ux * 6, hy - 8 + uy * 6
        toon(c, oval(tx, ty, 13 * s, 20 * s), L.skin_color, outline=5)  # pulgar hacia el centro del cuerpo
        if fist:
            toon(c, oval(hx + ux * 8, hy + uy * 8, 34 * s, 30 * s), L.skin_color, light=(-f, -0.5))
            for k in (-1, 0, 1):
                c.drawLine(hx + ux * 26 + k * 12, hy + uy * 26 - 8, hx + ux * 26 + k * 12, hy + uy * 26 + 8,
                           stroke(shade(L.skin_color, -0.4), 3.5))
            return
        hand = poly([(hx - 30 * s, hy - 24 * s), (hx + 28 * s, hy - 26 * s), (hx + (34 + ux * 14) * s, hy + (8 + uy * 14) * s),
                     (hx + ux * 26 * s, hy + (30 + uy * 20) * s), (hx + (-32 + ux * 10) * s, hy + (10 + uy * 14) * s)], smooth=True)
        toon(c, hand, L.skin_color, light=(-f, -0.5))
        for k in ((-1, 0, 1) if STYLE.get("outline", 1.0) > 0 else ()):  # dedos (el estilo plano los omite)
            c.drawLine(hx + (k * 12 + ux * 12) * s, hy + (4 + uy * 12) * s, hx + (k * 13 + ux * 26) * s, hy + (8 + uy * 26) * s,
                       stroke(shade(L.skin_color, -0.4), 3.5))
        if point:
            fx, fy = hx + ux * 50, hy + uy * 50
            c.drawLine(hx, hy, fx, fy, stroke(INK, 26))
            c.drawLine(hx, hy, fx, fy, stroke(L.skin_color, 14))

    def _held(self, c, p: Pose, hx: float, hy: float, f: float) -> None:
        """Objeto en la mano (carta, móvil, pistola, taza...), pequeño y a la altura del puño."""
        from .props import PROPS
        draw = PROPS.get(p.held)
        if not draw:
            return
        c.save()
        if p.action == "al_telefono":
            c.translate(hx + f * 4, hy - 30)
            c.rotate(-12 * f)
            c.scale(0.2, 0.2)
        else:
            c.translate(hx + f * 30, hy - 70)
            c.scale(0.24, 0.24)
        draw(c, p.t)
        c.restore()

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
            c.drawPath(edge, fill("#fff1d6", 0.2 + 0.5 * STYLE.get("rim", 0.5)))
        if L.hat not in ("ninguno", "corona", "mantilla"):  # sombra de la gorra en la frente
            c.drawRect(skia.Rect.MakeLTRB(-200, -600, 200, -545), fill("#000000", 0.16))
        if STYLE.get("stubble", True) and (L.beard in ("barba_corta", "barba") or L.age == "mayor" and L.beard == "ninguna" and not L.female):
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
            bk = 1 + max(0.0, STYLE.get("blush", 0.22) - 0.22) * 1.6
            c.drawPath(oval(side * 92 + f * 22, -380, 34 * bk, 22 * bk),
                       fill("#ff6f7d" if STYLE.get("blush", 0.22) > 0.3 else "#e0705a", STYLE.get("blush", 0.22)))
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
        if STYLE["eyes"] == "dot":  # estilo plano: ojos de punto con brillo, cejas finas
            for side in (-1, 1):
                ex, ey = side * 56 + f * 26 + (p.look * 0.6 + f * 0.6) * 6, -462 - look_up * 6
                ry = 24 * open_amt * big
                c.drawPath(oval(ex, ey, 15 * big, max(3, ry)), fill("#1f1a24"))
                if open_amt > 0.4:
                    c.drawCircle(ex + 5, ey - 8, 5, fill("#ffffff"))
                by = ey - 44 - p.brow * 12
                y_l, y_r = by, by
                if p.worry > 0:
                    up = p.worry * 16
                    y_l, y_r = (by, by - up) if side < 0 else (by - up, by)
                elif p.brow < -0.3:
                    dn = -p.brow * 12
                    y_l, y_r = (by - dn, by + dn) if side < 0 else (by + dn, by - dn)
                c.drawLine(ex - 24, y_l, ex + 24, y_r, stroke(mix(L.hair, "#000000", 0.2), 11))
            return
        soft = STYLE["eyes"] == "soft"
        for side in (-1, 1):
            ex, ey = side * 58 + f * 26, -468
            rx, ry = (30, 36) if side == f else (27, 34)  # el ojo lejano un poco más pequeño
            rx, ry = rx * big, ry * big
            rx, ry = rx * STYLE.get("eye_size", 1.0), ry * STYLE.get("eye_size", 1.0)
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
            c.drawPath(lash, stroke(INK, (10 if not L.female else 12) * (0.75 if soft else 1.0)))
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
        k = STYLE.get("nose", 1.0)
        if k != 1.0:  # nariz más pequeña según el estilo
            c.save()
            c.translate(f * 50, -430)
            c.scale(k, k)
            c.translate(-f * 50, 430)
            self._nose_shape(c, f)
            c.restore()
            return
        self._nose_shape(c, f)

    def _nose_shape(self, c: skia.Canvas, f: float) -> None:
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
        r = p.mouth_round
        if r > 0:  # o / u: boca redonda y más estrecha
            w, h = w * (1 - 0.42 * r), h * (1 + 0.15 * r)
        elif r < 0:  # e / i: boca estirada y más baja
            w, h = w * (1 - 0.3 * r), h * (1 + 0.45 * r)
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
