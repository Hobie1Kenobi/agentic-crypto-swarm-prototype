"""
Smart contract audit SKUs (Tier 1–3) for Base x402 seller.
Uses Blockscout/Etherscan-style APIs, optional Slither CLI, and repo audit artifacts.
"""
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

import requests

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_AGENTS = _REPO_ROOT / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

# Phase 6 counterparty intel (sc-audit) — encoded as Tier 1 detection signals for every screen.
PHASE6_KNOWN_EIP7702_DELEGATE = "0x63c0c19a282a1B52b07dD5a65b58948A07DAE32B".lower()
PHASE6_SNOT_OPERATOR_DEPLOYER = "0xb0d315A17c2A17dFBA0c67D53Ed91a247242dDc2".lower()

BRAND_TERMS = (
    "vanguard",
    "blackrock",
    "reserve",
    "federal",
    "trump",
    "official",
    "airdrop",
)
HOT_DETECTORS = (
    "reentrancy-eth",
    "arbitrary-send-erc20",
    "suicidal",
    "controlled-delegatecall",
    "tx-origin",
    "weak-prng",
)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _blockscout_base(chain_id: str) -> str:
    if chain_id in ("eip155:8453", "8453"):
        return _env("BLOCKSCOUT_BASE_URL", "https://base.blockscout.com").rstrip("/")
    if chain_id in ("eip155:1", "1"):
        return "https://eth.blockscout.com"
    return _env("BLOCKSCOUT_BASE_URL", "https://base.blockscout.com").rstrip("/")


def _etherscan_compatible_source(chain_id: str, address: str) -> tuple[bool, str, str, str]:
    """Return (verified, source_concat, reason_if_empty, contract_name)."""
    addr = address.strip()
    if not addr.startswith("0x") or len(addr) != 42:
        return False, "", "invalid_address", ""
    base = _blockscout_base(chain_id)
    url = f"{base}/api?module=contract&action=getsourcecode&address={addr}"
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        return False, "", f"fetch_error:{e}", ""
    res = j.get("result")
    if isinstance(res, list) and res:
        row = res[0]
    elif isinstance(res, dict):
        row = res
    else:
        return False, "", "no_result", ""
    src = (row.get("SourceCode") or "").strip()
    name = (row.get("ContractName") or "").strip()
    if not src or src == "":
        return False, "", "unverified", name
    return True, f"{name}\n{src}", "ok", name


