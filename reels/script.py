"""Genera con Claude una historia completa (1 o 2 partes) con guion, dirección visual y prompts."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import date
from typing import List, Literal

import anthropic
from pydantic import BaseModel, Field

from .config import ROOT

Camera = Literal["push_in", "pull_back", "pan_left", "pan_right", "tilt_up", "tilt_down"]


class Block(BaseModel):
    label: str = Field(description="Nombre del tramo: GANCHO, CONTEXTO, TENSIÓN, GIRO, CLIFFHANGER...")
    narration: str = Field(description="Voz en off de este plano (10-18 palabras).")
    camera: Camera
    visual_direction: str = Field(description="Dirección visual y micro-animación ambiental, en español.")
    image_prompt: str = Field(description="Prompt en inglés para el generador de imagen, sin el estilo maestro.")


class Part(BaseModel):
    part_number: int
    hook_title: str = Field(description="Texto grande en pantalla al inicio, máx. 7 palabras.")
    blocks: List[Block]
    cliffhanger: str = Field(description="Cómo termina esta parte y qué deja abierto (o el cierre final).")
    caption: str = Field(description="Texto del post para TikTok/Instagram, sin hashtags. Incluye 'Parte X/Y' si hay 2 partes.")
    hashtags: List[str] = Field(description="Entre 4 y 7 hashtags sin '#'.")
    youtube_title: str = Field(description="Título para YouTube Shorts, máx. 90 caracteres, con 'Parte X' si aplica.")
    youtube_description: str


class Series(BaseModel):
    series_title: str
    format: Literal["punto_inflexion", "crimen_historico"]
    year: str
    place: str
    topic: str = Field(description="Resumen del tema en una línea (para no repetirlo en el futuro).")
    master_style: str = Field(description="Estilo Visual Maestro en inglés, se añade a todos los prompts de imagen.")
    historical_notes: str = Field(description="Fuentes o matices: qué está documentado y qué es incierto.")
    parts: List[Part] = Field(description="1 o 2 partes.")


def _system_prompt() -> str:
    return (ROOT / "prompts" / "guionista.md").read_text(encoding="utf-8")


def next_format(history: list[dict], forced: str | None) -> str:
    if forced:
        return forced
    last = history[-1]["format"] if history else "crimen_historico"
    return "punto_inflexion" if last == "crimen_historico" else "crimen_historico"


def generate_series(cfg: dict, fmt: str, history: list[dict], topic: str | None = None) -> Series:
    fmt_name = {"punto_inflexion": "Punto de inflexión («El día que España estuvo a punto de...»)",
                "crimen_historico": "Crimen, conspiración o suceso oscuro real"}[fmt]
    done = [h["topic"] for h in history[-80:]]
    user = (
        f"Fecha: {date.today().isoformat()}\n"
        f"Formato: {fmt_name}\n"
        f"Tema a desarrollar: {topic or 'propón tú uno potente, poco trillado y bien documentado'}\n"
        f"Partes: máximo {cfg['series'].get('max_parts', 2)}.\n\n"
        "Historias ya publicadas (no repitas ninguna):\n"
        + ("\n".join(f"- {t}" for t in done) if done else "- (ninguna todavía)")
    )
    if _use_claude_code(cfg):
        series = _claude_code(cfg, _system_prompt(), user)
    else:
        series = _api(cfg, _system_prompt(), user)
    series.parts = series.parts[: cfg["series"].get("max_parts", 2)]
    for i, p in enumerate(series.parts, 1):
        p.part_number = i
    return series


def _use_claude_code(cfg: dict) -> bool:
    backend = cfg["claude"].get("backend", "auto")
    if backend == "auto":
        return bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) or not os.environ.get("ANTHROPIC_API_KEY")
    return backend == "claude-code"


def _claude_code(cfg: dict, system: str, user: str) -> Series:
    """Claude Code en modo no interactivo, con la suscripción (token de `claude setup-token`)."""
    if not shutil.which("claude"):
        raise SystemExit("No se encuentra Claude Code (`npm install -g @anthropic-ai/claude-code`).")
    cmd = [
        "claude", "-p", user,
        "--model", cfg["claude"]["model"],
        "--effort", cfg["claude"].get("effort", "high"),
        "--system-prompt", system,
        "--json-schema", json.dumps(Series.model_json_schema()),
        "--output-format", "json",
        "--tools", "",
        "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
        "--no-session-persistence",
    ]
    last_error = ""
    for _ in range(2):
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            last_error = (proc.stderr or proc.stdout)[-2000:]
            continue
        if data.get("is_error") or not data.get("structured_output"):
            last_error = str(data.get("result") or data)[:2000]
            continue
        return Series.model_validate(data["structured_output"])
    raise RuntimeError(f"Claude Code no devolvió un guion válido: {last_error}")


def _api(cfg: dict, system: str, user: str) -> Series:
    client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=cfg["claude"]["model"],
        max_tokens=32000,
        thinking={"type": "adaptive"},
        output_config={"effort": cfg["claude"].get("effort", "high")},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=Series,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude rechazó generar el guion: {response.stop_details}")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise RuntimeError(f"Guion incompleto (stop_reason={response.stop_reason}).")
    return response.parsed_output
