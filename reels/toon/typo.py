"""Modo «tipografía» (La Cabeza por Dentro): sin personajes. Fondo oscuro con humo, la palabra clave de cada plano
enorme (entra con un golpe), el número del punto de la lista y un icono simbólico en penumbra. Pensado para listas
de psicología oscura («3 señales de que…»)."""
from __future__ import annotations

import math
import random
import re
import subprocess
from pathlib import Path

import skia

from . import finish as F
from .draw import STYLE, fill, mix, oval, poly, radial, rrect, set_style, shade, stroke

FONT = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Anton-Regular.ttf"
_tf = None


def _font(size: float) -> skia.Font:
    global _tf
    if _tf is None:
        _tf = skia.Typeface.MakeFromFile(str(FONT))
    return skia.Font(_tf, size)


# ---------------- iconos simbólicos ----------------

def marioneta(c, t):
    """Mano que mueve hilos (manipulación)."""
    sw = math.sin(t * 1.6) * 8
    c.drawPath(poly([(-170, -330), (170, -330), (190, -250), (-190, -250)], smooth=True), fill("#d8d2c8"))
    for k, x in enumerate((-150, -75, 0, 75, 150)):
        c.drawPath(rrect(x - 22, -420 - (k % 2) * 30, 44, 110, 22), fill("#d8d2c8"))
        c.drawLine(x, -250, x * 0.6 + sw, 120 + abs(x) * 0.3, stroke("#e9e4d8", 3, 0.8))
    c.save()
    c.translate(sw * 0.6, 220)
    c.drawCircle(0, -70, 48, fill("#b9b1a6"))
    c.drawPath(rrect(-55, -25, 110, 160, 40), fill("#b9b1a6"))
    c.restore()


def mascara(c, t):
    """Máscara teatral (fingir, doble cara)."""
    face = poly([(-180, -220), (180, -220), (200, -40), (120, 160), (0, 230), (-120, 160), (-200, -40)], smooth=True)
    c.drawPath(face, fill("#e9e4d8"))
    for sx in (-80, 80):
        c.drawPath(oval(sx, -60, 46, 30), fill("#0c0a12"))
    smile = skia.Path()
    smile.moveTo(-90, 80)
    smile.quadTo(0, 150 + math.sin(t * 2) * 10, 90, 80)
    c.drawPath(smile, stroke("#0c0a12", 16))
    c.drawLine(0, -220, 0, 230, stroke("#0c0a12", 6, 0.35))


def ojo(c, t):
    """Ojo que observa (calar a la gente, mentiras)."""
    look = math.sin(t * 0.9) * 40
    eye = poly([(-260, 0), (0, -150), (260, 0), (0, 150)], smooth=True)
    c.drawPath(eye, fill("#e9e4d8"))
    c.save()
    c.clipPath(eye, doAntiAlias=True)
    c.drawCircle(look, 0, 105, fill("#3a2a5a"))
    c.drawCircle(look, 0, 50, fill("#0c0a12"))
    c.drawCircle(look + 30, -35, 18, fill("#ffffff", 0.8))
    c.restore()


def cadena(c, t):
    """Eslabones (dependencia, no poder irse)."""
    for k in range(4):
        y = -270 + k * 160 + math.sin(t * 1.4 + k) * 6
        r = skia.Rect.MakeLTRB(-70, y - 100, 70, y + 100) if k % 2 == 0 else skia.Rect.MakeLTRB(-25, y - 100, 25, y + 100)
        c.drawOval(r, stroke("#cfc8bd", 34))


ICONS = {"marioneta": marioneta, "mascara": mascara, "ojo": ojo, "cadena": cadena}


def _icon_for(block) -> str | None:
    if block.prop:
        return block.prop
    text = (block.narration + " " + (block.on_screen or "")).lower()
    for words, icon in ((("manipul", "control", "hilos", "marioneta"), "marioneta"),
                        (("miente", "mentir", "mentira", "finge", "cara", "falso"), "mascara"),
                        (("mira", "observa", "calar", "señal", "delata", "ojos"), "ojo"),
                        (("no puedes dejar", "atado", "depend", "engancha"), "cadena")):
        if any(w in text for w in words):
            return icon
    return None


# ---------------- plano ----------------

def _smoke(c, W, H, t, accent, seed):
    rnd = random.Random(seed)
    for k in range(9):
        x = (rnd.uniform(-0.2, 1.2) * W + t * rnd.uniform(-25, 25)) % (W * 1.4) - W * 0.2
        y = rnd.uniform(0.15, 0.95) * H + math.sin(t * 0.3 + k) * 30
        r = rnd.uniform(260, 520)
        p = fill(mix(accent, "#1a1626", 0.75), 0.18)
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, r * 0.45))
        c.drawCircle(x, y, r, p)


