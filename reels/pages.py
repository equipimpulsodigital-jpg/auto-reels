"""Página de enlaces para la bio de cada marca (GitHub Pages, carpeta docs/).

Muestra los libros recomendados de las historias publicadas (el último, destacado), con enlace de
afiliado de Amazon, y los enlaces a las redes de la marca. Se regenera sola cada vez que se programan
vídeos nuevos.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from .compile import amazon_link, enrich_book
from .config import ROOT, channel_data

DOCS = ROOT / "docs"
MAX_BOOKS = 40
E = html.escape

ICONS = {
    "youtube": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12 31 31 0 0 0 1 16.8a3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8zM9.8 15.1V8.9l5.4 3.1z"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 7.3A4.7 4.7 0 1 0 16.7 12 4.7 4.7 0 0 0 12 7.3zm0 7.7a3 3 0 1 1 3-3 3 3 0 0 1-3 3zm6-7.9a1.1 1.1 0 1 1-1.1-1.1A1.1 1.1 0 0 1 18 7.1zM21.9 8.2a5.4 5.4 0 0 0-1.5-3.8 5.4 5.4 0 0 0-3.8-1.5C15.1 2.8 8.9 2.8 7.4 2.9a5.4 5.4 0 0 0-3.8 1.5A5.4 5.4 0 0 0 2.1 8.2c-.1 1.5-.1 6.1 0 7.6a5.4 5.4 0 0 0 1.5 3.8 5.4 5.4 0 0 0 3.8 1.5c1.5.1 7.7.1 9.2 0a5.4 5.4 0 0 0 3.8-1.5 5.4 5.4 0 0 0 1.5-3.8c.1-1.5.1-6.1 0-7.6zM19.8 17.6a3 3 0 0 1-1.7 1.7c-1.2.5-4 .4-5.3.4s-4.1.1-5.3-.4a3 3 0 0 1-1.7-1.7c-.5-1.2-.4-4-.4-5.3s-.1-4.1.4-5.3a3 3 0 0 1 1.7-1.7c1.2-.5 4-.4 5.3-.4s4.1-.1 5.3.4a3 3 0 0 1 1.7 1.7c.5 1.2.4 4 .4 5.3s.1 4.1-.4 5.3z"/></svg>',
    "tiktok": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.6 6.7a4.8 4.8 0 0 1-3.8-4.2V2h-3.4v13.6a2.9 2.9 0 1 1-2-2.7V9.4a6.3 6.3 0 1 0 5.4 6.2V8.7a8.2 8.2 0 0 0 3.8 1.2z"/></svg>',
}
NAMES = {"youtube": "YouTube", "instagram": "Instagram", "tiktok": "TikTok"}

CSS = """
@font-face { font-family: Display; src: url(../assets/Anton-Regular.ttf) format("truetype"); font-display: swap; }
:root { --accent: %(accent)s; --bg: #0e0f13; --card: #171920; --line: #262a35; --text: #f4f4f6; --muted: #9ba1ad; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%%; }
body { margin: 0; background: var(--bg); color: var(--text);
       font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
a { color: inherit; }
.hero { position: relative; overflow: hidden; padding: 44px 16px 30px; text-align: center;
        background: radial-gradient(120%% 90%% at 50%% 0%%, color-mix(in srgb, var(--accent) 38%%, transparent), transparent 70%%); }
.wrap { max-width: 720px; margin: 0 auto; }
.emblem { width: 84px; height: 84px; margin: 0 auto 14px; border-radius: 24px; display: grid; place-items: center;
          background: var(--accent); color: #111; font: 46px/1 Display, Impact, sans-serif; transform: rotate(-4deg);
          box-shadow: 0 10px 30px color-mix(in srgb, var(--accent) 40%%, transparent); }
h1 { font: 44px/1 Display, Impact, sans-serif; letter-spacing: .5px; margin: 0 0 8px; text-transform: uppercase; }
.tagline { color: #d6d8de; margin: 0 auto; max-width: 420px; }
.social { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 20px; }
.social a { display: inline-flex; align-items: center; gap: 8px; text-decoration: none; padding: 9px 16px;
            border-radius: 999px; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12);
            font-size: 14px; font-weight: 600; }
.social a:hover { background: rgba(255,255,255,.14); }
.social svg { width: 18px; height: 18px; fill: currentColor; }
main { padding: 8px 16px 56px; }
.label { font: 15px/1 Display, Impact, sans-serif; letter-spacing: 1.5px; text-transform: uppercase; color: var(--accent);
         margin: 28px 0 14px; display: flex; align-items: center; gap: 10px; }
.label::after { content: ""; flex: 1; height: 1px; background: var(--line); }
.featured { display: grid; grid-template-columns: 150px 1fr; gap: 20px; align-items: center; text-decoration: none;
            background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 16%%, var(--card)), var(--card));
            border: 1px solid var(--line); border-radius: 20px; padding: 18px; }
