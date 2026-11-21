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
    build: Literal[K.BUILDS] = "normal"
    height: Literal[K.HEIGHTS] = "normal"


class Character(BaseModel):
    id: str = Field(description="Identificador corto en minúsculas, p. ej. 'paco' u 'oficial'.")
    name: str = Field(description="Nombre que se muestra en pantalla cuando habla (máx. 18 caracteres).")
    voice: VoiceKey
    look: LookSpec = Field(description="Caricatura del personaje: rasgos muy marcados y vestuario fiel a la época.")


class Block(BaseModel):
    label: str = Field(description="Nombre del tramo: GANCHO, CONTEXTO, TENSIÓN, GIRO, CLIFFHANGER...")
    speaker: str = Field(description="'narrador' o el id de un personaje que dice esta frase en pantalla.")
    narration: str = Field(description="Frase que se oye en este plano (4-8 palabras): voz en off del narrador o diálogo del personaje.")
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
    action: Literal[tuple(K.ACTIONS)] = "ninguna"
    held_prop: Optional[Literal[tuple(PROPS)]] = None
    camera: Literal[tuple(K.CAMERAS)] = "push_in"
    sfx: List[Literal[tuple(K.SFX)]] = Field(default_factory=list, description="Efectos extra al empezar el plano.")
    on_screen: Optional[str] = Field(default=None, description=(
        "Rótulo corto en pantalla (máx. 24 caracteres) con el dato duro de este plano: fecha, lugar, cifra o "
        "nombre (p. ej. «AGOSTO DE 1897», «12 MUERTOS», «EL 80 % LO HACE»). En 2-4 bloques por parte; null en el resto."))
    emphasis: Optional[str] = Field(default=None, description=(
        "UNA palabra de `narration` (copiada tal cual) que es el golpe de la frase: sale enorme en pantalla con un "
        "golpe de zoom y de sonido. Úsala en 4-6 bloques por parte, en las palabras más impactantes; null en el resto."))
    visual_direction: str = Field(description="Qué se ve y qué pasa en el plano, en español (para la ficha del guion).")


class Part(BaseModel):
    part_number: int
    hook_candidates: List[str] = Field(default_factory=list, description=(
        "5 ganchos alternativos para la primera frase, cada uno con una técnica distinta (ver EL GANCHO). "
        "Después elige el más fuerte y úsalo, tal cual o mejorado, como narración del primer bloque."))
    hook_title: str = Field(description=(
        "Texto grande en pantalla durante los primeros 3 s: 2-6 palabras que COMPLEMENTAN la primera frase "
        "(una pregunta, un dato o una amenaza), nunca la repiten ni dicen el título de la historia."))
    blocks: List[Block]
    cliffhanger: str = Field(description="Cómo termina esta parte y qué deja abierto (o el cierre final).")
    caption: str = Field(description=(
        "Texto del post para Instagram y TikTok, sin hashtags (ver TEXTOS DE PUBLICACIÓN): 1.ª línea = gancho "
        "distinto del vídeo; 2-3 líneas cortas; 'Parte X/Y' si hay 2 partes; termina con una pregunta. 150-350 caracteres."))
    comment_question: str = Field(default="", description=(
        "Pregunta de DOS opciones para que la gente comente, máx. 45 caracteres, que se pueda responder con una palabra o "
        "un número (ver COMENTARIOS). Ej.: «¿Real o fraude? Comenta 1 o 2», «¿Te ha pasado? Sí o no», «¿Culpable o inocente?». Sin emojis (no se ven en pantalla)."))
    first_comment: str = Field(default="", description=(
        "Primer comentario que publica la cuenta (Instagram y YouTube), máx. 220 caracteres: un dato extra sorprendente que "
        "NO sale en el vídeo y, al final, la misma pregunta de dos opciones."))
    hashtags: List[str] = Field(description="4-6 hashtags sin '#': 2 generales del nicho y 2-3 del tema concreto, en español.")
    youtube_title: str = Field(description=(
        "Título de YouTube: 40-65 caracteres, intriga + palabra clave que la gente buscaría, sin mayúsculas enteras "
        "ni engaños; termina en ' | Parte X' si hay 2 partes."))
    youtube_description: str = Field(description=(
        "Descripción de YouTube (ver TEXTOS DE PUBLICACIÓN): 2 primeras líneas con gancho y palabras clave, resumen "
        "breve sin destripar el final y, si es una historia real, 'Fuentes:' con 1-3 fuentes reales. Sin hashtags."))


