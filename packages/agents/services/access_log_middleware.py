"""
Optional JSONL access log for seller APIs. Enable with SELLER_ACCESS_LOG=/path/to/file.log
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def attach_access_log(app, service_name: str) -> None:
    path = (os.getenv("SELLER_ACCESS_LOG") or "").strip()
    if not path:
        return
    log_file = Path(path)

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
