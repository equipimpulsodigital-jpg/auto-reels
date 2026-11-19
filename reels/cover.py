"""Portada de cada vídeo (9:16): fotograma con el personaje + gancho enorme con el estilo de la marca.

Se envía como portada a Instagram y TikTok (y a YouTube si el canal está verificado), para que en el
perfil y en el feed no salga un fotograma cualquiera. El texto va en la franja central para que no se
corte en la cuadrícula del perfil (que recorta a 3:4).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import ASSETS
from .media import run_ffmpeg

FONT = ASSETS / "fonts" / "Anton-Regular.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size)


def _wrap(d: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if d.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def pick_frame(shots: list[Path], framings: list[str], durations: list[float]) -> tuple[Path, float]:
    """El mejor plano para la portada: el primer primer plano de un personaje (si no, el primer plano)."""
    for f, fr, d in zip(shots, framings, durations):
        if fr == "personaje":
            return f, d * 0.55
    return shots[0], min(1.2, durations[0] * 0.6)


def make_cover(shot: Path, at: float, hook: str, accent: str, badge: str, brand: str, out: Path) -> Path:
    frame = out.with_suffix(".frame.png")
    run_ffmpeg(["-ss", f"{at:.2f}", "-i", shot, "-frames:v", "1", frame])
    img = Image.open(frame).convert("RGB")
    W, H = img.size
    # oscurece arriba y abajo para que el texto se lea siempre
    shade = Image.new("L", (1, H))
    for y in range(H):
        v = max(0.0, (0.5 - y / H) / 0.5) * 170 + max(0.0, (y / H - 0.72) / 0.28) * 200
        shade.putpixel((0, y), int(min(220, v)))
    dark = Image.new("RGB", (W, H), (8, 8, 12))
    img = Image.composite(dark, img, shade.resize((W, H)))
    d = ImageDraw.Draw(img)

    text = hook.upper().strip()
    size = 150
    while size > 70:
        font = _font(size)
        lines = _wrap(d, text, font, int(W * 0.84))
        if len(lines) <= 3:
            break
        size -= 8
    line_h = int(size * 1.08)
    block_h = line_h * len(lines) + 60
    top = int(H * 0.15)  # arriba: así se ve la cara del personaje (el primer plano la deja en el centro)
    # caja de color de la marca, ligeramente girada, con sombra
    box = Image.new("RGBA", (W, block_h + 40), (0, 0, 0, 0))
    bd = ImageDraw.Draw(box)
    widest = max(d.textlength(line, font=font) for line in lines)
    x0 = int((W - widest) / 2) - 40
    bd.rounded_rectangle((x0, 20, W - x0, 20 + block_h), radius=34, fill=accent)
    y = 20 + 30
    for line in lines:
        lw = bd.textlength(line, font=font)
        bd.text(((W - lw) / 2, y - size * 0.06), line, font=font, fill="#111111")
        y += line_h
    shadow = Image.new("RGBA", box.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0 + 10, 34, W - x0 + 10, 34 + block_h), radius=34, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    layer = Image.alpha_composite(shadow, box).rotate(-2.5, resample=Image.BICUBIC, expand=False)
    img.paste(layer, (0, top), layer)

    if badge:
        bf = _font(64)
        bw = d.textlength(badge, font=bf)
        bx, by = (W - bw) / 2, top - 105
        d.rounded_rectangle((bx - 28, by - 10, bx + bw + 28, by + 84), radius=18, fill=(0, 0, 0, 255))
        d.text((bx, by), badge, font=bf, fill=accent)
    if brand:
        f2 = _font(52)
        tw = d.textlength(brand.upper(), font=f2)
        d.text(((W - tw) / 2, H * 0.84), brand.upper(), font=f2, fill="white", stroke_width=5, stroke_fill="black")
    img.save(out, quality=90)
    frame.unlink(missing_ok=True)
    return out
