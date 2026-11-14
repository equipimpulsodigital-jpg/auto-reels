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


def _edge(text: str, mp3: Path, voice: str, rate: str) -> list[Word]:
    import edge_tts

    async def go() -> list[Word]:
        words: list[Word] = []
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        with open(mp3, "wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 1e7
                    words.append(Word(chunk["text"], start, start + chunk["duration"] / 1e7))
        return words

    for attempt in range(3):
        try:
            return asyncio.run(go())
        except Exception:
            if attempt == 2:
                raise
    return []


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


def synthesize_scenes(narrations: list[str], cfg: dict, workdir: Path) -> tuple[Path, list[float], list[Word]]:
    """Genera la voz escena a escena. Devuelve (voz.wav, duración de cada escena, palabras con tiempos)."""
    vcfg = cfg["voice"]
    durations: list[float] = []
    all_words: list[Word] = []
    wavs: list[Path] = []
    offset = 0.0
    gap = 0.12  # pequeña pausa entre escenas
    for i, text in enumerate(narrations):
        mp3 = workdir / f"voice_{i}.mp3"
        if vcfg["provider"] == "elevenlabs":
            words = _elevenlabs(text, mp3, vcfg["elevenlabs_voice_id"], vcfg["elevenlabs_model"])
        else:
            words = _edge(text, mp3, vcfg["edge_voice"], vcfg.get("edge_rate", "+0%"))
        words = restore_punctuation(words, text)
        wav = workdir / f"voice_{i}.wav"
        run_ffmpeg(["-i", mp3, "-af", f"apad=pad_dur={gap}", "-ar", "44100", "-ac", "1", wav])
        dur = probe_duration(wav)
        all_words += [Word(w.text, w.start + offset, w.end + offset) for w in words]
        durations.append(dur)
        wavs.append(wav)
        offset += dur

    listfile = workdir / "voice_list.txt"
    listfile.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
    voice = workdir / "voice.wav"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", voice])
    return voice, durations, all_words
