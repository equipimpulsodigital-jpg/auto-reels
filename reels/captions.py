"""Subtítulos estilo TikTok (palabra activa resaltada) renderizados como PNG con Pillow.

Se genera una secuencia de imágenes transparentes con su duración y FFmpeg la superpone en una
sola pasada. Así no depende de libass/drawtext, que no todas las builds de FFmpeg incluyen.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import ASSETS
from .tts import Word

FONT = ASSETS / "fonts" / "Anton-Regular.ttf"
MAX_WORDS = 3
MAX_CHARS = 18


def _chunks(words: list[Word]) -> list[list[int]]:
    """Agrupa índices de palabras en bloques cortos que se muestran juntos."""
    groups: list[list[int]] = []
    cur: list[int] = []
    for i, w in enumerate(words):
        text_len = sum(len(words[j].text) + 1 for j in cur) + len(w.text)
        gap = w.start - words[i - 1].end if i else 0
        if cur and (len(cur) >= MAX_WORDS or text_len > MAX_CHARS or gap > 0.35):
            groups.append(cur)
            cur = []
        cur.append(i)
        if re.search(r"[.,;:!?…]$", w.text):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


class CaptionRenderer:
    def __init__(self, width: int, height: int, accent: str, hook: str, hook_seconds: float = 2.8):
        self.w, self.h = width, height
        self.accent = accent
        self.hook = hook.upper()
        self.hook_seconds = hook_seconds

    def _frame(self, words: list[Word], group: list[int] | None, active: int | None, show_hook: bool) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        if show_hook:
            font = _font(int(self.w * 0.085))
            lines = _wrap(d, self.hook, font, int(self.w * 0.82))
            lh = int(font.size * 1.2)
            top = int(self.h * 0.17)
            box_h = lh * len(lines) + 50
            box_w = max(d.textlength(l, font=font) for l in lines) + 70
            x0 = (self.w - box_w) / 2
            d.rounded_rectangle([x0, top, x0 + box_w, top + box_h], radius=28, fill=self.accent)
            for k, line in enumerate(lines):
                tw = d.textlength(line, font=font)
                d.text(((self.w - tw) / 2, top + 22 + k * lh), line, font=font, fill="#111111")

        if group:
            size = int(self.w * 0.105)
            texts = [words[j].text.strip(",.;:…").upper() for j in group]
            font = _font(size)
            while d.textlength(" ".join(texts), font=font) > self.w * 0.9 and size > 40:
                size -= 4
                font = _font(size)
            space = d.textlength(" ", font=font)
            total = sum(d.textlength(t, font=font) for t in texts) + space * (len(texts) - 1)
            x = (self.w - total) / 2
            y = int(self.h * 0.64)
            for j, t in zip(group, texts):
                fill = self.accent if j == active else "white"
                d.text((x, y), t, font=font, fill=fill, stroke_width=max(6, size // 14), stroke_fill="black")
                x += d.textlength(t, font=font) + space
        return img

    def render(self, words: list[Word], total: float, workdir: Path) -> Path:
        """Crea las imágenes y un fichero concat de FFmpeg con sus duraciones."""
        groups = _chunks(words)
        group_of = {j: g for g in groups for j in g}

        # Intervalos: cada palabra se ve desde su inicio hasta el de la siguiente
        # (o un poco después de terminar, si la siguiente es de otro bloque).
        events: list[tuple[float, float, int]] = []
        for i, w in enumerate(words):
            nxt = words[i + 1].start if i + 1 < len(words) else total
            same_group = i + 1 < len(words) and group_of[i + 1] is group_of[i]
            end = nxt if same_group else min(nxt, w.end + 0.4)
            events.append((w.start, max(end, w.start + 0.05), i))

        cuts = sorted({0.0, total, self.hook_seconds, *[t for s, e, _ in events for t in (s, e)]})
        cuts = [c for c in cuts if 0 <= c <= total]

        cap_dir = workdir / "captions"
        cap_dir.mkdir(exist_ok=True)
        cache: dict[tuple, Path] = {}
        entries: list[tuple[Path, float]] = []
        for a, b in zip(cuts, cuts[1:]):
            if b - a < 1e-3:
                continue
            mid = (a + b) / 2
            active = next((i for s, e, i in events if s <= mid < e), None)
            key = (active, mid < self.hook_seconds)
            if key not in cache:
                group = group_of[active] if active is not None else None
                path = cap_dir / f"c{len(cache):04d}.png"
                self._frame(words, group, active, key[1]).save(path, optimize=True)
                cache[key] = path
            if entries and entries[-1][0] == cache[key]:
                entries[-1] = (cache[key], entries[-1][1] + (b - a))
            else:
                entries.append((cache[key], b - a))

        listfile = workdir / "captions.txt"
        lines = [f"file '{p.resolve()}'\nduration {d:.3f}\n" for p, d in entries]
        lines.append(f"file '{entries[-1][0].resolve()}'\n")  # el demuxer concat ignora la última duración
        listfile.write_text("".join(lines))
        return listfile
