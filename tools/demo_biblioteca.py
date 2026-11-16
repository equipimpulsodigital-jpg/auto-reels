"""Vídeo muestrario de la biblioteca: lugares, planos, vestuario, objetos y sucesos."""
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

OUT = Path(__file__).resolve().parent.parent / "out" / "demo-biblioteca"
OUT.mkdir(parents=True, exist_ok=True)
cfg = load_config()
W, H, FPS = 1080, 1920, 30

chars = {
    "rey": Character("El rey", Look(skin="clara", hair="#5a3b22", hat="corona", beard="barba", outfit="capa",
                                   outfit_color="#8e1b26", accent_color="#f2ead6", nose="aguileña", jaw="fina", age="mayor", seed=11)),
    "noble": Character("El duque", Look(skin="clara", hair="#1f1a17", hat="sombrero", hat_color="#1d1d22", beard="perilla",
                                       outfit="noble", outfit_color="#23232b", accent_color="#c9a227", nose="gancho", jaw="fina", seed=12)),
    "monja": Character("Sor Inés", Look(skin="clara", hat="toca", hat_color="#1f1f26", outfit="sotana", outfit_color="#1f1f26",
                                       nose="pequeña", jaw="fina", female=True, eyes="#3a5a7a", seed=13)),
    "guardia": Character("El guardia", Look(skin="media", hair="#2b211a", hat="tricornio", hat_color="#15171b", beard="bigote",
                                           outfit="uniforme", outfit_color="#3f5a3a", accent_color="#c9a227", nose="patata", jaw="cuadrada", seed=14)),
    "campesina": Character("Rosario", Look(skin="morena", hair="#2b1a12", hair_style="moño", hat="pañuelo", hat_color="#a8242c",
                                          outfit="vestido", outfit_color="#3a4a6b", nose="pequeña", jaw="redonda", female=True, seed=15)),
    "caballero": Character("Don Julián", Look(skin="clara", hair="#7a5a3a", hat="chistera", hat_color="#1b1b20", accent_color="#7a1f2a",
                                             beard="bigotazo", outfit="levita", outfit_color="#2a2f3a", nose="patata", glasses=True, seed=16)),
    "soldado": Character("Soldado", Look(skin="media", hair="#2b211a", hat="casco", hat_color="#4f5a3a", outfit="uniforme",
                                        outfit_color="#5a6342", accent_color="#8a8a6a", nose="patata", jaw="cuadrada", age="joven", seed=17)),
}
voices = {"rey": "hombre_mayor", "noble": "hombre_joven", "monja": "mujer_joven", "guardia": "hombre_mayor",
          "campesina": "mujer", "caballero": "hombre_joven", "soldado": "hombre_joven"}

script = [
    (None, "Palacios reales.", Shot("palacio", cast=["rey"], era="1500")),
    ("rey", "¡Que traigan al embajador ahora mismo!", Shot("palacio", framing="personaje", cast=["rey", "noble"], gesture="point", brow=-0.6, era="1500")),
    ("noble", "Majestad... el embajador ha huido.", Shot("palacio", framing="personaje", cast=["noble", "rey"], gesture="chest", brow=0.6, era="1500")),
    (None, "Conventos e iglesias.", Shot("iglesia", cast=["monja"], camera="pull_back")),
    (None, "Castillos bajo asedio.", Shot("castillo", event="cañonazos", era="medieval")),
    (None, "Traiciones a punta de espada.", Shot("castillo", framing="objeto", prop="espada")),
    ("caballero", "¿Ha oído lo del tren correo? ¡Un escándalo!", Shot("taberna", framing="dos", cast=["caballero", "campesina"], gesture="explain", brow=0.7, mood="noche")),
    (None, "Estaciones de tren.", Shot("estacion", cast=["caballero"], walk=True)),
    (None, "Calles a medianoche.", Shot("ciudad", cast=["guardia"], walk=True, mood="noche", event="lluvia")),
    (None, "Venenos.", Shot("salon", framing="objeto", prop="veneno", mood="noche")),
    ("campesina", "¡Yo no he sido! ¡Lo juro por mis hijos!", Shot("carcel", framing="personaje", cast=["campesina", "guardia"], gesture="shrug", brow=0.9)),
    ("guardia", "Aquí hay algo que no cuadra...", Shot("despacho", framing="personaje", cast=["guardia", "caballero"], gesture="think", brow=-0.5, mood="noche")),
    (None, "Mapas secretos.", Shot("tienda", framing="objeto", prop="mapa")),
    (None, "Campos de olivos.", Shot("campo", cast=["campesina"], mood="atardecer")),
    (None, "Guerras.", Shot("batalla", cast=["soldado"], event="disparos", camera="shake")),
    (None, "Fortunas.", Shot("palacio", framing="objeto", prop="monedas")),
    (None, "Y pueblos que se rebelaron.", Shot("pueblo", event="multitud", mood="atardecer")),
    (None, "Y crímenes en la oscuridad.", Shot("bosque", cast=["caballero"], walk=True, mood="noche", sfx=[("hit", 1.0)])),
]

speakers = [(voices[s], chars[s].name) if s else ("", "") for s, _, _ in script]
voice, durations, words = synthesize_scenes([l for _, l, _ in script], cfg, OUT, speakers)
durations = [max(d, 2.2) for d in durations]
durations[-1] += 1.2
ctx = Ctx(W, H, FPS, chars)
files = []
for i, ((spk, _, shot), dur) in enumerate(zip(script, durations)):
    shot.duration, shot.speaker = dur, spk
    shot.mouth = mouth_envelope(OUT / f"voice_{i}.wav", FPS, round(dur * FPS)) if spk else []
    print(f"plano {i + 1}/{len(script)} · {shot.location} · {shot.framing} · {dur:.1f} s", flush=True)
    files.append(render_shot(ctx, shot, OUT / f"shot_{i}.mp4"))

# la voz debe durar lo mismo que los planos (algunos se alargaron a 2,2 s)
import subprocess  # noqa: E402
parts = []
for i, d in enumerate(durations):
    padded = OUT / f"vpad_{i}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", OUT / f"voice_{i}.wav", "-af", f"apad=whole_dur={d:.3f}", padded], check=True)
    parts.append(padded)
(OUT / "vlist.txt").write_text("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", OUT / "vlist.txt", "-c", "copy", OUT / "voice_full.wav"], check=True)
# recoloca los tiempos de las palabras según los planos alargados
orig = []
acc = 0.0
from reels.media import probe_duration  # noqa: E402
for i in range(len(script)):
    orig.append(acc)
    acc += probe_duration(OUT / f"voice_{i}.wav")
starts = [sum(durations[:i]) for i in range(len(durations))]
for w in words:
    i = max(k for k in range(len(orig)) if orig[k] <= w.start + 1e-6)
    w.start += starts[i] - orig[i]
    w.end += starts[i] - orig[i]

total = sum(durations)
cap = CaptionRenderer(W, H, cfg["style"]["accent_color"], "La biblioteca de escenarios", end_card="", caption_y=0.86)
cap_list = cap.render(words, total, OUT)
fx = build_track([s for _, _, s in script], durations, total, OUT / "sfx.wav")
video = assemble(files, durations, OUT / "voice_full.wav", cap_list, total, OUT / "reel.mp4", OUT, 0.35, 0.0, sfx=fx)
print("vídeo:", video, f"{total:.1f} s")
