"""Voz en off con marcas de tiempo por palabra (para los subtítulos)."""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import env
from .media import probe_duration, run_ffmpeg


@dataclass
class Word:
    text: str
    start: float
    end: float
    speaker: str = ""  # nombre del personaje que habla ("" = narrador)
    scene: int = -1    # plano al que pertenece
    emph: bool = False  # palabra clave del plano: se resalta en grande con golpe de zoom y sonido


def _edge(text: str, mp3: Path, voice: str, rate: str, pitch: str = "+0Hz") -> list[Word]:
    import edge_tts

    async def go() -> list[Word]:
        words: list[Word] = []
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
        with open(mp3, "wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 1e7
                    words.append(Word(chunk["text"], start, start + chunk["duration"] / 1e7))
        return words

    # El servicio gratuito de voces falla a veces de forma pasajera («No audio was received»): reintenta con esperas.
    # Si aun así no responde (o lo cortan), se usa una voz de reserva que funciona sin internet (Piper).
    import time
    for attempt in range(5):
        try:
            return asyncio.run(go())
        except Exception as e:
            if attempt == 4:
                print(f"  voz: el servicio principal no responde ({str(e)[:80]}); uso la voz de reserva", flush=True)
                return _piper(text, mp3, voice, rate)
            wait = (3, 8, 20, 45)[attempt]
            print(f"  voz: fallo pasajero ({str(e)[:80]}); reintento en {wait} s", flush=True)
            time.sleep(wait)
    return []


_PIPER = "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/{n}/medium/es_ES-{n}-medium.onnx"
_FEMALE = ("elvira", "ximena", "abril", "dalia", "elena", "irene", "triana", "vera", "estrella", "laia", "female")


def _piper(text: str, out: Path, voice: str, rate: str = "+0%") -> list[Word]:
    """Voz de reserva sin internet (Piper). Los tiempos de cada palabra se reparten según su longitud."""
    import shutil
    import subprocess
    import wave
    female = any(k in voice.lower() for k in _FEMALE)
    name, speaker = ("sharvard", "1") if female else ("davefx", None)
    models = Path.home() / ".cache" / "piper"
    models.mkdir(parents=True, exist_ok=True)
    model = models / f"es_ES-{name}-medium.onnx"
    for suffix in ("", ".json"):
        f = Path(str(model) + suffix)
        if not f.exists():
            r = requests.get(_PIPER.format(n=name) + suffix, timeout=300)
            r.raise_for_status()
            f.write_bytes(r.content)
    exe = shutil.which("piper") or "piper"
    try:
        speed = 1 / (1 + int(rate.strip("%+")) / 100) if rate.strip("%+-").isdigit() else 0.9
    except ValueError:
        speed = 0.9
    cmd = [exe, "--model", str(model), "--output_file", str(out), "--length_scale", f"{speed:.2f}"]
    if speaker:
        cmd += ["--speaker", speaker]
    subprocess.run(cmd, input=text, text=True, check=True, capture_output=True, timeout=300)
    with wave.open(str(out), "rb") as w:
        dur = w.getnframes() / w.getframerate()
    tokens = text.split()
    weights = [len(t) + 2 for t in tokens]
    total, t, words = sum(weights) or 1, 0.08, []
    span = max(0.1, dur - 0.2)
    for tok, wgt in zip(tokens, weights):
        d = span * wgt / total
        words.append(Word(tok, t, t + d * 0.9))
        t += d
    return words


def _elevenlabs(text: str, mp3: Path, voice_id: str, model: str) -> list[Word]:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
        headers={"xi-api-key": env("ELEVENLABS_API_KEY")},
        json={"text": text, "model_id": model},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    mp3.write_bytes(base64.b64decode(data["audio_base64"]))
    al = data["alignment"]
    words: list[Word] = []
    cur, start, end = "", None, 0.0
    for ch, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                words.append(Word(cur, start, end))
            cur, start = "", None
            continue
        if start is None:
            start = s
        cur += ch
        end = e
    if cur:
        words.append(Word(cur, start, end))
    return words


def _norm(t: str) -> str:
    return "".join(c for c in t.lower() if c.isalnum())


def restore_punctuation(words: list[Word], text: str) -> list[Word]:
    """Edge TTS devuelve las palabras sin puntuación; la recuperamos del texto original
    para que los subtítulos corten los bloques en comas y puntos."""
    tokens = text.split()
    p = 0
    for w in words:
        for k in range(p, min(p + 3, len(tokens))):
            if _norm(tokens[k]) == _norm(w.text):
                w.text = tokens[k]
                p = k + 1
                break
    return words


def synthesize_scenes(narrations: list[str], cfg: dict, workdir: Path,
                      speakers: list[tuple[str, str]] | None = None) -> tuple[Path, list[float], list[Word]]:
    """Genera la voz escena a escena. `speakers` da, por escena, (clave de voz del reparto, nombre en
    pantalla); ("", "") = narrador. Devuelve (voz.wav, duración de cada escena, palabras con tiempos)."""
    vcfg = cfg["voice"]
    cast = vcfg.get("cast", {})
    speakers = speakers or [("", "")] * len(narrations)
    durations: list[float] = []
    all_words: list[Word] = []
    wavs: list[Path] = []
    offset = 0.0
    gap = 0.18  # pausa entre escenas (natural, sin huecos muertos)
    for i, (text, (voice_key, name)) in enumerate(zip(narrations, speakers)):
        mp3 = workdir / f"voice_{i}.mp3"
        role = cast.get(voice_key) if voice_key else None
        if role:  # los personajes siempre con Edge: tiene acentos y voces variadas gratis
            words = _edge(text, mp3, role["voice"], role.get("rate", "+0%"), role.get("pitch", "+0Hz"))
        elif vcfg["provider"] == "elevenlabs":
            words = _elevenlabs(text, mp3, vcfg["elevenlabs_voice_id"], vcfg["elevenlabs_model"])
        else:
            words = _edge(text, mp3, vcfg["edge_voice"], vcfg.get("edge_rate", "+0%"), vcfg.get("edge_pitch", "+0Hz"))
        words = restore_punctuation(words, text)
        wav = workdir / f"voice_{i}.wav"
        # Los TTS dejan ~0,1 s de silencio al inicio y ~0,8 s al final de cada frase: lo recortamos
        # para que el ritmo no se arrastre (en 15 escenas son más de 10 s de silencio).
        af = f"apad=pad_dur={gap}"
        shift = 0.0
        if words:
            shift = max(0.0, words[0].start - 0.04)
            end = words[-1].end + 0.1
            af = f"atrim=start={shift:.3f}:end={end:.3f},asetpts=PTS-STARTPTS,{af}"
        run_ffmpeg(["-i", mp3, "-af", af, "-ar", "44100", "-ac", "1", wav])
        dur = probe_duration(wav)
        all_words += [Word(w.text, w.start - shift + offset, w.end - shift + offset, name if role else "", i)
                      for w in words]
        durations.append(dur)
        wavs.append(wav)
        offset += dur

    listfile = workdir / "voice_list.txt"
    listfile.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
    voice = workdir / "voice.wav"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", voice])
    return voice, durations, all_words
