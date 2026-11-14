"""Publicación en TikTok, Instagram Reels y YouTube Shorts mediante la API de Upload-Post."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from .config import env
from .script import Script

API = "https://api.upload-post.com/api"


def _caption(script: Script) -> str:
    tags = " ".join("#" + t.lstrip("#").replace(" ", "") for t in script.hashtags)
    return f"{script.caption}\n\n{tags}".strip()


def publish(video: Path, script: Script, cfg: dict, idempotency_key: str) -> dict:
    pcfg = cfg["publish"]
    platforms = pcfg["platforms"]
    ai = "true" if pcfg.get("label_as_ai", True) else "false"
    caption = _caption(script)

    fields: list[tuple[str, str]] = [("user", env("UPLOAD_POST_USER")), ("title", script.youtube_title[:100])]
    fields += [("platform[]", p) for p in platforms]
    fields += [("async_upload", "true"), ("external_id", idempotency_key)]
    if "tiktok" in platforms:
        fields += [("tiktok_title", caption[:2200]), ("is_aigc", ai)]
    if "instagram" in platforms:
        fields += [("instagram_title", caption[:2200]), ("media_type", "REELS"),
                   ("share_to_feed", "true"), ("is_ai_generated", ai)]
    if "youtube" in platforms:
        desc = f"{script.youtube_description}\n\n{caption}"
        fields += [("youtube_title", script.youtube_title[:100]), ("youtube_description", desc[:5000]),
                   ("privacyStatus", pcfg.get("youtube_privacy", "public")),
                   ("selfDeclaredMadeForKids", "false"), ("containsSyntheticMedia", ai)]
        fields += [("tags[]", t.lstrip("#")) for t in script.hashtags]

    headers = {"Authorization": f"Apikey {env('UPLOAD_POST_API_KEY')}", "Idempotency-Key": idempotency_key}
    with open(video, "rb") as f:
        r = requests.post(f"{API}/upload", headers=headers, data=fields,
                          files={"video": (video.name, f, "video/mp4")}, timeout=600)
    if r.status_code >= 400:
        raise RuntimeError(f"Upload-Post respondió {r.status_code}: {r.text[:2000]}")
    result = r.json()
    print("  Upload-Post:", json.dumps(result, ensure_ascii=False)[:1500])

    request_id = result.get("request_id")
    if request_id:
        result["final_status"] = wait_for_status(request_id, headers)
    return result


def wait_for_status(request_id: str, headers: dict, timeout_s: int = 900) -> dict:
    """Consulta el estado hasta que termina (TikTok e Instagram procesan el vídeo en segundo plano)."""
    deadline = time.time() + timeout_s
    status: dict = {}
    while time.time() < deadline:
        time.sleep(20)
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
    if status and str(status.get("status")).lower() != "completed":
        return [str(status.get("status"))]
    return [r.get("platform", "?") for r in status.get("results") or [] if not r.get("success")]
