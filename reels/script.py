"""Genera con Claude una historia completa (1 o 2 partes): guion, reparto y planificación de la animación."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import date
from typing import List, Literal, Optional

import anthropic
from pydantic import BaseModel, Field

from .config import ROOT

from .toon import catalog as K
from .toon.locations import LOCATIONS
from .toon.props import EVENTS, PROPS

VoiceKey = Literal["hombre_mayor", "hombre_joven", "mujer", "mujer_joven", "americano", "americana",
                   "frances", "italiano", "ingles", "latino"]
Color = Literal[tuple(K.COLORS)]
HairColor = Literal[tuple(K.HAIR)]


class LookSpec(BaseModel):
    """Vestuario y rasgos del personaje (opciones cerradas del catálogo)."""
    female: bool = False
    age: Literal[K.AGES] = "adulto"
    skin: Literal[K.SKINS] = "media"
    hair_color: HairColor = "castaño"
    hair_style: Literal[K.HAIR_STYLES] = "corto"
    hat: Literal[K.HATS] = "ninguno"
    hat_color: Color = "negro"
    beard: Literal[K.BEARDS] = "ninguna"
    beard_color: Optional[HairColor] = None
    outfit: Literal[K.OUTFITS] = "camisa"
    outfit_color: Color = "azul_marino"
    accent_color: Color = "dorado"
    pants_color: Color = "gris"
    nose: Literal[K.NOSES] = "patata"
    jaw: Literal[K.JAWS] = "redonda"
    eyes: Literal[tuple(K.EYES)] = "marrones"
    glasses: bool = False


class Character(BaseModel):
    id: str = Field(description="Identificador corto en minúsculas, p. ej. 'paco' u 'oficial'.")
    name: str = Field(description="Nombre que se muestra en pantalla cuando habla (máx. 18 caracteres).")
    voice: VoiceKey
    look: LookSpec = Field(description="Caricatura del personaje: rasgos muy marcados y vestuario fiel a la época.")


class Block(BaseModel):
    label: str = Field(description="Nombre del tramo: GANCHO, CONTEXTO, TENSIÓN, GIRO, CLIFFHANGER...")
    speaker: str = Field(description="'narrador' o el id de un personaje que dice esta frase en pantalla.")
    narration: str = Field(description="Frase que se oye en este plano (6-12 palabras): voz en off del narrador o diálogo del personaje.")
    location: Literal[tuple(LOCATIONS)]
    framing: Literal[tuple(K.FRAMINGS)]
    cast: List[str] = Field(default_factory=list, description="Ids de los personajes que salen en el plano (el que habla primero).")
    gesture: Literal[tuple(K.GESTURES)] = "explain"
    emotion: Literal[tuple(K.EMOTIONS)] = "neutral"
    listener_emotion: Literal[tuple(K.EMOTIONS)] = "neutral"
    mood: Literal[tuple(K.MOODS)] = "dia"
    event: Optional[Literal[tuple(EVENTS)]] = None
    prop: Optional[Literal[tuple(PROPS)]] = None
    walk: bool = False
    camera: Literal[tuple(K.CAMERAS)] = "push_in"
    sfx: List[Literal[tuple(K.SFX)]] = Field(default_factory=list, description="Efectos extra al empezar el plano.")
    visual_direction: str = Field(description="Qué se ve y qué pasa en el plano, en español (para la ficha del guion).")


class Part(BaseModel):
    part_number: int
    hook_candidates: List[str] = Field(description=(
        "5 ganchos alternativos para la primera frase, cada uno con una técnica distinta (ver EL GANCHO). "
        "Después elige el más fuerte y úsalo, tal cual o mejorado, como narración del primer bloque."))
    hook_title: str = Field(description=(
        "Texto grande en pantalla durante los primeros 3 s: 2-6 palabras que COMPLEMENTAN la primera frase "
        "(una pregunta, un dato o una amenaza), nunca la repiten ni dicen el título de la historia."))
    blocks: List[Block]
    cliffhanger: str = Field(description="Cómo termina esta parte y qué deja abierto (o el cierre final).")
    caption: str = Field(description="Texto del post para TikTok/Instagram, sin hashtags. Incluye 'Parte X/Y' si hay 2 partes.")
    hashtags: List[str] = Field(description="Entre 4 y 7 hashtags sin '#'.")
    youtube_title: str = Field(description="Título para YouTube Shorts, máx. 90 caracteres, con 'Parte X' si aplica.")
    youtube_description: str


class Series(BaseModel):
    series_title: str
    format: str = Field(description="Clave del formato indicado en la petición.")
    year: str
    place: str
    topic: str = Field(description="Resumen del tema en una línea (para no repetirlo en el futuro).")
    era: Literal[K.ERAS] = Field(description="Época de la historia (cambia detalles de los escenarios).")
    characters: List[Character] = Field(description="Personajes (2-5): los que hablan y los que salen en plano.")
    historical_notes: str = Field(description="Fuentes o matices: qué está documentado y qué es incierto.")
    parts: List[Part] = Field(description="1 o 2 partes.")


def _system_prompt(cfg: dict) -> str:
    """Guionista del canal (temática y reglas del guion) + reglas comunes de la animación + catálogo."""
    voices = list(VoiceKey.__args__)
    channel = (ROOT / cfg["channel"]["prompt"]).read_text(encoding="utf-8")
    animation = (ROOT / "prompts" / "animacion.md").read_text(encoding="utf-8")
    return channel.rstrip() + "\n\n" + animation + "\n" + K.catalog_text(voices)


def next_format(cfg: dict, history: list[dict], forced: str | None) -> str:
    """Alterna los formatos del canal."""
    formats = list(cfg["channel"]["formats"])
    if forced:
        if forced not in formats:
            raise SystemExit(f"Formato desconocido para este canal: {forced}. Opciones: {', '.join(formats)}")
        return forced
    last = history[-1]["format"] if history else None
    return formats[(formats.index(last) + 1) % len(formats)] if last in formats else formats[0]


def generate_series(cfg: dict, fmt: str, history: list[dict], topic: str | None = None) -> Series:
    fmt_name = cfg["channel"]["formats"][fmt]
    done = [h["topic"] for h in history[-80:]]
    user = (
        f"Fecha: {date.today().isoformat()}\n"
        f"Formato: {fmt_name} (en el campo `format` pon exactamente: {fmt})\n"
        f"Tema a desarrollar: {topic or 'propón tú uno potente, poco trillado y bien documentado'}\n"
        f"Partes: máximo {cfg['series'].get('max_parts', 2)}.\n\n"
        "Historias ya publicadas (no repitas ninguna):\n"
        + ("\n".join(f"- {t}" for t in done) if done else "- (ninguna todavía)")
    )
    if _use_claude_code(cfg):
        series = _claude_code(cfg, _system_prompt(cfg), user)
    else:
        series = _api(cfg, _system_prompt(cfg), user)
    series.format = fmt
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