.featured .cover { width: 150px; height: 225px; }
.featured h2 { margin: 6px 0 4px; font-size: 22px; line-height: 1.2; }
.pill { display: inline-block; font-size: 11px; font-weight: 800; letter-spacing: .5px; text-transform: uppercase;
        background: var(--accent); color: #111; padding: 3px 9px; border-radius: 999px; }
.from { color: var(--muted); font-size: 14px; margin: 0; }
.author { color: #c9ccd4; margin: 0; font-size: 15px; }
.pitch { color: #d6d8de; margin: 10px 0 0; font-size: 15px; }
.btn { display: inline-block; margin-top: 14px; background: var(--accent); color: #111; font-weight: 800;
       text-decoration: none; padding: 11px 18px; border-radius: 12px; font-size: 15px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px; }
.card { display: flex; flex-direction: column; text-decoration: none; background: var(--card);
        border: 1px solid var(--line); border-radius: 16px; padding: 12px; transition: transform .15s, border-color .15s; }
.card:hover, .featured:hover { transform: translateY(-2px); border-color: var(--accent); }
.card .cover { width: 100%%; aspect-ratio: 2 / 3; height: auto; margin-bottom: 10px; }
.card h3 { font-size: 15px; line-height: 1.25; margin: 0 0 3px; }
.card .author { font-size: 13px; }
.card .from { font-size: 12px; margin-top: 6px; }
.card .go { margin-top: auto; padding-top: 10px; font-size: 13px; font-weight: 800; color: var(--accent); }
.cover { display: block; border-radius: 8px; object-fit: cover; background: #232733;
         box-shadow: 0 8px 22px rgba(0,0,0,.45); }
.fake { display: flex; flex-direction: column; justify-content: space-between; padding: 12px; overflow: hidden;
        background: linear-gradient(160deg, color-mix(in srgb, var(--accent) 70%%, #000), #15161c); color: #fff; }
.fake b { font: 19px/1.05 Display, Impact, sans-serif; text-transform: uppercase; letter-spacing: .3px; }
.fake span { font-size: 11px; opacity: .85; }
footer { color: var(--muted); font-size: 12px; text-align: center; padding: 0 16px 36px; }
@media (max-width: 480px) {
  h1 { font-size: 36px; }
  .featured { grid-template-columns: 110px 1fr; gap: 14px; padding: 14px; }
  .featured .cover { width: 110px; height: 165px; }
  .featured h2 { font-size: 18px; }
  .grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
}
"""


def _cover(b: dict, cls: str = "cover") -> str:
    if b.get("cover"):
        return f'<img class="{cls}" src="{E(b["cover"])}" alt="Portada de {E(b["title"])}" loading="lazy">'
    return (f'<div class="{cls} fake" aria-hidden="true"><b>{E(b["title"][:60])}</b>'
            f'<span>{E(b["author"])}</span></div>')


def build(cfg: dict) -> Path:
    ch = cfg["channel"]
    tag = ch.get("affiliate_tag") or cfg.get("affiliate", {}).get("tag")
    hist_path = channel_data(cfg) / "history.json"
    history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
    seen, items = set(), []
    for h in reversed(history):
        b = h.get("book")
        if not b or not tag or not h.get("published_parts"):
            continue
        key = (b["title"].lower(), b["author"].lower())
        if key in seen:
            continue
        seen.add(key)
        enrich_book(b)  # portada e ISBN (se guardan en el historial)
        items.append((h, b))
        if len(items) >= MAX_BOOKS:
            break
    if history:
        hist_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    body = []
    if items:
        h, b = items[0]
        pitch = f'<p class="pitch">{E(b["pitch"])}</p>' if b.get("pitch") else ""
        body.append('<div class="label">El libro de la última historia</div>')
        body.append(
            f'<a class="featured" href="{E(amazon_link(b, tag))}" rel="sponsored noopener" target="_blank">'
            f'{_cover(b)}<div><span class="pill">Nuevo</span><h2>{E(b["title"])}</h2>'
            f'<p class="author">{E(b["author"])}</p><p class="from">De la historia «{E(h["series_title"])}»</p>'
            f'{pitch}<span class="btn">Ver en Amazon</span></div></a>')
    if len(items) > 1:
        body.append('<div class="label">Más libros de nuestras historias</div><div class="grid">')
        for h, b in items[1:]:
            body.append(
                f'<a class="card" href="{E(amazon_link(b, tag))}" rel="sponsored noopener" target="_blank">'
                f'{_cover(b)}<h3>{E(b["title"])}</h3><p class="author">{E(b["author"])}</p>'
                f'<p class="from">«{E(h["series_title"])}»</p><span class="go">Ver en Amazon →</span></a>')
        body.append("</div>")
    if not items:
        body.append('<p class="tagline" style="text-align:center;margin-top:30px">'
                    'Muy pronto, los libros de nuestras historias.</p>')

    links = ch.get("links") or {}
    social = "".join(f'<a href="{E(u)}" rel="noopener" target="_blank">{ICONS.get(k, "")}{NAMES.get(k, k)}</a>'
                     for k, u in links.items())
    accent = ch.get("accent_color", "#E2A84B")
    og = items[0][1].get("cover", "") if items else ""
    name, tagline = E(ch["name"]), E(ch.get("tagline", ""))
    page = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · libros</title>
<meta name="description" content="{tagline}">
<meta name="robots" content="noindex">
<meta name="theme-color" content="{accent}">
<meta property="og:title" content="{name} · los libros de nuestras historias">
<meta property="og:description" content="{tagline}">
{f'<meta property="og:image" content="{E(og)}">' if og else ''}
<style>{CSS % {"accent": accent}}</style>
</head>
<body>
<header class="hero"><div class="wrap">
  <div class="emblem" aria-hidden="true">{E(ch["name"].lstrip("¿")[:1].upper())}</div>
  <h1>{name}</h1>
  <p class="tagline">{tagline}</p>
  <nav class="social">{social}</nav>
</div></header>
<main><div class="wrap">
{chr(10).join(body)}
</div></main>
<footer>{E(cfg.get("affiliate", {}).get("disclosure", ""))}</footer>
</body>
</html>
"""
    out = DOCS / ch["id"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("")
    return out
