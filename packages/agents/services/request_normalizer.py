from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedTask:
    # Internal task model for our orchestration / private marketplace.
    query: str
    task_metadata: str
    worker_metadata: str = "swarm-worker-1"
    # External correlation fields (optional)
    external_source: str | None = None
    external_request_id: str | None = None
    external_tool: str | None = None
    external_chain: str | None = None


def normalize_olas_request(payload: dict[str, Any]) -> NormalizedTask:
    """
    Normalize a Mech/Olas-style request payload into our internal task model.

    Expected payload shape (flexible):
    - prompt: str (or prompts[0])
    - tool: str (or tools[0])
    - request_id / requestId / correlation_id: str|int
    """
    prompt = (payload.get("prompt") or "").strip()
    if not prompt and isinstance(payload.get("prompts"), list) and payload["prompts"]:
        prompt = str(payload["prompts"][0]).strip()
    tool = (payload.get("tool") or "").strip()
    if not tool and isinstance(payload.get("tools"), list) and payload["tools"]:
        tool = str(payload["tools"][0]).strip()

    req_id = payload.get("request_id") or payload.get("requestId") or payload.get("correlation_id") or payload.get("id")
    req_id_s = str(req_id) if req_id is not None else None

    # Keep metadata short; it will be stored onchain in our private marketplace.
    task_metadata = f"public_adapter:olas:{tool or 'unknown'}"

    return NormalizedTask(
        query=prompt or "Empty prompt.",
        task_metadata=task_metadata[:256],
        external_source="olas",
        external_request_id=req_id_s,
        external_tool=tool or None,
        external_chain=str(payload.get("chain") or payload.get("chain_config") or "") or None,
    )

