"""
Load T54 seller SKU definitions from JSON (see config/t54_seller_skus.json).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _agents_dir() -> Path:
    return Path(__file__).resolve().parent


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_t54_seller_skus() -> list[dict[str, Any]]:
    env_path = (os.getenv("T54_SELLER_SKUS_JSON") or "").strip()
    candidates: list[Path] = []
    if env_path:
        p = Path(env_path)
        candidates.append(p)
        if not p.is_absolute():
            candidates.append(_repo_root() / env_path)
            candidates.append(_agents_dir() / env_path)
    candidates.append(_agents_dir() / "config" / "t54_seller_skus.json")

    data: dict[str, Any] | None = None
    for p in candidates:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            break
    if not data:
        raise FileNotFoundError("T54 seller SKU file not found; set T54_SELLER_SKUS_JSON or add config/t54_seller_skus.json")

    skus = data.get("skus") if isinstance(data, dict) else data
    if not isinstance(skus, list) or not skus:
        raise ValueError("t54_seller_skus.json: missing non-empty 'skus' array")

    out: list[dict[str, Any]] = []
    for row in skus:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("sku_id", "")).strip()
        path = str(row.get("path", "")).strip()
        handler = str(row.get("handler", "")).strip()
        desc = str(row.get("description", sid)).strip()
        try:
            price = int(row.get("price_drops", 0))
        except (TypeError, ValueError):
            price = 0
        if not sid or not path.startswith("/") or not handler or price <= 0:
            raise ValueError(f"invalid SKU row: {row!r}")
        out.append({
            "sku_id": sid,
            "path": path,
            "price_drops": price,
            "description": desc,
            "handler": handler,
        })
    return out
