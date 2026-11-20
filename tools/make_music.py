"""Compone las pistas de música de fondo (propias, sin derechos de terceros) en assets/music.

Cada pista es una producción completa en estéreo: batería (trap, cinemática, pop, lo-fi o latido), bajo,
acordes, melodía con un motivo que se repite y varía, arpegios, subidas («risers») y golpes de impacto,
con reverb. Está pensada para vídeos cortos: ya suena con fuerza desde el segundo 0 (el gancho), entra
entera hacia el segundo 6-8, tiene un respiro a mitad y vuelve a subir para el final.

  pip install numpy && python tools/make_music.py            # todas
  python tools/make_music.py misterio cosmos                  # solo esas
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "music"

QUAL = {"m": [0, 3, 7], "M": [0, 4, 7], "m7": [0, 3, 7, 10], "M7": [0, 4, 7, 11], "7": [0, 4, 7, 10],
        "sus": [0, 5, 7], "m9": [0, 3, 7, 10, 14], "M9": [0, 4, 7, 11, 14], "dim": [0, 3, 6]}
MINOR = [0, 2, 3, 5, 7, 8, 10]
MAJOR = [0, 2, 4, 5, 7, 9, 11]
HARM = [0, 2, 3, 5, 7, 8, 11]  # menor armónica: más inquietante


def hz(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def tt(n: int) -> np.ndarray:
    return np.arange(n) / SR


# ---------- filtros (en frecuencia: rápidos y sin bucles) ----------
def _shape(x: np.ndarray, gain_fn) -> np.ndarray:
    if len(x) < 4:
        return x
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(spec * gain_fn(np.maximum(f, 1.0)), n=len(x))


def lowpass(x, fc, order=2):
    return _shape(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))


def highpass(x, fc, order=2):
    return _shape(x, lambda f: 1 / np.sqrt(1 + (fc / f) ** (2 * order)))


def bandpass(x, lo, hi):
    return highpass(lowpass(x, hi), lo)


def adsr(n, a=0.005, d=0.1, s=0.7, r=0.1):
    t = tt(n)
    dur = n / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((dur - t) / max(r, 1e-4), 0, 1)
    return e * rel


def saw(f, n, phase=0.0):
    return 2 * ((f * tt(n) + phase) % 1.0) - 1


# ---------- instrumentos ----------
def kick(punch=1.0, f_end=48, decay=0.32):
    n = int(0.6 * SR)
    t = tt(n)
    f = f_end + (160 * punch) * np.exp(-t * 28)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)
    click = highpass(np.random.default_rng(1).standard_normal(n), 3000) * np.exp(-t * 300) * 0.25
    return np.tanh(1.6 * (body + click))


def snare(tone=190, decay=0.16, bright=1.0, seed=2):
    n = int(0.45 * SR)
    t = tt(n)
    noise = bandpass(np.random.default_rng(seed).standard_normal(n), 900, 7000 * bright) * np.exp(-t / decay)
    body = np.sin(2 * np.pi * tone * t) * np.exp(-t * 28)
    x = 0.8 * noise / (np.abs(noise).max() + 1e-9) + 0.6 * body
    return x / np.abs(x).max()


def clap(seed=3):
    n = int(0.35 * SR)
    t = tt(n)
    nz = bandpass(np.random.default_rng(seed).standard_normal(n), 1000, 6000)
    env = np.zeros(n)
    for k, off in enumerate((0, 0.011, 0.022)):
        i = int(off * SR)
        env[i:] += np.exp(-(t[: n - i]) * (90 if k < 2 else 16))
    x = nz * env
    return x / np.abs(x).max()


def hat(open_=False, seed=4):
    n = int((0.3 if open_ else 0.06) * SR)
    t = tt(n)
    x = highpass(np.random.default_rng(seed).standard_normal(n), 7500, 3) * np.exp(-t * (14 if open_ else 70))
    return x / (np.abs(x).max() + 1e-9)


def tom(f0=90, decay=0.45):
    n = int(1.0 * SR)
    t = tt(n)
    f = f0 * (1 + 0.6 * np.exp(-t * 18))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)
    skin = lowpass(np.random.default_rng(5).standard_normal(n), 1200) * np.exp(-t * 40) * 0.5
    return np.tanh(1.4 * (body + skin))


def shaker(seed=6):
    n = int(0.09 * SR)
    t = tt(n)
    x = bandpass(np.random.default_rng(seed).standard_normal(n), 4000, 12000)
    env = np.minimum(1, t / 0.012) * np.exp(-t * 45)
    return x * env / (np.abs(x).max() + 1e-9)


def impact(dur=3.0):
    """Golpe cinematográfico: sub grave + cuerpo + cola."""
    n = int(dur * SR)
    t = tt(n)
    sub = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t * 6)) / SR) * np.exp(-t * 1.3)
    body = lowpass(np.random.default_rng(7).standard_normal(n), 500) * np.exp(-t * 2.2)
    x = sub + 0.6 * body / (np.abs(body).max() + 1e-9)
    return np.tanh(1.3 * x)


def riser(dur):
    """Subida de ruido y tono antes de que entre la parte fuerte."""
    n = int(dur * SR)
    t = tt(n)
    k = t / dur
    nz = np.random.default_rng(8).standard_normal(n)
    out = np.zeros(n)
    seg = int(0.05 * SR)  # ruido filtrado cada vez más agudo
    for i in range(0, n, seg):
        j = min(n, i + seg)
        c = 400 + 7000 * (i / n) ** 2
        out[i:j] = bandpass(nz[i:j + 200], c * 0.6, c * 1.6)[: j - i]
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * k ** 2) / SR) * 0.15
    x = (out / (np.abs(out).max() + 1e-9) * 0.6 + tone) * k ** 2.2
    return x


def sub808(f, dur, glide=True):
    n = int(dur * SR)
    t = tt(n)
    ff = f * (1 + (0.5 * np.exp(-t * 30) if glide else 0))
    x = np.sin(2 * np.pi * np.cumsum(ff) / SR) * adsr(n, 0.003, 0.6, 0.55, 0.08)
    return np.tanh(2.2 * x) * 0.8


def synth_bass(f, dur, cutoff=500):
    n = int(dur * SR)
    x = saw(f, n) + 0.5 * saw(f * 1.004, n, 0.3) + 0.6 * np.sin(2 * np.pi * f / 2 * tt(n))
    x = lowpass(x, cutoff, 3) * adsr(n, 0.004, 0.12, 0.6, 0.05)
    return x / 1.6


def additive(f, dur, partials, decay_base, decay_k, inharm=0.0, attack=0.003):
    n = int(dur * SR)
    t = tt(n)
    x = np.zeros(n)
    for k, amp in enumerate(partials, 1):
        fk = f * k * np.sqrt(1 + inharm * k * k)
        if fk > SR / 2.2:
            break
        x += amp * np.sin(2 * np.pi * fk * t) * np.exp(-t * (decay_base + decay_k * k))
    return x * np.minimum(1, t / attack) * np.clip((dur - t) / 0.02, 0, 1)


def pluck(f, dur):
    return additive(f, dur, [1, 0.5, 0.33, 0.25, 0.2, 0.16, 0.12, 0.1], 3.0, 1.6)


def piano(f, dur):
    a = additive(f, dur, [1, 0.6, 0.3, 0.22, 0.12, 0.08, 0.05], 1.2, 0.5, inharm=0.0004)
    b = additive(f * 1.002, dur, [0.5, 0.2, 0.1], 0.6, 0.3)
    return (a + b) / 1.6


def bell(f, dur):
    n = int(dur * SR)
    t = tt(n)
    s = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 5)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 9) + 0.15 * np.sin(2 * np.pi * f * 8.9 * t) * np.exp(-t * 14))
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 1.6) * np.clip((dur - t) / 0.03, 0, 1)


def string_stab(f, dur):
    n = int(dur * SR)
    x = saw(f, n) + saw(f * 1.006, n, 0.4) + saw(f * 0.995, n, 0.7)
    return lowpass(x, 1800, 2) * adsr(n, 0.008, 0.08, 0.45, 0.04) / 3


def supersaw_pad(freqs, dur, cutoff):
    n = int(dur * SR)
    x = np.zeros(n)
    rng = np.random.default_rng(int(freqs[0]))
    for f in freqs:
        for det in (-0.14, -0.06, 0.0, 0.06, 0.14):
            x += saw(f * 2 ** (det / 12), n, rng.uniform())
    x = lowpass(x, cutoff, 2)
    t = tt(n)
    x *= np.clip(np.minimum(t / 0.35, (dur - t) / 0.5), 0, 1)
    return x / (len(freqs) * 5) * 2.2


def warm_pad(freqs, dur):
    n = int(dur * SR)
    t = tt(n)
    x = np.zeros(n)
    rng = np.random.default_rng(int(freqs[-1]))
    for f in freqs:
        for det in (-0.1, 0.0, 0.1):
            ff = f * 2 ** (det / 12)
            for h, amp in ((1, 1.0), (2, 0.3), (3, 0.12)):
                x += amp * np.sin(2 * np.pi * ff * h * t + rng.uniform(0, 6.28))
    x *= np.clip(np.minimum(t / 0.6, (dur - t) / 0.6), 0, 1)
    return x / (len(freqs) * 3)


# ---------- mezcla ----------
class Bus:
    def __init__(self, n):
        self.x = np.zeros((2, n))

    def add(self, snd, at, gain=1.0, pan=0.0):
        i = int(at * SR)
        j = min(self.x.shape[1], i + len(snd))
        if i >= j or i < 0:
            return
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.x[0, i:j] += snd[: j - i] * gain * l * 1.414
        self.x[1, i:j] += snd[: j - i] * gain * r * 1.414


def reverb(x: np.ndarray, decay=1.8, mix=0.25, tone=5000) -> np.ndarray:
    n_ir = int(decay * 1.5 * SR)
    t = tt(n_ir)
    out = np.zeros_like(x)
    for ch, seed in ((0, 11), (1, 12)):
        ir = np.random.default_rng(seed).standard_normal(n_ir) * np.exp(-t * 6.9 / decay)
        ir = lowpass(ir, tone)
        ir[: int(0.012 * SR)] = 0  # predelay
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        size = 1 << int(np.ceil(np.log2(x.shape[1] + n_ir)))
        wet = np.fft.irfft(np.fft.rfft(x[ch], size) * np.fft.rfft(ir, size), size)[: x.shape[1]]
        out[ch] = wet
    return x * (1 - mix * 0.5) + out * mix


def chord_tones(root, qual):
    return [root + i for i in QUAL[qual]]


# ---------- composición ----------
@dataclass
class Song:
    name: str
    bpm: float
    chords: list  # [(raíz MIDI, calidad)] uno por compás
    scale: list
    drums: str  # trap | cinematic | pop | bounce | lofi | pulse | ambient
    bass: str  # 808 | synth | sub | none
    lead: str  # pluck | piano | bell | strings | none
    pad: str = "supersaw"  # supersaw | warm
    arp: str = "none"  # pluck | bell | none
    ostinato: bool = False  # cuerdas en semicorcheas (épico, tensión)
    swing: float = 0.0
    seed: int = 1
    reverb_decay: float = 1.8
    reverb_mix: float = 0.25
    vinyl: bool = False
    lead_octave: int = 12
    extra: dict = field(default_factory=dict)


def motif(song: Song, rng) -> list[tuple[float, float, int]]:
    """Motivo de 2 compases: (paso de 16, duración en 16, grado de la escala)."""
    rhythms = [
        [(0, 3), (3, 3), (6, 2), (8, 4), (14, 2), (16, 6), (24, 4), (28, 4)],
        [(0, 2), (2, 2), (4, 4), (10, 2), (12, 4), (16, 3), (19, 3), (22, 6), (28, 4)],
        [(0, 6), (6, 2), (8, 6), (14, 2), (16, 4), (20, 4), (24, 8)],
        [(2, 2), (4, 2), (6, 4), (12, 4), (18, 2), (20, 2), (22, 4), (28, 4)],
    ]
    r = rhythms[rng.integers(len(rhythms))]
    deg, out = int(rng.integers(0, 5)), []
    for k, (s, ln) in enumerate(r):
        if k:
            deg += int(rng.choice([-2, -1, -1, 1, 1, 2, 3, -3]))
            deg = int(np.clip(deg, -1, 9))
        out.append((s, ln, deg))
    return out


def degree_to_midi(song: Song, root_key: int, deg: int) -> int:
    sc = song.scale
    return root_key + 12 * (deg // len(sc)) + sc[deg % len(sc)]


def compose(song: Song) -> np.ndarray:
    rng = np.random.default_rng(song.seed)
    spb = 60 / song.bpm
    bar = 4 * spb
    s16 = spb / 4
    bars = int(np.ceil(64 / bar))
    bars += bars % 2
    total = bars * bar + 4.0
    n = int(total * SR)
    # secciones: arranque (2) · groove (resto hasta 8 s aprox.) · todo · respiro (2) · todo · final
    a_end = 2
    b_end = max(a_end + 2, int(round(8 / bar)) + a_end - 1)
    full1 = b_end + max(4, (bars - b_end - 4) // 2)
    brk_end = full1 + 2
    full2 = bars - 1

    def section(b):
        if b < a_end:
            return "intro"
        if b < b_end:
            return "groove"
        if b < full1:
            return "full"
        if b < brk_end:
            return "break"
        if b < full2:
            return "full2"
        return "outro"

    drums, bass, harm, lead, fx = Bus(n), Bus(n), Bus(n), Bus(n), Bus(n)
    key_root = song.chords[0][0]
    mot = motif(song, rng)
    mot_b = [(s, ln, d + (1 if k == len(mot) - 1 else 0)) for k, (s, ln, d) in enumerate(mot)]

    def at(b, step):
        sw = song.swing * s16 if step % 2 == 1 else 0.0
        return b * bar + step * s16 + sw

    kick_snd, sn, cl = kick(), snare(), clap()
    hc, ho, sh = hat() * 0.75, hat(True) * 0.7, shaker() * 0.8
    pump = np.ones(n)

    fx.add(impact(), 0.0, 0.9)
    for b in range(bars):
        sec = section(b)
        root, qual = song.chords[b % len(song.chords)]
        tones = chord_tones(root, qual)
        t0 = b * bar
        energy = {"intro": 0.6, "groove": 0.8, "full": 1.0, "break": 0.45, "full2": 1.0, "outro": 0.5}[sec]

        # acordes
        cutoff = {"intro": 900, "groove": 1500, "full": 3200, "break": 700, "full2": 3800, "outro": 900}[sec]
        freqs = [hz(x) for x in tones] + [hz(root - 12)]
        if song.pad == "supersaw":
            harm.add(supersaw_pad(freqs, bar + 0.5, cutoff), t0, 0.5 * (0.7 + 0.3 * energy))
        else:
            harm.add(warm_pad(freqs, bar + 0.6), t0, 0.7)
        if song.ostinato and sec in ("groove", "full", "full2"):
            seq = [tones[0], tones[1], tones[2], tones[1]]
            for s in range(16):
                harm.add(string_stab(hz(seq[s % 4] + 12), s16 * 0.9), at(b, s), 0.32 if s % 4 == 0 else 0.22,
                         pan=-0.3 if s % 2 else 0.3)

        # bajo
        if song.bass != "none" and sec != "break" and not (sec == "intro" and song.drums in ("pop", "bounce")):
            bf = hz(root - 24)
            if song.bass == "808":
                pat = [(0, 6), (10, 4)] if sec != "intro" else [(0, 16)]
                for s, ln in pat:
                    bass.add(sub808(bf, ln * s16, glide=s == 0), at(b, s), 0.85)
            elif song.bass == "synth":
                for s in range(0, 16, 2):
                    if sec == "intro" and s % 8:
                        continue
                    bass.add(synth_bass(bf * (2 if s in (6, 14) else 1), s16 * 1.8, 380 + 500 * energy), at(b, s), 0.6)
            else:
                bass.add(sub808(bf, bar * 0.95, glide=False), t0, 0.7)

        # arpegio
        if song.arp != "none" and sec in ("groove", "full", "full2", "break"):
            seq = (tones + [tones[0] + 12, tones[1] + 12])
            order = [0, 2, 1, 3, 2, 4, 3, 1]
            inst = bell if song.arp == "bell" else pluck
            for s in range(0, 16, 1 if sec in ("full", "full2") else 2):
                note = seq[order[s % 8] % len(seq)] + 12
                lead.add(inst(hz(note), s16 * 2.2), at(b, s), 0.16, pan=0.45 if s % 2 else -0.45)

        # melodía (motivo en compases pares, respuesta en impares)
        if song.lead != "none" and sec in ("full", "full2", "break"):
            phrase = mot if (b // 2) % 2 == 0 else mot_b
            half = (b % 2) * 16
            inst = {"pluck": pluck, "piano": piano, "bell": bell, "strings": string_stab}[song.lead]
            for s, ln, d in phrase:
                if half <= s < half + 16:
                    midi = degree_to_midi(song, key_root + song.lead_octave, d)
                    dur = ln * s16 * (1.0 if song.lead == "strings" else 1.6)
                    g = 0.42 if song.lead != "bell" else 0.3
                    lead.add(inst(hz(midi), dur), at(b, s - half), g * (0.8 if sec == "break" else 1.0), pan=0.1)
                    if song.lead in ("piano", "bell"):  # eco una octava abajo, suave
                        lead.add(inst(hz(midi - 12), dur), at(b, s - half) + s16 * 3, g * 0.25, pan=-0.3)

        # batería
        if sec != "break" and sec != "outro":
            light = sec == "intro"
            st = song.drums
            if st == "trap":
                kp = [0] if light else [0, 7, 10] if b % 2 else [0, 10]
                for s in kp:
                    drums.add(kick_snd, at(b, s), 0.9)
                if not light:
                    drums.add(sn, at(b, 8), 0.75)
                    drums.add(cl, at(b, 8), 0.35)
                    roll = b % 4 == 3
                    for s in range(0, 16, 2):
                        drums.add(hc, at(b, s), 0.32 if s % 4 == 0 else 0.22, pan=0.25)
                    if roll:
                        for k in range(8):
                            drums.add(hc, at(b, 12) + k * s16 / 2, 0.18 + 0.02 * k, pan=0.25)
                    drums.add(ho, at(b, 14), 0.15, pan=-0.3)
            elif st == "cinematic":
                pat = [(0, 70, 1.0), (6, 95, 0.55), (8, 70, 0.8), (11, 110, 0.5), (14, 95, 0.6)]
                for s, f0, g in (pat[:1] if light else pat):
                    drums.add(tom(f0), at(b, s), g * 0.9, pan=(f0 - 90) / 80)
                if not light:
                    drums.add(kick_snd, at(b, 0), 0.7)
                    drums.add(sn, at(b, 8), 0.5 if sec == "groove" else 0.8)
                    if sec != "groove":
                        for s in range(0, 16, 2):
                            drums.add(sh, at(b, s), 0.2, pan=0.35)
            elif st in ("pop", "bounce"):
                kp = [0, 4, 8, 12] if st == "pop" else [0, 7, 10]
                for s in kp if not light else [0, 8]:
                    drums.add(kick_snd, at(b, s), 0.8)
                    i = int(at(b, s) * SR)
                    seg = int(spb * 0.45 * SR)
                    pump[i:i + seg] = np.minimum(pump[i:i + seg], 0.45 + 0.55 * np.linspace(0, 1, len(pump[i:i + seg])) ** 0.7)
                if not light:
                    for s in (4, 12):
                        drums.add(cl, at(b, s), 0.6)
                    for s in range(16):
                        drums.add(sh if s % 2 else hc, at(b, s), 0.18 if s % 2 else 0.12, pan=0.3)
                    drums.add(ho, at(b, 14), 0.14, pan=-0.3)
            elif st == "lofi":
                for s in ([0] if light else [0, 7, 10]):
                    drums.add(lowpass(kick_snd, 900), at(b, s), 0.85)
                if not light:
                    for s in (4, 12):
                        drums.add(lowpass(sn, 3500), at(b, s), 0.45)
                    for s in range(0, 16, 2):
                        drums.add(lowpass(hc, 9000), at(b, s), 0.16, pan=0.3)
            elif st == "pulse":
                for s in (0, 3) if b % 2 == 0 or not light else (0,):
                    drums.add(tom(52, 0.3), at(b, s), 0.9 if s == 0 else 0.55)
                if not light:
                    for s in range(0, 16, 2):
                        drums.add(hc, at(b, s), 0.2 if s % 4 == 0 else 0.12, pan=0.25)
                    if sec != "groove":
                        drums.add(sn, at(b, 8), 0.35)
            elif st == "ambient":
                drums.add(tom(46, 0.6), at(b, 0), 0.7)
                if sec in ("full", "full2"):
                    drums.add(tom(46, 0.6), at(b, 8), 0.45)
                    for s in range(0, 16, 4):
                        drums.add(sh, at(b, s + 2), 0.12, pan=0.4)

        # subidas e impactos en los cambios de sección
        if section(b + 1) != sec and section(b + 1) in ("full", "full2", "groove") and b + 1 < bars:
            r = riser(bar)
            fx.add(r, t0, 0.35)
        if b > 0 and section(b - 1) != sec and sec in ("full", "full2"):
            fx.add(impact(2.4), t0, 0.7)
    fx.add(impact(3.5), full2 * bar, 0.8)

    if song.vinyl:  # crepitar de vinilo para el lo-fi
        crack = np.zeros(n)
        idx = np.random.default_rng(9).integers(0, n, int(total * 9))
        crack[idx] = np.random.default_rng(10).uniform(-0.6, 0.6, len(idx))
        hiss = highpass(np.random.default_rng(13).standard_normal(n), 3000) * 0.012
        fx.add(lowpass(crack, 6000) + hiss, 0, 0.5)

    harm.x *= pump
    bass.x *= np.sqrt(pump)
    mix = (0.9 * drums.x + 0.85 * bass.x + 0.55 * harm.x + 0.7 * lead.x + 0.6 * fx.x)
    send = 0.15 * drums.x + 0.6 * harm.x + 0.8 * lead.x + 0.3 * fx.x
    mix = mix + reverb(send, song.reverb_decay, 1.0) * song.reverb_mix
    mix = np.stack([lowpass(highpass(c, 28), 12500, 1) for c in mix])  # sin graves inaudibles ni agudos chillones
    tvec = tt(n)
    mix *= np.clip(np.minimum(tvec / 0.02, (total - tvec) / 3.0), 0, 1)
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-9) * 1.4) / np.tanh(1.4)
    return mix * 0.9


def save(name: str, x: np.ndarray) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "x.wav"
        inter = np.clip(x.T, -1, 1)
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((inter * 32767).astype("<i2").tobytes())
        mp3 = OUT / f"{name}.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", "loudnorm=I=-15:TP=-1.5:LRA=9",
                        "-ar", "44100", "-b:a", "192k", mp3], check=True)
    print("  ", mp3.name)


# Re menor: Dm Bb Gm A · La menor: Am F C E · Do menor: Cm Ab Eb Bb ...
SONGS = [
    # Historia y misterio (Bien Contadas, Archivo del Misterio)
    Song("misterio", 70, [(50, "m"), (46, "M"), (43, "m"), (45, "M")], HARM, "trap", "808", "bell", arp="pluck", seed=3),
    Song("intriga", 140, [(48, "m"), (44, "M"), (51, "M"), (46, "M")], MINOR, "trap", "808", "pluck", seed=5,
         lead_octave=24),
    Song("epica", 92, [(50, "m"), (46, "M"), (48, "M"), (45, "M")], MINOR, "cinematic", "sub", "strings",
         ostinato=True, seed=7, reverb_decay=2.6, reverb_mix=0.32),
    Song("suspense", 100, [(54, "m"), (50, "M"), (52, "M"), (49, "7")], HARM, "pulse", "synth", "bell", arp="bell",
         seed=9),
    Song("niebla", 76, [(52, "m9"), (48, "M7"), (45, "m7"), (47, "7")], HARM, "lofi", "sub", "piano", pad="warm",
         swing=0.18, seed=11, vinyl=True, reverb_decay=2.4),
    Song("conspiracion", 128, [(45, "m"), (41, "M"), (43, "M"), (40, "7")], HARM, "trap", "808", "strings",
         ostinato=True, seed=13),
    Song("batalla", 96, [(47, "m"), (43, "M"), (45, "M"), (42, "7")], MINOR, "cinematic", "synth", "strings",
         ostinato=True, seed=15, reverb_decay=2.8, reverb_mix=0.3),
    Song("expediente", 84, [(49, "m"), (45, "M"), (47, "sus"), (44, "7")], HARM, "pulse", "808", "piano", arp="bell",
         seed=17, reverb_decay=2.2),
    # Ligar y relaciones (Conexión con Chispa)
    Song("chispa", 118, [(60, "M"), (55, "M"), (57, "m"), (53, "M")], MAJOR, "bounce", "synth", "pluck", arp="pluck",
         seed=19),
    Song("cita", 90, [(55, "M7"), (52, "m7"), (57, "m7"), (50, "7")], MAJOR, "lofi", "sub", "piano", pad="warm",
         swing=0.2, seed=21, vinyl=True),
    Song("verano", 122, [(57, "M"), (54, "m"), (50, "M"), (52, "M")], MAJOR, "pop", "synth", "bell", arp="pluck",
         seed=23),
    # Psicología (La Cabeza por Dentro)
    Song("calma", 78, [(57, "m7"), (53, "M7"), (48, "M7"), (55, "7")], MINOR, "lofi", "sub", "piano", pad="warm",
         swing=0.16, seed=25, vinyl=True),
    Song("pensar", 86, [(50, "M7"), (55, "M7"), (47, "m7"), (52, "m7")], MAJOR, "lofi", "synth", "bell", arp="bell",
         pad="warm", swing=0.12, seed=27),
    Song("mente", 96, [(52, "m9"), (48, "M7"), (55, "M"), (50, "sus")], MINOR, "pulse", "sub", "pluck", arp="pluck",
         seed=29),
    # Ciencia (¿Y si…?)
    Song("cosmos", 100, [(52, "M"), (54, "m"), (49, "m"), (47, "sus")], MAJOR, "ambient", "sub", "bell", arp="bell",
         seed=31, reverb_decay=3.2, reverb_mix=0.38),
    Song("experimento", 116, [(58, "M"), (53, "M"), (55, "m"), (51, "M")], MAJOR, "pop", "synth", "pluck", arp="pluck",
         seed=33),
    Song("orbita", 124, [(53, "m"), (49, "M"), (56, "M"), (51, "M")], MINOR, "trap", "808", "bell", arp="pluck",
         seed=35, lead_octave=24),
]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for s in SONGS:
        if not want or s.name in want:
            save(s.name, compose(s))
