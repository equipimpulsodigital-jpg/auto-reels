"""Genera los episodios de un canal y los deja programados en Upload-Post.

Uso:
  python -m reels --channel bien_contadas            # programa todas las franjas de las próximas 24 h
  python -m reels --channel bien_contadas --dry-run  # genera un vídeo de prueba, no publica nada
  python -m reels --channel bien_contadas --now      # genera uno y lo publica al momento
  python -m reels --channel elanecdotario --dry-run --topic "El paso Diatlov" --new
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import OUT, channel_data, load_config


def _load(cfg: dict, name: str, default):
    path = channel_data(cfg) / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _save(cfg: dict, name: str, value) -> None:
    folder = channel_data(cfg)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pending_slots(cfg: dict, state: dict, now: datetime | None = None, horizon: float = 24) -> list[datetime]:
    """Franjas de las próximas `horizon` horas que aún no tienen vídeo programado."""
    pcfg = cfg["publish"]
    tz = ZoneInfo(pcfg.get("timezone", "Europe/Madrid"))
    now = (now or datetime.now(timezone.utc)).astimezone(tz)
    start = now + timedelta(minutes=int(pcfg.get("min_lead_minutes", 20)))
    done = set(state.get("scheduled", []))
    taken = [datetime.fromisoformat(d) for d in done]
    gap = timedelta(minutes=int(pcfg.get("min_gap_minutes", 100)))
    out = []
    for day in (now.date() + timedelta(days=k) for k in range(int(horizon // 24) + 2)):
        for hhmm in cfg["channel"].get("slots") or pcfg["slots"]:
            h, m = map(int, hhmm.split(":"))
            slot = datetime.combine(day, time(h, m), tz)
            if start <= slot <= now + timedelta(hours=horizon) and slot.isoformat() not in done \
                    and all(abs(slot - t) >= gap for t in taken):  # al cambiar las horas, no amontona vídeos
                out.append(slot)
                taken.append(slot)
    return out


def _fmt_time(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def write_guion(cfg, path, series, part, durations) -> None:
    """Guion legible con la estructura de la serie (ficha, estilo, bloques con tiempos, cierre)."""
    fmt = cfg["channel"]["formats"].get(series.format, series.format)
    n = len(series.parts)
    out = [
        f"# {series.series_title} · Parte {part.part_number}/{n}", "",
        "## 1. Ficha del episodio",
        f"- **Serie:** {series.series_title}", f"- **Parte:** {part.part_number}/{n}",
        f"- **Formato:** {fmt}", f"- **Año y lugar:** {series.year} · {series.place}",
        f"- **Notas históricas:** {series.historical_notes}",
        f"- **Ángulo:** {series.angle}", f"- **Pregunta abierta:** {series.open_question}",
        f"- **Giro final:** {series.payoff}",
        *([f"- **Escaleta:**"] + [f"  {k}. {s}" for k, s in enumerate(series.beats, 1)] if series.beats else []), "",
        f"## 2. Reparto (época: {series.era})",
        *[f"- **{c.name}** ({c.voice}): " + ", ".join(f"{k}={v}" for k, v in c.look.model_dump().items() if v not in (None, False, "ninguno", "ninguna"))
          for c in series.characters], "",
        "## 3. Guion + Dirección Visual",
    ]
    t = 0.0
    for b, d in zip(part.blocks, durations):
        who = next((c.name for c in series.characters if c.id == b.speaker), "Narrador")
        out += [f"**[{_fmt_time(t)} - {_fmt_time(t + d)}] {b.label.upper()}**",
                f"- *{who}:* \"{b.narration}\"",
                f"- *Plano:* {b.location} · {b.framing} · {b.mood}" + (f" · suceso: {b.event}" if b.event else "")
                + (f" · objeto: {b.prop}" if b.framing == "objeto" else "") + f" · cámara: {b.camera}",
                *([f"- *Rótulo:* {b.on_screen}"] if b.on_screen else []),
                f"- *Animación:* {b.visual_direction} (gesto: {b.gesture}, emoción: {b.emotion})", ""]
        t += d
    out += ["## 4. Cierre / Gancho para la siguiente parte", part.cliffhanger, ""]
    path.write_text("\n".join(out), encoding="utf-8")


def _norm(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(ch for ch in t if ch.isalnum())


def _mark_emphasis(words, blocks) -> None:
    """Marca la palabra clave de cada plano (la que eligió el guionista) para resaltarla."""
    for i, b in enumerate(blocks):
        target = _norm(getattr(b, "emphasis", None) or "")
        if not target:
            continue
        for w in words:
            if w.scene == i and _norm(w.text) == target:
                w.emph = True
                break


def cancel_slot(cfg: dict, when: str) -> bool:
    """Quita de Upload-Post el vídeo programado en una franja y la deja libre para volver a llenarla."""
    from .publish import cancel_scheduled
    tz = ZoneInfo(cfg["publish"].get("timezone", "Europe/Madrid"))
    slot = datetime.fromisoformat(when.strip().replace(" ", "T"))
    slot = slot if slot.tzinfo else slot.replace(tzinfo=tz)
    history = _load(cfg, "history.json", [])
    state = _load(cfg, "state.json", {"queue": [], "scheduled": []})
    for h in history:
        for p in list(h.get("published_parts", [])):
            if p.get("slot") and datetime.fromisoformat(p["slot"]) == slot:
                print(f"Quitando «{h['series_title']}» (parte {p['part']}) de la franja {slot:%d/%m %H:%M}")
                if not p.get("job_id") or not cancel_scheduled(p["job_id"]):
                    print("No se pudo quitar de Upload-Post.", file=sys.stderr)
                    return False
                h["published_parts"].remove(p)
                state["scheduled"] = [s for s in state.get("scheduled", []) if datetime.fromisoformat(s) != slot]
                _save(cfg, "history.json", history)
                _save(cfg, "state.json", state)
                return True
    print(f"No hay ningún vídeo programado el {slot:%d/%m %H:%M}.", file=sys.stderr)
    return False


def _continuation_after(state: dict, history: list[dict], slot: datetime) -> bool:
    """¿La siguiente parte pendiente es una continuación cuya parte anterior sale DESPUÉS de esta franja?
    (pasa al rellenar tarde una franja que falló). Entonces esta franja necesita una historia suelta."""
    if not state["queue"] or state["queue"][0]["part"] == 0:
        return False
    title = state["queue"][0]["series"].get("series_title")
    prev = state["queue"][0]["part"]  # número de la parte anterior (part es el índice desde 0)
    for h in reversed(history):
        if h.get("series_title") == title:
            for p in h.get("published_parts", []):
                if p.get("part") == prev and p.get("slot") and datetime.fromisoformat(p["slot"]) > slot:
                    print(f"  La parte {prev} de «{title}» sale el {datetime.fromisoformat(p['slot']):%d/%m %H:%M}: "
                          "esta franja, anterior, lleva una historia suelta para no adelantar la continuación.")
                    return True
            return False
    return False


def update_stats(cfg: dict) -> None:
    """Consulta en Upload-Post las visualizaciones de lo publicado en los últimos 30 días y las guarda
    en el historial: así el guionista sabe qué historias han gustado más."""
    from .publish import post_stats
    history = _load(cfg, "history.json", [])
    now = datetime.now(timezone.utc)
    raw_shown = False
    n = 0
    for h in history:
        total = {"views": 0, "likes": 0, "comments": 0, "shares": 0}
        got = False
        for p in h.get("published_parts", []):
            rid, slot = p.get("request_id"), p.get("slot")
            if not rid or not slot:
                continue
            age = now - datetime.fromisoformat(slot)
            if age < timedelta(hours=6) or age > timedelta(days=30):
                continue
            st = post_stats(rid, show_raw=not raw_shown)
            raw_shown = True
            if st is None:
                continue
            p["stats"] = st
            got = True
            n += 1
            for m in total:
                total[m] += sum(v.get(m, 0) for v in st.values())
            yt = st.get("youtube", {}).get("views", 0)
            total["youtube_views"] = total.get("youtube_views", 0) + yt
        if got:
            h["stats"] = {**total, "updated": now.strftime("%Y-%m-%d")}
            print(f"  {total['views']:>7} vis · {total['likes']:>5} me gusta · {total['comments']:>4} coment. · {h['series_title'][:60]}")
    _save(cfg, "history.json", history)
    print(f"  {n} publicaciones consultadas")
    from .publish import _ACCOUNT
    if _ACCOUNT:  # seguidores de cada red, con histórico diario para ver el crecimiento
        acc = _load(cfg, "account.json", {"history": []})
        today = now.strftime("%Y-%m-%d")
        acc["latest"] = dict(_ACCOUNT)
        acc["history"] = [e for e in acc.get("history", []) if e.get("date") != today]
        acc["history"].append({"date": today, **{k: v.get("followers") for k, v in _ACCOUNT.items()}})
        _save(cfg, "account.json", acc)
        print("  seguidores: " + ", ".join(f"{k} {v.get('followers')}" for k, v in _ACCOUNT.items()))


def _stamps(blocks, durations) -> list[tuple[float, float, str]]:
    """Rótulos de datos (fecha, lugar, cifra) que pidió el guionista, durante su plano."""
    out, t = [], 0.0
    for b, d in zip(blocks, durations):
        text = (getattr(b, "on_screen", None) or "").strip()
        if text:
            out.append((t + 0.08, t + max(d - 0.05, 1.4), text[:28]))
        t += d
    return out


def make_episode(cfg: dict, state: dict, history: list[dict], args, label: str):
    """Escribe (si hace falta) la historia, y genera el vídeo de la siguiente parte pendiente."""
    from pydantic import ValidationError

    from .captions import CaptionRenderer
    from .render import assemble
    from .script import Series, generate_series, next_format
    from .toon.episode import render_episode
    from .tts import synthesize_scenes

    today = date.today().isoformat()
    # Historia pendiente en un formato antiguo (p. ej. de antes de la animación): se reescribe el mismo tema.
    if state["queue"] and not args.new:
        try:
            Series.model_validate(state["queue"][0]["series"])
        except ValidationError:
            old = state["queue"][0]["series"]
            print(f"  «{old.get('series_title')}» está en un formato antiguo: se vuelve a escribir para animación.")
            history[:] = [h for h in history
                          if not (h.get("series_title") == old.get("series_title") and not h.get("published_parts"))]
            state["queue"] = []
            args.topic = args.topic or old.get("topic")
            args.format = args.format or old.get("format")

    # 1. Guion: siguiente parte pendiente o historia nueva (con todas sus partes de una vez)
    single = getattr(args, "single", False)
    if args.new or not state["queue"] or single:
        fmt = next_format(cfg, history, args.format)
        print(f"1/5 Historia nueva · {fmt}" + (f" · tema: {args.topic}" if args.topic else "")
              + (" · de una sola parte (hueco antes de una parte 2 ya programada)" if single else ""))
        series = generate_series(cfg, fmt, history, args.topic, max_parts=1 if single else None)
        history.append({"date": today, "format": series.format, "topic": series.topic,
                        "series_title": series.series_title, "parts": len(series.parts), "published_parts": [],
                        "book": series.book.model_dump() if series.book else None})
        items = [{"series": series.model_dump(), "part": i} for i in range(len(series.parts))]
        # una historia suelta para un hueco va delante, sin perder las partes pendientes
        state["queue"] = items + state["queue"] if single else items
        args.single = False
        _save(cfg, "history.json", history)
        _save(cfg, "state.json", state)
        args.new, args.topic, args.format = False, None, None  # solo para la primera historia
    else:
        print("1/5 Siguiente parte pendiente")
    item = state["queue"][0]
    series = Series.model_validate(item["series"])
    part = series.parts[item["part"]]
    n = len(series.parts)
    print(f"  «{series.series_title}» · Parte {part.part_number}/{n} · {series.year}, {series.place}")
    print(f"  gancho: {part.hook_title}")

    workdir = OUT / f"{cfg['channel']['id']}_{label}"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "series.json").write_text(series.model_dump_json(indent=2), encoding="utf-8")

    # 2. Voz en off (un audio por plano: así cada imagen dura lo que su frase)
    print("2/5 Voz en off")
    chars = {c.id: c for c in series.characters}
    speakers = [(chars[b.speaker].voice, chars[b.speaker].name) if b.speaker in chars else ("", "")
                for b in part.blocks]
    voice, durations, words = synthesize_scenes([b.narration for b in part.blocks], cfg, workdir, speakers)
    _mark_emphasis(words, part.blocks)
    tail = 1.6 if n > 1 and part.part_number < n else 1.2
    if getattr(part, "comment_question", ""):
        tail += 1.0  # tiempo para leer la pregunta final
    durations[-1] += tail
    total = sum(durations)
    print(f"  {len(words)} palabras · {total:.1f} s · {len(part.blocks)} planos")
    write_guion(cfg, workdir / "guion.md", series, part, durations)

    # 3. Animación: caricaturas, escenarios, sucesos y efectos de sonido
    print("3/5 Animación")
    v = cfg["video"]
    shots, sfx = render_episode(series, part, durations, workdir, cfg, words)

    # 4. Subtítulos + montaje
    print("4/5 Subtítulos y montaje")
    badge = f"Parte {part.part_number}/{n}" if n > 1 else ""
    question = (getattr(part, "comment_question", "") or "").strip()
    follow = cfg["channel"].get("end_card", "Sígueme para más")
    if badge and part.part_number < n:
        end_card, end_sub = "Sigue en la parte 2", question
    elif question:  # la pregunta de dos opciones, en grande; debajo, la promesa de la marca
        end_card, end_sub = question, follow
    else:
        end_card, end_sub = follow, ""
    captions = CaptionRenderer(v["width"], v["height"], cfg["channel"].get("accent_color", "#E2A84B"), part.hook_title,
                               badge=badge, end_card=end_card, end_sub=end_sub, end_start=total - tail + 0.2,
                               caption_y=cfg.get("animation", {}).get("caption_y", 0.86),
                               stamps=_stamps(part.blocks, durations))
    cap_list = captions.render(words, total, workdir)
    video = assemble(shots, durations, voice, cap_list, total, workdir / "reel.mp4", workdir,
                     v.get("music_volume", 0.35), 0.0, sfx=sfx,
                     progress_color=cfg["channel"].get("accent_color") if v.get("progress_bar", True) else None,
                     music_names=cfg["channel"].get("music"))
    try:  # portada diseñada (fotograma del personaje + gancho), para que el vídeo no se vea con un fotograma cualquiera
        from .cover import make_cover, pick_frame
        f, at = pick_frame(shots, [b.framing for b in part.blocks], durations)
        make_cover(f, at, part.hook_title, cfg["channel"].get("accent_color", "#E2A84B"), badge,
                   cfg["channel"]["name"], workdir / "portada.jpg")
    except Exception as e:
        print(f"  Aviso: no se pudo crear la portada: {e}", file=sys.stderr)
    print(f"  vídeo: {video}")
    return video, series, part


def _platforms_for(cfg: dict, slot) -> list[str]:
    """Redes de la marca para un vídeo; TikTok se salta si está en pausa (`tiktok_paused_until`) ese día."""
    ch = cfg["channel"]
    every = ch.setdefault("_all_platforms", list(ch["platforms"]))
    until = ch.get("tiktok_paused_until")
    tz = ZoneInfo(cfg["publish"].get("timezone", "Europe/Madrid"))
    day = (slot or datetime.now(timezone.utc)).astimezone(tz).date()
    if until and day <= date.fromisoformat(str(until)):
        return [p for p in every if p != "tiktok"]
    return every


def publish_episode(cfg: dict, state: dict, history: list[dict], video, series, part, slot) -> bool:
    from .publish import failed_platforms, publish

    ch = cfg["channel"]
    n = len(series.parts)
    when = f"programado para {slot:%d/%m %H:%M}" if slot else "ahora"
    ch["platforms"] = _platforms_for(cfg, slot)
    print(f"5/5 Publicando en {ch['profile']} ({', '.join(ch['platforms'])}) · {when}")
    key = f"{ch['id']}-{zlib.crc32((series.series_title + series.topic).encode())}-{part.part_number}"
    if slot:
        key += f"-{slot:%Y%m%d%H%M}"
    # Solo algunas historias mencionan el libro (no todo vídeo debe vender), y solo en su última parte.
    every = int(cfg.get("affiliate", {}).get("mention_every", 3) or 0)
    mention = bool(series.book and cfg.get("affiliate", {}).get("tag") and every and part.part_number == n
                   and zlib.crc32(series.series_title.encode()) % every == 0)
    result = publish(video, part, cfg, idempotency_key=key, total_parts=n, scheduled_at=slot, book=mention)
    failed = failed_platforms(result)
    if len(failed) >= len(ch["platforms"]) or failed in (["failed"], ["not_found"]):
        print(f"No se publicó en ninguna plataforma: {failed}. La parte queda pendiente.", file=sys.stderr)
        return False
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state["queue"].pop(0)
    state["last_published"] = now
    if slot:
        state.setdefault("scheduled", []).append(slot.isoformat())
    for h in reversed(history):
        if h["series_title"] == series.series_title:
            h["published_parts"].append({"part": part.part_number, "date": (slot or datetime.now()).date().isoformat(),
                                         "slot": slot.isoformat() if slot else None,
                                         "request_id": result.get("request_id"), "job_id": result.get("job_id"),
                                         "failed": failed, "at": now})
            break
    _save(cfg, "history.json", history)
    _save(cfg, "state.json", state)
    if failed:
        print(f"Publicado, pero falló en: {failed}", file=sys.stderr)
    return True


def compile_week(cfg: dict, args) -> int:
    from pathlib import Path

    from . import compile as C

    ch, cc = cfg["channel"], cfg.get("compilation", {})
    print(f"== Recopilación · {ch['name']} ==")
    if not cc.get("enabled", True) or not ch.get("enabled", True):
        print("Recopilaciones o canal desactivados.")
        return 0
    slot = C.next_slot(cfg)
    week = f"{slot.isocalendar()[0]}-W{slot.isocalendar()[1]:02d}"
    done = _load(cfg, "compilations.json", [])
    if any(c.get("week") == week for c in done) and not args.dry_run:
        print(f"La recopilación de la semana {week} ya está hecha.")
        return 0
    roots = [Path(p) for p in (args.clips or [str(OUT)])]
    clips = C.find_clips(ch["id"], roots)
    stories = C.pick_stories(cfg, clips, float(cc.get("max_minutes", 20)))
    print(f"  {len(clips)} vídeos disponibles · {len(stories)} historias completas: "
          + "; ".join(s["title"] for s in stories))
    if len(stories) < int(cc.get("min_stories", 3)):
        print(f"  Hacen falta al menos {cc.get('min_stories', 3)} historias completas: esta semana no hay recopilación.")
        return 0
    workdir = OUT / f"{ch['id']}_recopilacion_{week}"
    video, chapters = C.build_video(stories, workdir)
    texts = C.make_texts(cfg, stories, chapters, slot)
    thumb = C.thumbnail(texts["thumb_text"], stories[0]["dirs"][0] / "reel.mp4", ch.get("accent_color", "#E2A84B"),
                        workdir / "miniatura.jpg")
    (workdir / "textos.json").write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  vídeo: {video} ({C._ts(sum(s['seconds'] for s in stories))}) · título: {texts['title']}")
    if args.dry_run:
        print("Modo prueba: no se publica.")
        return 0
    from .publish import publish_youtube
    result = publish_youtube(video, texts["title"], texts["description"], texts["tags"], cfg,
                             key=f"{ch['id']}-recopilacion-{week}", scheduled_at=slot, thumb=thumb)
    done.append({"week": week, "slot": slot.isoformat(), "title": texts["title"],
                 "stories": [s["title"] for s in stories],
                 "request_id": result.get("request_id"), "job_id": result.get("job_id")})
    _save(cfg, "compilations.json", done)
    print(f"Recopilación programada para {slot:%d/%m %H:%M}.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Episodios automáticos por canal")
    ap.add_argument("--channel", help="canal de config.yaml (por defecto, el primero)")
    ap.add_argument("--dry-run", action="store_true", help="genera un vídeo de prueba y no publica")
    ap.add_argument("--now", action="store_true", help="genera uno y lo publica al momento (sin programar)")
    ap.add_argument("--max", type=int, default=0, help="máximo de franjas a programar en esta ejecución")
    ap.add_argument("--horizon", type=float, default=24, help="programa las franjas de las próximas N horas")
    ap.add_argument("--new", action="store_true", help="empieza una historia nueva aunque haya partes pendientes")
    ap.add_argument("--topic", help="tema concreto para la historia nueva")
    ap.add_argument("--format", help="formato de la historia nueva (ver formats del canal en config.yaml)")
    ap.add_argument("--force", action="store_true", help="publica aunque el canal esté en pausa (enabled: false)")
    ap.add_argument("--check", action="store_true", help="lista los canales activos y sus franjas pendientes")
    ap.add_argument("--status", action="store_true", help="consulta en Upload-Post cómo acabaron las últimas publicaciones")
    ap.add_argument("--unlabel", action="store_true", help="quita la etiqueta de IA de las publicaciones ya programadas")
    ap.add_argument("--compile", action="store_true", help="recopilación semanal para YouTube (con --clips)")
    ap.add_argument("--clips", action="append", default=[], help="carpeta con vídeos ya publicados (se puede repetir)")
    ap.add_argument("--pages", action="store_true", help="regenera la página de enlaces de la bio (docs/)")
    ap.add_argument("--cancel", help="quita de la programación el vídeo de una franja, p. ej. «2026-11-21 10:00»")
    ap.add_argument("--stats", action="store_true", help="guarda las visualizaciones de cada vídeo publicado")
    ap.add_argument("--accounts", action="store_true", help="enlaces de las cuentas conectadas en Upload-Post")
    args = ap.parse_args()
    if args.pages:
        from .pages import build
        names = [args.channel] if args.channel else list(load_config().get("channels", {}))
        for cid in names:
            print("  página:", build(load_config(cid)))
        return 0
    if args.accounts:
        from .publish import list_accounts
        cfg = load_config(args.channel)
        print(f"== {cfg['channel']['name']} (perfil {cfg['channel']['profile']}) ==")
        list_accounts(cfg["channel"]["profile"])
        return 0
    if args.compile:
        return compile_week(load_config(args.channel), args)
    if args.unlabel:
        from .publish import unlabel_scheduled
        unlabel_scheduled(load_config(args.channel)["channel"]["profile"])
        return 0
    if args.cancel:
        ok = cancel_slot(load_config(args.channel), args.cancel)
        if not ok:
            return 1
        # sigue: se vuelve a programar la franja vacía con una historia nueva

    if args.stats:
        update_stats(load_config(args.channel))
        return 0

    if args.status:
        from .publish import report
        cfg = load_config(args.channel)
        recent = [p for h in _load(cfg, "history.json", []) for p in h.get("published_parts", [])][-8:]
        for p in recent:
            print(f"Parte {p['part']} · {p.get('slot') or p.get('date')}")
            report([p.get("job_id") or p.get("request_id")] if (p.get("job_id") or p.get("request_id")) else [])
        return 0
    if args.check:
        for cid in load_config().get("channels", {}):
            c = load_config(cid)
            if c["channel"].get("enabled", True):
                st = _load(c, "state.json", {})
                print(cid, len(pending_slots(c, {"scheduled": st.get("scheduled", [])}, horizon=args.horizon)))
        return 0
    if args.topic or args.format:
        args.new = True

    cfg = load_config(args.channel)
    ch = cfg["channel"]
    print(f"== Canal {ch['id']} · {ch['name']} · perfil {ch['profile']} ==")
    history: list[dict] = _load(cfg, "history.json", [])
    state: dict = _load(cfg, "state.json", {"queue": [], "last_published": None, "scheduled": []})
    state.setdefault("scheduled", [])

    if args.dry_run:
        make_episode(cfg, state, history, args, f"prueba_{datetime.now():%Y%m%d_%H%M}")
        print("Modo prueba: no se publica. La parte sigue pendiente.")
        return 0
    if not ch.get("enabled", True) and not args.force:
        print("Canal en pausa (enabled: false en config.yaml): no se publica nada.")
        return 0
    if args.now:
        video, series, part = make_episode(cfg, state, history, args, f"{datetime.now():%Y%m%d_%H%M}")
        return 0 if publish_episode(cfg, state, history, video, series, part, None) else 1

    # Olvida las franjas ya pasadas hace más de 2 días
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    state["scheduled"] = [s for s in state["scheduled"] if datetime.fromisoformat(s) > cutoff]
    slots = pending_slots(cfg, state, horizon=args.horizon)
    if args.max:
        slots = slots[: args.max]
    if not slots:
        print(f"Todas las franjas de las próximas {args.horizon:g} h ya tienen vídeo programado.")
        _save(cfg, "state.json", state)
        return 0
    from .publish import LimitReached
    print("Franjas por programar:", ", ".join(f"{s:%d/%m %H:%M}" for s in slots))
    errors = 0
    for slot in slots:
        print(f"\n--- Franja {slot:%d/%m %H:%M} ---")
        try:
            args.single = _continuation_after(state, history, slot)
            video, series, part = make_episode(cfg, state, history, args, f"{slot:%Y%m%d_%H%M}")
            ok = publish_episode(cfg, state, history, video, series, part, slot)
        except LimitReached as e:
            print(f"{e}\nSe para aquí: contrata un plan con más publicaciones o espera al reinicio mensual.", file=sys.stderr)
            errors += 1
            break
        except Exception as e:  # una franja fallida no impide preparar las siguientes
            print(f"Error en la franja {slot:%H:%M}: {e}", file=sys.stderr)
            ok = False
        errors += not ok
        if errors >= 2:
            print("Dos franjas fallidas: se detiene esta ejecución.", file=sys.stderr)
            break
    _save(cfg, "state.json", state)
    try:  # la página de enlaces de la bio incluye los libros de las historias recién programadas
        from .pages import build
        build(cfg)
    except Exception as e:  # nunca debe impedir la publicación
        print(f"Aviso: no se pudo actualizar la página de enlaces: {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
