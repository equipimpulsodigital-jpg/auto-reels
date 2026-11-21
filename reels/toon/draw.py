"""Utilidades de dibujo vectorial (Skia) para la animación tipo caricatura."""
from __future__ import annotations

import math

import skia

INK = "#1b1411"  # color del contorno de todo el dibujo
OUTLINE = 7.0


# Estilo visual de la marca (lo fija film.render_shot según config: channels.<id>.style).
STYLES = {
    # Clave común: outline (grosor de la tinta; 0 = sin líneas), ink (color de la tinta; "auto" = del color de la forma),
    # shade (fuerza de la sombra lateral), gradient (degradado vertical en cada forma), sat/light/warm/contrast
    # (etalonaje de todos los colores), head/eyes/nose/stubble/blush/eye_size (personaje), y el acabado de la imagen:
    # bloom (brillo de las luces), grain (grano), paper (textura de papel), mood (fuerza de la luz de ambiente),
    # rim (luz de contorno en los personajes), vignette.
    # el de siempre, con más acabado: sombras ricas, luz de contorno, un punto de brillo y de grano
    "caricatura": dict(outline=1.0, ink=None, shade=1.15, gradient=0.06, sat=1.04, light=0.0, warm=0.0, contrast=1.04,
                       head=1.0, eyes="cartoon", vignette=0.3, nose=1.0, stubble=True, blush=0.22, eye_size=1.0,
                       bloom=0.18, grain=0.018, paper=0.0, mood=1.0, rim=0.5),
    # divulgación moderna (tipo Kurzgesagt): sin ninguna línea, degradados suaves, colores vivos y mucho brillo
    "plano": dict(outline=0.0, ink=None, shade=0.3, gradient=0.13, sat=1.14, light=0.03, warm=0.0, contrast=1.06,
                  head=0.82, eyes="dot", vignette=0.12, nose=0.55, stubble=False, blush=0.3, eye_size=1.0,
                  bloom=0.22, grain=0.02, paper=0.0, mood=0.9, rim=0.0),
    # novela gráfica de misterio (sin uso por ahora)
    "comic": dict(outline=1.4, ink="#0b0a0d", shade=2.2, gradient=0.0, sat=0.55, light=-0.07, warm=-0.12, contrast=1.25,
                  head=0.84, eyes="cartoon", vignette=0.65, nose=0.9, stubble=True, blush=0.0, eye_size=0.85,
                  bloom=0.1, grain=0.08, paper=0.0, mood=1.2, rim=0.3),
    # ilustración amable: línea fina del color de la forma, degradados suaves, papel y brillo cálido
    "amable": dict(outline=0.6, ink="auto", shade=0.45, gradient=0.1, sat=1.0, light=0.0, warm=0.05, contrast=1.04,
                   head=0.92, eyes="soft", vignette=0.08, nose=0.6, stubble=False, blush=0.5, eye_size=1.25,
                   bloom=0.24, grain=0.0, paper=0.07, mood=0.8, rim=0.25),
}
STYLE = dict(STYLES["caricatura"])


def set_style(name: str) -> None:
    STYLE.clear()
    STYLE.update(STYLES.get(name or "caricatura", STYLES["caricatura"]))
    _cache.clear()


_cache: dict = {}


