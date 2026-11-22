# Manual de auto-reels

Sistema que escribe, dibuja, pone voz, monta y publica vídeos cortos de cinco marcas, solo, todos los días.
Repositorio: https://github.com/equipimpulsodigital-jpg/auto-reels (GitHub → pestaña **Actions** para lanzar cosas a mano).

## 1. Cómo funciona un día normal

1. **2:10 (cron-job.org)** lanza en GitHub la ejecución nocturna. De reserva, GitHub lo intenta también a las 1:17, 3:43 y 5:29 (si ya está todo hecho, terminan en segundos).
2. La ejecución, para cada marca:
   - mira las visualizaciones de lo publicado (para aprender qué funciona);
   - lee lo que se busca hoy (Google Trends) y las noticias de la semana sobre su tema;
   - **Claude** propone 5 temas, elige el mejor y escribe el guion (28–35 s);
   - pone la voz, anima los dibujos, añade música, ambiente y subtítulos;
   - lo deja **programado en Upload-Post** para hoy y mañana a sus horas;
   - actualiza la página de libros (Amazon) de la marca.
3. **De día** (7:40, 13:40, 18:40) hay reservas que rellenan cualquier hueco y **vuelven a subir** lo que haya fallado por un error pasajero.
4. **Avisos**: a las 8:23 y a las 17:23 se comprueba todo. Si hay algo que hacer, te llega un correo de GitHub («⚠️ auto-reels: hay algo que revisar»). Si todo va bien, no llega nada. Cuando se arregla, el aviso se cierra solo.
5. **Lunes 8:37**: resumen semanal por correo (visualizaciones, seguidores, mejores y peores vídeos).
6. **Domingo 11:00**: recopilación larga de la semana en YouTube, por marca.

## 2. Las marcas

| Marca | Tema | Estilo | Vídeos/día | Horas |
|---|---|---|---|---|
| Bien Contadas | Historia real de España | Volumen (3D) | 5 | 10, 12, 16, 18, 21 |
| Archivo del Misterio | Casos famosos de misterio y paranormales | Volumen (3D) | 5 | 10, 12, 16, 18, 21 |
| Conexión con Chispa | Citas y relaciones (debates, red flags) | Volumen (3D) | 7 | 9:30, 11:45, 14, 16, 18, 20, 21:45 |
| La Cabeza por Dentro | Psicología cotidiana | Plano | 5 | 10, 12, 16, 18, 21 |
| ¿Y si…? | Escenarios imposibles, hora a hora | Plano | 5 | 10, 12, 16, 18, 21 |

Cada vídeo sale en Instagram, YouTube y TikTok. Cada marca tiene su presentador fijo que cierra el vídeo con una pregunta de dos opciones (para que la gente comente) y un primer comentario automático (Instagram y YouTube).
Una de cada 5 franjas reutiliza un vídeo ganador (más de 14 días y un 30 % por encima de la media) con un gancho nuevo.

## 3. Qué hacer si…

| Pasa esto | Haz esto |
|---|---|
| Te llega un aviso de **franjas sin vídeo** | GitHub → Actions → **Episodio diario** → Run workflow → canal `todos`, modo **programar** |
| El aviso dice **«pide reconectarla»** o **«session… password»** | En Upload-Post → Users → la marca → reconecta esa red (pasa si cambias la contraseña) |
| El aviso dice **TikTok «risky»** | TikTok desconfía de la cuenta: úsala unos días desde el móvil y sube algún vídeo a mano |
| El aviso dice **canal de YouTube no disponible** | Revisa el correo de esa cuenta de Google; si YouTube lo cerró, apela desde ese correo |
| Un vídeo **falló en una red** por un error pasajero | Nada: se reintenta solo. A mano: modo **reintentar** |
| Quieres **quitar un vídeo programado** y poner otro | Modo **cancelar** con la franja (p. ej. `2026-11-25 16:00`) |
| Quieres ver **cómo salieron** las últimas publicaciones | Modo **estado** |
| Quieres las **visualizaciones** ya | Modo **estadisticas** |
| Quieres **probar** un vídeo sin publicarlo | Modo **prueba** (el vídeo queda en la ejecución, en «Artifacts») |
| Claude dice **«5-hour limit»** | Nada: las reservas del día rellenan los huecos cuando se recupera |

## 4. Cómo cambiar cosas (archivo `config.yaml`, o pídeselo a Claude)

- **Horas**: `publish.slots` (todas las marcas) o `slots` dentro de una marca.
- **Pausar una marca**: `enabled: false` en esa marca.
- **Pausar TikTok unos días**: `tiktok_paused_until: "AAAA-MM-DD"` en la marca.
- **Estilo de dibujo**: `style: volumen | plano | caricatura | amable`.
- **Temas y tono**: el guionista de cada marca está en `prompts/<marca>.md`; las reglas comunes, en `prompts/animacion.md`.
- **Formatos y su rotación**: `formats` y `format_cycle` en la marca.
- **Noticias que inspiran los temas**: `interest_queries` en la marca.
- **Presentador**: `host` en la marca.
- **Enlaces de la página de libros**: `links` en la marca (cambia aquí los @ si los cambias en las redes).
- **Caducidades** (para que te avise 15 días antes): `expirations` en la configuración general.

## 5. Claves y servicios (dónde está cada cosa)

| Qué | Dónde | Caduca / se paga |
|---|---|---|
| Claude (guiones) | GitHub → Settings → Secrets → `CLAUDE_CODE_OAUTH_TOKEN` | suele durar 1 año; se renueva con `claude setup-token` |
| Upload-Post (publicar) | GitHub → Secrets → `UPLOAD_POST_API_KEY` | plan Basic, mensual |
| cron-job.org (ejecución nocturna puntual) | cron-job.org → tarea «auto-reels noche» | la clave de GitHub que usa caduca según la creaste |
| Amazon Afiliados | etiqueta `historiasbien-21` en `config.yaml` | pide 3 ventas en 180 días para no darse de baja |
| Páginas de libros | https://equipimpulsodigital-jpg.github.io/auto-reels/<marca>/ | gratis (GitHub Pages) |

Coste mensual: Upload-Post Basic + tu plan de Claude. GitHub, cron-job.org, la música, las voces y los dibujos son gratis.

## 6. Ojo con

- **El repositorio es público**: nunca pongas contraseñas ni datos personales en los archivos. Las claves van solo en *Secrets*.
- **Las incidencias (avisos y resúmenes) también son públicas**: muestran visualizaciones y nombres de cuentas, nada privado.
- Los vídeos generados se guardan **14 días** en GitHub (Actions → la ejecución → Artifacts).
- Para cobrar en YouTube hacen falta 1.000 suscriptores y 10 M de visualizaciones de Shorts en 90 días; TikTok solo paga vídeos de más de 1 minuto.
