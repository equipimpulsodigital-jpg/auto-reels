"""Busca y descarga clips verticales gratuitos de Pexels."""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Optional

import requests

from .config import CACHE

FALLBACK_QUERIES = ["padel", "padel court", "tennis court", "racket sport"]


class Footage:
    def __init__(self) -> None:
        self.key = os.environ.get("PEXELS_API_KEY", "").strip()
        self.used: set[int] = set()
        (CACHE / "pexels").mkdir(parents=True, exist_ok=True)

    def _search(self, query: str) -> list[dict]:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": self.key},
            params={"query": query, "orientation": "portrait", "per_page": 30, "size": "medium"},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("videos", [])

    @staticmethod
    def _best_file(video: dict) -> Optional[dict]:
        files = [
            f for f in video.get("video_files", [])
            if f.get("width") and f.get("height") and f["height"] > f["width"] and f.get("file_type") == "video/mp4"
        ]
        if not files:
            return None
        # el más cercano a 1080 de ancho, sin pasarse mucho (para no descargar 4K)
        return min(files, key=lambda f: abs(f["width"] - 1080) + (2000 if f["width"] > 2200 else 0))

    def clip_for(self, query: str, min_seconds: float) -> Optional[Path]:
        if not self.key:
            return None
        for q in [query, *FALLBACK_QUERIES]:
            try:
                videos = self._search(q)
            except requests.RequestException as e:
                print(f"  Pexels: error buscando '{q}': {e}")
                continue
            random.shuffle(videos)
            for v in videos:
                if v["id"] in self.used or v.get("duration", 0) < min(min_seconds, 4):
                    continue
                f = self._best_file(v)
                if not f:
                    continue
                path = CACHE / "pexels" / f"{v['id']}_{f['width']}.mp4"
                if not path.exists():
                    with requests.get(f["link"], stream=True, timeout=120) as r:
                        r.raise_for_status()
                        with open(path, "wb") as out:
                            for chunk in r.iter_content(1 << 20):
                                out.write(chunk)
                self.used.add(v["id"])
                print(f"  clip '{q}' -> pexels #{v['id']} ({f['width']}x{f['height']})")
                return path
        return None
