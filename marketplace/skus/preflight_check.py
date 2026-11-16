"""Agent pre-flight check — screen a contract, seller/payTo, and optional resource.

Stable output schema: asm.preflight.v1 (see docs/preflight-schema.md).

Honesty rule (same as contract-triage): a lookup or network failure is
INCONCLUSIVE, never RISKY. RISKY is reserved for positive evidence.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

SCHEMA_ID = "asm.preflight.v1"
SKU_ID = "agent-preflight-check"
SUPPORTED_NETWORKS = ("eip155:8453", "xrpl:mainnet", "xrpl:0")
NETWORK_BASE = "eip155:8453"
NETWORK_XRPL = "xrpl:mainnet"
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ASM-Preflight/1.0; +https://agentic-swarm-marketplace.com)",
    "Accept": "application/json, text/plain, */*",
}
_EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")
_TIMEOUT = 12
_KNOWN_BASE = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {
        "name": "Circle USDC (Base)",
        "kind": "official_stablecoin",
    },
    "0x2ce6311ddae708829bc0784c967b7d77d19fd779": {
        "name": "Circle FiatTokenV2_2 implementation (Base USDC)",
        "kind": "official_stablecoin_implementation",
    },
    "0x408f39b19266022fec03076091e59d1f4f163658": {
        "name": "Agentic Swarm Marketplace Base USDC payTo",
        "kind": "asm_seller",
    },
}
# XRPL AccountSet flags that are positive risk evidence when set.
_RISKY_XRPL_FLAGS = {
    "lsfGlobalFreeze": "Account has GlobalFreeze set",
    "lsfDisableMaster": "Master key is disabled (unusual for an unaudited seller)",
}
_XRPL_FLAG_MAP = {
    0x00010000: "lsfRequireDestTag",
    0x00020000: "lsfRequireAuth",
    0x00040000: "lsfDisallowXRP",
    0x00080000: "lsfDisableMaster",
    0x00100000: "lsfNoFreeze",
    0x00200000: "lsfGlobalFreeze",
    0x00400000: "lsfDefaultRipple",
    0x01000000: "lsfDepositAuth",
}

# Make repo importable when this file is loaded as marketplace.skus.*
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_AGENTS = _REPO / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_network(raw: str | None) -> str | None:
    v = (raw or "").strip()
    if not v:
        return None
    low = v.lower()
    if low in {"eip155:8453", "base", "base-mainnet", "8453"}:
        return NETWORK_BASE
    if low in {"xrpl:mainnet", "xrpl:0", "xrpl", "xrpl-mainnet", "0"}:
        return NETWORK_XRPL
    return v


def is_evm_address(value: str) -> bool:
    return bool(_EVM.fullmatch((value or "").strip()))


def is_xrpl_address(value: str) -> bool:
    try:
        from xrpl_discovery.validate import is_valid_classic_address

        return is_valid_classic_address(value)
    except Exception:
        s = (value or "").strip()
        return bool(re.match(r"^r[1-9A-HJ-NP-Za-km-z]{25,34}$", s))


def _classify_address(value: str) -> str | None:
    v = (value or "").strip()
    if is_evm_address(v):
        return "evm"
    if is_xrpl_address(v):
        return "xrpl"
    return None


def parse_preflight_request(params: Mapping[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Parse and validate input. Returns (target, error). error is a 400 payload."""
    p = params or {}

    def _get(*keys: str) -> str:
        for k in keys:
            raw = p.get(k)
            if raw is None:
                continue
            val = str(raw).strip()
            if val:
                return val
        return ""

    contract = _get("contractAddress", "address", "contract", "contract_address")
    pay_to = _get("payTo", "seller", "sellerAddress", "pay_to", "seller_address")
    resource = _get("resource", "url", "resourceUrl", "resource_url")
    network = _norm_network(_get("network", "chainId", "chain_id"))
    target_blob = _get("target")

    if target_blob and not contract and not pay_to:
        kind = _classify_address(target_blob)
        if kind == "evm":
            contract = target_blob
        elif kind == "xrpl":
            pay_to = target_blob
        elif target_blob.startswith("http://") or target_blob.startswith("https://"):
            resource = resource or target_blob

    if not contract and not pay_to:
        return None, {
            "error": "missing_or_invalid_target",
            "message": (
                "Pass a contractAddress (Base 0x…) and/or a payTo/seller address "
                "(Base 0x… or XRPL classic r…). Optional resource URL. "
                "This request was not charged."
            ),
            "hint": (
                "GET /x402/v1/preflight?contractAddress=0x…&payTo=0x…&resource=https://…"
                " or ?payTo=r…&network=xrpl:mainnet"
            ),
            "example": (
                "/x402/v1/preflight?contractAddress=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
                "&payTo=0x408f39B19266022FeC03076091e59D1f4f163658"
            ),
            "schema": SCHEMA_ID,
        }

    if contract:
        if not is_evm_address(contract):
            if is_xrpl_address(contract):
                return None, {
                    "error": "invalid_contractAddress",
                    "message": (
                        "contractAddress must be a Base EVM address (0x + 40 hex). "
                        "Put an XRPL classic address in payTo/seller. This request was not charged."
                    ),
                    "hint": "GET /x402/v1/preflight?payTo=r…&network=xrpl:mainnet",
                    "schema": SCHEMA_ID,
                }
            return None, {
                "error": "invalid_contractAddress",
                "message": "contractAddress must be 0x followed by 40 hex characters. This request was not charged.",
                "hint": "GET /x402/v1/preflight?contractAddress=0x…&chainId=eip155:8453",
                "example": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "schema": SCHEMA_ID,
            }

    if pay_to and not _classify_address(pay_to):
        return None, {
            "error": "invalid_payTo",
            "message": (
                "payTo/seller must be a Base EVM address (0x + 40 hex) or an XRPL "
                "mainnet classic address (r…). This request was not charged."
            ),
            "hint": "GET /x402/v1/preflight?payTo=0x… or ?payTo=r…&network=xrpl:mainnet",
            "schema": SCHEMA_ID,
        }

    if network and network not in {NETWORK_BASE, NETWORK_XRPL} and network not in SUPPORTED_NETWORKS:
        return None, {
            "error": "unsupported_network",
            "message": (
                f"Unsupported network {network!r}. Supported: eip155:8453 (Base) and "
                "xrpl:mainnet (alias xrpl:0). This request was not charged."
            ),
            "schema": SCHEMA_ID,
        }

    if resource:
        parsed = urlparse(resource)
        if parsed.scheme not in {"http", "https", "javascript", "data", "file"} or not (parsed.netloc or parsed.scheme in {"javascript", "data", "file"}):
            return None, {
                "error": "invalid_resource",
                "message": "resource must be an absolute URL. This request was not charged.",
                "hint": "Pass ?resource=https://example.com/path",
                "schema": SCHEMA_ID,
            }

    pay_kind = _classify_address(pay_to) if pay_to else None
    networks: list[str] = []
    if contract or pay_kind == "evm":
        networks.append(NETWORK_BASE)
    if pay_kind == "xrpl":
        networks.append(NETWORK_XRPL)
    if network == NETWORK_BASE and NETWORK_BASE not in networks:
        networks.insert(0, NETWORK_BASE)
    if network == NETWORK_XRPL and NETWORK_XRPL not in networks:
        networks.append(NETWORK_XRPL)
    if network and pay_kind == "xrpl" and network == NETWORK_BASE:
        return None, {
            "error": "network_mismatch",
            "message": "XRPL payTo cannot be checked on eip155:8453. Use network=xrpl:mainnet. This request was not charged.",
            "schema": SCHEMA_ID,
        }
    if network and (contract or pay_kind == "evm") and network == NETWORK_XRPL and pay_kind != "xrpl":
        return None, {
            "error": "network_mismatch",
            "message": "Base EVM addresses cannot be checked on xrpl:mainnet. Use network=eip155:8453. This request was not charged.",
            "schema": SCHEMA_ID,
        }

    target = {
        "contractAddress": contract or None,
        "payTo": pay_to or None,
        "resource": resource or None,
        "networks": networks or [NETWORK_BASE],
    }
    return target, None


