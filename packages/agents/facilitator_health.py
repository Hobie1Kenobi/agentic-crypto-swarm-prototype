"""x402 facilitator reachability probe for api_seller_x402."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx

_LOG = logging.getLogger("facilitator_health")


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


class FacilitatorMonitor:
    def __init__(self, facilitator_url: str, *, disable_env: str = "X402_FACILITATOR_HEALTH_DISABLE") -> None:
        self._url = (facilitator_url or "").rstrip("/")
        self._disable_env = disable_env
        self._ok = True

    def _disabled(self) -> bool:
        return _truthy(self._disable_env)

    async def _probe(self) -> bool:
        if self._disabled() or not self._url:
            return True
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                for path in ("/health", "/"):
                    try:
                        r = await client.get(f"{self._url}{path}")
                        if r.status_code < 500:
                            return True
                    except Exception:
                        continue
        except Exception as exc:
            _LOG.warning("facilitator probe failed %s: %s", self._url, exc)
        return False

    def is_ok(self) -> bool:
        if self._disabled():
            return True
        return self._ok

    def make_lifespan(self):
        monitor = self

        @asynccontextmanager
        async def _lifespan(app: Any):
            if not monitor._disabled():
                monitor._ok = await monitor._probe()
                if not monitor._ok:
                    _LOG.error("facilitator unhealthy at startup: %s", monitor._url)

                async def _loop() -> None:
                    while True:
                        await asyncio.sleep(60)
                        monitor._ok = await monitor._probe()

                task = asyncio.create_task(_loop())
            else:
                task = None
            try:
                yield
            finally:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        return _lifespan
