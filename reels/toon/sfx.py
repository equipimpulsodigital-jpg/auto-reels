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


ONESHOTS = {"boom": (boom, 0.9), "splash": (splash, 0.55), "whoosh": (whoosh, 0.35), "hit": (hit, 0.6)}
AMBIENCES = {"mar": (waves, 0.16), "viento": (wind, 0.14), "avion": (drone, 0.22)}


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