def _http_get_json(url: str, timeout: int = _TIMEOUT) -> tuple[Any, str | None]:
    try:
        import requests

        resp = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
        resp.raise_for_status()
        try:
            return resp.json(), None
        except Exception:
            return {"_text": (resp.text or "")[:4000]}, None
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}"[:180]


def _http_get_text(url: str, timeout: int = _TIMEOUT) -> tuple[str | None, int | None, str | None]:
    try:
        import requests

        resp = requests.get(url, headers={**HTTP_HEADERS, "Accept": "text/plain, */*"}, timeout=timeout)
        return (resp.text or ""), resp.status_code, None
    except Exception as exc:
        return None, None, f"{type(exc).__name__}:{exc}"[:180]


def _http_post_json(url: str, payload: dict[str, Any], timeout: int = _TIMEOUT) -> tuple[Any, str | None]:
    try:
        import requests

        resp = requests.post(url, json=payload, headers=HTTP_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}"[:180]


def _load_known_xrpl_catalogs() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    paths = [
        _REPO / "docs" / "identity" / "xrpl-merchant.json",
        _REPO / "packages" / "agents" / "identity" / "xrpl_catalog_snapshot.json",
        _REPO / "docs" / "identity" / "identity.json",
    ]
    for path in paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries.append({"path": str(path.relative_to(_REPO)), "data": data})
    return entries


