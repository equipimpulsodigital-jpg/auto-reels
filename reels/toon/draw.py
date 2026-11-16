"""Utilidades de dibujo vectorial (Skia) para la animación tipo caricatura."""
from __future__ import annotations

import math

import skia

INK = "#1b1411"  # color del contorno de todo el dibujo
OUTLINE = 7.0


def col(hex_color: str, alpha: float = 1.0) -> int:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
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
    canvas.drawPath(path, fill(color))
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
    if outline > 0:
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
