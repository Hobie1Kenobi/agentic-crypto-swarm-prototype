"""Background polling for contract-monitor subscriptions (10-minute cadence)."""
from __future__ import annotations

import asyncio
import logging
import time

import requests

_LOG = logging.getLogger("contract_monitor_worker")


def _post_webhook(url: str, payload: dict) -> None:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    try:
        import sys
        from pathlib import Path

        agents = Path(__file__).resolve().parents[2] / "packages" / "agents"
        if str(agents) not in sys.path:
            sys.path.insert(0, str(agents))
        from integrations.marketplace.contract_monitor_webhook import webhook_headers

        headers.update(webhook_headers())
    except Exception:
        pass
    requests.post(url, json=payload, headers=headers, timeout=15)


async def run_contract_monitor_worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            from marketplace.skus.contract_monitor_store import list_active
        except Exception:
            await asyncio.sleep(60)
            continue
        try:
            subs = list_active()
            for s in subs:
                try:
                    _post_webhook(
                        s.webhook_url,
                        {
                            "event": "monitor_tick",
                            "subscriptionId": s.id,
                            "addresses": s.addresses,
                            "ts": time.time(),
                            "note": "Placeholder tick; extend with Blockscout admin txs + DexScreener + Slither",
                        },
                    )
                except Exception as e:
                    _LOG.debug("monitor webhook: %s", e)
        except Exception as e:
            _LOG.warning("monitor_tick_err %s", e)
        try:
            await asyncio.wait_for(stop.wait(), timeout=600.0)
        except asyncio.TimeoutError:
            pass
