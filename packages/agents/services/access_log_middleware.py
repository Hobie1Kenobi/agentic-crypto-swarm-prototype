"""
JSONL access log for seller APIs.

Writes logs/seller-access.jsonl unless SELLER_ACCESS_LOG is set.
Set SELLER_ACCESS_LOG=0 to disable.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def access_log_path() -> Path | None:
    raw = (os.getenv("SELLER_ACCESS_LOG") or "").strip()
    if raw.lower() in {"0", "off", "false", "no"}:
        return None
    if not raw or raw.lower() in {"1", "true", "yes"}:
        return _repo_root() / "logs" / "seller-access.jsonl"
    path = Path(raw)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def attach_access_log(app, service_name: str) -> None:
    log_file = access_log_path()
    if log_file is None:
        return

    @app.middleware("http")
    async def _access_log(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        line = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": service_name,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query)[:500],
            "client": request.client.host if request.client else None,
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
        }
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line) + "\n")
        except OSError:
            pass
        return response
