"""Catálogo de la biblioteca de animación: opciones cerradas que puede usar el guionista y su
traducción a parámetros de dibujo. El texto del catálogo se genera desde el código, así Claude
nunca pide algo que no existe."""
from __future__ import annotations

from .character import Character, Look
from .locations import LOCATIONS
from .more_props import EXTRA_EVENT_DESC, EXTRA_PROP_DESC
from .props import EVENTS, PROPS

COLORS = {
    "negro": "#1d1d22", "gris": "#6b6f78", "blanco": "#efeae0", "crema": "#e9dcb8", "marron": "#6b4a2f",
    "granate": "#7e1c28", "rojo": "#b3262d", "azul_marino": "#23324f", "azul": "#2e5aa8", "verde_oscuro": "#2f4a36",
    "verde_oliva": "#5a6342", "caqui": "#b59a62", "mostaza": "#c9a227", "morado": "#5a3a6b", "dorado": "#d4af37",
    "plateado": "#c9ced6", "beige": "#cbb897",
}
HAIR = {"negro": "#1f1a17", "castaño": "#5a3b22", "rubio": "#c9a25a", "pelirrojo": "#a5482a", "canoso": "#8a8580",
        "blanco": "#e2ddd5"}
EYES = {"marrones": "#5b3a22", "azules": "#3a6a9a", "verdes": "#4a7a4a", "negros": "#2a1d16"}

SKINS = ("clara", "media", "morena", "oscura")
HAIR_STYLES = ("corto", "calvo", "largo", "moño", "rapado")
HATS = ("ninguno", "gorra_plana", "gorra_militar", "boina", "sombrero", "casco", "tricornio", "corona", "mantilla",
        "chistera", "bombin", "toca", "pañuelo")
BEARDS = ("ninguna", "barba_corta", "barba", "bigote", "bigotazo", "perilla")
OUTFITS = ("jersey", "uniforme", "traje", "camisa", "vestido", "sotana", "armadura", "capa", "noble", "levita", "campesino")
NOSES = ("patata", "aguileña", "pequeña", "gancho")
JAWS = ("redonda", "cuadrada", "fina")
AGES = ("joven", "adulto", "mayor")

FRAMINGS = {
    "general": "plano general del lugar; los personajes de `cast` salen de cuerpo entero (quietos o caminando con `walk`)",
    "personaje": "primer plano del personaje que habla; si en `cast` hay otro, se ve su nuca desenfocada (plano/contraplano)",
    "dos": "dos personajes de medio cuerpo juntos (el primero de `cast` habla o reacciona)",
    "objeto": "primer plano de un objeto (`prop`) sobre una mesa, con el lugar desenfocado detrás",
}
GESTURES = {
    "explain": "explica moviendo las manos", "point": "señala hacia algo", "chest": "mano al pecho (sinceridad, juramento)",
    "shrug": "se encoge de hombros", "fist": "puño en alto (rabia, arenga)", "wave": "saluda o llama con la mano",
    "think": "mano en la barbilla (duda)", "idle": "brazos quietos",
}
EMOTIONS = {  # (cejas, sonrisa, preocupación: cejas en pena, extra visual)
    "neutral": (0.0, 0.0, 0.0, ""), "serio": (-0.4, -0.1, 0.0, ""), "enfadado": (-0.9, -0.4, 0.0, ""),
    "furioso": (-1.0, -0.6, 0.0, "furia"), "sorprendido": (0.9, 0.0, 0.0, "abierta"),
    "asustado": (0.8, -0.5, 0.7, "sudor"), "horrorizado": (1.0, -0.6, 0.5, "shock"),
    "triste": (0.1, -0.7, 0.9, ""), "llorando": (0.1, -0.9, 1.0, "lagrimas"), "contento": (0.3, 0.8, 0.0, ""),
    "euforico": (0.6, 1.0, 0.0, "brillo"), "pensativo": (-0.3, 0.0, 0.0, "mira_arriba"), "burlon": (0.2, 0.6, 0.0, ""),
    "desconfiado": (-0.6, 0.2, 0.0, "entorna"), "nervioso": (0.3, -0.2, 0.6, "sudor"),
    "avergonzado": (0.2, 0.2, 0.5, "rubor"), "enamorado": (0.4, 0.7, 0.0, "enamorado"),
    "aliviado": (0.2, 0.5, 0.3, "suspiro"), "decidido": (-0.6, 0.15, 0.0, ""),
}
EMOTION_DESC = {
    "furioso": "rojo de ira, con la vena marcada", "sorprendido": "boca abierta", "asustado": "con una gota de sudor",
    "horrorizado": "pálido, pupilas diminutas y boca en O", "triste": "cejas caídas de pena",
    "llorando": "con lágrimas", "euforico": "sonrisa enorme y ojos brillantes", "desconfiado": "ojos entornados",
    "nervioso": "sudando", "avergonzado": "colorado, mirando abajo", "enamorado": "colorado y con corazones",
    "aliviado": "suspira con los ojos medio cerrados", "decidido": "ceño firme y media sonrisa",
}


