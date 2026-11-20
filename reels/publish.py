"""Publicación en TikTok, Instagram Reels y YouTube Shorts mediante la API de Upload-Post."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests

from .config import env
if TYPE_CHECKING:  # solo para anotaciones: así «--status» no necesita la animación
    from .script import Part

API = "https://api.upload-post.com/api"


class LimitReached(RuntimeError):
    """No quedan publicaciones en el plan de Upload-Post: no tiene sentido seguir generando vídeos."""


def report(ids: list[str]) -> None:
    """Muestra cómo acabó cada publicación (sin publicar nada). Solo plataforma, resultado, enlace y error."""
    headers = {"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}"}
    for rid in ids:
        for key in ("request_id", "job_id"):
            try:
                r = requests.get(f"{API}/uploadposts/status", headers=headers, params={key: rid}, timeout=60)
                st = r.json()
            except (requests.RequestException, ValueError) as e:
                print(f"  {rid}: error consultando ({e})")
                break
            if r.status_code == 404 or str(st.get("status", "")).lower() == "not_found":
                continue
            state = str(st.get("status", "")).lower()
            print(f"  {rid} ({key}): estado={st.get('status')} {st.get('message') or st.get('error') or ''}")
            if state not in ("completed", "failed", "error", "partial", "partially_completed"):
                print("    (pendiente: aún no es su hora de publicación)")
                break
            for res in st.get("results") or []:
                ok = "OK " if res.get("success") else "ERROR"
                print(f"    [{ok}] {res.get('platform')}: {res.get('post_url') or res.get('url') or ''} "
                      f"{res.get('error_message') or res.get('message') or res.get('error') or ''}"[:600])
            break
        else:
            print(f"  {rid}: Upload-Post no lo encuentra")


# Avisos que ya no se publican (los guiones antiguos en cola aún los llevan)
_DROP = re.compile(r"\s*\(?(Recreaci[oó]n animada basada en hechos reales|Di[aá]logos recreados[^.)\n]*)\.?\)?", re.I)


def _clean(text: str) -> str:
    return _DROP.sub("", text).strip()


def publish_youtube(video: Path, title: str, description: str, tags: list[str], cfg: dict, key: str,
                    scheduled_at: Optional[datetime] = None, thumb: Optional[Path] = None) -> dict:
    """Vídeo largo solo en YouTube (recopilaciones), programado a la hora indicada."""
    pcfg = cfg["publish"]
    ai = "true" if pcfg.get("label_as_ai", False) else "false"
    fields = [("user", cfg["channel"]["profile"]), ("platform[]", "youtube"), ("title", title[:100]),
              ("youtube_title", title[:100]), ("youtube_description", description[:5000]),
              ("privacyStatus", pcfg.get("youtube_privacy", "public")), ("selfDeclaredMadeForKids", "false"),
              ("containsSyntheticMedia", ai), ("defaultLanguage", "es"), ("defaultAudioLanguage", "es"),
              ("external_id", key)]
    fields += [("tags[]", t) for t in tags]
    if scheduled_at is not None:
        fields += [("scheduled_date", scheduled_at.strftime("%Y-%m-%dT%H:%M:%S")),
                   ("timezone", pcfg.get("timezone", "Europe/Madrid"))]
    else:
        fields.append(("async_upload", "true"))
    headers = {"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}", "Idempotency-Key": key}
    files = {"video": (video.name, open(video, "rb"), "video/mp4")}
    if thumb and thumb.exists():
        files["thumbnail"] = (thumb.name, open(thumb, "rb"), "image/jpeg")
    try:
        r = requests.post(f"{API}/upload", headers=headers, data=fields, files=files, timeout=3600)
    finally:
        for f in files.values():
            f[1].close()
    if r.status_code >= 400:
        raise RuntimeError(f"Upload-Post respondió {r.status_code}: {r.text[:1000]}")
    result = r.json()
    print("  Upload-Post:", json.dumps(result, ensure_ascii=False)[:800])
    return result


def list_accounts(profile: str) -> None:
    """Cuentas conectadas a un perfil de Upload-Post, con su enlace público."""
    headers = {"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}"}
    r = requests.get(f"{API}/uploadposts/users/{profile}", headers=headers, timeout=60)
    if r.status_code >= 400:
        print(f"  {profile}: error {r.status_code} {r.text[:200]}")
        return
    data = r.json()
    prof = data.get("profile") or data.get("user") or data
    accounts = prof.get("social_accounts") or {}
    for platform, acc in sorted(accounts.items()):
        if not isinstance(acc, dict) or not acc:
            continue
        handle = (acc.get("handle") or "").lstrip("@")
        uid = acc.get("username") or ""
        url = {"instagram": f"https://www.instagram.com/{handle}/" if handle else "",
               "tiktok": f"https://www.tiktok.com/@{handle}" if handle else "",
               "youtube": f"https://www.youtube.com/@{handle}" if handle else f"https://www.youtube.com/channel/{uid}",
               "facebook": f"https://www.facebook.com/{uid}" if uid else ""}.get(platform, "")
        warn = "  ⚠ hay que reconectarla" if acc.get("reauth_required") else ""
        print(f"  {platform:10} {acc.get('display_name') or ''} (@{handle}) {url}{warn}")


_AI_FLAGS = ("is_aigc", "containsSyntheticMedia", "is_ai_generated", "made_with_ai",
             "facebook_is_ai_generated", "threads_is_made_with_ai")


def unlabel_scheduled(profile: str) -> None:
    """Quita la etiqueta de IA y el aviso de recreación de las publicaciones ya programadas del perfil."""
    headers = {"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}"}
    r = requests.get(f"{API}/uploadposts/schedule", headers=headers,
                     params={"profile_username": profile, "limit": 100}, timeout=60)
    r.raise_for_status()
    jobs = r.json().get("scheduled_posts") or []
    print(f"  {len(jobs)} publicaciones programadas en {profile}")

    def clean(v):
        if isinstance(v, str):
            return _clean(v) if _DROP.search(v) else v
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x) for x in v]
        return v

    for job in jobs:
        jid = job.get("job_id")
        if job.get("profile_username") not in (None, profile):
            continue
        fields = dict(job.get("fields") or {})
        for k in _AI_FLAGS:
            if k in fields or k in ("is_aigc", "containsSyntheticMedia", "is_ai_generated"):
                fields[k] = False
        body = {"fields": clean(fields)}
        for k in ("caption", "description", "title"):
            if isinstance(job.get(k), str) and _DROP.search(job[k]):
                body["caption" if k == "description" else k] = _clean(job[k])
        if job.get("platform_content"):
            body["platform_content"] = clean(job["platform_content"])
        resp = requests.patch(f"{API}/uploadposts/schedule/{jid}", headers=headers, json=body, timeout=60)
        ok = resp.status_code < 300
        print(f"  [{'OK ' if ok else 'ERROR'}] {job.get('scheduled_date')} {jid}"
              + ("" if ok else f" → {resp.status_code} {resp.text[:200]}"))


def _hashtags(script: Part, brand: str = "") -> str:
    tags = ["#" + t.lstrip("#").replace(" ", "") for t in script.hashtags][:6]
    if brand and brand.lower() not in (t.lower() for t in tags):
        tags.append(brand)
    return " ".join(tags)


def _caption(script: Part, total_parts: int = 1, book: bool = False, brand: str = "") -> str:
    tags = _hashtags(script, brand)
    follow = f"\n\nSígueme para la parte {script.part_number + 1}" if script.part_number < total_parts else ""
    books = "\n\n📚 El libro de esta historia, en el enlace de mi perfil." if book else ""
    return f"{_clean(script.caption)}{follow}{books}\n\n{tags}".strip()


def publish(video: Path, script: Part, cfg: dict, idempotency_key: str, total_parts: int = 1,
            scheduled_at: Optional[datetime] = None, book: bool = False) -> dict:
    """Publica ya o, con scheduled_at, deja la publicación programada en Upload-Post a esa hora exacta."""
    pcfg, ch = cfg["publish"], cfg["channel"]
    platforms = ch["platforms"]
    ai = "true" if pcfg.get("label_as_ai", True) else "false"
    brand = cfg["channel"].get("hashtag", "")
    caption = _caption(script, total_parts, book and bool(cfg["channel"].get("links_page", True)), brand)

    fields: list[tuple[str, str]] = [("user", ch["profile"]), ("title", script.youtube_title[:100])]
    fields += [("platform[]", p) for p in platforms]
    fields.append(("external_id", idempotency_key))
    if scheduled_at is not None:
        fields += [("scheduled_date", scheduled_at.strftime("%Y-%m-%dT%H:%M:%S")),
                   ("timezone", pcfg.get("timezone", "Europe/Madrid"))]
    else:
        # Modo síncrono: la propia subida espera al resultado (1 sola llamada por publicación).
        fields.append(("async_upload", "false"))
    if "tiktok" in platforms:
        fields += [("tiktok_title", caption[:2200]), ("is_aigc", ai)]
    if "instagram" in platforms:
        fields += [("instagram_title", caption[:2200]), ("media_type", "REELS"),
                   ("share_to_feed", "true"), ("is_ai_generated", ai)]
    if "youtube" in platforms:
        # YouTube lleva su propia descripción (pensada para el buscador), no la de Instagram repetida
        follow = (f"\n\n▶ Sígueme para la parte {script.part_number + 1}." if script.part_number < total_parts else "")
        desc = f"{_clean(script.youtube_description)}{follow}\n\n{_hashtags(script, brand)}"
        fields += [("youtube_title", script.youtube_title[:100]), ("youtube_description", desc[:5000]),
                   ("privacyStatus", pcfg.get("youtube_privacy", "public")),
                   ("selfDeclaredMadeForKids", "false"), ("containsSyntheticMedia", ai)]
        fields += [("tags[]", t.lstrip("#")) for t in script.hashtags]

    headers = {"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}", "Idempotency-Key": idempotency_key}
    files = {"video": (video.name, open(video, "rb"), "video/mp4")}
    cover = video.parent / "portada.jpg"
    if cover.exists():  # portada diseñada: Instagram, TikTok y (si el canal está verificado) YouTube
        if "instagram" in platforms:
            files["cover_image"] = (cover.name, open(cover, "rb"), "image/jpeg")
        if "tiktok" in platforms:
            files["tiktok_cover_image"] = (cover.name, open(cover, "rb"), "image/jpeg")
        if "youtube" in platforms and pcfg.get("youtube_thumbnail", False):
            files["thumbnail"] = (cover.name, open(cover, "rb"), "image/jpeg")
    try:
        r = requests.post(f"{API}/upload", headers=headers, data=fields, files=files, timeout=1200)
    finally:
        for f in files.values():
            f[1].close()
    if r.status_code == 429 and "limit" in r.text:
        raise LimitReached(f"Upload-Post: límite del plan alcanzado ({r.text[:300]})")
    if r.status_code >= 400:
        raise RuntimeError(f"Upload-Post respondió {r.status_code}: {r.text[:2000]}")
    result = r.json()
    print("  Upload-Post:", json.dumps(result, ensure_ascii=False)[:1500])

    if scheduled_at is not None:
        ok = bool(result.get("success", True)) and bool(result.get("job_id") or result.get("request_id"))
        result["final_status"] = {"status": "scheduled" if ok else "failed", "results": []}
        return result

    request_id = result.get("request_id")
    # Si Upload-Post pasa la subida a segundo plano (tarda demasiado), se espera a la confirmación final.
    if request_id and not result.get("results"):
        result["final_status"] = wait_for_status(request_id, headers, interval=45)
    else:
        result["final_status"] = _sync_status(result)
    return result


def _sync_status(result: dict) -> dict:
    """Traduce la respuesta síncrona al mismo formato que la consulta de estado."""
    res = result.get("results") or {}
    items = res.items() if isinstance(res, dict) else [(r.get("platform"), r) for r in res]
    rows = []
    for platform, r in items:
        r = r if isinstance(r, dict) else {}
        ok = bool(r.get("success", result.get("success")))
        rows.append({"platform": platform, "success": ok,
                     "post_url": r.get("url") or r.get("post_url"), "message": r.get("error") or r.get("message")})
        print(f"  [{'OK ' if ok else 'ERROR'}] {platform}: {rows[-1]['post_url'] or rows[-1]['message'] or ''}")
    if not rows:
        return {"status": "completed" if result.get("success") else "failed", "results": []}
    return {"status": "completed", "results": rows}


def wait_for_status(request_id: str, headers: dict, timeout_s: int = 900, interval: int = 20) -> dict:
    """Consulta el estado hasta que termina (TikTok e Instagram procesan el vídeo en segundo plano)."""
    deadline = time.time() + timeout_s
    status: dict = {}
    while time.time() < deadline:
        time.sleep(interval)
        try:
            r = requests.get(f"{API}/uploadposts/status", headers=headers,
                             params={"request_id": request_id}, timeout=60)
            status = r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  estado: error consultando ({e}), reintento")
            continue
        state = str(status.get("status", "")).lower()
        print(f"  estado: {state or json.dumps(status, ensure_ascii=False)[:300]}")
        if state in {"completed", "failed", "not_found"}:
            break
    for res in status.get("results") or []:
        ok = "OK " if res.get("success") else "ERROR"
        print(f"  [{ok}] {res.get('platform')}: {res.get('post_url') or res.get('message') or ''}")
    return status


def failed_platforms(result: dict) -> list[str]:
    status = result.get("final_status") or {}
    if status and str(status.get("status")).lower() not in {"completed", "scheduled"}:
        return [str(status.get("status"))]
    return [r.get("platform", "?") for r in status.get("results") or [] if not r.get("success")]


_METRICS = {"views": ("views", "view_count", "video_views", "plays", "play_count", "impressions", "reach"),
            "likes": ("likes", "like_count", "likes_count"),
            "comments": ("comments", "comment_count", "comments_count"),
            "shares": ("shares", "share_count", "shares_count")}


def _metrics(obj) -> dict:
    """Busca en la respuesta (sea cual sea su forma) visualizaciones, me gusta, comentarios y compartidos."""
    found = {k: 0 for k in _METRICS}

    def walk(o):
        if isinstance(o, dict):
            for key, val in o.items():
                kl = str(key).lower()
                for m, names in _METRICS.items():
                    if kl in names and isinstance(val, (int, float)):
                        found[m] = max(found[m], int(val))
                walk(val)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(obj)
    return found


def post_stats(request_id: str, show_raw: bool = False) -> dict | None:
    """Estadísticas de una publicación (todas sus redes): {"instagram": {"views": .., ...}, ...}."""
    headers = {"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}"}
    r = requests.get(f"{API}/uploadposts/post-analytics/{request_id}", headers=headers, timeout=60)
    if show_raw:
        print("  respuesta de ejemplo:", r.status_code, r.text[:1500])
    if r.status_code >= 400:
        return None
    data = r.json()
    out = {}
    container = data.get("platforms") or data.get("results") or data.get("analytics") or data
    if isinstance(container, dict):
        for platform in ("instagram", "youtube", "tiktok", "facebook"):
            if platform in container:
                out[platform] = _metrics(container[platform])
    elif isinstance(container, list):
        for item in container:
            if isinstance(item, dict) and item.get("platform"):
                out[str(item["platform"]).lower()] = _metrics(item)
    if not out:
        out["total"] = _metrics(data)
    return out
