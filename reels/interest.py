"""Temas de interés del momento, para que el guionista pueda aprovechar la actualidad.

Fuentes gratuitas y sin clave: búsquedas en tendencia de Google en España, artículos más leídos ayer en la
Wikipedia en español y aniversarios («tal día como hoy») de los próximos días. Si algo falla, se sigue sin ello.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from functools import lru_cache

import requests

UA = {"User-Agent": "auto-reels/1.0 (topic research)"}
_SKIP = re.compile(r"^(Wikipedia|Especial|Anexo|Portal|Categoría|Archivo|Ayuda):|Portada|Pornograf", re.I)


def _trends() -> list[str]:
    r = requests.get("https://trends.google.com/trending/rss?geo=ES", headers=UA, timeout=15)
    titles = re.findall(r"<title>([^<]+)</title>", r.text)
    return [t.strip() for t in titles[1:26]]


def _wiki_top(day: date) -> list[str]:
    d = day - timedelta(days=1)
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/es.wikipedia/all-access/{d:%Y/%m/%d}"
    arts = requests.get(url, headers=UA, timeout=15).json()["items"][0]["articles"]
    return [a["article"].replace("_", " ") for a in arts if not _SKIP.search(a["article"])][:35]


def _on_this_day(day: date, days: int = 3) -> list[str]:
    out = []
    for k in range(1, days + 1):  # se publica a partir de mañana
        d = day + timedelta(days=k)
        url = f"https://es.wikipedia.org/api/rest_v1/feed/onthisday/events/{d.month:02d}/{d.day:02d}"
        events = requests.get(url, headers=UA, timeout=15).json().get("events", [])
        old = [e for e in events if isinstance(e.get("year"), int) and e["year"] <= 1995]
        for e in old[:12]:
            text = re.sub(r"\s+", " ", e["text"])[:140]
            out.append(f"{d.day}/{d.month}: {e['year']} — {text}")
    return out


@lru_cache(maxsize=1)
def current_interest(day: date | None = None) -> str:
    day = day or date.today()
    parts = []
    for name, fn in (("Búsquedas en tendencia en España (Google)", _trends),
                     ("Lo más leído ayer en la Wikipedia en español", lambda: _wiki_top(day)),
                     ("Aniversarios de los próximos días", lambda: _on_this_day(day))):
        try:
            items = fn()
        except Exception as e:  # sin conexión o la fuente ha cambiado: se sigue sin ella
            print(f"  temas de interés: no se pudo leer «{name}» ({type(e).__name__})")
            continue
        if items:
            parts.append(f"{name}:\n" + "\n".join(f"- {x}" for x in items))
    if not parts:
        return ""
    return ("\n\nTEMAS DE INTERÉS AHORA MISMO (opcional, como inspiración):\n" + "\n\n".join(parts) +
            "\n\nSi alguno encaja de verdad con este canal y da para una historia excelente y verídica, aprovéchalo "
            "como uno de los 5 `topic_candidates` (lo que la gente ya está buscando, o un aniversario de estos días, "
            "multiplica las visualizaciones; menciónalo en el gancho o en el texto si ayuda: «Hace 80 años, tal día "
            "como mañana...»). Puede ser una conexión indirecta (una serie de moda → la historia real que la inspiró; "
            "un fenómeno del que se habla → la ciencia o la psicología que lo explica). No fuerces nada: nada de "
            "política de partidos, noticias de sucesos recientes con víctimas reales, ni cotilleos de famosos vivos.")