def _run_slither_json_on_source(source: str, timeout_sec: int = 25) -> dict[str, Any] | None:
    if not source.strip() or source.strip().startswith("{"):
        return None
    slither = shutil.which("slither")
    if not slither:
        return None
    import tempfile

    try:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "contracts"
            p.mkdir()
            (p / "Triage.sol").write_text(source[:400000], encoding="utf-8")
            proc = subprocess.run(
                [
                    slither,
                    str(d),
                    "--json",
                    "-",
                    "--exclude-dependencies",
                    "--exclude-optimization",
                ],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            if proc.stdout:
                return json.loads(proc.stdout)
    except Exception:
        return None
    return None


def _brand_flags(text: str) -> list[str]:
    low = text.lower()
    out: list[str] = []
    for t in BRAND_TERMS:
        if t in low:
            out.append(f"brand:{t}")
    return out


def _count_slither_severity(slither_json: dict[str, Any] | None) -> tuple[int, int, list[str]]:
    if not slither_json:
        return 0, 0, []
    highs = 0
    meds = 0
    flags: list[str] = []
    detectors = slither_json.get("results", {}).get("detectors", [])
    for d in detectors:
        check = (d.get("check") or "").lower()
        impact = (d.get("impact") or "").lower()
        if impact == "high":
            highs += 1
        elif impact == "medium":
            meds += 1
        if check in HOT_DETECTORS or any(h in check for h in HOT_DETECTORS):
            flags.append(f"slither:{check}")
    return highs, meds, flags


def _risk_from_counts(high: int, med: int, brand: list[str], verified: bool) -> tuple[int, str]:
    if not verified:
        return 95, "MALICIOUS"
    score = min(100, high * 25 + med * 8 + len(brand) * 5)
    if score >= 70:
        return score, "MALICIOUS"
    if score >= 35 or brand:
        return score, "SUSPICIOUS"
    return score, "SAFE"


def _contract_creator_address(chain_id: str, address: str) -> str | None:
    addr = address.strip()
    if not addr.startswith("0x") or len(addr) != 42:
        return None
    base = _blockscout_base(chain_id)
    url = f"{base}/api?module=contract&action=getcontractcreation&contractaddresses={addr}"
    try:
        r = requests.get(url, timeout=18)
        r.raise_for_status()
        j = r.json()
    except Exception:
        return None
    res = j.get("result")
    rows = res if isinstance(res, list) else [res] if isinstance(res, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c = (row.get("contractCreator") or row.get("contract_creator") or "").strip()
        if c.startswith("0x") and len(c) == 42:
            return c
    return None


def _phase6_triage_intel(
    contract_address: str,
    chain_id: str,
    contract_name: str,
    verified: bool,
) -> tuple[list[str], dict[str, Any]]:
    """Signals from Phase 6 report: EIP-7702 delegate, SNOT name, known operator deployer."""
    flags: list[str] = []
    probe = _code_delegate_probe(contract_address, chain_id)
    del_addr = (probe.get("eip7702Delegate") or "").strip()
    del_l = del_addr.lower() if del_addr.startswith("0x") else ""
    known_delegate = bool(del_l and del_l == PHASE6_KNOWN_EIP7702_DELEGATE)
    if known_delegate:
        flags.append("phase6_intel:known_eip7702_delegate:EIP7702StatelessDeleGator")
    elif del_l and len(del_l) == 42:
        flags.append("phase6_intel:eip7702_delegate_present")

    cnl = (contract_name or "").lower()
    snot_name = "snot" in cnl or "snot by virtuals" in cnl
    if snot_name:
        flags.append("phase6_intel:snot_token_name_pattern")

    creator: str | None = None
    deployer_match = False
    if verified:
        creator = _contract_creator_address(chain_id, contract_address)
        if creator and creator.lower() == PHASE6_SNOT_OPERATOR_DEPLOYER:
            deployer_match = True
            flags.append("phase6_intel:deployer_matches_phase6_snot_operator_wallet")

    intel = {
        "eip7702Delegate": del_addr or None,
        "bytecodeLen": probe.get("bytecode_len"),
        "knownDelegateMatch": known_delegate,
        "snotNamePattern": snot_name,
        "contractCreator": creator,
        "deployerMatchesPhase6SnotOperator": deployer_match,
    }
    return flags, intel


def _apply_phase6_score_bump(score: int, phase6_flags: list[str]) -> int:
    bump = 0
    for f in phase6_flags:
        if "known_eip7702_delegate" in f:
            bump += 18
        elif "eip7702_delegate_present" in f:
            bump += 8
    for f in phase6_flags:
        if "snot_token_name_pattern" in f:
            bump += 12
        if "deployer_matches_phase6" in f:
            bump += 15
    return min(100, score + bump)


def triage_contract(contract_address: str, chain_id: str = "eip155:8453") -> dict[str, Any]:
    t0 = time.time()
    verified, source, reason, cname = _etherscan_compatible_source(chain_id, contract_address)
    p6_flags, phase6_intel = _phase6_triage_intel(contract_address, chain_id, cname, verified)

    if not verified:
        top = list(dict.fromkeys(["unverified_source"] + p6_flags))[:14]
        return {
            "riskScore": min(100, 95 + (5 if p6_flags else 0)),
            "verdict": "MALICIOUS",
            "topFlags": top,
            "verified": False,
            "slitherHighCount": 0,
            "slitherMedCount": 0,
            "completedIn": int((time.time() - t0) * 1000),
            "reason": reason,
            "phase6Intel": phase6_intel,
        }
    brands = _brand_flags(source)
    sj = _run_slither_json_on_source(source, timeout_sec=25)
    hi, md, sflags = _count_slither_severity(sj)
    flags = list(dict.fromkeys(brands + sflags + p6_flags))[:14]
    score, verdict = _risk_from_counts(hi, md, brands, True)
    score = _apply_phase6_score_bump(score, p6_flags)
    if score >= 70:
        verdict = "MALICIOUS"
    elif score >= 35 or brands or p6_flags:
        verdict = "SUSPICIOUS" if verdict == "SAFE" else verdict

    return {
        "riskScore": score,
        "verdict": verdict,
        "topFlags": flags,
        "verified": True,
        "slitherHighCount": hi,
        "slitherMedCount": md,
        "completedIn": int((time.time() - t0) * 1000),
        "phase6Intel": phase6_intel,
    }


def _eip7702_delegate_from_code(code: bytes) -> str | None:
    if len(code) == 23 and code[:3] == b"\xef\x01\x00":
        return "0x" + code[3:23].hex()
    return None


def _rpc_url(chain_id: str) -> str:
    if chain_id in ("eip155:8453", "8453"):
        return _env("RPC_URL_BASE", "https://mainnet.base.org")
    if chain_id in ("eip155:1", "1"):
        return _env("RPC_URL_ETH", "https://eth.llamarpc.com")
    return _env("RPC_URL_BASE", "https://mainnet.base.org")


def _code_delegate_probe(address: str, chain_id: str) -> dict[str, Any]:
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(_rpc_url(chain_id)))
        ch = w3.eth.get_code(Web3.to_checksum_address(address))
        del_addr = _eip7702_delegate_from_code(ch)
        return {"bytecode_len": len(ch), "eip7702Delegate": del_addr}
    except Exception as e:
        return {"error": str(e)[:200]}


def _load_audit_v2_excerpt() -> str | None:
    p = _REPO_ROOT / "sc-audit" / "reports" / "audit_report_v2.md"
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8", errors="replace")[:120000]


def deep_audit(contract_addresses: list[str], chain_id: str = "eip155:8453") -> dict[str, Any]:
    addrs = [a.strip() for a in contract_addresses if a.startswith("0x")][:3]
    per: list[dict[str, Any]] = []
    delegates: list[str | None] = []
    for a in addrs:
        tr = triage_contract(a, chain_id)
        dprobe = _code_delegate_probe(a, chain_id)
        delegates.append(dprobe.get("eip7702Delegate"))
        per.append(
            {
                "address": a,
                "triage": tr,
                "codeProbe": dprobe,
            }
        )
    shared = None
    non_null = [x for x in delegates if x]
    if len(non_null) >= 2 and len(set(non_null)) == 1:
        shared = non_null[0]
    excerpt = _load_audit_v2_excerpt()
    return {
        "schema": "audit_report_v2",
        "chainId": chain_id,
        "contracts": per,
        "sharedEip7702Delegate": shared,
        "coordinatedDeploymentSuspected": bool(shared),
        "echidna": {
            "note": "Echidna fork-mode (12k) is run offline in sc-audit/echidna-corpus; HTTP SKU returns static + triage + on-chain probe.",
            "corpusPath": "sc-audit/echidna-corpus/base_fork/",
        },
        "auditReportV2ExcerptPresent": bool(excerpt),
        "auditReportV2Chars": len(excerpt or ""),
    }


def monitor_subscribe(
    addresses: list[str],
    webhook_url: str,
    thresholds: dict[str, Any] | None,
    duration_days: int,
) -> dict[str, Any]:
    from marketplace.skus.contract_monitor_store import create_subscription  # noqa: PLC0415

    sub = create_subscription(addresses, webhook_url, thresholds, duration_days)
    out = {
        "subscriptionId": sub.id,
        "addresses": sub.addresses,
        "expiresAt": sub.expires_at,
        "webhookUrl": sub.webhook_url,
        "status": sub.status,
    }
    try:
        import requests

        headers = {"Content-Type": "application/json"}
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
        requests.post(
            webhook_url,
            json={
                "event": "subscription_created",
                "subscriptionId": sub.id,
                "addresses": sub.addresses,
                "expiresAt": sub.expires_at,
                "status": sub.status,
            },
            headers=headers,
            timeout=15,
        )
        out["webhookProbe"] = "subscription_created_sent"
    except Exception as e:
        out["webhookProbe"] = f"failed: {e!s}"
    return out
