"""Prototipo: escena de Palomares con caricaturas animadas (narrador + Paco + oficial)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reels.captions import CaptionRenderer  # noqa: E402
from reels.config import load_config  # noqa: E402
from reels.render import assemble  # noqa: E402
from reels.toon.character import Character, Look  # noqa: E402
from reels.toon.film import Ctx, Shot, mouth_envelope, render_shot  # noqa: E402
from reels.toon.sfx import build_track  # noqa: E402
from reels.tts import synthesize_scenes  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out" / "proto-toon"
OUT.mkdir(parents=True, exist_ok=True)
cfg = load_config()
W, H, FPS = 1080, 1920, 30

chars = {
    "paco": Character("Paco", Look(skin="morena", hair="#8a8580", hat="gorra_plana", hat_color="#1f2a44",
                                   beard="bigotazo", beard_color="#e2ddd5", outfit="jersey", outfit_color="#2c3e66",
                                   nose="patata", jaw="redonda", age="mayor", seed=3)),
    "oficial": Character("Oficial", Look(skin="clara", hair="#6b4a2b", hat="gorra_militar", hat_color="#c9b27c",
                                         outfit="uniforme", outfit_color="#b59a62", accent_color="#d4af37",
                                         nose="aguileña", jaw="cuadrada", seed=5)),
}
names = {"paco": ("hombre_mayor", "Paco Simó"), "oficial": ("americano", "Oficial de la Navy")}

script = [
    (None, "17 de enero de 1966. Un B-52 reposta en pleno vuelo sobre Almería.",
     Shot("aviones", 0, camera="push_in", ambience="avion")),
    (None, "De repente, chocan. Y cuatro bombas de hidrógeno caen del cielo.",
     Shot("explosion", 0, camera="static", ambience="viento", sfx=[("boom", 0.9), ("whoosh", 2.0)])),
    ("paco", "¡Mira allí! Un paracaídas enorme... ¡y lleva algo colgando!",
     Shot("costa_mar_paracaídas", 0, gesture="point", brow=0.9, cast=["paco"], mood="dia", ambience="mar",
          sfx=[("hit", 0.0)])),
    (None, "El pescador Paco Simó lo ve hundirse frente a la costa.",
     Shot("hundimiento", 0, camera="pull_back", ambience="mar", sfx=[("whoosh", 1.0), ("splash", 1.6)])),
    ("oficial", "¿Está seguro, señor? ¿Dónde cayó exactamente?",
     Shot("costa_tierra", 0, gesture="explain", brow=-0.4, cast=["oficial", "paco"], ambience="mar")),
    ("paco", "Aquí mismo. ¡Lo vi hundirse con mis propios ojos!",
     Shot("costa_mar", 0, gesture="chest", brow=-0.3, cast=["paco", "oficial"], ambience="mar")),
    ("oficial", "El mar es enorme. Necesitamos algo más que una corazonada.",
     Shot("costa_tierra", 0, gesture="shrug", brow=0.2, smile=-0.3, cast=["oficial", "paco"], ambience="mar")),
    (None, "Nadie le hizo caso. Y la bomba seguía ahí abajo...",
     Shot("dos", 0, cast=["paco", "oficial"], listener_brow=-0.9, camera="push_in", ambience="mar",
          sfx=[("hit", 2.2)])),
]

speakers = [names[s] if s else ("", "") for s, _, _ in script]
voice, durations, words = synthesize_scenes([l for _, l, _ in script], cfg, OUT, speakers)
durations[-1] += 1.6
ctx = Ctx(W, H, FPS, chars)
files = []
for i, ((spk, _, shot), dur) in enumerate(zip(script, durations)):
    shot.duration = dur
    shot.speaker = spk
    frames = round(dur * FPS)
    shot.mouth = mouth_envelope(OUT / f"voice_{i}.wav", FPS, frames) if spk else []
    print(f"plano {i + 1}/{len(script)} · {shot.scene} · {dur:.1f} s", flush=True)
    files.append(render_shot(ctx, shot, OUT / f"shot_{i}.mp4"))

total = sum(durations)
cap = CaptionRenderer(W, H, cfg["style"]["accent_color"], "Vio caer una bomba H al mar", badge="Parte 1/2",
                      end_card="Sigue en la parte 2", end_start=total - 1.4, caption_y=0.86)
cap_list = cap.render(words, total, OUT)
fx = build_track([s for _, _, s in script], durations, total, OUT / "sfx.wav")
video = assemble(files, durations, voice, cap_list, total, OUT / "reel.mp4", OUT, 0.35, 0.0, sfx=fx)
print("vídeo:", video, f"{total:.1f} s")
