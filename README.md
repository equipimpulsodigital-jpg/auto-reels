# auto-reels · canales automáticos de historias animadas

Genera vídeos verticales (9:16, 35–50 s) de **caricaturas 2D animadas por código** y los publica en
Instagram Reels, YouTube Shorts y TikTok mediante Upload-Post. Hay un canal por perfil de Upload-Post:

| Canal (`config.yaml`) | Perfil Upload-Post | Temática | Estado |
|---|---|---|---|
| `bien_contadas` | bien_contadas | Historia oscura de España (puntos de inflexión, crímenes históricos) | activo |
| `elanecdotario` | elanecdotario | Historias de misterio reales (casos sin resolver, enigmas) | en pausa |

Cada historia se cuenta en **1 o 2 partes**. Claude escribe todas las partes de golpe, con reparto de
personajes, vestuario y planificación de cada plano.

```
Claude (guion + reparto + planos) → voces Edge TTS → caricaturas animadas (Skia) → música y efectos
propios → subtítulos → FFmpeg → Upload-Post (programado a la hora exacta)
```

## Cómo se publica

- Las horas están en `config.yaml` → `publish.slots` (10, 13, 16, 19 y 22 h, hora de España).
- GitHub se ejecuta **de noche**: genera los vídeos de las próximas 24 h de cada canal activo y los deja
  **programados en Upload-Post** a esas horas. Así da igual que GitHub se retrase (le pasa a menudo).
- Hay ejecuciones de reserva (madrugada y mediodía): si ya está todo programado, terminan en segundos.

## Añadir o activar un canal

1. En Upload-Post, crea el perfil y conecta sus redes.
2. En `config.yaml` → `channels`, pon el nombre exacto del perfil (`profile`), sus redes
   (`platforms`), su guionista (`prompt`) y sus formatos, y `enabled: true`.
3. Escribe su guionista en `prompts/<canal>.md` (temática y reglas del guion). Las reglas de la
   animación son comunes a todos los canales: `prompts/animacion.md`.

## Uso desde GitHub (Actions → Episodio diario → Run workflow)

- **Canal**: uno o todos los activos.
- **Modo**: `prueba` (solo genera el vídeo; descárgalo en el resumen de la ejecución), `programar`
  (prepara las franjas de las próximas 24 h) o `ahora` (publica uno al momento).
- **Empezar historia nueva**, **Tema** y **Formato** (clave de `formats` del canal; vacío = alterna).
- **Publicar aunque el canal esté en pausa**: para publicar en un canal con `enabled: false`.

Desde el ordenador: `python -m reels --channel elanecdotario --dry-run` (ver `python -m reels -h`).

## Secrets de GitHub

`CLAUDE_CODE_OAUTH_TOKEN` (de `claude setup-token`) y `UPLOAD_POST_API_KEY`; opcional `ELEVENLABS_API_KEY`.
El perfil de cada canal está en `config.yaml`.

## Archivos importantes

```
config.yaml               canales, horas de publicación, vídeo, voces del reparto
prompts/<canal>.md        guionista de cada canal
prompts/animacion.md      reglas comunes de personajes, vestuario y planos
data/<canal>/state.json   partes pendientes y franjas ya programadas
data/<canal>/history.json historias ya hechas (Claude no las repite)
reels/script.py           guion con Claude (salida estructurada)
reels/toon/               animación: personajes, escenarios, objetos, sucesos, efectos de sonido
reels/captions.py         subtítulos, etiqueta «Parte X/2» y cartel final
reels/render.py           montaje, música (baja sola bajo la voz) y efectos
reels/publish.py          publicación y programación vía Upload-Post
tools/make_music.py       compone las pistas propias de assets/music (sin derechos de terceros)
```

Cada vídeo guarda también `guion.md` con la ficha del episodio, el reparto y el guion plano a plano.
