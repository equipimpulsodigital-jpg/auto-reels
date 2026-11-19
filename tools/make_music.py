"""Compone las pistas de música de fondo (propias, sin derechos de terceros) en assets/music.

Solo hace falta ejecutarlo una vez (o si quieres pistas nuevas):
  pip install numpy && python tools/make_music.py
"""
from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "music"
rng = np.random.default_rng(7)


def hz(note: int) -> float:  # nota MIDI → Hz
    return 440.0 * 2 ** ((note - 69) / 12)


def env(n: int, a: float, r: float) -> np.ndarray:
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / r)
    return e


def pad(freqs: list[float], dur: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):  # ligeramente desafinado → coro suave
            ff = f * 2 ** (det / 12)
            for h, amp in ((1, 1.0), (2, 0.35), (3, 0.15), (4, 0.07)):
                out += amp * np.sin(2 * np.pi * ff * h * t + rng.uniform(0, 6.28))
    fade = np.minimum(1.0, np.minimum(t / 0.8, (dur - t) / 0.8))
    return out * np.clip(fade, 0, 1) / (len(freqs) * 4)


def pluck(f: float, dur: float, bright: float = 0.5) -> np.ndarray:
    """Cuerda pulsada (Karplus-Strong): pizzicato / arpa."""
    n = int(dur * SR)
    period = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.5 * (buf[i % period] + buf[(i + 1) % period]) * (0.990 + 0.009 * bright)
    return out * env(n, 0.002, dur / 3)


def bell(f: float, dur: float) -> np.ndarray:
    """Caja de música / celesta."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
         + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 10))
    return s * env(n, 0.003, 0.7)


def drum(dur: float, f0: float = 70, decay: float = 0.25) -> np.ndarray:
    """Bombo/timbal grave (latido)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + 1.5 * np.exp(-t * 30))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)


def tick(dur: float = 0.08) -> np.ndarray:
    n = int(dur * SR)
    noise = rng.uniform(-1, 1, n)
    noise = np.diff(noise, prepend=0)  # agudo
    return noise * np.exp(-np.arange(n) / SR / 0.015) * 0.5


def place(track: np.ndarray, sound: np.ndarray, at: float, gain: float) -> None:
    i = int(at * SR)
    j = min(len(track), i + len(sound))
    if i < j:
        track[i:j] += sound[: j - i] * gain


def chord_notes(root: int, minor: bool) -> list[int]:
    return [root, root + (3 if minor else 4), root + 7]


def compose(name: str, bpm: int, chords: list[tuple[int, bool]], lead: str, beat: str, bars: int = 24) -> np.ndarray:
    spb = 60 / bpm  # segundos por pulso
    bar = 4 * spb
    total = bars * bar + 2.5
    tr = {k: np.zeros(int(total * SR)) for k in ("pad", "lead", "perc")}
    for b in range(bars):
        root, minor = chords[b % len(chords)]
        notes = chord_notes(root, minor)
        t0 = b * bar
        place(tr["pad"], pad([hz(n) for n in notes] + [hz(root - 12)], bar + 0.8), t0, 1.0)
        # arpegio: más denso a partir de la 2.ª vuelta para que la pista crezca
        steps = 8 if b >= len(chords) else 4
        pattern = [0, 1, 2, 1, 0, 2, 1, 2] if steps == 8 else [0, 1, 2, 1]
        for s in range(steps):
            n = notes[pattern[s]] + 12 + (12 if lead == "bell" else 0)
            at = t0 + s * bar / steps
            snd = bell(hz(n), 1.2) if lead == "bell" else pluck(hz(n), 1.0, 0.4)
            place(tr["lead"], snd, at, 0.55 if lead == "bell" else 0.8)
        if b >= 1:
            if beat == "heart":
                for p in (0, 2):
                    place(tr["perc"], drum(0.5, 55, 0.18), t0 + p * spb, 0.9)
                    place(tr["perc"], drum(0.4, 50, 0.14), t0 + p * spb + 0.28, 0.55)
            elif beat == "tick":
                for p in range(8):
                    place(tr["perc"], tick(), t0 + p * spb / 2, 0.25 if p % 2 else 0.4)
                place(tr["perc"], drum(0.6, 60, 0.25), t0, 0.7)
            elif beat == "bounce":  # alegre: bombo suave en 1 y 3, chasquido en 2 y 4, hi-hat a contratiempo
                for p in range(4):
                    if p % 2 == 0:
                        place(tr["perc"], drum(0.35, 65, 0.12), t0 + p * spb, 0.75)
                    else:
                        place(tr["perc"], tick(0.12), t0 + p * spb, 0.8)
                    place(tr["perc"], tick(0.05), t0 + p * spb + spb / 2, 0.25)
            elif beat == "none":
                pass
            elif beat == "taiko":
                for p, g in ((0, 1.0), (1.5, 0.6), (2, 0.85), (3.5, 0.5)):
                    place(tr["perc"], drum(0.9, 48, 0.35), t0 + p * spb, g)
    mix = 0.55 * tr["pad"] + 0.35 * tr["lead"] + 0.45 * tr["perc"]
    t = np.arange(len(mix)) / SR
    mix *= np.clip(np.minimum(t / 1.5, (total - t) / 2.5), 0, 1)
    return mix / (np.max(np.abs(mix)) + 1e-9) * 0.9


def save(name: str, x: np.ndarray) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "x.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        mp3 = OUT / f"{name}.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af",
                        "aecho=0.8:0.6:90|170:0.25|0.15,lowpass=f=9000,loudnorm=I=-16:TP=-1.5",
                        "-ac", "2", "-b:a", "160k", mp3], check=True)
    print("  ", mp3.name)


if __name__ == "__main__":
    # Re menor: Dm - Bb - Gm - A  · La menor: Am - F - C - E · Mi menor: Em - C - G - D
    save("misterio", compose("misterio", 84, [(50, True), (46, False), (43, True), (45, False)], "pluck", "heart"))
    save("intriga", compose("intriga", 96, [(57, True), (53, False), (48, False), (52, False)], "bell", "tick"))
    save("epica", compose("epica", 90, [(52, True), (48, False), (43, False), (50, False)], "pluck", "taiko"))
    # Más variedad (cada marca usa las suyas: config.yaml → channels.<canal>.music)
    save("suspense", compose("suspense", 100, [(54, True), (50, False), (52, False), (49, False)], "bell", "tick"))
    save("niebla", compose("niebla", 72, [(48, True), (44, False), (46, False), (43, False)], "pluck", "heart"))
    save("chispa", compose("chispa", 112, [(60, False), (55, False), (57, True), (53, False)], "pluck", "bounce"))
    save("cita", compose("cita", 104, [(55, False), (50, False), (52, True), (48, False)], "bell", "bounce"))
    save("calma", compose("calma", 74, [(57, True), (53, False), (48, False), (55, False)], "bell", "none"))
    save("pensar", compose("pensar", 82, [(50, False), (55, False), (47, True), (52, False)], "pluck", "tick"))
    save("cosmos", compose("cosmos", 96, [(52, False), (54, False), (49, True), (47, False)], "bell", "tick"))
    save("experimento", compose("experimento", 110, [(58, False), (53, False), (55, True), (51, False)], "pluck", "bounce"))
