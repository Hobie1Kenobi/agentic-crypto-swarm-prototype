from __future__ import annotations

import json
import os
import re
import shutil
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


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_hex_address(addr: str) -> bool:
    return bool(addr and re.fullmatch(r"0x[a-fA-F0-9]{40}", (addr or "").strip()))


def _resolve_mechx() -> dict[str, Any]:
    p = _env("OLAS_MECHX_PATH")
    if p:
        pp = Path(p)
        if pp.exists():
            return {"ok": True, "path": str(pp)}
        return {"ok": False, "path": str(pp), "reason": "OLAS_MECHX_PATH provided but file does not exist."}
    root = _root()
    candidate = root / ".venv-olas" / "Scripts" / "mechx.exe"
    if candidate.exists():
        return {"ok": True, "path": str(candidate)}
    exe = shutil.which("mechx") or shutil.which("mechx.exe")
    if exe:
        return {"ok": True, "path": exe}
    return {"ok": False, "path": None, "reason": "mechx not found in PATH or repo-local .venv-olas."}


def _eoa_address_from_key() -> str | None:
    pk = _env("OLAS_EOA_PRIVATE_KEY")
    if not pk or "your_" in pk.lower():
        return None
    try:
        from eth_account import Account
        return Account.from_key(pk).address
    except Exception:
        return None


def _check_gnosis_balance(address: str) -> dict[str, Any]:
    rpc = _env("PUBLIC_OLAS_RPC_URL") or "https://rpc.ankr.com/gnosis"
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            return {"ok": False, "balance_wei": 0, "reason": "RPC not connected", "rpc": rpc}
        bal = w3.eth.get_balance(Web3.to_checksum_address(address))
        return {"ok": True, "balance_wei": bal, "funded": bal > 0, "rpc": rpc}
    except Exception as e:
        return {"ok": False, "balance_wei": 0, "reason": str(e), "rpc": rpc}


def main() -> None:
    _load_dotenv()
    ts = int(time.time())
    private_chain_name = _env("PRIVATE_CHAIN_NAME") or _env("CHAIN_NAME") or "celo-sepolia"
    public_chain_config = _env("OLAS_CHAIN_CONFIG") or "gnosis"

    checks: dict[str, dict[str, Any]] = {}
    missing: list[str] = []

    # 1) Feature flag
    olas_enabled = _truthy(_env("OLAS_ENABLED"))
    checks["OLAS_ENABLED"] = {"ok": olas_enabled, "value": _env("OLAS_ENABLED")}
    if not olas_enabled:
        missing.append("OLAS_ENABLED (set to 1/true/yes/on)")

    # 2) Chain config
    chain_cfg = public_chain_config.lower()
    checks["OLAS_CHAIN_CONFIG"] = {"ok": chain_cfg == "gnosis", "value": chain_cfg}
    if chain_cfg != "gnosis":
        missing.append("OLAS_CHAIN_CONFIG=gnosis")

    # 3) EOA private key
    pk = _env("OLAS_EOA_PRIVATE_KEY")
    pk_ok = bool(pk) and "your_" not in pk.lower()
    checks["OLAS_EOA_PRIVATE_KEY"] = {"ok": pk_ok, "value_present": bool(pk)}
    if not pk_ok:
        missing.append("OLAS_EOA_PRIVATE_KEY (funded EOA for gnosis)")

    # 4) Priority mech contract address
    mech_addr = _env("OLAS_PRIORITY_MECH_ADDRESS")
    mech_ok = bool(mech_addr) and _is_hex_address(mech_addr)
    checks["OLAS_PRIORITY_MECH_ADDRESS"] = {"ok": mech_ok, "value_present": bool(mech_addr), "value": mech_addr if mech_ok else None}
    if not mech_ok:
        missing.append("OLAS_PRIORITY_MECH_ADDRESS (priority mech contract address on the OLAS chain)")

    # 5) Tool
    tool = _env("OLAS_TOOL")
    tool_ok = bool(tool)
    checks["OLAS_TOOL"] = {"ok": tool_ok, "value": tool if tool_ok else None}
    if not tool_ok:
        missing.append("OLAS_TOOL (tool name string that mech-client/mechx expects)")

    # 6) mechx availability
    mechx = _resolve_mechx()
    checks["MECHX_EXECUTABLE"] = mechx
    if not mechx["ok"]:
        missing.append("mechx executable (install via npm run olas:install or set OLAS_MECHX_PATH)")

    eoa_address = _eoa_address_from_key() if pk_ok else None
    if eoa_address:
        root = _root()
        (root / "olas_funding_address.txt").write_text(eoa_address + "\n", encoding="utf-8")
        funded = _check_gnosis_balance(eoa_address)
        checks["EOA_FUNDED_GNOSIS"] = {**funded, "address": eoa_address}
        if not funded.get("ok") or not funded.get("funded", False):
            missing.append("Fund EOA on Gnosis (see olas_funding_address.txt)")
    else:
        checks["EOA_FUNDED_GNOSIS"] = {"ok": False, "funded": False, "reason": "No EOA key to check"}

    ok = len(missing) == 0

    remediation: list[str] = []
    if "mechx executable" in " ".join(missing).lower():
        remediation.append("Run: `npm run olas:install` (installs mech-client into a repo-local .venv-olas).")
    if "OLAS_EOA_PRIVATE_KEY" in " ".join(missing):
        remediation.append("Fund the `OLAS_EOA_PRIVATE_KEY` EOA on the Gnosis chain for transaction gas and mech execution.")
    if "OLAS_PRIORITY_MECH_ADDRESS" in " ".join(missing):
        remediation.append("Set `OLAS_PRIORITY_MECH_ADDRESS` to the target Mech contract address for your desired tool flow.")

    report: dict[str, Any] = {
        "ok": ok,
        "ts": ts,
        "private_chain": {"name": private_chain_name},
        "public_olas_chain": {"chain_config": chain_cfg, "requirement": "gnosis"},
        "checks": checks,
        "missing": missing,
        "blockers": [],
        "remediation": remediation,
        "eoa_funding_address": eoa_address,
    }

    for m in missing:
        if m.startswith("OLAS_") or m.startswith("MECHX"):
            report["blockers"].append({"type": "missing_or_invalid_env", "item": m})
        else:
            report["blockers"].append({"type": "blocker", "detail": m})

    out_json = _root() / "olas_preflight_report.json"
    out_md = _root() / "olas_env_checklist.md"

    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md: list[str] = []
    md.append("# Olas Preflight Validation (Gnosis)")
    md.append("")
    md.append(f"- Timestamp: `{ts}`")
    md.append(f"- ok: `{ok}`")
    md.append(f"- Target: `OLAS_CHAIN_CONFIG=gnosis`")
    md.append("")

    md.append("## Checklist")
    for k, v in checks.items():
        val = v.get("value")
        present = v.get("value_present")
        status = "x" if v.get("ok") else " "
        if present is True:
            md.append(f"- [{status}] {k}: present")
        elif val is not None:
            md.append(f"- [{status}] {k}: `{val}`")
        else:
            md.append(f"- [{status}] {k}: ok={v.get('ok')}")

    md.append("")
    md.append("## Blockers / Missing")
    if missing:
        for m in missing:
            md.append(f"- {m}")
    else:
        md.append("- (none)")

    if remediation:
        md.append("")
        md.append("## Remediation Steps")
        for r in remediation:
            md.append(f"- {r}")

    out_md.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")

    # Fail fast for stage gating.
    if not ok:
        raise SystemExit(2)

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()

