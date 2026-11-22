"""Acabado de cada fotograma según el estilo: luz de ambiente por hora del día, brillo de las luces (bloom),
grano de película y textura de papel. Se aplica sobre la imagen ya dibujada, antes de los subtítulos."""
from __future__ import annotations

import numpy as np
import skia

from .draw import STYLE

_textures: dict = {}


def _noise_image(W: int, H: int, seed: int, scale: int = 1, smooth: bool = False) -> skia.Image:
    rng = np.random.default_rng(seed)
    h, w = H // scale, W // scale
    n = rng.normal(0.5, 0.22 if not smooth else 0.12, (h, w))
    if smooth:  # textura de papel: manchas suaves + fibras
        k = np.ones(9) / 9
        n = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, n)
        n = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 0, n)
        n += rng.normal(0, 0.04, (h, w))
    g = (np.clip(n, 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([g, g, g, np.full_like(g, 255)])
    img = skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.ColorType.kRGBA_8888_ColorType)
    if scale > 1:
        img = img.resize(W, H)
    return img


def _texture(kind: str, W: int, H: int, k: int = 0) -> skia.Image:
    key = (kind, W, H, k)
    if key not in _textures:
        _textures[key] = _noise_image(W, H, seed=k + (100 if kind == "paper" else 0), scale=2 if kind == "grain" else 1,
                                      smooth=kind == "paper")
    return _textures[key]


MOOD_LIGHT = {  # (color, modo de mezcla, opacidad) de la luz de ambiente
    "noche": [("#22306e", skia.BlendMode.kMultiply, 0.32), ("#4a6cff", skia.BlendMode.kSoftLight, 0.18)],
    "atardecer": [("#ff9a4d", skia.BlendMode.kSoftLight, 0.2), ("#ffcf8a", skia.BlendMode.kScreen, 0.04)],
    "tormenta": [("#5a6878", skia.BlendMode.kMultiply, 0.22), ("#8aa0b8", skia.BlendMode.kSoftLight, 0.2)],
    "dia": [("#fff3d6", skia.BlendMode.kSoftLight, 0.14)],
}


def _hex(c: str, a: float) -> int:
    h = c.lstrip("#")
    return skia.ColorSetARGB(int(a * 255), int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def mood_light(c: skia.Canvas, W: int, H: int, mood: str, strength: float = 1.0) -> None:
    k = STYLE.get("mood", 1.0) * strength
    if not k:
        return
    for color, mode, a in MOOD_LIGHT.get(mood, []):
        p = skia.Paint(BlendMode=mode)
        # la luz entra desde arriba: más intensa arriba, se suaviza abajo
        p.setShader(skia.GradientShader.MakeLinear(points=[(0, 0), (0, H)],
                                                   colors=[_hex(color, min(1, a * k * 1.25)), _hex(color, a * k * 0.7)]))
        c.drawRect(skia.Rect.MakeWH(W, H), p)


def bloom(c: skia.Canvas, surface: skia.Surface, W: int, H: int) -> None:
    """Brillo solo en lo que ya es muy luminoso (lámparas, sol, pantallas, ventanas), sin velar el resto."""
    amt = STYLE.get("bloom", 0.0)
    if amt <= 0:
        return
    img = surface.makeImageSnapshot()
    t, g = 0.6, 2.6  # umbral y ganancia: (valor - umbral) * ganancia
    m = [g, 0, 0, 0, -t * g,
         0, g, 0, 0, -t * g,
         0, 0, g, 0, -t * g,
         0, 0, 0, 1, 0]
    cf = skia.ImageFilters.ColorFilter(skia.ColorFilters.Matrix(m))
    # se calcula a un tercio de tamaño (9 veces menos trabajo; el brillo es borroso, no se nota) y se amplía
    small = img.resize(W // 3, H // 3)
    flt = skia.ImageFilters.Blur(12, 12, skia.TileMode.kClamp, cf)
    p = skia.Paint(ImageFilter=flt, BlendMode=skia.BlendMode.kScreen, Alphaf=min(1.0, amt * 3.2))
    c.save()
    c.scale(3, 3)
    c.drawImage(small, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), p)
    c.restore()


def texture(c: skia.Canvas, W: int, H: int, frame: int) -> None:
    gr = STYLE.get("grain", 0.0)
    if gr > 0:  # grano de película: cambia cada fotograma (4 texturas en bucle)
        p = skia.Paint(BlendMode=skia.BlendMode.kOverlay, Alphaf=min(1.0, gr * 4))
        c.drawImage(_texture("grain", W, H, frame % 4), 0, 0, skia.SamplingOptions(), p)
    pa = STYLE.get("paper", 0.0)
    if pa > 0:  # textura de papel: fija, como una ilustración impresa
        p = skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=min(1.0, pa * 4))
        c.drawImage(_texture("paper", W, H), 0, 0, skia.SamplingOptions(), p)
