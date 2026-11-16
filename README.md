# auto-reels · Historia oscura de España

Publica cada día un episodio vertical (9:16, 35–50 s) en **TikTok, Instagram Reels y YouTube Shorts**
sobre historia real de España, en dos formatos:

1. **«El día que España estuvo a punto de...»**: puntos de inflexión, errores críticos y decisiones límite.
2. **Crímenes, conspiraciones y sucesos oscuros reales.**

Cada historia se cuenta en **1 o 2 partes** (como máximo), con una parte publicada cada día. Claude escribe
todas las partes de golpe, así que la Parte 2 encaja con el cliffhanger de la Parte 1 y mantiene el mismo
estilo visual.

```
Claude (guion + dirección visual + prompts) → voz IA → dibujos animados 2D (12–16 planos cortos con
movimiento de cámara y fundidos) → música de fondo → subtítulos animados → FFmpeg → Upload-Post
```

## Costes

| Servicio | Coste |
|---|---|
| Upload-Post Basic (necesario para TikTok) | ~16–24 $/mes |
| Claude | incluido en tu suscripción (token de Claude Code) |
| Imágenes (Pollinations) | gratis (1 imagen/45 s, calidad básica) · opcional Replicate: ~0,05 $/vídeo |
| Voz (Edge TTS) | gratis · opcional ElevenLabs desde ~5 $/mes |
| GitHub Actions | gratis (~15 min por ejecución) |

## Puesta en marcha

1. **Upload-Post**: contrata el plan Basic, crea un *perfil* y conecta TikTok, Instagram (cuenta
   Business/Creator) y YouTube. Copia la API key.
2. **GitHub → Settings → Secrets and variables → Actions**:
   - Secrets: `CLAUDE_CODE_OAUTH_TOKEN` (de `claude setup-token`), `UPLOAD_POST_API_KEY`
     y, opcionalmente, `REPLICATE_API_TOKEN` o `ELEVENLABS_API_KEY`
   - Variables: `UPLOAD_POST_USER` = nombre del perfil de Upload-Post
3. **Prueba**: *Actions → Episodio diario → Run workflow* con «Solo generar el vídeo» marcado. En el
   resumen de la ejecución tienes dos descargas: `preview-…` (fotogramas + guion, pesa poco) y
   `reel-…` (vídeo completo).

## Uso desde GitHub (Run workflow)

- **Solo generar el vídeo**: prueba sin publicar. La parte sigue pendiente y será la que se publique después.
- **Empezar historia nueva** + **Tema**: por ejemplo «El motín de Esquilache» o «El crimen del Expreso de Andalucía».
- **Formato**: fuerza punto de inflexión o crimen histórico (por defecto se alternan).

## Archivos importantes

```
prompts/guionista.md   reglas creativas del guionista (edítalas a tu gusto)
config.yaml            partes por historia, voz, imágenes, colores, plataformas
data/state.json        partes pendientes de publicar
data/history.json      historias ya hechas (Claude no las repite)
reels/script.py        guion con Claude (salida estructurada)
reels/images.py        imágenes 9:16 (Pollinations o Replicate)
reels/render.py        movimiento de cámara, fundidos, música (baja sola bajo la voz) y montaje
assets/music/          pistas de fondo; se elige una al azar en cada vídeo
tools/make_music.py    compone las pistas propias de assets/music (sin derechos de terceros)
reels/captions.py      subtítulos, etiqueta «Parte X/2» y cartel final
reels/publish.py       publicación vía Upload-Post
```

Cada ejecución guarda también `guion.md` con la ficha del episodio, el Estilo Visual Maestro y el guion
bloque a bloque con tiempos, cámara y prompt de imagen.

Para añadir música, pon pistas libres de derechos (ambiente oscuro o tensión) en `assets/music/`.
