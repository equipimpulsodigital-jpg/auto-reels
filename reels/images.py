"""Generación de imágenes 9:16 para cada plano."""
from __future__ import annotations

import io
import os
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from PIL import Image

NEGATIVE = "no text, no letters, no captions, no watermark, no logo"


def _pollinations(prompt: str, seed: int, model: str) -> Image.Image:
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
    params = {"width": 1080, "height": 1920, "seed": seed, "model": model, "nologo": "true"}
    r = requests.get(url, params=params, timeout=180)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/"):
        raise RuntimeError(f"respuesta inesperada: {r.text[:200]}")
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    # El plan gratuito añade una marca de agua abajo a la derecha: recortamos la franja inferior.
    w, h = img.size
    return img.crop((0, 0, w, int(h * 0.94)))


def _replicate(prompt: str, seed: int) -> Image.Image:
    token = os.environ["REPLICATE_API_TOKEN"]
    r = requests.post(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
        headers={"Authorization": f"Bearer {token}", "Prefer": "wait"},
        json={"input": {"prompt": prompt, "aspect_ratio": "9:16", "output_format": "jpg",
                        "seed": seed, "output_quality": 92}},
        timeout=180,
    )
    r.raise_for_status()
    out = r.json().get("output")
    if not out:
        raise RuntimeError(f"Replicate sin imagen: {r.text[:300]}")
    img_bytes = requests.get(out[0] if isinstance(out, list) else out, timeout=120).content
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")


def generate_image(prompt: str, style: str, out: Path, seed: int, cfg: dict) -> Optional[Path]:
    full = f"{prompt}. {style}. {NEGATIVE}"
    provider = cfg["images"].get("provider", "pollinations")
    if provider == "replicate" and not os.environ.get("REPLICATE_API_TOKEN"):
        print("  (sin REPLICATE_API_TOKEN: uso Pollinations)")
        provider = "pollinations"
    for attempt in range(4):
        try:
            if provider == "replicate":
                img = _replicate(full, seed)
            else:
                img = _pollinations(full, seed, cfg["images"].get("pollinations_model", "flux"))
            img.save(out, quality=95)
            return out
        except Exception as e:  # red, límites de uso, etc.
            wait = 20 * (attempt + 1)
            print(f"  imagen: error ({e}); reintento en {wait}s")
            time.sleep(wait)
    return None