def _xrpl_catalog_hits(account: str) -> list[dict[str, Any]]:
    acct = (account or "").strip()
    hits: list[dict[str, Any]] = []
    for rec in _load_known_xrpl_catalogs():
        blob = json.dumps(rec["data"], default=str)
        if acct and acct in blob:
            label = None
            data = rec["data"]
            if isinstance(data, dict):
                label = data.get("name") or data.get("brand") or data.get("legalName")
            hits.append({"catalog": rec["path"], "label": label, "matched": acct})
    return hits


def _known_evm(addr: str) -> dict[str, Any] | None:
    return _KNOWN_BASE.get((addr or "").lower())


def lookup_evm_address(address: str) -> dict[str, Any]:
    """Blockscout v2 address metadata. lookup_failed stays honest."""
    addr = address.strip()
    url = f"https://base.blockscout.com/api/v2/addresses/{addr}"
    data, err = _http_get_json(url)
    if err or not isinstance(data, dict):
        return {"ok": False, "lookup_failed": True, "reason": err or "invalid_response", "source": "blockscout_v2_address"}
    return {
        "ok": True,
        "lookup_failed": False,
        "source": "blockscout_v2_address",
        "is_contract": bool(data.get("is_contract")),
        "is_verified": bool(data.get("is_verified")),
        "name": data.get("name") or data.get("implementation_name") or "",
        "creation_tx": (data.get("creation_tx_hash") or None),
        "has_logs": data.get("has_logs"),
        "has_token_transfers": data.get("has_token_transfers"),
        "raw_keys": sorted(list(data.keys()))[:20],
    }


def lookup_xrpl_account(account: str) -> dict[str, Any]:
    """account_info + optional xrpscan inception. Failures are lookup_failed."""
    out: dict[str, Any] = {"ok": False, "lookup_failed": False, "sources": []}
    rpc, err = _http_post_json(
        "https://xrplcluster.com",
        {"method": "account_info", "params": [{"account": account, "ledger_index": "validated"}]},
    )
    if err or not isinstance(rpc, dict):
        out["lookup_failed"] = True
        out["reason"] = err or "invalid_rpc_response"
        out["sources"].append("xrplcluster_account_info")
        return out
    result = rpc.get("result") if isinstance(rpc.get("result"), dict) else rpc
    status = (result or {}).get("status") or rpc.get("status")
    if status == "error" or (result or {}).get("error"):
        err_name = (result or {}).get("error") or "rpc_error"
        # actNotFound is a definitive result, not a transport failure.
        if err_name == "actNotFound":
            out.update({"ok": True, "exists": False, "reason": "account_not_found", "sources": ["xrplcluster_account_info"]})
            return out
        out["lookup_failed"] = True
        out["reason"] = str(err_name)
        out["sources"].append("xrplcluster_account_info")
        return out
    info = (result or {}).get("account_data") or {}
    flags_int = int(info.get("Flags") or 0)
    flags = [name for bit, name in _XRPL_FLAG_MAP.items() if flags_int & bit]
    domain_hex = info.get("Domain") or ""
    domain = ""
    if domain_hex:
        try:
            domain = bytes.fromhex(domain_hex).decode("utf-8", errors="replace")
        except Exception:
            domain = ""
    out.update(
        {
            "ok": True,
            "exists": True,
            "balance_drops": str(info.get("Balance") or ""),
            "sequence": info.get("Sequence"),
            "flags": flags,
            "flags_int": flags_int,
            "domain": domain,
            "owner_count": info.get("OwnerCount"),
            "sources": ["xrplcluster_account_info"],
        }
    )
    scan, scan_err = _http_get_json(f"https://api.xrpscan.com/api/v1/account/{account}")
    if not scan_err and isinstance(scan, dict):
        out["sources"].append("xrpscan_account")
        out["inception"] = scan.get("inception") or scan.get("activatedAt") or scan.get("created")
        out["account_name"] = scan.get("accountName") or (scan.get("name") if isinstance(scan.get("name"), str) else None)
    elif scan_err:
        out.setdefault("age_lookup_error", scan_err)
    return out