class Book(BaseModel):
    title: str = Field(description="Título exacto del libro.")
    author: str = Field(description="Autor o autora.")
    pitch: Optional[str] = Field(default=None, description=(
        "Una frase (máx. 18 palabras) que dé ganas de leerlo, sin spoilers, p. ej. «La investigación que reabrió el caso "
        "con documentos inéditos.»"))


class TopicIdea(BaseModel):
    topic: str = Field(description="El tema en una frase, con el detalle que lo hace irresistible.")
    hook: str = Field(description="Cómo empezaría el vídeo (la primera frase).")
    why: str = Field(description="Por qué le importaría a alguien que no sabe nada del tema (emoción, cercanía, sorpresa).")
    score: int = Field(description="Del 1 al 10: ganas de verlo entero y comentarlo, siendo exigente (un 8 es excepcional).")


class Series(BaseModel):
    topic_candidates: List[TopicIdea] = Field(default_factory=list, description=(
        "PRIMERO: 5 temas posibles muy distintos entre sí (o 5 ángulos del tema pedido), puntuados con los criterios "
        "de ELEGIR EL TEMA. Desarrolla el de mayor puntuación."))
    series_title: str = Field(description="Título concreto de esta historia o tema (nunca el nombre del canal).")
    format: str = Field(description="Clave del formato indicado en la petición.")
    year: str
    place: str
    topic: str = Field(description="Resumen del tema en una línea (para no repetirlo en el futuro).")
    angle: str = Field(default="", description=(
        "PLAN (escríbelo antes que nada): el ángulo que hace que esta historia enganche, en una frase: qué tiene de "
        "sorprendente, injusto, absurdo o útil y qué está en juego."))
    open_question: str = Field(default="", description=(
        "PLAN: la pregunta que el espectador se hace en el segundo 3 y que no se responde hasta el final."))
    payoff: str = Field(default="", description=(
        "PLAN: el dato, giro o consejo más potente (y cierto) de la historia. Se guarda para el final de la última parte."))
    beats: List[str] = Field(default_factory=list, description=(
        "PLAN: escaleta de 6-9 pasos (una frase cada uno) de principio a fin, con los re-ganchos marcados."))
    era: Literal[K.ERAS] = Field(description="Época de la historia (cambia detalles de los escenarios).")
    characters: List[Character] = Field(description="Personajes (2-5): los que hablan y los que salen en plano.")
    historical_notes: str = Field(description="Fuentes o matices: qué está documentado y qué es incierto.")
    parts: List[Part] = Field(description="1 o 2 partes.")
    book: Optional[Book] = Field(default=None, description=(
        "Un libro REAL, ya publicado y fácil de encontrar en español en Amazon.es, sobre esta historia o tema, "
        "para recomendarlo al público. Solo si estás seguro de que existe (título y autor exactos); si no, null."))


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
    cycle = [f for f in cfg["channel"].get("format_cycle") or [] if f in formats]
    if cycle:  # rotación con pesos: los formatos que mejor funcionan salen más a menudo
        return cycle[len(history) % len(cycle)]
    last = history[-1]["format"] if history else None
    return formats[(formats.index(last) + 1) % len(formats)] if last in formats else formats[0]


def _max_parts(cfg: dict) -> int:
    return int(cfg["channel"].get("max_parts") or cfg["series"].get("max_parts", 2))


