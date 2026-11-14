# auto-reels

Genera y publica cada día un vídeo vertical con voz en off en **TikTok, Instagram Reels y YouTube Shorts**.

```
Claude (guion) → voz IA (Edge TTS / ElevenLabs) → clips de Pexels → subtítulos animados → FFmpeg → Upload-Post
```

Todo se ejecuta gratis en **GitHub Actions** una vez al día (17:00 UTC). El historial de temas
(`data/history.json`) se guarda en el repo para que Claude no repita temas.

## Costes aproximados

| Servicio | Coste |
|---|---|
| Upload-Post Basic (necesario para TikTok) | ~16–24 $/mes |
| Claude (un guion al día) | incluido en tu suscripción de Claude (token de Claude Code) |
| Voz Edge TTS | gratis (ElevenLabs opcional: desde ~5 $/mes) |
| Pexels | gratis |
| GitHub Actions | gratis (repo público, o los 2.000 min/mes del plan gratuito en uno privado) |

## Puesta en marcha

1. **Upload-Post**: crea la cuenta, contrata el plan Basic, crea un *perfil* (p. ej. `avora`) y conecta
   TikTok, Instagram (cuenta Business/Creator) y YouTube. Copia la API key.
2. **Claude**: en tu terminal ejecuta `claude setup-token`. Genera un token de larga duración
   ligado a tu suscripción (Pro/Max), sin coste extra. Los guiones consumen un poco de tu cuota.
3. **Pexels**: API key gratuita en https://www.pexels.com/api/ (sin ella, el vídeo usa fondos de color).
4. **GitHub**: sube este repo y ve a *Settings → Secrets and variables → Actions*:
   - Secrets: `CLAUDE_CODE_OAUTH_TOKEN`, `UPLOAD_POST_API_KEY`, `PEXELS_API_KEY` (y `ELEVENLABS_API_KEY` si la usas)
   - Variables: `UPLOAD_POST_USER` = el nombre del perfil de Upload-Post
5. **Primera prueba**: *Actions → Reel diario → Run workflow* con «Solo generar el vídeo» marcado.
   Descarga el vídeo en *Artifacts* y revísalo. Cuando te guste, ya se publicará solo cada día.

## Personalizar

Todo está en `config.yaml`: descripción de la marca, mezcla de formatos y su peso, voz, duración,
color de los subtítulos, plataformas y etiqueta de contenido IA. Para añadir música, mete pistas
libres de derechos en `assets/music/`.

## Probar en local

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # requiere ffmpeg instalado
.venv/bin/python -m reels --sample        # guion de ejemplo, sin gastar API ni publicar
export PEXELS_API_KEY=...
.venv/bin/python -m reels --dry-run       # guion real (usa tu sesión de Claude Code), sin publicar
```

El resultado queda en `out/AAAA-MM-DD/reel.mp4`.

## Estructura

```
reels/script.py    guion con Claude (Claude Code con tu suscripción, o la API)
reels/tts.py       voz en off + tiempos por palabra
reels/footage.py   clips verticales de Pexels
reels/captions.py  subtítulos con la palabra activa resaltada
reels/render.py    montaje FFmpeg
reels/publish.py   publicación vía Upload-Post
.github/workflows/daily-reel.yml   ejecución diaria
```
