from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_hex_address(addr: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", (addr or "").strip()))


def _load_dotenv() -> None:
    root = _root()
    env_path = root / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
        except Exception:
            pass


def _resolve_mechx() -> dict[str, Any]:
    p = _env("OLAS_MECHX_PATH")
    if p:
        pp = Path(p)
        if pp.exists():
            return {"ok": True, "path": str(pp.resolve())}
        return {"ok": False, "path": str(pp), "reason": "OLAS_MECHX_PATH file does not exist."}
    root = _root()
    candidate = root / ".venv-olas" / "Scripts" / "mechx.exe"
    if candidate.exists():
        return {"ok": True, "path": str(candidate)}
    exe = shutil.which("mechx") or shutil.which("mechx.exe")
    if exe:
        return {"ok": True, "path": exe}
    return {"ok": False, "path": None, "reason": "mechx not found. Run: npm run olas:install"}


def _install_mechx() -> bool:
    root = _root()
    ps_script = root / "scripts" / "install-olas-mech-client.ps1"
    if not ps_script.exists():
        return False
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception:
        return False
    return _resolve_mechx().get("ok", False)


def _get_olas_eoa_address() -> tuple[str | None, str | None]:
    pk = _env("OLAS_EOA_PRIVATE_KEY")
    if not pk or "your_" in pk.lower():
        return None, None
    try:
        from eth_account import Account
        addr = Account.from_key(pk).address
        return addr, pk
    except Exception:
        return None, None


def _generate_olas_eoa() -> tuple[str, str]:
    from eth_account import Account
    from eth_account.signers.local import LocalAccount
    acc: LocalAccount = Account.create()
    return acc.address, acc.key.hex()


def _check_gnosis_balance(address: str) -> tuple[bool, int, str]:
    rpc = _env("PUBLIC_OLAS_RPC_URL") or "https://rpc.ankr.com/gnosis"
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            return False, 0, "RPC not connected"
        bal = w3.eth.get_balance(Web3.to_checksum_address(address))
        return True, bal, rpc
    except Exception as e:
        return False, 0, str(e)


def main() -> int:
    _load_dotenv()
    root = _root()
    ts = int(time.time())

    checklist: dict[str, Any] = {}
    missing_vars: list[str] = []
    address_to_fund: str | None = None
    generated_key: str | None = None

    mechx = _resolve_mechx()
    if not mechx["ok"]:
        checklist["MECHX_EXECUTABLE"] = {"ok": False, "reason": mechx.get("reason"), "action": "Run: npm run olas:install"}
        print("mechx not found; attempting install via npm run olas:install ...")
        if _install_mechx():
            mechx = _resolve_mechx()
            checklist["MECHX_EXECUTABLE"] = {"ok": True, "path": mechx.get("path"), "action": "Installed."}
        else:
            checklist["MECHX_EXECUTABLE"] = {"ok": False, "reason": "Install failed or still not found.", "action": "Run: npm run olas:install"}
            missing_vars.append("MECHX_EXECUTABLE (install mechx)")
    else:
        checklist["MECHX_EXECUTABLE"] = {"ok": True, "path": mechx.get("path")}

    olas_enabled = _truthy(_env("OLAS_ENABLED"))
    checklist["OLAS_ENABLED"] = {"ok": olas_enabled, "value": _env("OLAS_ENABLED") or "(not set)"}
    if not olas_enabled:
        missing_vars.append("OLAS_ENABLED=1")

    chain_cfg = _env("OLAS_CHAIN_CONFIG", "gnosis").lower()
    checklist["OLAS_CHAIN_CONFIG"] = {"ok": chain_cfg == "gnosis", "value": chain_cfg}
    if chain_cfg != "gnosis":
        missing_vars.append("OLAS_CHAIN_CONFIG=gnosis")

    eoa_addr, eoa_pk = _get_olas_eoa_address()
    if not eoa_addr:
        eoa_addr, generated_key = _generate_olas_eoa()
        checklist["OLAS_EOA_PRIVATE_KEY"] = {
            "ok": False,
            "action": "Add the generated key to .env (see below) and fund the address in olas_funding_address.txt",
            "generated_address": eoa_addr,
        }
        missing_vars.append("OLAS_EOA_PRIVATE_KEY")
        address_to_fund = eoa_addr
    else:
        checklist["OLAS_EOA_PRIVATE_KEY"] = {"ok": True, "address": eoa_addr}
        address_to_fund = eoa_addr

    mech_addr = _env("OLAS_PRIORITY_MECH_ADDRESS")
    mech_ok = bool(mech_addr) and _is_hex_address(mech_addr)
    checklist["OLAS_PRIORITY_MECH_ADDRESS"] = {"ok": mech_ok, "value": mech_addr if mech_ok else None}
    if not mech_ok:
        missing_vars.append("OLAS_PRIORITY_MECH_ADDRESS")

    tool = _env("OLAS_TOOL")
    tool_ok = bool(tool)
    checklist["OLAS_TOOL"] = {"ok": tool_ok, "value": tool or None}
    if not tool_ok:
        missing_vars.append("OLAS_TOOL")

    funded_ok = False
    balance_wei = 0
    if address_to_fund:
        funded_ok, balance_wei, balance_note = _check_gnosis_balance(address_to_fund)
        checklist["EOA_FUNDED_GNOSIS"] = {
            "ok": funded_ok,
            "address": address_to_fund,
            "balance_wei": balance_wei,
            "balance_note": balance_note,
        }
        if not funded_ok or balance_wei == 0:
            missing_vars.append("Fund EOA on Gnosis (see olas_funding_address.txt)")

    (root / "olas_funding_address.txt").write_text(
        (address_to_fund or "NOT_SET") + "\n",
        encoding="utf-8",
    )

    config_complete = (
        checklist.get("OLAS_ENABLED", {}).get("ok")
        and checklist.get("OLAS_CHAIN_CONFIG", {}).get("ok")
        and checklist.get("OLAS_EOA_PRIVATE_KEY", {}).get("ok")
        and checklist.get("OLAS_PRIORITY_MECH_ADDRESS", {}).get("ok")
        and checklist.get("OLAS_TOOL", {}).get("ok")
        and checklist.get("MECHX_EXECUTABLE", {}).get("ok")
        and checklist.get("EOA_FUNDED_GNOSIS", {}).get("ok")
        and (checklist.get("EOA_FUNDED_GNOSIS", {}).get("balance_wei", 0) > 0)
    )

    md_lines = [
        "# Olas activation checklist",
        "",
        f"- Timestamp: `{ts}`",
        f"- Config complete (ready for live request): `{config_complete}`",
        "",
        "## What is missing",
        "",
    ]
    if missing_vars:
        for m in missing_vars:
            md_lines.append(f"- {m}")
    else:
        md_lines.append("- (nothing)")
    md_lines.append("")
    md_lines.append("## Address to fund (Gnosis)")
    md_lines.append("")
    md_lines.append(f"Fund this EOA on Gnosis with xDAI for gas and mech execution:")
    md_lines.append("")
    md_lines.append(f"```")
    md_lines.append(address_to_fund or "NOT_SET")
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("(Also written to `olas_funding_address.txt`.)")
    md_lines.append("")
    md_lines.append("## Variables still needing values")
    md_lines.append("")
    for k in ["OLAS_ENABLED", "OLAS_CHAIN_CONFIG", "OLAS_EOA_PRIVATE_KEY", "OLAS_PRIORITY_MECH_ADDRESS", "OLAS_TOOL", "OLAS_MECHX_PATH"]:
        v = checklist.get(k) or {}
        ok = v.get("ok", False)
        if not ok:
            md_lines.append(f"- **{k}**: set in `.env`")
            if k == "OLAS_EOA_PRIVATE_KEY" and generated_key:
                md_lines.append("  - (Generated key was printed to stdout; add it to .env and do not commit.)")
    md_lines.append("")
    md_lines.append("## Checklist detail")
    md_lines.append("")
    for k, v in checklist.items():
        ok = v.get("ok", False)
        status = "[x]" if ok else "[ ]"
        md_lines.append(f"- {status} **{k}**: {json.dumps(v)}")
    md_lines.append("")

    (root / "olas_activation_checklist.md").write_text("\n".join(md_lines), encoding="utf-8")

    if config_complete:
        try:
            subprocess.run(
                [sys.executable, str(root / "scripts" / "olas_preflight_validate.py")],
                cwd=str(root),
                timeout=30,
            )
        except (subprocess.TimeoutExpired, Exception):
            pass

    if generated_key:
        print("Generated new Gnosis EOA for Olas. Add to .env:")
        print(f"OLAS_EOA_PRIVATE_KEY={generated_key}")
        print("Then fund the address in olas_funding_address.txt on Gnosis (xDAI).")
    print("Wrote olas_activation_checklist.md")
    print("Wrote olas_funding_address.txt")
    return 0 if config_complete else 1


if __name__ == "__main__":
    sys.exit(main())
