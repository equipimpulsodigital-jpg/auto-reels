"""Prueba de humo: genera un vídeo corto con un guion fijo (sin Claude ni publicar) en cada estilo en uso y
comprueba que sale bien. Se ejecuta en GitHub cada vez que cambia el código; si falla, GitHub avisa por correo."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import reels.__main__ as M
from reels.config import load_config

ROOT = Path(__file__).resolve().parent.parent
fixture = json.loads((ROOT / "tests" / "fixture_series.json").read_text(encoding="utf-8"))
tmp = Path(tempfile.mkdtemp(prefix="smoke_"))
M.channel_data = lambda cfg: tmp / cfg["channel"]["id"]

failures = []
styles_done = set()
for cid in load_config().get("channels", {}):
    cfg = load_config(cid)
    style = (cfg["channel"].get("render", "dibujos"), cfg["channel"].get("style", "caricatura"))
    if style in styles_done:  # un canal por estilo (y modo de dibujo) basta
        continue
    styles_done.add(style)
    folder = tmp / cid
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "state.json").write_text(json.dumps({"queue": [{"series": fixture, "part": 0}], "scheduled": []}))
    (folder / "history.json").write_text("[]")
    print(f"== {cid} ({style})", flush=True)
    sys.argv = ["reels", "--channel", cid, "--dry-run"]
    try:
        M.main()
        video = sorted(M.OUT.glob(f"{cid}_prueba_*/reel.mp4"))[-1]
        problem = M.qa_video(video)
    except Exception as e:  # noqa: BLE001
        problem = f"error: {e}"
    print(f"   {'OK' if not problem else 'FALLO: ' + problem}", flush=True)
    if problem:
        failures.append(f"{cid}: {problem}")

# la voz de reserva (por si el servicio principal falla algún día)
try:
    from reels.tts import _piper
    words = _piper("Esto es una prueba de la voz de reserva.", tmp / "piper.wav", "es-ES-AlvaroNeural", "+10%")
    print("   voz de reserva: OK" if words else "   voz de reserva: sin palabras")
    if not words:
        failures.append("voz de reserva sin palabras")
except Exception as e:  # noqa: BLE001
    failures.append(f"voz de reserva: {e}")
    print(f"   voz de reserva: FALLO {e}")

if failures:
    print("\nFALLOS:\n- " + "\n- ".join(failures))
    sys.exit(1)
print("\nTodo bien.")
