"""Optional probe middleware for paid intake-resale routes."""
from __future__ import annotations

from typing import Callable


def create_intake_resale_probe_middleware():
    async def middleware(request, call_next: Callable):
        return await call_next(request)

    return middleware