def emotion(name: str) -> tuple[float, float, float, str]:
    return EMOTIONS.get(name, EMOTIONS["neutral"])


CAMERAS = {"push_in": "acercamiento lento", "pull_back": "alejamiento que revela", "static": "cámara quieta",
           "shake": "cámara temblorosa (caos, golpes)"}
MOODS = {"dia": "día", "atardecer": "atardecer", "noche": "noche", "tormenta": "cielo de tormenta"}
ERAS = ("medieval", "1500", "1700", "1800", "1900", "1950", "moderno")
SFX = {"hit": "golpe grave dramático", "whoosh": "silbido rápido", "boom": "explosión", "splash": "chapuzón"}
PROP_DESC = {
    "carta": "carta manuscrita con sello de lacre", "documento": "documento oficial", "mapa": "mapa con ruta marcada",
    "bomba": "bomba", "corona": "corona real", "pistola": "pistola", "espada": "espada", "monedas": "monedas de oro",
    "reloj": "reloj de bolsillo en marcha", "llave": "llave antigua", "veneno": "frasco de veneno",
    "periodico": "periódico", "cuchillo": "cuchillo ensangrentado", "anillo": "anillo con piedra preciosa",
    "movil": "móvil con un chat cuyos mensajes van apareciendo", "cerebro": "cerebro con chispas de actividad",
    "tierra": "la Tierra girando", "corazon": "corazón que late", "cafe": "taza de café humeante",
}
EVENT_DESC = {
    "aviones": "dos aviones repostando en vuelo (lugar: cielo)", "explosion": "gran explosión con bola de fuego",
    "bombardeo": "varias explosiones en tierra", "paracaidas": "cuatro bombas cayendo con paracaídas",
    "hundimiento": "algo cae con paracaídas al mar y se hunde (lugares con mar)", "fuego": "incendio con llamas y humo",
    "disparos": "fogonazos de disparos y humo de pólvora", "lluvia": "lluvia con relámpagos", "nieve": "nevada",
    "multitud": "muchedumbre en silueta agitando los brazos (motín, protesta, celebración)",
    "barco": "velero que cruza (lugares con mar)", "cañonazos": "cañonazos con fogonazo y humo",
    "meteorito": "meteorito que cruza el cielo y se estrella con una gran explosión",
    "corazones": "corazones que suben flotando (flechazo, amor)",
    "pensamientos": "nubes de pensamientos girando sobre la escena (darle vueltas a algo, dudas, ansiedad)",
}


PROP_DESC.update(EXTRA_PROP_DESC)
EVENT_DESC.update(EXTRA_EVENT_DESC)


