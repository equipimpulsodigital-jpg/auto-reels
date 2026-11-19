"""Recopilación semanal para YouTube.

Junta las historias completas (todas sus partes) publicadas en los últimos días en un vídeo largo
horizontal (el vertical en el centro sobre un fondo difuminado), con capítulos, título y miniatura.
Los vídeos salen de los artefactos que guarda GitHub (14 días); no hace falta volver a generarlos.
"""
from __future__ import annotations

import json
import re
from urllib.parse import quote_plus
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import ASSETS, channel_data
from .media import probe_duration, run_ffmpeg

FONT = ASSETS / "fonts" / "Anton-Regular.ttf"
W, H = 1920, 1080


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def find_clips(cid: str, roots: list[Path]) -> dict[str, Path]:
    """Vídeos publicados disponibles: {"20261119_1300": carpeta} (el nombre de la carpeta es la franja)."""
    pat = re.compile(rf"^{re.escape(cid)}_(\d{{8}}_\d{{4}})$")
    found: dict[str, Path] = {}
    for root in roots:
        for reel in root.rglob("reel.mp4"):
            m = pat.match(reel.parent.name)
            if m:
                found[m.group(1)] = reel.parent
    return found


def pick_stories(cfg: dict, clips: dict[str, Path], max_minutes: float) -> list[dict]:
    """Historias completas, en orden de publicación, que no hayan salido ya en otra recopilación."""
    tz = ZoneInfo(cfg["publish"].get("timezone", "Europe/Madrid"))
    folder = channel_data(cfg)
    history = _load(folder / "history.json", [])
    done = {t for c in _load(folder / "compilations.json", []) for t in c.get("stories", [])}
    stories = []
    for h in history:
        parts = sorted(h.get("published_parts", []), key=lambda p: p["part"])
        if h["series_title"] in done or len(parts) < h.get("parts", 1) or not all(p.get("slot") for p in parts):
            continue
        keys = [datetime.fromisoformat(p["slot"]).astimezone(tz).strftime("%Y%m%d_%H%M") for p in parts]
        if not all(k in clips for k in keys):
            continue
        dirs = [clips[k] for k in keys]
        stories.append({"title": h["series_title"], "topic": h.get("topic", ""), "first": keys[0], "dirs": dirs,
                        "book": h.get("book") or _book_from_queue(folder, h["series_title"]),
                        "seconds": sum(probe_duration(d / "reel.mp4") for d in dirs)})
    stories.sort(key=lambda s: s["first"])
    chosen, total = [], 0.0
    for s in stories:
        if total + s["seconds"] > max_minutes * 60 and chosen:
            break
        chosen.append(s)
        total += s["seconds"]
    return chosen


def _book_from_queue(folder: Path, title: str):
    """Libro recomendado de historias escritas antes de guardarlo en el historial (si lo tienen)."""
    for q in _load(folder / "state.json", {}).get("queue", []):
        if q["series"].get("series_title") == title:
            return q["series"].get("book")
    return None


def amazon_link(book: dict, tag: str) -> str:
    """Búsqueda del libro en Amazon.es con el ID de afiliado (siempre lleva a la edición disponible)."""
    return f"https://www.amazon.es/s?k={quote_plus(book['title'] + ' ' + book['author'])}&i=stripbooks&tag={tag}"


def _horizontal(src: Path, out: Path) -> None:
    """Vertical 9:16 → horizontal 16:9 con el mismo vídeo difuminado de fondo."""
    run_ffmpeg([
        "-i", src, "-filter_complex",
        "[0:v]split[a][b];"
        f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:2,eq=brightness=-0.18[bg];"
        f"[b]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0,fps=30,format=yuv420p[v];"
        "[0:a]aresample=48000,aformat=channel_layouts=stereo[aud]",
        "-map", "[v]", "-map", "[aud]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out,
    ])