def _grade(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Etalonaje del estilo: saturación, luz, temperatura y contraste aplicados a todos los colores."""
    S = STYLE
    if S["sat"] == 1.0 and not S["light"] and not S["warm"] and S["contrast"] == 1.0:
        return r, g, b
    key = (r, g, b)
    if key in _cache:
        return _cache[key]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    out = []
    for k, v in enumerate((r, g, b)):
        v = lum + (v - lum) * S["sat"]
        v = (v - 128) * S["contrast"] + 128
        v += S["light"] * 255
        v += S["warm"] * 255 * (0.6, 0.15, -0.6)[k]
        out.append(int(max(0, min(255, v))))
    _cache[key] = tuple(out)
    return _cache[key]


def col(hex_color: str, alpha: float = 1.0) -> int:
    h = hex_color.lstrip("#")
    r, g, b = _grade(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return skia.ColorSetARGB(int(max(0, min(1, alpha)) * 255), r, g, b)


def mix(a: str, b: str, t: float) -> str:
    """Mezcla dos colores hex (t=0 → a, t=1 → b)."""
    ha, hb = a.lstrip("#"), b.lstrip("#")
    out = []
    for k in range(0, 6, 2):
        va, vb = int(ha[k:k + 2], 16), int(hb[k:k + 2], 16)
        out.append(round(va + (vb - va) * t))
    return "#" + "".join(f"{v:02x}" for v in out)


def shade(c: str, t: float) -> str:
    """t<0 oscurece, t>0 aclara."""
    return mix(c, "#000000", -t) if t < 0 else mix(c, "#ffffff", t)


def fill(color: str, alpha: float = 1.0) -> skia.Paint:
    return skia.Paint(Color=col(color, alpha), AntiAlias=True, Style=skia.Paint.kFill_Style)


def stroke(color: str = INK, width: float = OUTLINE, alpha: float = 1.0) -> skia.Paint:
    if color == INK:  # el contorno sigue el estilo (grosor y color de la tinta)
        if STYLE["outline"] == 0:  # estilo sin líneas: los detalles finos se ven como un trazo suave, no negro
            width *= 0.6
            color, alpha = "#2a2238", alpha * 0.35
        else:
            width *= STYLE["outline"]
            if STYLE["ink"] and STYLE["ink"] != "auto":
                color = STYLE["ink"]
            elif STYLE["ink"] == "auto":
                alpha *= 0.55
    return skia.Paint(Color=col(color, alpha), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                      StrokeWidth=width, StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)


def blur(paint: skia.Paint, sigma: float) -> skia.Paint:
    paint.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sigma))
    return paint


def linear(paint: skia.Paint, p0, p1, colors: list[str], pos: list[float] | None = None) -> skia.Paint:
    paint.setShader(skia.GradientShader.MakeLinear(points=[p0, p1], colors=[col(c) for c in colors],
                                                   positions=pos))
    return paint


def radial(paint: skia.Paint, center, r: float, colors: list[str], alphas: list[float] | None = None) -> skia.Paint:
    alphas = alphas or [1.0] * len(colors)
    paint.setShader(skia.GradientShader.MakeRadial(center=center, radius=max(r, 1),
                                                   colors=[col(c, a) for c, a in zip(colors, alphas)]))
    return paint


def oval(cx: float, cy: float, rx: float, ry: float) -> skia.Path:
    p = skia.Path()
    p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    return p


def rrect(x: float, y: float, w: float, h: float, r: float) -> skia.Path:
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r))
    return p


def poly(points: list[tuple[float, float]], smooth: bool = False) -> skia.Path:
    """Polígono; con smooth=True pasa suavemente por los puntos medios (formas orgánicas)."""
    p = skia.Path()
    if not smooth:
        p.moveTo(*points[0])
        for pt in points[1:]:
            p.lineTo(*pt)
        p.close()
        return p
    n = len(points)
    mids = [((points[i][0] + points[(i + 1) % n][0]) / 2, (points[i][1] + points[(i + 1) % n][1]) / 2)
            for i in range(n)]
    p.moveTo(*mids[-1])
    for i in range(n):
        p.quadTo(points[i][0], points[i][1], mids[i][0], mids[i][1])
    p.close()
    return p


def toon(canvas: skia.Canvas, path: skia.Path, color: str, outline: float = OUTLINE,
         light: tuple[float, float] | None = None, shade_amt: float = 0.22) -> None:
    """Relleno plano + sombra lateral suave + contorno grueso: el look de caricatura."""
    g = STYLE.get("gradient", 0.0)
    if g > 0:  # degradado vertical suave: más luz arriba, más sombra abajo
        b0 = path.computeTightBounds()
        canvas.drawPath(path, linear(fill(color), (0, b0.top()), (0, b0.bottom()), [shade(color, g), shade(color, -g)]))
    else:
        canvas.drawPath(path, fill(color))
    shade_amt *= STYLE["shade"]
    if light is not None:
        b = path.computeTightBounds()
        canvas.save()
        canvas.clipPath(path, doAntiAlias=True)
        dx, dy = light
        sh = skia.Path(path)
        sh.offset(-dx * b.width() * 0.22, -dy * b.height() * 0.18)
        # zona en sombra = forma original menos la forma desplazada hacia la luz
        diff = skia.Op(path, sh, skia.PathOp.kDifference_PathOp)
        if diff is not None:
            canvas.drawPath(diff, fill(shade(color, -shade_amt)))
        canvas.restore()
    if outline > 0 and STYLE["outline"] > 0:
        if STYLE["ink"] == "auto":  # línea del mismo color, más oscura
            canvas.drawPath(path, skia.Paint(Color=col(shade(color, -0.42)), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                             StrokeWidth=outline * STYLE["outline"], StrokeJoin=skia.Paint.kRound_Join))
        else:
            canvas.drawPath(path, stroke(INK, outline))


def limb(canvas: skia.Canvas, pts: list[tuple[float, float]], width: float, color: str) -> None:
    """Brazo/pierna: trazo grueso redondeado con contorno."""
    p = skia.Path()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    canvas.drawPath(p, stroke(INK, width + OUTLINE * 2))
    canvas.drawPath(p, stroke(color, width))


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def noise1(t: float, seed: float = 0.0) -> float:
    """Ruido suave y determinista en [-1, 1] (suma de senos)."""
    return (math.sin(t * 1.7 + seed) * 0.5 + math.sin(t * 2.9 + seed * 2.3) * 0.3
            + math.sin(t * 4.3 + seed * 0.7) * 0.2)
