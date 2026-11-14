"""Genera y publica el reel del día.

Uso:
  python -m reels                 # genera y publica
  python -m reels --dry-run       # genera el vídeo pero no lo publica
  python -m reels --sample        # usa un guion de ejemplo (no llama a Claude) y no publica
  python -m reels --format consejo --force
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone

from .config import DATA, OUT, load_config


def load_history() -> list[dict]:
    path = DATA / "history.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save_history(history: list[dict]) -> None:
    DATA.mkdir(exist_ok=True)
    (DATA / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Reel diario automático")
    ap.add_argument("--dry-run", action="store_true", help="no publica, solo genera el vídeo")
    ap.add_argument("--sample", action="store_true", help="guion de ejemplo sin llamar a Claude (implica --dry-run)")
    ap.add_argument("--format", help="fuerza un formato de config.yaml")
    ap.add_argument("--force", action="store_true", help="publica aunque ya se haya publicado hoy")
    args = ap.parse_args()
    dry = args.dry_run or args.sample

    # Imports diferidos: así --help funciona sin dependencias instaladas.
    from .captions import CaptionRenderer
    from .footage import Footage
    from .publish import failed_platforms, publish
    from .render import assemble, scene_clip
    from .script import generate_script, pick_format, sample_script
    from .tts import synthesize_scenes

    cfg = load_config()
    history = load_history()
    today = date.today().isoformat()
    if not dry and not args.force and any(h["date"] == today and h.get("published") for h in history):
        print(f"Ya se publicó un reel hoy ({today}). Usa --force para publicar otro.")
        return 0

    workdir = OUT / today
    workdir.mkdir(parents=True, exist_ok=True)

    # 1. Guion
    fmt = pick_format(cfg, history, args.format)
    print(f"1/5 Guion · formato «{fmt['id']}»")
    script = sample_script() if args.sample else generate_script(cfg, fmt, history)
    (workdir / "script.json").write_text(script.model_dump_json(indent=2), encoding="utf-8")
    print(f"  tema: {script.topic}\n  gancho: {script.hook_title}")

    # 2. Voz en off
    print("2/5 Voz en off")
    voice, durations, words = synthesize_scenes([s.narration for s in script.scenes], cfg, workdir)
    tail = 0.6
    durations[-1] += tail
    total = sum(durations)
    print(f"  {len(words)} palabras · {total:.1f} s")

    # 3. Clips de fondo
    print("3/5 Clips de fondo")
    v = cfg["video"]
    footage = Footage()
    if not footage.key:
        print("  (sin PEXELS_API_KEY: se usarán fondos de color)")
    scene_files = []
    for i, (scene, dur) in enumerate(zip(script.scenes, durations)):
        src = footage.clip_for(scene.footage_query, dur)
        scene_files.append(scene_clip(src, dur, workdir / f"scene_{i}.mp4", v["width"], v["height"], v["fps"], i))

    # 4. Subtítulos + montaje
    print("4/5 Subtítulos y montaje")
    captions = CaptionRenderer(v["width"], v["height"], cfg["brand"]["accent_color"], script.hook_title)
    cap_list = captions.render(words, total, workdir)
    video = assemble(scene_files, voice, cap_list, total, workdir / "reel.mp4", workdir, v.get("music_volume", 0.12))
    print(f"  vídeo: {video}")

    entry = {"date": today, "format": fmt["id"], "topic": script.topic, "hook": script.hook_title,
             "published": False, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    # 5. Publicación
    if dry:
        print("5/5 Publicación omitida (modo prueba)")
        if not args.sample:
            history.append(entry)
            save_history(history)
        return 0

    print("5/5 Publicando en", ", ".join(cfg["publish"]["platforms"]))
    result = publish(video, script, cfg, idempotency_key=f"reel-{today}-{len(history)}")
    failed = failed_platforms(result)
    entry.update(published=True, request_id=result.get("request_id"), failed=failed)
    history.append(entry)
    save_history(history)
    if failed:
        print(f"Fallo en: {failed}", file=sys.stderr)
        return 1
    print("Publicado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
