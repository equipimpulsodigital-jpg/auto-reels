"""Página de enlaces para la bio de cada marca (GitHub Pages, carpeta docs/).

Muestra los libros recomendados de las últimas historias, con enlace de afiliado de Amazon, y los
enlaces a las redes de la marca. Se regenera sola cada vez que se programan vídeos nuevos.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from .compile import amazon_link
from .config import ROOT, channel_data

DOCS = ROOT / "docs"
MAX_BOOKS = 30

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · enlaces</title>
<meta name="description" content="{tagline}">
<meta name="robots" content="noindex">
<style>
  :root {{ --accent: {accent}; --bg: #111317; --card: #1c1f26; --text: #f2f2f2; --muted: #a3a8b3; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text);
         font: 16px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 560px; margin: 0 auto; padding: 32px 16px 48px; }}
  header {{ text-align: center; margin-bottom: 24px; }}
  .logo {{ width: 76px; height: 76px; border-radius: 50%; margin: 0 auto 12px; display: grid; place-items: center;
           background: var(--accent); color: #111; font-size: 34px; font-weight: 800; }}
  h1 {{ font-size: 24px; margin: 0 0 4px; }}
  .tagline {{ color: var(--muted); margin: 0; }}
  .social {{ display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin: 16px 0 28px; }}
  .social a {{ color: var(--text); text-decoration: none; border: 1px solid #333844; border-radius: 999px;
               padding: 6px 14px; font-size: 14px; }}
  h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .06em; color: var(--accent); margin: 0 0 12px; }}
  .book {{ display: block; background: var(--card); border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
           color: inherit; text-decoration: none; border-left: 4px solid var(--accent); }}
  .book:hover {{ filter: brightness(1.15); }}
  .story {{ color: var(--muted); font-size: 13px; margin: 0 0 4px; }}
  .title {{ font-weight: 700; margin: 0; }}
  .author {{ color: var(--muted); font-size: 14px; margin: 2px 0 0; }}
  .cta {{ display: inline-block; margin-top: 8px; font-size: 13px; font-weight: 700; color: var(--accent); }}
  footer {{ color: var(--muted); font-size: 12px; text-align: center; margin-top: 32px; }}
</style>
</head>
<body>
<main>
  <header>
    <div class="logo" aria-hidden="true">{initial}</div>
    <h1>{name}</h1>
    <p class="tagline">{tagline}</p>
  </header>
  <nav class="social">{social}</nav>
  <h2>📚 Los libros de nuestras historias</h2>
  {books}
  <footer>{disclosure}</footer>
</main>
</body>
</html>
"""

SOCIAL = {"instagram": "Instagram", "youtube": "YouTube", "tiktok": "TikTok"}


def build(cfg: dict) -> Path:
    ch = cfg["channel"]
    tag = ch.get("affiliate_tag") or cfg.get("affiliate", {}).get("tag")
    history = json.loads((channel_data(cfg) / "history.json").read_text(encoding="utf-8")) \
        if (channel_data(cfg) / "history.json").exists() else []
    seen, cards = set(), []
    for h in reversed(history):
        b = h.get("book")
        if not b or not tag or not h.get("published_parts"):
            continue
        key = (b["title"].lower(), b["author"].lower())
        if key in seen:
            continue
        seen.add(key)
        cards.append(
            f'<a class="book" href="{html.escape(amazon_link(b, tag))}" rel="sponsored noopener" target="_blank">'
            f'<p class="story">{html.escape(h["series_title"])}</p>'
            f'<p class="title">{html.escape(b["title"])}</p>'
            f'<p class="author">{html.escape(b["author"])}</p>'
            f'<span class="cta">Ver en Amazon →</span></a>')
        if len(cards) >= MAX_BOOKS:
            break
    links = ch.get("links") or {}
    social = "".join(f'<a href="{html.escape(u)}" rel="noopener" target="_blank">{SOCIAL.get(k, k)}</a>'
                     for k, u in links.items())
    page = PAGE.format(
        name=html.escape(ch["name"]), tagline=html.escape(ch.get("tagline", "")), accent=ch.get("accent_color", "#E2A84B"),
        initial=html.escape(ch["name"].lstrip("¿")[:1].upper()), social=social,
        books="\n  ".join(cards) or '<p class="tagline">Pronto, los libros de nuestras historias.</p>',
        disclosure=html.escape(cfg.get("affiliate", {}).get("disclosure", "")))
    out = DOCS / ch["id"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("")
    return out
