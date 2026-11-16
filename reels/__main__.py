"""Genera y publica el episodio del día (historia real de España, series de 1-2 partes).

Uso:
  python -m reels                       # siguiente parte pendiente, o una historia nueva
  python -m reels --dry-run             # genera el vídeo pero no lo publica
  python -m reels --topic "El motín de Esquilache" --new
  python -m reels --format crimen_historico --new
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from datetime import date, datetime, timezone

from .config import DATA, OUT, load_config


def _load(name: str, default):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _save(name: str, value) -> None:
    DATA.mkdir(exist_ok=True)
    (DATA / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hours_since(stamp) -> float:
    """Horas desde la última publicación (acepta el formato antiguo, solo fecha)."""
    if not stamp:
        return float("inf")
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return float("inf")
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - when).total_seconds() / 3600


def _fmt_time(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def write_guion(path, series, part, durations) -> None:
    """Guion legible con la estructura de la serie (ficha, estilo, bloques con tiempos, cierre)."""
    fmt = {"punto_inflexion": "Punto de inflexión", "crimen_historico": "Crimen histórico"}[series.format]
    n = len(series.parts)
    out = [
        f"# {series.series_title} · Parte {part.part_number}/{n}", "",
        "## 1. Ficha del episodio",
        f"- **Serie:** {series.series_title}", f"- **Parte:** {part.part_number}/{n}",
        f"- **Formato:** {fmt}", f"- **Año y lugar:** {series.year} · {series.place}",
        f"- **Notas históricas:** {series.historical_notes}", "",
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
                f"- *Animación:* {b.visual_direction} (gesto: {b.gesture}, emoción: {b.emotion})", ""]
        t += d
    out += ["## 4. Cierre / Gancho para la siguiente parte", part.cliffhanger, ""]
    path.write_text("\n".join(out), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Episodio diario automático")
    ap.add_argument("--dry-run", action="store_true", help="no publica, solo genera el vídeo")
    ap.add_argument("--new", action="store_true", help="empieza una historia nueva aunque haya partes pendientes")
    ap.add_argument("--topic", help="tema concreto para la historia nueva")
    ap.add_argument("--format", choices=["punto_inflexion", "crimen_historico"])
    ap.add_argument("--force", action="store_true", help="publica aunque ya se haya publicado hoy")
    args = ap.parse_args()

    from .captions import CaptionRenderer
    from .publish import failed_platforms, publish
    from .render import assemble
    from .toon.episode import render_episode
    from pydantic import ValidationError

    from .script import Series, generate_series, next_format
    from .tts import synthesize_scenes

    cfg = load_config()
    history: list[dict] = _load("history.json", [])
    state: dict = _load("state.json", {"queue": [], "last_published": None})
    today = date.today().isoformat()
    gap_h = float(cfg["publish"].get("min_hours_between", 2))
    if not args.dry_run and not args.force and _hours_since(state.get("last_published")) < gap_h:
        print(f"Se publicó hace menos de {gap_h:g} h ({state.get('last_published')}). Usa --force para publicar otro.")
        return 0

    # Historia pendiente en un formato antiguo (p. ej. de antes de la animación): se reescribe el mismo tema.
    if state["queue"] and not args.new:
        try:
            Series.model_validate(state["queue"][0]["series"])
        except ValidationError:
            old = state["queue"][0]["series"]
            print(f"  «{old.get('series_title')}» está en un formato antiguo: se vuelve a escribir para animación.")
            history = [h for h in history
                       if not (h.get("series_title") == old.get("series_title") and not h.get("published_parts"))]
            state["queue"] = []
            args.topic = args.topic or old.get("topic")
            args.format = args.format or old.get("format")

    # 1. Guion: siguiente parte pendiente o historia nueva (con todas sus partes de una vez)
    if args.new or args.topic or args.format or not state["queue"]:
        fmt = next_format(history, args.format)
        print(f"1/5 Historia nueva · {fmt}" + (f" · tema: {args.topic}" if args.topic else ""))
        series = generate_series(cfg, fmt, history, args.topic)
        history.append({"date": today, "format": series.format, "topic": series.topic,
                        "series_title": series.series_title, "parts": len(series.parts), "published_parts": []})
        state["queue"] = [{"series": series.model_dump(), "part": i} for i in range(len(series.parts))]
        _save("history.json", history)
        _save("state.json", state)
    else:
        print("1/5 Siguiente parte pendiente")
    item = state["queue"][0]
    series = Series.model_validate(item["series"])
    part = series.parts[item["part"]]
    n = len(series.parts)
    print(f"  «{series.series_title}» · Parte {part.part_number}/{n} · {series.year}, {series.place}")
    print(f"  gancho: {part.hook_title}")

    workdir = OUT / f"{today}_p{part.part_number}"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "series.json").write_text(series.model_dump_json(indent=2), encoding="utf-8")

    # 2. Voz en off (un audio por plano: así cada imagen dura lo que su frase)
    print("2/5 Voz en off")
    chars = {c.id: c for c in series.characters}
    speakers = [(chars[b.speaker].voice, chars[b.speaker].name) if b.speaker in chars else ("", "")
                for b in part.blocks]
    voice, durations, words = synthesize_scenes([b.narration for b in part.blocks], cfg, workdir, speakers)
    tail = 1.6 if n > 1 and part.part_number < n else 0.8
    durations[-1] += tail
    total = sum(durations)
    print(f"  {len(words)} palabras · {total:.1f} s · {len(part.blocks)} planos")
    write_guion(workdir / "guion.md", series, part, durations)

    # 3. Animación: caricaturas, escenarios, sucesos y efectos de sonido
    print("3/5 Animación")
    v = cfg["video"]
    shots, sfx = render_episode(series, part, durations, workdir, cfg)

    # 4. Subtítulos + montaje
    print("4/5 Subtítulos y montaje")
    badge = f"Parte {part.part_number}/{n}" if n > 1 else ""
    end_card = "Sigue en la parte 2" if badge and part.part_number < n else ""
    captions = CaptionRenderer(v["width"], v["height"], cfg["style"]["accent_color"], part.hook_title,
                               badge=badge, end_card=end_card, end_start=total - tail + 0.2, caption_y=cfg.get("animation", {}).get("caption_y", 0.86))
    cap_list = captions.render(words, total, workdir)
    video = assemble(shots, durations, voice, cap_list, total, workdir / "reel.mp4", workdir,
                     v.get("music_volume", 0.35), 0.0, sfx=sfx)
    print(f"  vídeo: {video}")

    # 5. Publicación
    if args.dry_run:
        print("5/5 Publicación omitida (modo prueba). Esta parte sigue pendiente para la próxima ejecución.")
        return 0
    print("5/5 Publicando en", ", ".join(cfg["publish"]["platforms"]))
    result = publish(video, part, cfg, idempotency_key=f"ep-{today}-{zlib.crc32(series.series_title.encode())}-{part.part_number}",
                     total_parts=n)
    failed = failed_platforms(result)
    platforms = cfg["publish"]["platforms"]
    if len(failed) >= len(platforms) or failed == ["failed"]:
        print(f"No se publicó en ninguna plataforma: {failed}. La parte queda pendiente.", file=sys.stderr)
        return 1
    state["queue"].pop(0)
    state["last_published"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for h in reversed(history):
        if h["series_title"] == series.series_title:
            h["published_parts"].append({"part": part.part_number, "date": today,
                                         "request_id": result.get("request_id"), "failed": failed,
                                         "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            break
    _save("history.json", history)
    _save("state.json", state)
    if failed:
        print(f"Publicado, pero falló en: {failed}", file=sys.stderr)
        return 1
    print("Publicado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
