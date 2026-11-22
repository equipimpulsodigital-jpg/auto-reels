"""Comprobación diaria del sistema y resumen semanal.

  python -m reels.health check    → report.md con lo que hay que revisar (y problems.txt con el número de avisos)
  python -m reels.health weekly   → report.md con el resumen de la semana

El workflow «Avisos y resumen» abre una incidencia en GitHub con el texto (GitHub la envía por correo) solo cuando
hay algo que hacer, y la cierra sola cuando se arregla.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from .__main__ import _load, _platforms_for, pending_slots
from .config import load_config
from .publish import API, RETRYABLE, env, post_results

NAMES = {"instagram": "Instagram", "youtube": "YouTube", "tiktok": "TikTok"}


def _channels() -> list[dict]:
    return [load_config(cid) for cid, ch in load_config().get("channels", {}).items() if ch.get("enabled", True)]


def _accounts(profile: str) -> dict:
    r = requests.get(f"{API}/uploadposts/users/{profile}", timeout=60,
                     headers={"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}"})
    if r.status_code >= 400:
        raise RuntimeError(f"Upload-Post respondió {r.status_code}")
    data = r.json()
    prof = data.get("profile") or data.get("user") or data
    return {k: v for k, v in (prof.get("social_accounts") or {}).items() if isinstance(v, dict) and v}


def check() -> tuple[list[str], list[str]]:
    """(problemas, notas). Problema = algo que hay que hacer; nota = información."""
    problems, notes = [], []
    now = datetime.now(timezone.utc)
    for cfg in _channels():
        ch = cfg["channel"]
        name = ch["name"]
        tz = ZoneInfo(cfg["publish"].get("timezone", "Europe/Madrid"))
        state = _load(cfg, "state.json", {"scheduled": []})
        # 1. franjas sin vídeo en las próximas 12 horas
        missing = pending_slots(cfg, {"scheduled": state.get("scheduled", [])}, horizon=12)
        if missing:
            problems.append(f"**{name}**: {len(missing)} franja(s) de las próximas 12 h sin vídeo programado "
                            f"({', '.join(f'{s:%d/%m %H:%M}' for s in missing)}). Si la ejecución nocturna no corrió, "
                            "lanza en GitHub → Actions → Episodio diario el modo «programar».")
        # 2. cuentas que piden reconectar
        try:
            for plat, acc in _accounts(ch["profile"]).items():
                if acc.get("reauth_required") and plat in ch["platforms"]:
                    problems.append(f"**{name}**: la cuenta de {NAMES.get(plat, plat)} pide **reconectarla** en "
                                    f"Upload-Post (Users → {ch['profile']} → {NAMES.get(plat, plat)}).")
        except Exception as e:
            problems.append(f"**{name}**: no se pudo consultar Upload-Post ({e}).")
        # 3. canal de YouTube caído
        yt = (ch.get("links") or {}).get("youtube")
        if yt and "youtube" in ch["platforms"]:
            try:
                r = requests.get(yt, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 404:
                    problems.append(f"**{name}**: el canal de YouTube ({yt}) **no está disponible**. Revisa el correo "
                                    "de la cuenta de Google por si YouTube lo ha cerrado (se puede apelar).")
            except requests.RequestException:
                pass
        # 4. publicaciones de las últimas 26 h que fallaron y no se arreglan solas
        history = _load(cfg, "history.json", [])
        for h in history:
            for p in h.get("published_parts", []):
                slot, rid = p.get("slot"), p.get("job_id") or p.get("request_id")
                if not slot or not rid:
                    continue
                when = datetime.fromisoformat(slot)
                if not (now - timedelta(hours=26) < when < now - timedelta(minutes=30)):
                    continue
                for res in post_results(rid) or []:
                    plat = res.get("platform")
                    if res.get("success") or plat not in _platforms_for(cfg, when):
                        continue
                    err = str(res.get("error_message") or res.get("message") or res.get("error") or "")
                    if any(k in err.lower() for k in RETRYABLE) and plat not in p.get("retried", []):
                        continue  # lo reintentará la próxima ejecución
                    hint = ""
                    if "risky" in err.lower():
                        hint = " TikTok desconfía de la cuenta: úsala unos días desde el móvil y sube algún vídeo a mano."
                    elif "session" in err.lower() or "token" in err.lower() or "password" in err.lower():
                        hint = " Hay que reconectar la cuenta en Upload-Post."
                    problems.append(f"**{name}**: «{h['series_title'][:60]}» ({when.astimezone(tz):%d/%m %H:%M}) falló en "
                                    f"{NAMES.get(plat, plat)}: {err[:160]}.{hint}")
    # 5. claves y planes que caducan (config.yaml → expirations: {nombre: AAAA-MM-DD})
    for what, when in (load_config().get("expirations") or {}).items():
        try:
            left = (date.fromisoformat(str(when)) - date.today()).days
        except ValueError:
            continue
        if left <= 15:
            problems.append(f"**Caducidad:** «{what}» caduca el {when} ({left} días). Renuévalo antes para que no se pare nada.")
    return problems, notes


def _views(p: dict) -> int:
    return sum(v.get("views", 0) for v in (p.get("stats") or {}).values())


def weekly() -> str:
    today = date.today()
    lines = [f"## Resumen semanal · {today:%d/%m/%Y}", "",
             "Visualizaciones de los vídeos publicados en los últimos 7 días (todas las redes) y seguidores actuales.", "",
             "| Marca | Vídeos | Visualizaciones | Media | Semana anterior (media) | Seguidores (YouTube / Instagram / TikTok) |",
             "|---|---|---|---|---|---|"]
    best, worst, details = [], [], []
    for cfg in _channels():
        ch = cfg["channel"]
        history = _load(cfg, "history.json", [])
        cur, prev = [], []
        for h in history:
            for p in h.get("published_parts", []):
                if not p.get("slot") or not p.get("stats"):
                    continue
                age = (today - datetime.fromisoformat(p["slot"]).date()).days
                row = (_views(p), h["series_title"], h.get("format", ""), ch["name"])
                if age < 7:
                    cur.append(row)
                elif age < 14:
                    prev.append(row)
        acc = _load(cfg, "account.json", {}).get("latest", {})
        fol = " / ".join(str((acc.get(k) or {}).get("followers", "–")) for k in ("youtube", "instagram", "tiktok"))
        avg = sum(r[0] for r in cur) // max(len(cur), 1)
        pavg = sum(r[0] for r in prev) // max(len(prev), 1) if prev else None
        trend = "–" if pavg is None else f"{pavg} ({'+' if avg >= pavg else ''}{round(100 * (avg - pavg) / max(pavg, 1))} %)"
        lines.append(f"| {ch['name']} | {len(cur)} | {sum(r[0] for r in cur):,} | {avg:,} | {trend} | {fol} |".replace(",", "."))
        cur.sort(reverse=True)
        best += cur[:2]
        worst += cur[-2:] if len(cur) > 3 else []
        fmts: dict = {}
        for r in cur:
            fmts.setdefault(r[2], []).append(r[0])
        if fmts:
            top = max(fmts.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
            details.append(f"- **{ch['name']}**: el formato que mejor funciona esta semana es «{top[0]}» "
                           f"({sum(top[1]) // len(top[1]):,} de media).".replace(",", "."))
    best.sort(reverse=True)
    worst.sort()
    lines += ["", "**Los más vistos de la semana**"] + [f"- {v:,} · {t} ({m})".replace(",", ".") for v, t, _, m in best[:5]]
    lines += ["", "**Los menos vistos**"] + [f"- {v:,} · {t} ({m})".replace(",", ".") for v, t, _, m in worst[:5]]
    lines += ["", "**Formatos**"] + details
    lines += ["", "_Las cifras de los vídeos de los últimos dos días aún están subiendo._"]
    return "\n".join(lines)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "weekly":
        text = weekly()
        Path("report.md").write_text(text, encoding="utf-8")
        print(text)
        return 0
    problems, notes = check()
    text = ("## Hay algo que revisar en auto-reels\n\n" + "\n".join(f"- {p}" for p in problems) +
            "\n\n_Esta incidencia se cierra sola cuando todo vuelve a estar bien._") if problems else "Todo en orden."
    Path("report.md").write_text(text, encoding="utf-8")
    Path("problems.txt").write_text(str(len(problems)))
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
