from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
OUT = ROOT / "out"
CACHE = ROOT / ".cache"


def load_config(channel: str | None = None, path: Path | None = None) -> dict:
    """Configuración general + la del canal elegido en cfg["channel"] (por defecto, el primero)."""
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    channels = cfg.get("channels") or {}
    if channels:
        cid = channel or next(iter(channels))
        if cid not in channels:
            raise SystemExit(f"Canal desconocido: {cid}. Canales: {', '.join(channels)}")
        cfg["channel"] = {"id": cid, **channels[cid]}
        nar = channels[cid].get("narrator") or {}  # voz del narrador propia de la marca
        for k_src, k_dst in (("voice", "edge_voice"), ("rate", "edge_rate"), ("pitch", "edge_pitch")):
            if nar.get(k_src):
                cfg["voice"][k_dst] = nar[k_src]
    return cfg


def channel_data(cfg: dict) -> Path:
    """Carpeta con el historial y las partes pendientes del canal."""
    return DATA / cfg["channel"]["id"]


def env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        raise SystemExit(f"Falta la variable de entorno {name}. Revisa el README (sección Secrets).")
    return value
