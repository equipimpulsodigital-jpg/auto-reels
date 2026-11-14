"""Genera el guion del reel con Claude (salida estructurada y validada con Pydantic)."""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
from datetime import date
from typing import List

import anthropic
from pydantic import BaseModel, Field


class Scene(BaseModel):
    narration: str = Field(description="Frase(s) que dice la voz en off en esta escena.")
    footage_query: str = Field(
        description="Búsqueda en inglés (1-3 palabras) para un clip vertical de stock en Pexels."
    )


class Script(BaseModel):
    topic: str = Field(description="Tema del vídeo en pocas palabras (para no repetirlo).")
    hook_title: str = Field(description="Texto grande en pantalla los primeros segundos, máx. 6 palabras.")
    scenes: List[Scene]
    caption: str = Field(description="Texto del post para TikTok e Instagram, sin hashtags.")
    hashtags: List[str] = Field(description="Entre 3 y 6 hashtags, sin el símbolo #.")
    youtube_title: str = Field(description="Título para YouTube Shorts, máx. 90 caracteres.")
    youtube_description: str


SYSTEM = """Eres guionista de vídeos verticales cortos (TikTok, Reels, Shorts) para {brand}.

Sobre la marca:
{description}

Escribe en {language}. Reglas:
- La primera frase es el gancho: tiene que hacer que alguien deje de hacer scroll (pregunta, \
dato sorprendente o situación muy reconocible). Nada de "Hola, hoy os traigo...".
- Locución total de unos {words} palabras ({seconds} s), dividida en 4-7 escenas cortas.
- Frases cortas, para decir en voz alta. Escribe los números con letras si se leen mejor así.
- Aporta valor real y concreto: un vídeo que se podría haber escrito sobre cualquier deporte no vale.
- No te inventes datos, estadísticas, nombres de clubes ni funciones de la app que no aparezcan arriba.
- La última escena cierra con una llamada a la acción breve y natural relacionada con: "{cta}". \
En formatos que no van de la app, la mención a {brand} es breve y al final.
- footage_query: busca imágenes que existan en bancos de vídeo (p. ej. "padel", "padel court", \
"tennis racket", "friends sport", "smartphone app", "sports celebration"). Varía entre escenas.
"""


def pick_format(cfg: dict, history: list[dict], forced: str | None = None) -> dict:
    formats = cfg["formats"]
    if forced:
        for f in formats:
            if f["id"] == forced:
                return f
        raise SystemExit(f"Formato desconocido: {forced}. Opciones: {[f['id'] for f in formats]}")
    last = history[-1]["format"] if history else None
    candidates = [f for f in formats if f["id"] != last] or formats
    return random.choices(candidates, weights=[f.get("weight", 1) for f in candidates])[0]


def generate_script(cfg: dict, fmt: dict, history: list[dict]) -> Script:
    brand = cfg["brand"]
    seconds = cfg["video"]["target_seconds"]
    system = SYSTEM.format(
        brand=brand["name"],
        description=brand["description"].strip(),
        language=cfg["language"],
        words=int(seconds * 2.7),
        seconds=seconds,
        cta=brand["cta"],
    )
    recent = [h["topic"] for h in history[-40:]]
    user = (
        f"Fecha: {date.today().isoformat()}\n"
        f"Formato de hoy ({fmt['id']}): {fmt['brief'].strip()}\n\n"
        "Temas ya publicados (no repitas ninguno ni un enfoque casi igual):\n"
        + ("\n".join(f"- {t}" for t in recent) if recent else "- (ninguno todavía)")
    )

    if _use_claude_code(cfg):
        return _generate_with_claude_code(cfg, system, user)

    client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=cfg["claude"]["model"],
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": cfg["claude"].get("effort", "medium")},
        # Si el modelo rechaza la petición, la API la reintenta con el modelo de respaldo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=Script,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude rechazó generar el guion: {response.stop_details}")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise RuntimeError(f"Guion incompleto (stop_reason={response.stop_reason}).")
    return response.parsed_output


def _use_claude_code(cfg: dict) -> bool:
    backend = cfg["claude"].get("backend", "auto")
    if backend == "auto":
        return bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) or not os.environ.get("ANTHROPIC_API_KEY")
    return backend == "claude-code"


def _generate_with_claude_code(cfg: dict, system: str, user: str) -> Script:
    """Usa Claude Code en modo no interactivo, con la suscripción (token de `claude setup-token`)."""
    if not shutil.which("claude"):
        raise SystemExit("No se encuentra Claude Code (`npm install -g @anthropic-ai/claude-code`).")
    cmd = [
        "claude", "-p", user,
        "--model", cfg["claude"]["model"],
        "--effort", cfg["claude"].get("effort", "medium"),
        "--system-prompt", system,
        "--json-schema", json.dumps(Script.model_json_schema()),
        "--output-format", "json",
        "--tools", "",                 # sin herramientas: solo escribe el guion
        "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
        "--no-session-persistence",
    ]
    last_error = ""
    for _ in range(2):
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            last_error = (proc.stderr or proc.stdout)[-2000:]
            continue
        if data.get("is_error") or not data.get("structured_output"):
            last_error = str(data.get("result") or data)[:2000]
            continue
        return Script.model_validate(data["structured_output"])
    raise RuntimeError(f"Claude Code no devolvió un guion válido: {last_error}")


def sample_script() -> Script:
    """Guion fijo para probar el montaje sin gastar API (--sample)."""
    return Script.model_validate(json.loads("""{
      "topic": "salir de la pared con el globo",
      "hook_title": "Deja de regalar el punto",
      "scenes": [
        {"narration": "¿Te pasa que la bola sale de la pared y no sabes qué hacer con ella?", "footage_query": "padel"},
        {"narration": "La mayoría la pega fuerte y plana. Y el rival, en la red, solo tiene que bloquear.", "footage_query": "padel court"},
        {"narration": "Prueba esto: deja que baje, flexiona las piernas y tira un globo alto y profundo.", "footage_query": "tennis racket"},
        {"narration": "Así recuperas la red y el que sufre ahora es el otro.", "footage_query": "sports celebration"},
        {"narration": "¿Te falta gente para practicarlo? En AVORA encuentras partido de tu nivel cerca de ti.", "footage_query": "smartphone app"}
      ],
      "caption": "El golpe que más puntos regala en pádel amateur (y cómo arreglarlo).",
      "hashtags": ["padel", "padelolot", "consejospadel", "garrotxa"],
      "youtube_title": "Cómo salir de la pared en pádel sin regalar el punto",
      "youtube_description": "Un consejo rápido de pádel para tu próximo partido."
    }"""))