def generate_series(cfg: dict, fmt: str, history: list[dict], topic: str | None = None,
                    max_parts: int | None = None) -> Series:
    if max_parts is None and _max_parts(cfg) > 1 and any(h.get("parts", 1) > 1 for h in history[-2:]):
        max_parts = 1  # las historias de 2 partes, solo de vez en cuando (nunca dos seguidas ni casi)
    fmt_name = cfg["channel"]["formats"][fmt]
    done = [h["topic"] for h in history[-80:]]
    user = (
        f"Fecha: {date.today().isoformat()}\n"
        f"Formato: {fmt_name} (en el campo `format` pon exactamente: {fmt})\n"
        f"Tema a desarrollar: {topic or 'propón tú uno potente, poco trillado y bien documentado'}\n"
        f"Partes: máximo {max_parts or _max_parts(cfg)}.\n\n"
        "Historias ya publicadas (no repitas ninguna):\n"
        + ("\n".join(f"- {t}" for t in done) if done else "- (ninguna todavía)")
        + _performance(history)
        + ("" if topic else _interest(cfg))
    )
    write = _claude_code if _use_claude_code(cfg) else _api
    series = write(cfg, _system_prompt(cfg), user)
    longest = max(sum(len(b.narration.split()) for b in p.blocks) for p in series.parts)
    if longest > 120:  # se ha pasado de largo: un vídeo de 55 s se ve entero mucho menos que uno de 40 s
        print(f"  guion demasiado largo ({longest} palabras en una parte): se pide otra versión más corta")
        try:
            series = write(cfg, _system_prompt(cfg), user + (
                f"\n\nIMPORTANTE: cada parte debe tener entre 85 y 105 palabras en total (un intento anterior tenía "
                f"{longest}). Frases más cortas y menos bloques de contexto; el gancho y el final, intactos."))
        except Exception as e:  # si falla, mejor un vídeo algo largo que ninguno
            print(f"  no se pudo acortar ({e}); se usa la primera versión")
    series.format = fmt
    series.parts = series.parts[: max_parts or _max_parts(cfg)]
    for i, p in enumerate(series.parts, 1):
        p.part_number = i
    return series


def _interest(cfg: dict) -> str:
    from .interest import current_interest
    return current_interest(cfg)


def _performance(history: list[dict]) -> str:
    """Qué historias del canal han gustado más y menos (visualizaciones reales), para aprender de ellas."""
    rated = [h for h in history if (h.get("stats") or {}).get("views") is not None and h.get("published_parts")]
    if len(rated) < 4:
        return ""
    rated.sort(key=lambda h: h["stats"]["views"], reverse=True)
    k = min(5, len(rated) // 2)

    def line(h):
        st = h["stats"]
        return (f"- {st['views']} visualizaciones, {st.get('likes', 0)} me gusta, {st.get('comments', 0)} comentarios · "
                f"[{h.get('format')}] «{h['series_title']}» — {h.get('topic', '')}")
    return ("\n\nRESULTADOS REALES DEL CANAL (aprende de ellos al elegir el tema y el gancho):\n"
            "Las que MÁS han gustado:\n" + "\n".join(line(h) for h in rated[:k]) +
            "\nLas que MENOS:\n" + "\n".join(line(h) for h in rated[-k:]) +
            "\nFíjate en qué tienen en común las que funcionan (tipo de tema, emoción, cercanía, gancho) y busca "
            "un tema NUEVO con esas cualidades. Evita lo que tienen en común las que no funcionan.")


def _schema() -> dict:
    """Esquema para Claude: en las historias nuevas los 5 ganchos alternativos son obligatorios."""
    schema = Series.model_json_schema()
    part = schema["$defs"]["Part"]
    part["required"] = sorted(set(part.get("required", [])) | {"hook_candidates"})
    part["properties"]["hook_candidates"].update(minItems=5, maxItems=5)
    part["required"] = sorted(set(part["required"]) | {"comment_question", "first_comment"})
    # la planificación va antes que el guion y es obligatoria: obliga a pensar la historia antes de escribirla
    schema["required"] = sorted(set(schema.get("required", [])) | {"angle", "open_question", "payoff", "beats",
                                                                    "topic_candidates"})
    schema["properties"]["topic_candidates"].update(minItems=5, maxItems=5)
    schema["properties"]["beats"].update(minItems=6, maxItems=9)
    return schema


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
        "--json-schema", json.dumps(_schema()),
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
