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
    def __init__(self, width: int, height: int, accent: str, hook: str, hook_seconds: float = 2.8,
                 badge: str = "", end_card: str = "", end_start: float | None = None, caption_y: float = 0.64,
                 stamps: list[tuple[float, float, str]] | None = None, end_sub: str = ""):
        self.w, self.h = width, height
        self.stamps = [(a, b, t.upper().strip()) for a, b, t in (stamps or []) if t and t.strip()]
        self.caption_y = caption_y
        self.accent = accent
        self.hook = hook.upper()
        self.hook_seconds = hook_seconds
        self.badge = badge.upper()
        self.end_card = end_card.upper()
        self.end_sub = end_sub.upper()
        self.end_start = end_start

    def _box(self, d: ImageDraw.ImageDraw, text: str, size: int, top: int, fill: str, color: str) -> None:
        font = _font(size)
        lines = _wrap(d, text, font, int(self.w * 0.82))
        lh = int(font.size * 1.2)
        pad = int(size * 0.3)
        box_h = lh * len(lines) + pad * 2
        box_w = max(d.textlength(l, font=font) for l in lines) + pad * 3
        x0 = (self.w - box_w) / 2
        d.rounded_rectangle([x0, top, x0 + box_w, top + box_h], radius=int(size * 0.3), fill=fill)
        for k, line in enumerate(lines):
            tw = d.textlength(line, font=font)
            d.text(((self.w - tw) / 2, top + pad + k * lh), line, font=font, fill=color)

    def _stamp(self, d: ImageDraw.ImageDraw, text: str, slide: float) -> None:
        """Rótulo de dato (fecha, lugar, cifra): caja oscura con una franja del color de la marca, arriba a la izquierda."""
        size = int(self.w * 0.062)
        font = _font(size)
        while d.textlength(text, font=font) > self.w * 0.8 and size > 30:
            size -= 3
            font = _font(size)
        tw = d.textlength(text, font=font)
        pad = int(size * 0.32)
        bar = int(size * 0.22)
        x0 = int(self.w * 0.06 - slide * self.w * 0.12)
        y0 = int(self.h * 0.215)
        h = int(size * 1.25) + pad
        d.rounded_rectangle([x0, y0, x0 + bar + pad * 2 + tw, y0 + h], radius=int(size * 0.18), fill=(10, 10, 14, 215))
        d.rectangle([x0, y0, x0 + bar, y0 + h], fill=self.accent)
        d.text((x0 + bar + pad, y0 + pad * 0.55), text, font=font, fill="white")

    def _frame(self, words: list[Word], group: list[int] | None, active: int | None, show_hook: bool,
               show_end: bool = False, pop: bool = False, stamp: str | None = None,
               stamp_slide: float = 0.0) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if stamp and not show_hook and not show_end:
            self._stamp(d, stamp, stamp_slide)

        if self.badge:
            self._box(d, self.badge, int(self.w * 0.045), int(self.h * 0.085), (0, 0, 0, 170), self.accent)
        if show_end and self.end_card:
            self._box(d, self.end_card, int(self.w * 0.08), int(self.h * 0.36), self.accent, "#111111")
            if self.end_sub:  # promesa de la marca, debajo y más pequeña
                self._box(d, self.end_sub, int(self.w * 0.05), int(self.h * 0.6), (0, 0, 0, 200), "#ffffff")
            return img

        if show_hook:
            self._box(d, self.hook, int(self.w * 0.085), int(self.h * 0.16), self.accent, "#111111")

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
            y = int(self.h * self.caption_y)
            speaker = words[active].speaker if active is not None else ""
            if speaker:  # diálogo: etiqueta con el nombre de quien habla
                self._box(d, speaker.upper(), int(self.w * 0.05), y - int(self.w * 0.11), self.accent, "#111111")
            for j, t in zip(group, texts):
                if j == active and pop and not words[j].emph:  # rebote: entra un 18 % más grande
                    pf = _font(int(size * 1.18))
                    d.text((x - size * 0.04, y - size * 0.1), t, font=pf, fill=self.accent,
                           stroke_width=max(6, size // 13), stroke_fill="black")
                    x += d.textlength(t, font=pf) + space - size * 0.08
                    continue
                if words[j].emph and j == active:  # palabra clave: más grande, en color y un poco más arriba
                    big = _font(int(size * (1.5 if pop else 1.35)))
                    d.text((x, y - size * 0.22), t, font=big, fill=self.accent, stroke_width=max(8, size // 10),
                           stroke_fill="black")
                    x += d.textlength(t, font=big) + space
                    continue
                fill = self.accent if j == active or words[j].emph else "white"
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

        end_start = self.end_start if self.end_card and self.end_start is not None else total
        POP = 0.09  # cada palabra entra un poco más grande y "salta" a su tamaño
        SLIDE = 0.12  # el rótulo entra deslizándose
        cuts = sorted({0.0, total, self.hook_seconds, end_start, *[t for s, e, _ in events for t in (s, e)],
                       *[s + POP for s, e, _ in events if e - s > POP * 1.5],
                       *[t for a, b, _ in self.stamps for t in (a, a + SLIDE / 2, a + SLIDE, b)]})
        cuts = [c for c in cuts if 0 <= c <= total]

        cap_dir = workdir / "captions"
        cap_dir.mkdir(exist_ok=True)
        cache: dict[tuple, Path] = {}
        entries: list[tuple[Path, float]] = []
        for a, b in zip(cuts, cuts[1:]):
            if b - a < 1e-3:
                continue
            mid = (a + b) / 2
            ev = next(((s, e, i) for s, e, i in events if s <= mid < e), None)
            active = ev[2] if ev else None
            show_end = mid >= end_start
            pop = bool(ev) and (mid - ev[0]) < POP and (ev[1] - ev[0]) > POP * 1.5
            st = next(((a, t) for a, b, t in self.stamps if a <= mid < b), None)
            slide = round(max(0.0, 1 - (mid - st[0]) / SLIDE), 2) if st else 0.0
            key = (None if show_end else active, mid < self.hook_seconds, show_end, pop and not show_end,
                   st[1] if st else None, slide)
            if key not in cache:
                group = group_of[active] if active is not None and not show_end else None
                path = cap_dir / f"c{len(cache):04d}.png"
                self._frame(words, group, key[0], key[1], show_end, pop=key[3], stamp=key[4],
                            stamp_slide=key[5]).save(path, optimize=True)
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