def make_character(name: str, look: dict, seed: int) -> Character:
    """Convierte la ficha elegida por el guionista en un personaje dibujable."""
    def col(key: str, default: str) -> str:
        return COLORS.get(look.get(key) or "", default)
    beard = look.get("beard", "ninguna")
    hat = {"gorra_plato": "gorra_militar", "gorra_marino": "gorra_militar"}.get(look.get("hat", ""), look.get("hat", "ninguno"))
    return Character(name, Look(
        skin=look.get("skin", "media"),
        hair=HAIR.get(look.get("hair_color") or "", HAIR["castaño"]),
        hair_style=look.get("hair_style", "corto"),
        hat=hat,
        hat_color=col("hat_color", "#2b2f3a"),
        beard=beard,
        beard_color=HAIR.get(look.get("beard_color") or "", None),
        outfit=look.get("outfit", "camisa"),
        outfit_color=col("outfit_color", "#2d3d5c"),
        accent_color=col("accent_color", "#c9a227"),
        pants_color=col("pants_color", "#3a3a42"),
        nose=look.get("nose", "patata"),
        jaw=look.get("jaw", "redonda"),
        age=look.get("age", "adulto"),
        glasses=bool(look.get("glasses", False)),
        female=bool(look.get("female", False)),
        eyes=EYES.get(look.get("eyes") or "", EYES["marrones"]),
        seed=seed,
    ))


def catalog_text(voices: list[str]) -> str:
    def lst(d):
        return "\n".join(f"  - `{k}`: {v}" for k, v in d.items())
    locs = "\n".join(f"  - `{k}`: {v.desc}" + (" (interior)" if v.interior else "") for k, v in LOCATIONS.items())
    return f"""
## CATÁLOGO DE LA BIBLIOTECA DE ANIMACIÓN (usa solo estas claves)
- **Lugares (`location`)**:
{locs}
- **Tipos de plano (`framing`)**:
{lst(FRAMINGS)}
- **Objetos (`prop`, solo con framing `objeto`)**:
{lst({k: PROP_DESC.get(k, k) for k in PROPS})}
- **Sucesos (`event`, se superponen al plano)**:
{lst({k: EVENT_DESC.get(k, k) for k in EVENTS})}
- **Gestos (`gesture`, del personaje que habla)**:
{lst(GESTURES)}
- **Emociones (`emotion` del que habla, `listener_emotion` del que escucha)**: {", ".join(f"`{k}`" + (f" ({EMOTION_DESC[k]})" if k in EMOTION_DESC else "") for k in EMOTIONS)}. Que la cara diga lo mismo que la frase: una mala noticia es `triste` o `llorando`, nunca `neutral`; quien escucha algo grave reacciona (`sorprendido`, `triste`, `horrorizado`).
- **Cámara (`camera`)**:
{lst(CAMERAS)}
- **Luz (`mood`)**: {", ".join(f"`{k}`" for k in MOODS)} · **Época (`era`, de la serie)**: {", ".join(f"`{e}`" for e in ERAS)}
- **Efectos de sonido extra (`sfx`)**: {", ".join(f"`{k}` ({v})" for k, v in SFX.items())}. Los sucesos ya traen su sonido.
- **Voces (`voice`)**: {", ".join(f"`{v}`" for v in voices)}
- **Vestuario (`look` de cada personaje)**:
  - `skin`: {", ".join(SKINS)} · `hair_color`/`beard_color`: {", ".join(HAIR)} · `hair_style`: {", ".join(HAIR_STYLES)}
  - `hat`: {", ".join(HATS)} (gorra_plana = gorra de paño de pescador/obrero; gorra_militar = gorra de plato con visera de oficial, policía o marino)
  - `outfit`: {", ".join(OUTFITS)} (noble = jubón con gorguera s. XVI-XVII; levita = s. XIX; capa = rey/noble; uniforme = militar/policía)
  - `beard`: {", ".join(BEARDS)} · `nose`: {", ".join(NOSES)} · `jaw`: {", ".join(JAWS)} · `age`: {", ".join(AGES)}
  - colores (`outfit_color`, `hat_color`, `accent_color` para botones/galones/corbata, `pants_color`): {", ".join(COLORS)}
  - `eyes`: {", ".join(EYES)} · `glasses` y `female`: true/false
"""
