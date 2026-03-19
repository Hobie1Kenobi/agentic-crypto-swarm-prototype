from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env_path = _root() / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
    except Exception:
        pass


def _env_snapshot(keys: list[str]) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for k in keys:
        v = os.getenv(k)
        if v is None:
            snap[k] = None
        elif "PRIVATE_KEY" in k:
            snap[k] = "***set***" if v.strip() else ""
        else:
            snap[k] = v
    return snap


def main() -> None:
    _load_dotenv()
    # Force a live attempt (will still fail cleanly if required config/creds are missing).
    os.environ["OLAS_ENABLED"] = "1"
    os.environ.setdefault("OLAS_CHAIN_CONFIG", "gnosis")

    prompt = os.getenv("OLAS_TEST_PROMPT", "Ping: hybrid demo live Olas attempt.").strip()

    started = time.time()
    outcome: dict[str, Any] = {
        "ts": int(started),
        "ok": False,
        "boundary": "real_external_integration",
        "prompt": prompt,
        "env": _env_snapshot(
            [
                "OLAS_ENABLED",
                "OLAS_CHAIN_CONFIG",
                "OLAS_PRIORITY_MECH_ADDRESS",
                "OLAS_TOOL",
                "OLAS_EOA_PRIVATE_KEY",
                "OLAS_MECHX_PATH",
                "MARKET_MODE",
            ]
        ),
        "result": None,
        "blocker": None,
    }

    try:
        from packages.agents.services.olas_adapter import send_olas_mech_request  # type: ignore
    except Exception:
        # When run from repo root, imports should resolve via PYTHONPATH only if configured.
        # Fall back to a direct relative import style by adjusting sys.path.
        import sys

        sys.path.insert(0, str((_root() / "packages" / "agents").resolve()))
        from services.olas_adapter import send_olas_mech_request  # type: ignore

    res = send_olas_mech_request(prompt)
    outcome["result"] = {
        "ok": bool(getattr(res, "ok", False)),
        "boundary": getattr(res, "boundary", None),
        "request_id": getattr(res, "request_id", None),
        "tx_hash": getattr(res, "tx_hash", None),
        "mech_address": os.getenv("OLAS_PRIORITY_MECH_ADDRESS"),
        "tool": getattr(res, "tool", None) or os.getenv("OLAS_TOOL"),
        "response": getattr(res, "result", None),
        "error": getattr(res, "error", None),
        "raw": getattr(res, "raw", None),
    }
    outcome["ok"] = bool(outcome["result"]["ok"])
    outcome["boundary"] = str(outcome["result"]["boundary"] or "unknown")

    if not outcome["ok"]:
        err = str(outcome["result"].get("error") or "")
        missing: list[str] = []
        for k in ["OLAS_CHAIN_CONFIG", "OLAS_PRIORITY_MECH_ADDRESS", "OLAS_TOOL", "OLAS_EOA_PRIVATE_KEY"]:
            if not (os.getenv(k) or "").strip():
                missing.append(k)
        if missing:
            outcome["blocker"] = {"type": "missing_credentials_or_config", "missing": missing, "detail": err}
        elif "mechx" in err.lower() and ("not found" in err.lower() or "path" in err.lower()):
            outcome["blocker"] = {"type": "package_or_tool_limitation", "detail": err}
        else:
            outcome["blocker"] = {"type": "rpc_or_wallet_issue", "detail": err}

    root = _root()
    (root / "olas_live_attempt_report.json").write_text(json.dumps(outcome, indent=2), encoding="utf-8")

    md: list[str] = []
    md.append("# Olas Live Attempt Report")
    md.append("")
    md.append("## Attempt summary")
    md.append(f"- ok: `{outcome['ok']}`")
    md.append(f"- boundary: `{outcome['boundary']}`")
    md.append(f"- ts: `{outcome['ts']}`")
    md.append("")
    md.append("## Environment readiness (redacted)")
    for k, v in outcome["env"].items():
        md.append(f"- {k}: `{v}`")
    md.append("")
    md.append("## Result")
    r = outcome["result"] or {}
    md.append(f"- request_id: `{r.get('request_id')}`")
    md.append(f"- tx_hash: `{r.get('tx_hash')}`")
    md.append(f"- mech_address: `{r.get('mech_address')}`")
    md.append(f"- tool: `{r.get('tool')}`")
    md.append(f"- response/result: `{r.get('response') or '(none)'}`")
    md.append(f"- error: `{(r.get('error') or '')}`")
    md.append("")
    md.append("## Blocker (if any)")
    md.append("```json")
    md.append(json.dumps(outcome["blocker"], indent=2))
    md.append("```")
    md.append("")
    md.append("## Boundary guarantees")
    md.append("- `real_external_integration`: only if `ok=true` and we have a real request id / tx hash from `mechx`.")
    md.append("- otherwise this report is an explicit failed attempt with the blocker categorized.")
    md.append("")

    (root / "olas_live_attempt_report.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {root / 'olas_live_attempt_report.md'}")


if __name__ == "__main__":
    main()

