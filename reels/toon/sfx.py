"""Efectos de sonido sintetizados (propios, sin derechos de terceros) y pista de efectos del vídeo."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
_rng = np.random.default_rng(11)


def _shape(noise: np.ndarray, lo: float, hi: float, tilt: float = 0.0) -> np.ndarray:
    """Filtra ruido en frecuencia (paso banda lo-hi, con inclinación tipo ruido rosa/marrón)."""
    spec = np.fft.rfft(noise)
    f = np.fft.rfftfreq(len(noise), 1 / SR)
    gain = ((f >= lo) & (f <= hi)).astype(float)
    if tilt:
        gain *= 1 / np.maximum(f, 20) ** tilt
    out = np.fft.irfft(spec * gain, n=len(noise))
    return out / (np.max(np.abs(out)) + 1e-9)


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def boom(dur: float = 4.0) -> np.ndarray:
    t = _t(dur)
    sub = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t * 3)) / SR) * np.exp(-t * 1.1)
    body = _shape(_rng.standard_normal(len(t)), 20, 900, tilt=1.0) * np.exp(-t * 1.4)
    crack = _shape(_rng.standard_normal(len(t)), 1500, 9000) * np.exp(-t * 9)
    x = 0.9 * sub + 0.9 * body + 0.35 * crack
    x[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
    return x / np.max(np.abs(x))


def drone(dur: float) -> np.ndarray:
    """Motores de avión a reacción lejanos."""
    t = _t(dur)
    roar = _shape(_rng.standard_normal(len(t)), 60, 2500, tilt=0.8)
    whine = 0.15 * np.sin(2 * np.pi * (520 + 8 * np.sin(t * 0.7)) * t)
    lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.35 * t)
    return (0.8 * roar + whine) * lfo


def waves(dur: float) -> np.ndarray:
    t = _t(dur)
    surf = _shape(_rng.standard_normal(len(t)), 80, 6000, tilt=0.9)
    swell = 0.45 + 0.55 * np.maximum(0, np.sin(2 * np.pi * t / 5.5)) ** 2
    return surf * swell


def wind(dur: float) -> np.ndarray:
    t = _t(dur)
    w = _shape(_rng.standard_normal(len(t)), 200, 1400, tilt=0.5)
    return w * (0.5 + 0.5 * np.sin(2 * np.pi * t / 7 + 1) ** 2)


def splash(dur: float = 2.0) -> np.ndarray:
    t = _t(dur)
    hiss = _shape(_rng.standard_normal(len(t)), 700, 9000) * np.exp(-t * 3.5)
    thump = np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-t * 18)) / SR) * np.exp(-t * 7)
    return 0.8 * hiss + 0.8 * thump


def whoosh(dur: float = 0.7) -> np.ndarray:
    t = _t(dur)
    env = np.sin(np.pi * t / dur) ** 2
    lo = _shape(_rng.standard_normal(len(t)), 150, 1200)
    hi = _shape(_rng.standard_normal(len(t)), 1200, 7000)
    k = t / dur
    return (lo * (1 - k) + hi * k) * env


def hit(dur: float = 0.8) -> np.ndarray:
    """Golpe grave de transición (énfasis dramático)."""
    t = _t(dur)
    return np.sin(2 * np.pi * np.cumsum(45 + 70 * np.exp(-t * 25)) / SR) * np.exp(-t * 6)


def _room(dur: float, level: float = 0.25) -> np.ndarray:
    """Tono de sala: el silencio de un interior (aire, nevera lejana)."""
    t = _t(dur)
    return _shape(_rng.standard_normal(len(t)), 60, 900, tilt=0.6) * level


def _place(track: np.ndarray, snd: np.ndarray, at: float, gain: float) -> None:
    i = int(at * SR)
    j = min(len(track), i + len(snd))
    if 0 <= i < j:
        track[i:j] += snd[: j - i] * gain


def _blip(freq: float, dur: float, decay: float) -> np.ndarray:
    t = _t(dur)
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)


def cafe(dur: float) -> np.ndarray:
    """Cafetería o bar: murmullo de gente y tazas que tintinean."""
    t = _t(dur)
    murmur = _shape(_rng.standard_normal(len(t)), 250, 2800, tilt=0.3)
    murmur *= 0.7 + 0.3 * np.abs(np.sin(2 * np.pi * t * 0.6) * np.sin(2 * np.pi * t * 1.7))
    out = murmur * 0.8 + _room(dur, 0.3)
    for k in range(int(dur / 1.3) + 1):
        _place(out, _blip(_rng.uniform(2800, 4800), 0.3, 22) + 0.5 * _blip(_rng.uniform(5000, 7000), 0.3, 30),
               _rng.uniform(0, dur), 0.25)
    return out


def trafico(dur: float) -> np.ndarray:
    """Calle: rumor de tráfico, coches que pasan y algún claxon lejano."""
    t = _t(dur)
    out = _shape(_rng.standard_normal(len(t)), 30, 450, tilt=0.8) * 1.2
    for k in range(int(dur / 2.2) + 1):
        at, d = _rng.uniform(-0.5, dur), 2.0
        tt = _t(d)
        car = _shape(_rng.standard_normal(len(tt)), 80, 2500, tilt=0.5) * np.sin(np.pi * tt / d) ** 3
        _place(out, car, max(0.0, at), 0.6)
    if dur > 3 and _rng.random() < 0.5:
        horn = (np.sign(np.sin(2 * np.pi * 420 * _t(0.35))) + np.sign(np.sin(2 * np.pi * 530 * _t(0.35)))) * 0.15
        _place(out, _shape(horn, 200, 3000), _rng.uniform(0.5, dur - 1), 0.25)
    return out


def noche(dur: float) -> np.ndarray:
    """Exterior de noche: grillos y un poco de viento."""
    t = _t(dur)
    chirp = np.sin(2 * np.pi * 4600 * t) * (np.sin(2 * np.pi * 28 * t) > 0.3) * (np.sin(2 * np.pi * 1.1 * t) > -0.2)
    chirp2 = np.sin(2 * np.pi * 5200 * t) * (np.sin(2 * np.pi * 31 * t + 1) > 0.4) * (np.sin(2 * np.pi * 0.8 * t + 2) > 0)
    return 0.18 * chirp + 0.12 * chirp2 + 0.5 * wind(dur)


def pajaros(dur: float) -> np.ndarray:
    """Campo de día: pájaros y brisa."""
    out = 0.4 * wind(dur)
    for k in range(int(dur * 1.5) + 1):
        d = _rng.uniform(0.08, 0.2)
        tt = _t(d)
        f0 = _rng.uniform(2500, 4500)
        sw = np.sin(2 * np.pi * np.cumsum(f0 + 1800 * np.sin(np.pi * tt / d)) / SR) * np.sin(np.pi * tt / d)
        _place(out, sw, _rng.uniform(0, dur), 0.22)
    return out


def reloj(dur: float) -> np.ndarray:
    """Despacho, aula o salón: tono de sala y el tic-tac de un reloj."""
    out = _room(dur, 0.5)
    for k in range(int(dur) + 1):
        _place(out, _shape(_rng.standard_normal(int(0.02 * SR)), 2000, 8000) * np.exp(-_t(0.02) * 200), k + 0.1, 0.5)
    return out


def hospital(dur: float) -> np.ndarray:
    out = _room(dur, 0.6)
    for k in range(int(dur / 0.9) + 1):
        _place(out, _blip(1000, 0.12, 15), k * 0.9 + 0.2, 0.25)
    return out


def oficina(dur: float) -> np.ndarray:
    out = _room(dur, 0.6)
    for k in range(int(dur * 4)):
        click = _shape(_rng.standard_normal(int(0.015 * SR)), 1500, 6000) * np.exp(-_t(0.015) * 300)
        _place(out, click, _rng.uniform(0, dur), 0.18)
    return out


def lluvia(dur: float) -> np.ndarray:
    t = _t(dur)
    rain = _shape(_rng.standard_normal(len(t)), 1500, 9000, tilt=0.3)
    drops = np.zeros(len(t))
    for k in range(int(dur * 25)):
        _place(drops, _blip(_rng.uniform(1500, 4000), 0.03, 120), _rng.uniform(0, dur), 0.3)
    return 0.7 * rain + drops + 0.3 * wind(dur)


def fuego(dur: float) -> np.ndarray:
    t = _t(dur)
    roar = _shape(_rng.standard_normal(len(t)), 40, 600, tilt=0.8)
    out = roar * 0.8
    for k in range(int(dur * 18)):
        crack = _shape(_rng.standard_normal(int(0.01 * SR)), 1500, 9000) * np.exp(-_t(0.01) * 400)
        _place(out, crack, _rng.uniform(0, dur), _rng.uniform(0.2, 0.6))
    return out


def sala(dur: float) -> np.ndarray:
    return _room(dur, 0.7)


def pasos(dur: float, every: float = 0.48) -> np.ndarray:
    """Pasos (cada `every` segundos): caminar 0.48 s, correr 0.26 s."""
    out = np.zeros(int(dur * SR) + 1)
    k = 0
    while k * every < dur:
        st = _shape(_rng.standard_normal(int(0.07 * SR)), 80, 1800, tilt=0.4) * np.exp(-_t(0.07) * 60)
        _place(out, st, k * every + _rng.uniform(-0.02, 0.02), 0.7 if k % 2 else 0.55)
        k += 1
    return out


ONESHOTS = {"boom": (boom, 0.9), "splash": (splash, 0.55), "whoosh": (whoosh, 0.35), "hit": (hit, 0.6)}
AMBIENCES = {"mar": (waves, 0.16), "viento": (wind, 0.14), "avion": (drone, 0.22), "cafe": (cafe, 0.12),
             "trafico": (trafico, 0.12), "noche": (noche, 0.12), "pajaros": (pajaros, 0.12), "reloj": (reloj, 0.1),
             "hospital": (hospital, 0.1), "oficina": (oficina, 0.1), "lluvia": (lluvia, 0.14), "fuego": (fuego, 0.14),
             "sala": (sala, 0.08)}

# ambiente de cada escenario (de día / de noche) cuando el escenario no trae uno propio
LOC_AMBIENCE = {
    "cafeteria": ("cafe", "cafe"), "taberna": ("cafe", "cafe"), "calle": ("trafico", "trafico"),
    "ciudad": ("trafico", "noche"), "carretera": ("viento", "noche"), "pueblo": ("pajaros", "noche"),
    "campo": ("pajaros", "noche"), "bosque": ("pajaros", "noche"), "cementerio": ("viento", "noche"),
    "caseron": ("noche", "noche"), "castillo": ("viento", "noche"), "despacho": ("reloj", "reloj"),
    "aula": ("reloj", "reloj"), "salon": ("reloj", "reloj"), "palacio": ("sala", "sala"), "iglesia": ("sala", "sala"),
    "carcel": ("sala", "sala"), "tribunal": ("sala", "sala"), "hospital": ("hospital", "hospital"),
    "oficina": ("oficina", "oficina"), "casa": ("sala", "sala"), "dormitorio": ("sala", "reloj"),
    "laboratorio": ("sala", "sala"), "estacion": ("viento", "noche"), "desierto": ("viento", "viento"),
}


def pick_ambience(shot, loc_ambience: str, event_ambience: str) -> str:
    """El ambiente del plano: el del suceso, si no el del escenario, y si no uno según el lugar y la hora."""
    if shot.event in ("lluvia",) or shot.mood == "tormenta":
        return "lluvia"
    if shot.event in ("fuego", "explosion", "bombardeo"):
        return "fuego"
    if shot.ambience or event_ambience:
        return shot.ambience or event_ambience
    day, night = LOC_AMBIENCE.get(shot.location, (loc_ambience, loc_ambience))
    return night if shot.mood == "noche" else (day or loc_ambience)


def build_track(shots: list, durations: list[float], total: float, out: Path) -> Path:
    """Pista de efectos alineada con los planos: ambiente de cada plano + efectos puntuales."""
    track = np.zeros(int(total * SR) + SR)
    start = 0.0
    for shot, dur in zip(shots, durations):
        a = int(start * SR)
        amb_name = shot.resolved_ambience() if hasattr(shot, "resolved_ambience") else shot.ambience
        if amb_name in AMBIENCES:
            fn, gain = AMBIENCES[amb_name]
            amb = fn(dur)
            fade = min(len(amb) // 2, int(0.25 * SR))
            amb[:fade] *= np.linspace(0, 1, fade)
            amb[-fade:] *= np.linspace(1, 0, fade)
            track[a:a + len(amb)] += amb[: len(track) - a] * gain
        action = getattr(shot, "action", "")
        if shot.framing == "general" and (getattr(shot, "walk", False) or action == "correr"):  # pasos
            steps = pasos(dur, 0.26 if action == "correr" else 0.48)
            track[a:a + len(steps)] += steps[: len(track) - a] * 0.3
        for name, at in (shot.resolved_sfx() if hasattr(shot, "resolved_sfx") else shot.sfx):
            if name in ONESHOTS:
                fn, gain = ONESHOTS[name]
                snd = fn()
                b = int((start + at) * SR)
                if 0 <= b < len(track):
                    track[b:b + len(snd)] += snd[: len(track) - b] * gain
        start += dur
    track = np.tanh(track * 1.2) * 0.8  # limita picos sin distorsión fea
    pcm = (np.clip(track, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out