def _text_center(c, text, size, y, W, color, alpha=1.0, stroke_w=0.0):
    f = _font(size)
    w = f.measureText(text)
    while w > W * 0.88 and size > 40:
        size *= 0.92
        f = _font(size)
        w = f.measureText(text)
    x = (W - w) / 2
    if stroke_w:
        c.drawString(text, x, y, f, skia.Paint(Color=skia.ColorSetARGB(int(255 * alpha), 0, 0, 0), AntiAlias=True,
                                                Style=skia.Paint.kStroke_Style, StrokeWidth=stroke_w))
    c.drawString(text, x, y, f, fill(color, alpha))
    return size


def _split_keyword(text: str) -> tuple[str, str]:
    """«3 · CULPA» → ("3", "CULPA"). Sin número → ("", texto)."""
    m = re.match(r"^\s*(?:N[º°o]\.?\s*)?(\d{1,2})\s*[·.:\-–)]\s*(.+)$", text or "")
    return (m.group(1), m.group(2).strip()) if m else ("", (text or "").strip())


def draw_typo(c, W, H, t, dur, block, accent, seed, punches):
    k = t / max(dur, 0.01)
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#0c0a12"))
    c.drawRect(skia.Rect.MakeWH(W, H), radial(fill("#0c0a12"), (W * 0.5, H * 0.42), H * 0.7,
                                              [mix(accent, "#1a1626", 0.6), "#08070c"]))
    _smoke(c, W, H, t, accent, seed)
    # icono en penumbra, con luz de contorno del color de la marca
    icon = _icon_for(block) or ("ojo", "mascara", "marioneta", "cerebro", "cadena", "movil")[seed % 6]
    from .props import PROPS
    draw = ICONS.get(icon) or PROPS.get(icon or "")
    if draw:
        c.save()
        c.translate(W * 0.5, H * 0.66 + math.sin(t * 1.2) * 10)
        sc = 0.9 + 0.04 * k
        c.scale(sc, sc)
        c.saveLayer(None, skia.Paint(Alphaf=0.55))
        draw(c, t)
        c.restore()
        c.restore()
        glow = fill(accent, 0.18)
        glow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 120))
        c.drawCircle(W * 0.5, H * 0.66, 260, glow)
    # palabra clave enorme (entra con un golpe y respira)
    num, word = _split_keyword(block.on_screen or block.emphasis or "")
    pop = 1 + 0.35 * max(0.0, 1 - t / 0.22) ** 2
    for p in punches:
        d = t - p
        if 0 <= d < 0.35:
            pop *= 1 + 0.12 * (1 - d / 0.35)
    shake = (math.sin(t * 60) * 6 * max(0.0, 1 - t / 0.25))
    if num:
        c.save()
        c.translate(W / 2 + shake, H * 0.2)
        c.scale(pop, pop)
        c.translate(-W / 2, -H * 0.2)
        _text_center(c, num, 300, H * 0.27, W, accent, 0.95)
        c.restore()
    if word:
        c.save()
        c.translate(W / 2 + shake, H * 0.4)
        c.scale(pop, pop)
        c.translate(-W / 2, -H * 0.4)
        words = word.upper().split()
        lines = [" ".join(words)] if len(words) <= 2 else [" ".join(words[: len(words) // 2]), " ".join(words[len(words) // 2:])]
        for i, line in enumerate(lines):
            _text_center(c, line, 170, H * (0.42 + i * 0.09) - (len(lines) - 1) * H * 0.045, W, "#f2eee8", 1.0, 10)
        c.restore()
    # línea fina del color de la marca bajo la palabra
    c.drawRect(skia.Rect.MakeXYWH(W * 0.35, H * 0.47, W * 0.3 * min(1.0, t / 0.4), 6), fill(accent, 0.8))


def _rgb(hexc):
    h = hexc.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def render_typo_shot(block, dur: float, out: Path, W: int, H: int, fps: int, accent: str, seed: int,
                     punches: list[float]) -> Path:
    set_style("tipografia")
    frames = max(1, round(dur * fps))
    surface = skia.Surface(W, H)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps),
         "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", str(out)],
        stdin=subprocess.PIPE)
    for i in range(frames):
        t = i / fps
        c = surface.getCanvas()
        c.clear(skia.ColorBLACK)
        c.save()
        z = 1 + 0.05 * (t / max(dur, 0.01))  # acercamiento lento
        c.translate(W / 2, H / 2)
        c.scale(z, z)
        c.translate(-W / 2, -H / 2)
        draw_typo(c, W, H, t, dur, block, accent, seed, punches)
        c.restore()
        F.bloom(c, surface, W, H)
        F.texture(c, W, H, i)
        from . import scenes as S
        S.vignette(c, W, H, STYLE["vignette"])
        proc.stdin.write(surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg falló renderizando {out}")
    return out