def lookup_xrpl_toml(domain: str, account: str) -> dict[str, Any]:
    if not domain:
        return {"ok": False, "present": False}
    host = domain.strip().lstrip("https://").lstrip("http://").split("/")[0]
    url = f"https://{host}/.well-known/xrp-ledger.toml"
    text, status, err = _http_get_text(url)
    if err or status is None:
        return {"ok": False, "lookup_failed": True, "reason": err or "no_status", "url": url, "source": "xrp_ledger_toml"}
    if status >= 400 or text is None:
        return {
            "ok": True,
            "present": False,
            "status": status,
            "url": url,
            "source": "xrp_ledger_toml",
            "listed": False,
        }
    listed = account in text
    return {
        "ok": True,
        "present": True,
        "status": status,
        "url": url,
        "source": "xrp_ledger_toml",
        "listed": listed,
        "snippet_len": len(text),
    }


def _triage(address: str, chain_id: str = NETWORK_BASE) -> dict[str, Any]:
    try:
        from marketplace.skus.smart_contract_audit import triage_contract

        return triage_contract(address, chain_id)
    except Exception as exc:
        return {
            "verdict": "INCONCLUSIVE",
            "riskScore": 0,
            "verified": False,
            "reason": "triage_engine_error",
            "lookupFailed": True,
            "detail": f"{type(exc).__name__}:{exc}"[:180],
        }


def _score_and_verdict(reasons: list[dict[str, Any]]) -> tuple[str, int, list[str], bool]:
    """Compose SAFE / RISKY / INCONCLUSIVE. lookup failures never become RISKY."""
    lookup_failed = any(r.get("lookup_failed") for r in reasons)
    risky = [r for r in reasons if r.get("severity") == "risky"]
    inconclusive = [r for r in reasons if r.get("severity") == "inconclusive" or r.get("lookup_failed")]
    positive_safe = [r for r in reasons if r.get("severity") == "safe"]
    texts = [str(r.get("reason") or r.get("code")) for r in reasons if r.get("reason") or r.get("code")]

    if risky:
        # Risk score: start at 60, add 10 per risky signal, cap 95.
        score = min(95, 60 + 10 * (len(risky) - 1))
        return "RISKY", score, texts, lookup_failed
    if lookup_failed or inconclusive or not positive_safe:
        return "INCONCLUSIVE", 0, texts, lookup_failed
    return "SAFE", 0, texts, lookup_failed


