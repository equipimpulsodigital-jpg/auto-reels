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
        "## 2. Estilo Visual Maestro (fijo)", series.master_style, "",
        "## 3. Guion + Dirección Visual",
    ]
    t = 0.0
    for b, d in zip(part.blocks, durations):
        out += [f"**[{_fmt_time(t)} - {_fmt_time(t + d)}] {b.label.upper()}**",
                f"- *Voz en off:* \"{b.narration}\"",
                f"- *Cámara y animación:* {b.camera} · {b.visual_direction}",
                f"- *Prompt visual (9:16):* {b.image_prompt}", ""]
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
    from .images import generate_image
    from .publish import failed_platforms, publish
    from .render import assemble, shot_clip
    from .script import Series, generate_series, next_format
    from .tts import synthesize_scenes

    cfg = load_config()
    history: list[dict] = _load("history.json", [])
    state: dict = _load("state.json", {"queue": [], "last_published": None})
    today = date.today().isoformat()
    if not args.dry_run and not args.force and state.get("last_published") == today:
        print(f"Ya se publicó un episodio hoy ({today}). Usa --force para publicar otro.")
        return 0

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
    voice, durations, words = synthesize_scenes([b.narration for b in part.blocks], cfg, workdir)
    tail = 1.6 if n > 1 and part.part_number < n else 0.8
    durations[-1] += tail
    total = sum(durations)
    print(f"  {len(words)} palabras · {total:.1f} s · {len(part.blocks)} planos")
    write_guion(workdir / "guion.md", series, part, durations)

    # 3. Imágenes + movimiento de cámara
    print("3/5 Imágenes")
    v = cfg["video"]
    seed_base = zlib.crc32(series.series_title.encode()) % 100000
    shots = []
    for i, (b, dur) in enumerate(zip(part.blocks, durations)):
        img = generate_image(b.image_prompt, series.master_style, workdir / f"img_{i}.jpg",
                             seed_base + i, cfg)
        print(f"  plano {i + 1}/{len(part.blocks)} · {b.camera}" + ("" if img else " · SIN IMAGEN"))
        shots.append(shot_clip(img, b.camera, dur, workdir / f"shot_{i}.mp4", v["width"], v["height"], v["fps"]))

    # 4. Subtítulos + montaje
    print("4/5 Subtítulos y montaje")
    badge = f"Parte {part.part_number}/{n}" if n > 1 else ""
    end_card = "Sigue en la parte 2" if badge and part.part_number < n else ""
    captions = CaptionRenderer(v["width"], v["height"], cfg["style"]["accent_color"], part.hook_title,
                               badge=badge, end_card=end_card, end_start=total - tail + 0.2)
    cap_list = captions.render(words, total, workdir)
    video = assemble(shots, voice, cap_list, total, workdir / "reel.mp4", workdir, v.get("music_volume", 0.15))
    print(f"  vídeo: {video}")

    # 5. Publicación
    if args.dry_run:
        print("5/5 Publicación omitida (modo prueba). Esta parte sigue pendiente para la próxima ejecución.")
        return 0
    print("5/5 Publicando en", ", ".join(cfg["publish"]["platforms"]))
    result = publish(video, part, cfg, idempotency_key=f"ep-{today}-{zlib.crc32(series.series_title.encode())}-{part.part_number}")
    failed = failed_platforms(result)
    platforms = cfg["publish"]["platforms"]
    if len(failed) >= len(platforms) or failed == ["failed"]:
        print(f"No se publicó en ninguna plataforma: {failed}. La parte queda pendiente.", file=sys.stderr)
        return 1
    state["queue"].pop(0)
    state["last_published"] = today
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
