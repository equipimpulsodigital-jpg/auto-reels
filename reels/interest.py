"""Temas de interés del momento, para que el guionista pueda aprovechar la actualidad.

Fuentes gratuitas y sin clave: búsquedas en tendencia de Google en España (lo que la gente busca hoy) y
noticias de la última semana en Google Noticias sobre el tema de cada marca (`interest_queries` en config.yaml).
Si algo falla, se sigue sin ello.
"""
from __future__ import annotations

import html
import re
from datetime import date
from urllib.parse import quote_plus

import requests

UA = {"User-Agent": "auto-reels/1.0 (topic research)"}
_cache: dict[str, str] = {}


def _rss_titles(url: str, n: int) -> list[str]:
    r = requests.get(url, headers=UA, timeout=15)
    titles = [html.unescape(t).strip() for t in re.findall(r"<title>([^<]+)</title>", r.text)]
    return titles[1:n + 1]  # el primero es el título del canal RSS


def _trends() -> list[str]:
    return _rss_titles("https://trends.google.com/trending/rss?geo=ES", 25)


def _news(queries: list[str], days: int = 7, per: int = 8, cap: int = 30) -> list[str]:
    seen, out = set(), []
    for q in queries:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}+when:{days}d&hl=es&gl=ES&ceid=ES:es"
        for t in _rss_titles(url, per):
            t = re.sub(r"\s+-\s+[^-]+$", "", t)  # quita « - Nombre del medio»
            if t.lower() not in seen and t != "Google News":
                seen.add(t.lower())
                out.append(t)
    return out[:cap]


def current_interest(cfg: dict) -> str:
    cid = cfg["channel"]["id"]
    if cid in _cache:
        return _cache[cid]
    queries = cfg["channel"].get("interest_queries") or []
    days = int(cfg["channel"].get("news_days", 7))
    news_label = "Noticias de esta semana" if days >= 7 else f"Noticias de las últimas {days * 24} horas"
    parts = []
    for name, fn in (("Lo que más se busca hoy en España (Google Trends)", _trends),
                     (f"{news_label} sobre el tema del canal (Google Noticias)",
                      lambda: _news(queries, days, per=8 if days >= 7 else 10, cap=30 if days >= 7 else 45))):
        try:
            items = fn()
        except Exception as e:  # sin conexión o la fuente ha cambiado: se sigue sin ella
            print(f"  temas de interés: no se pudo leer «{name}» ({type(e).__name__})")
            continue
        if items:
            parts.append(f"{name}:\n" + "\n".join(f"- {x}" for x in items))
    text = ("\n\nTEMAS DE INTERÉS AHORA MISMO (opcional, como inspiración):\n" + "\n\n".join(parts) if parts else "\n")
    text += (
        f"\n\nAniversarios: hoy es {date.today():%d/%m/%Y} y el vídeo sale en los próximos 1-2 días. Si en estos días "
        "se cumple un aniversario redondo (25, 50, 75, 100... años) de algo que encaje con el canal, es un gran tema.\n"
        "Si algo de esto encaja de verdad con este canal y da para una historia excelente y verídica, aprovéchalo como "
        "uno de los 5 `topic_candidates` (lo que la gente ya está buscando multiplica las visualizaciones; menciónalo "
        "en el gancho si ayuda). Puede ser una conexión indirecta (una serie o película de moda → la historia real que "
        "la inspiró; algo de lo que se habla → la ciencia o la psicología que lo explica). " +
        (cfg["channel"].get("interest_note") or "No fuerces nada: nada de política de partidos, sucesos recientes "
         "con víctimas reales ni cotilleos de famosos vivos."))
    _cache[cid] = text
    return text