def _ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def build_video(stories: list[dict], workdir: Path) -> tuple[Path, list[tuple[float, str]]]:
    workdir.mkdir(parents=True, exist_ok=True)
    pieces, chapters, t = [], [], 0.0
    for i, s in enumerate(stories):
        chapters.append((t, s["title"]))
        for j, d in enumerate(s["dirs"]):
            out = workdir / f"h_{i:02d}_{j}.mp4"
            _horizontal(d / "reel.mp4", out)
            pieces.append(out)
            t += probe_duration(out)
    lst = workdir / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in pieces))
    video = workdir / "recopilacion.mp4"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", video])
    return video, chapters


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size)


def thumbnail(text: str, frame_src: Path, accent: str, out: Path) -> Path:
    """Miniatura 1280x720: fotograma de fondo, el dibujo a la derecha y el título enorme a la izquierda."""
    frame = out.with_suffix(".frame.png")
    run_ffmpeg(["-ss", "1.6", "-i", frame_src, "-frames:v", "1", frame])
    src = Image.open(frame).convert("RGB")
    tw, th = 1280, 720
    bg = src.resize((tw, int(src.height * tw / src.width))).crop((0, 300, tw, 300 + th))
    bg = bg.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.45))
    fg = src.resize((int(src.width * th / src.height), th))
    bg.paste(fg, (tw - fg.width - 30, 0))
    d = ImageDraw.Draw(bg)
    words, lines, size = text.upper().split(), [], 128
    max_w = tw - fg.width - 90
    while size > 50:
        font, lines, cur = _font(size), [], ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if d.textlength(trial, font=font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) * size * 1.08 <= th - 80:
            break
        size -= 8
    y = (th - len(lines) * size * 1.08) / 2
    for k, line in enumerate(lines):
        d.text((45, y), line, font=font, fill=accent if k == 0 else "white", stroke_width=max(6, size // 12),
               stroke_fill="black")
        y += size * 1.08
    bg.save(out, quality=92)
    return out


def next_slot(cfg: dict, now: datetime | None = None) -> datetime:
    """Próximo día y hora de publicación de la recopilación (por defecto, domingo a las 11:00)."""
    cc = cfg.get("compilation", {})
    tz = ZoneInfo(cfg["publish"].get("timezone", "Europe/Madrid"))
    now = (now or datetime.now(timezone.utc)).astimezone(tz)
    h, m = map(int, cc.get("time", "11:00").split(":"))
    day = now.date() + timedelta(days=(int(cc.get("weekday", 6)) - now.weekday()) % 7)
    slot = datetime(day.year, day.month, day.day, h, m, tzinfo=tz)
    if slot < now + timedelta(minutes=30):  # ya ha pasado: lo antes posible, en la siguiente hora en punto
        slot = (now + timedelta(minutes=90)).replace(minute=0, second=0, microsecond=0)
    return slot


def make_texts(cfg: dict, stories: list[dict], chapters: list[tuple[float, str]], slot: datetime) -> dict:
    ch = cfg["channel"]
    templates = ch.get("compilation_titles") or ["{n} historias que no te puedes perder | Recopilación"]
    title = templates[slot.isocalendar()[1] % len(templates)].format(n=len(stories))[:100]
    lines = [ch.get("compilation_intro", f"Las mejores historias de la semana de {ch['name']}, seguidas."), "",
             "Capítulos:"]
    lines += [f"{_ts(t)} {name}" for t, name in chapters]
    tag = ch.get("affiliate_tag") or cfg.get("affiliate", {}).get("tag")
    books = [s for s in stories if s.get("book")]
    if tag and books:
        lines += ["", "📚 Libros de este vídeo:"]
        lines += [f"• {s['book']['title']}, de {s['book']['author']} ({s['title']}): {amazon_link(s['book'], tag)}"
                  for s in books]
        lines += ["", cfg.get("affiliate", {}).get("disclosure", "")]
    tags = ch.get("compilation_tags", [])
    lines += ["", "Suscríbete para no perderte la próxima recopilación.", "", " ".join(f"#{t}" for t in tags[:5])]
    return {"title": title, "description": "\n".join(lines)[:5000], "tags": tags,
            "thumb_text": ch.get("compilation_thumb", "{n} historias").format(n=len(stories))}