def run_preflight(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Run the hero pre-flight check. Caller must already have validated input for paid paths."""
    target, err = parse_preflight_request(params)
    if err or not target:
        # Defensive: paid path should not reach here. Still never call this a RISKY verdict.
        return {
            "schema": SCHEMA_ID,
            "sku": SKU_ID,
            "verdict": "INCONCLUSIVE",
            "riskScore": 0,
            "reasons": [err.get("message") if err else "invalid_input"],
            "evidence": [],
            "sources": [],
            "timestamp": _now_iso(),
            "target": target,
            "error": err,
        }

    evidence: list[dict[str, Any]] = []
    sources: list[str] = []
    checks: dict[str, Any] = {}

    def _note(check: str, **row: Any) -> None:
        item = {"check": check, **row}
        evidence.append(item)

    contract = target.get("contractAddress")
    pay_to = target.get("payTo")
    resource = target.get("resource")

    if contract:
        known = _known_evm(contract)
        triage = _triage(contract, NETWORK_BASE)
        sources.append(str(triage.get("sourceProvider") or "contract_triage"))
        checks["contract"] = {
            "address": contract,
            "network": NETWORK_BASE,
            "triage": {
                "verdict": triage.get("verdict"),
                "riskScore": triage.get("riskScore"),
                "verified": triage.get("verified"),
                "reason": triage.get("reason"),
                "contractName": triage.get("contractName"),
                "isProxy": triage.get("isProxy"),
                "implementation": triage.get("implementation"),
                "sourceProvider": triage.get("sourceProvider"),
                "topFlags": triage.get("topFlags") or [],
            },
            "known": known,
        }
        tv = (triage.get("verdict") or "").upper()
        lookup_fail = bool(triage.get("lookupFailed") or (triage.get("reason") or "").startswith("fetch_error"))
        if tv == "MALICIOUS" or int(triage.get("slitherHighCount") or 0) > 0:
            _note("contract_triage", severity="risky", reason=f"Contract triage verdict {tv or 'MALICIOUS'} / high-severity findings", lookup_failed=False, source="contract_triage")
        elif lookup_fail or tv in {"INCONCLUSIVE", ""} or (tv != "SAFE" and not triage.get("verified")):
            why = triage.get("reason") or "unverified_or_lookup_failed"
            _note("contract_triage", severity="inconclusive", reason=f"Contract triage is {tv or 'INCONCLUSIVE'} ({why})", lookup_failed=lookup_fail, source="contract_triage")
        else:
            label = (known or {}).get("name") or triage.get("contractName") or contract
            _note("contract_triage", severity="safe", reason=f"Verified Base contract {label} is SAFE", lookup_failed=False, source="contract_triage")
        if known:
            _note("known_catalog", severity="safe", reason=f"Listed as {known['name']}", source="asm_known_base")

    if pay_to and is_evm_address(pay_to):
        known = _known_evm(pay_to)
        meta = lookup_evm_address(pay_to)
        sources.append(meta.get("source") or "blockscout_v2_address")
        checks["seller_evm"] = {"address": pay_to, "network": NETWORK_BASE, "lookup": meta, "known": known}
        if meta.get("lookup_failed") and not known:
            _note("seller_evm", severity="inconclusive", reason=f"Seller address lookup failed: {meta.get('reason')}", lookup_failed=True, source=meta.get("source"))
        elif meta.get("lookup_failed") and known:
            _note("seller_evm", severity="safe", reason=f"payTo listed as {known['name']}", source="asm_known_base")
        elif meta.get("is_contract"):
            # Reuse triage for a contract seller (supplier-trust style: screen the payTo).
            if contract and pay_to.lower() == contract.lower():
                _note("seller_evm", severity="safe" if any(e.get("check") == "contract_triage" and e.get("severity") == "safe" for e in evidence) else "inconclusive", reason="payTo is the same address as contractAddress", source="blockscout_v2_address")
            else:
                triage = _triage(pay_to, NETWORK_BASE)
                sources.append(str(triage.get("sourceProvider") or "contract_triage"))
                checks["seller_evm"]["triage"] = {
                    "verdict": triage.get("verdict"),
                    "verified": triage.get("verified"),
                    "reason": triage.get("reason"),
                    "contractName": triage.get("contractName"),
                    "sourceProvider": triage.get("sourceProvider"),
                }
                tv = (triage.get("verdict") or "").upper()
                lookup_fail = bool(triage.get("lookupFailed") or (triage.get("reason") or "").startswith("fetch_error"))
                if tv == "MALICIOUS" or int(triage.get("slitherHighCount") or 0) > 0:
                    _note("seller_evm", severity="risky", reason=f"payTo contract triage verdict {tv or 'MALICIOUS'}", source="contract_triage")
                elif lookup_fail or tv != "SAFE":
                    _note("seller_evm", severity="inconclusive", reason=f"payTo contract triage is {tv or 'INCONCLUSIVE'}", lookup_failed=lookup_fail, source="contract_triage")
                else:
                    _note("seller_evm", severity="safe", reason=f"payTo contract {triage.get('contractName') or pay_to} is verified SAFE", source="contract_triage")
        else:
            # EOA seller: known-good helps; otherwise existence is not enough for SAFE.
            if known:
                _note("seller_evm", severity="safe", reason=f"payTo listed as {known['name']}", source="asm_known_base")
            else:
                _note("seller_evm", severity="inconclusive", reason="payTo is an EOA with no catalog listing; no positive risk evidence", source="blockscout_v2_address")

    if pay_to and is_xrpl_address(pay_to):
        info = lookup_xrpl_account(pay_to)
        sources.extend(info.get("sources") or ["xrplcluster_account_info"])
        catalogs = _xrpl_catalog_hits(pay_to)
        toml = {"ok": False, "present": False}
        if info.get("domain"):
            toml = lookup_xrpl_toml(info["domain"], pay_to)
            if toml.get("source"):
                sources.append(str(toml["source"]))
        checks["seller_xrpl"] = {"address": pay_to, "network": NETWORK_XRPL, "account": info, "toml": toml, "catalogs": catalogs}
        if info.get("lookup_failed"):
            _note("seller_xrpl", severity="inconclusive", reason=f"XRPL account lookup failed: {info.get('reason')}", lookup_failed=True, source="xrplcluster_account_info")
        elif not info.get("exists"):
            _note("seller_xrpl", severity="inconclusive", reason="XRPL account is unfunded or not found", source="xrplcluster_account_info")
        else:
            flags = info.get("flags") or []
            risky_flags = [f for f in flags if f in _RISKY_XRPL_FLAGS]
            if "lsfGlobalFreeze" in flags:
                _note("seller_xrpl_flags", severity="risky", reason=_RISKY_XRPL_FLAGS["lsfGlobalFreeze"], source="xrplcluster_account_info")
            if toml.get("lookup_failed"):
                _note("seller_xrpl_toml", severity="inconclusive", reason=f"xrp-ledger.toml lookup failed for domain {info.get('domain')}", lookup_failed=True, source="xrp_ledger_toml")
            elif info.get("domain") and toml.get("present") and toml.get("listed") is False:
                _note("seller_xrpl_toml", severity="risky", reason=f"Account domain {info.get('domain')} serves a TOML that does not list this account", source="xrp_ledger_toml")
            elif info.get("domain") and toml.get("present") and toml.get("listed"):
                _note("seller_xrpl_toml", severity="safe", reason=f"Account is listed in https://{info.get('domain')}/.well-known/xrp-ledger.toml", source="xrp_ledger_toml")
            elif info.get("domain") and toml.get("present") is False:
                _note("seller_xrpl_toml", severity="inconclusive", reason=f"Domain {info.get('domain')} is set but xrp-ledger.toml was not found", source="xrp_ledger_toml")
            if catalogs:
                labels = ", ".join(sorted({(c.get("label") or c.get("catalog")) for c in catalogs}))
                _note("seller_xrpl_catalog", severity="safe", reason=f"Listed in known catalogs ({labels})", source="asm_xrpl_catalog")
            if not risky_flags and not catalogs and not (toml.get("listed")) and not any(e.get("check", "").startswith("seller_xrpl") and e.get("severity") != "inconclusive" for e in evidence if e.get("check") != "seller_xrpl"):
                age = info.get("inception") or "unknown inception"
                _note("seller_xrpl", severity="inconclusive", reason=f"XRPL account exists (flags={flags or 'none'}, inception={age}) but is not catalog- or TOML-confirmed", source="xrplcluster_account_info")
            elif not risky_flags and (catalogs or toml.get("listed")):
                _note("seller_xrpl", severity="safe", reason="XRPL seller account is funded and corroborated by catalog and/or TOML", source="xrplcluster_account_info")

    if resource:
        parsed = urlparse(resource)
        checks["resource"] = {"url": resource, "scheme": parsed.scheme, "host": parsed.netloc}
        if parsed.scheme in {"javascript", "data", "file"}:
            _note("resource", severity="risky", reason=f"Resource URL uses unsafe scheme {parsed.scheme}:", source="resource_url")
        elif parsed.scheme == "http":
            _note("resource", severity="risky", reason="Resource URL is plaintext HTTP, not HTTPS", source="resource_url")
        elif parsed.scheme == "https" and parsed.netloc:
            # Light reachability check; failure is inconclusive, not risky.
            text, status, err = _http_get_text(resource)
            if err:
                _note("resource", severity="inconclusive", reason=f"Resource URL lookup failed: {err}", lookup_failed=True, source="resource_url")
                checks["resource"]["lookup_failed"] = True
            else:
                checks["resource"]["status"] = status
                _note("resource", severity="safe", reason=f"Resource URL is HTTPS and responded with HTTP {status}", source="resource_url")
        else:
            _note("resource", severity="inconclusive", reason="Resource URL could not be interpreted", source="resource_url")

    verdict, score, reason_texts, lookup_failed = _score_and_verdict(evidence)
    # De-duplicate sources, keep order
    seen_src: set[str] = set()
    uniq_sources: list[str] = []
    for s in sources:
        if s and s not in seen_src:
            seen_src.add(s)
            uniq_sources.append(s)
    for ev in evidence:
        s = ev.get("source")
        if s and s not in seen_src:
            seen_src.add(s)
            uniq_sources.append(str(s))

    return {
        "schema": SCHEMA_ID,
        "sku": SKU_ID,
        "verdict": verdict,
        "riskScore": score,
        "reasons": reason_texts,
        "evidence": evidence,
        "sources": uniq_sources,
        "timestamp": _now_iso(),
        "network": target["networks"],
        "target": {
            "contractAddress": contract,
            "payTo": pay_to,
            "resource": resource,
        },
        "checks": checks,
        "lookupFailed": lookup_failed,
    }


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "contractAddress": {
            "type": "string",
            "description": "Base EVM contract to screen (0x + 40 hex). Aliases: address, contract.",
            "pattern": "^0x[0-9a-fA-F]{40}$",
            "examples": ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
        },
        "payTo": {
            "type": "string",
            "description": "Seller settlement address: Base 0x… or XRPL classic r…. Aliases: seller, sellerAddress.",
        },
        "resource": {
            "type": "string",
            "description": "Optional x402 resource URL claimed by the seller. Aliases: url, resourceUrl.",
        },
        "network": {
            "type": "string",
            "description": "Optional CAIP-2 network. Supported: eip155:8453, xrpl:mainnet (alias xrpl:0). Alias: chainId.",
            "enum": ["eip155:8453", "xrpl:mainnet", "xrpl:0"],
        },
    },
    "anyOf": [{"required": ["contractAddress"]}, {"required": ["payTo"]}, {"required": ["address"]}, {"required": ["seller"]}],
}

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["schema", "sku", "verdict", "riskScore", "reasons", "evidence", "sources", "timestamp", "target", "lookupFailed"],
    "properties": {
        "schema": {"type": "string", "const": SCHEMA_ID},
        "sku": {"type": "string", "const": SKU_ID},
        "verdict": {"type": "string", "enum": ["SAFE", "RISKY", "INCONCLUSIVE"]},
        "riskScore": {"type": "integer", "minimum": 0, "maximum": 100, "description": "0 is safest. Set only when verdict is RISKY; lookup failures stay 0."},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "object"}},
        "sources": {"type": "array", "items": {"type": "string"}, "description": "Evidence providers used for this result."},
        "timestamp": {"type": "string", "format": "date-time"},
        "network": {"type": "array", "items": {"type": "string"}},
        "target": {
            "type": "object",
            "properties": {
                "contractAddress": {"type": ["string", "null"]},
                "payTo": {"type": ["string", "null"]},
                "resource": {"type": ["string", "null"]},
            },
        },
        "checks": {"type": "object"},
        "lookupFailed": {"type": "boolean"},
    },
}

EXAMPLE_REQUEST = {
    "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x408f39B19266022FeC03076091e59D1f4f163658",
    "network": "eip155:8453",
}

EXAMPLE_RESPONSE = {
    "schema": SCHEMA_ID,
    "sku": SKU_ID,
    "verdict": "SAFE",
    "riskScore": 0,
    "reasons": [
        "Verified Base contract FiatTokenProxy->FiatTokenV2_2 is SAFE",
        "payTo listed as Agentic Swarm Marketplace Base USDC payTo",
    ],
    "evidence": [
        {"check": "contract_triage", "severity": "safe", "reason": "Verified Base contract FiatTokenProxy->FiatTokenV2_2 is SAFE", "source": "contract_triage"},
        {"check": "seller_evm", "severity": "safe", "reason": "payTo listed as Agentic Swarm Marketplace Base USDC payTo", "source": "asm_known_base"},
    ],
    "sources": ["blockscout_v2", "asm_known_base"],
    "timestamp": "2026-11-16T22:00:00Z",
    "network": ["eip155:8453"],
    "target": {
        "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "payTo": "0x408f39B19266022FeC03076091e59D1f4f163658",
        "resource": None,
    },
    "checks": {},
    "lookupFailed": False,
}


def bazaar_discovery_extension():
    """Coinbase Bazaar discovery extension for /x402/v1/preflight."""
    try:
        from x402.extensions.bazaar import declare_discovery_extension
        from x402.extensions.bazaar.resource_service import OutputConfig

        return declare_discovery_extension(
            input=EXAMPLE_REQUEST,
            input_schema=INPUT_SCHEMA,
            output=OutputConfig(example=EXAMPLE_RESPONSE),
        )
    except ImportError:
        return None
