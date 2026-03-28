"""
LLM-backed airdrop opportunity screening (constitution-first). No chain execution here.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

CONSTITUTION_AIRDROP = (
    "Only ethical, non-harmful analysis. No gambling, no illegal content, no sybil-style farming guidance. "
    "Do not recommend interacting with unverified contracts. Not financial advice."
)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = (str(text) or "").strip()
    try:
        out = json.loads(text)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            out = json.loads(m.group(1).strip())
            if isinstance(out, dict):
                return out
        except json.JSONDecodeError:
            pass
    raise ValueError("model did not return a JSON object")


def _llm() -> Any:
    from swarm.llm import get_llm

    return get_llm()


def _fallback_report(topic: str, context: str) -> dict[str, Any]:
    return {
        "opportunities": [
            {
                "name": "dry_run_placeholder",
                "farm_score": 50,
                "rationale": "LLM_DRY_RUN or parse fallback: replace with real scan when Ollama is available.",
                "risk_flags": ["unverified_in_demo_mode"],
                "constitution_pass": True,
            }
        ],
        "scan_summary": f"Fallback scan for topic={topic!r}. Context length={len(context):d}.",
        "notes": "Set LLM_DRY_RUN=0 and run Ollama for full JSON output.",
    }


def generate_airdrop_report(topic: str, context: str | None) -> dict[str, Any]:
    topic = (topic or "").strip() or "Upcoming ethical airdrops and testnet incentives (public info only)"
    if len(topic) > 256:
        topic = topic[:256]
    ctx = (context or "").strip()[:4000] if context else ""

    llm = _llm()
    sys = CONSTITUTION_AIRDROP + " Evaluate only high-level, publicly discussable opportunities. Output JSON only."
    human = f"""Topic / focus: {topic}

Optional user context (URLs or notes, may be empty):
{ctx}

Reply with JSON only:
{{
  "opportunities": [
    {{
      "name": "short label",
      "farm_score": <integer 0-100>,
      "rationale": "one or two sentences",
      "risk_flags": ["string"],
      "constitution_pass": true
    }}
  ],
  "scan_summary": "one paragraph",
  "notes": "optional"
}}
Use at most 5 opportunities. If nothing suitable, use an empty opportunities array and explain in scan_summary."""

    raw = ""
    try:
        resp = llm.invoke([SystemMessage(content=sys), HumanMessage(content=human)])
        raw = (getattr(resp, "content", None) or str(resp)).strip()
        data = _extract_json_object(raw)
    except Exception:
        data = _fallback_report(topic, ctx)

    opps = data.get("opportunities") or []
    if not isinstance(opps, list):
        opps = []
    normalized: list[dict[str, Any]] = []
    for item in opps[:8]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "unknown"))[:200]
        try:
            score = int(item.get("farm_score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))
        rationale = str(item.get("rationale", ""))[:800]
        risks = item.get("risk_flags") or []
        if not isinstance(risks, list):
            risks = [str(risks)]
        risks = [str(x)[:200] for x in risks[:12]]
        cp = bool(item.get("constitution_pass", True))
        normalized.append(
            {
                "name": name,
                "farm_score": score,
                "rationale": rationale,
                "risk_flags": risks,
                "constitution_pass": cp,
            }
        )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "sku_id": "airdrop-intelligence-report",
        "seller": "t54_xrpl",
        "topic": topic,
        "generated_at": ts,
        "farm_score_threshold": int(os.getenv("AIRDROP_FARM_SCORE_THRESHOLD", "75")),
        "opportunities": normalized,
        "scan_summary": str(data.get("scan_summary", ""))[:2000],
        "notes": str(data.get("notes", ""))[:1500],
        "disclaimer": (
            "Heuristic LLM screening only — not financial advice. "
            "No execution or contract interaction is performed by this endpoint. "
            "Verify all claims on-chain and with official sources."
        ),
    }
