"""
Smart contract audit SKUs (Tier 1–3) for Base x402 seller.
Uses Blockscout (with a real User-Agent), Sourcify, optional Etherscan V2,
optional Slither CLI, and repo audit artifacts.

Lookup failures and unverified contracts are INCONCLUSIVE, never MALICIOUS.
MALICIOUS is reserved for positive evidence (e.g. high-impact Slither findings).
Proxy contracts (such as USDC) resolve the implementation before scoring.
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

_UA = "Mozilla/5.0 (compatible; ASM-Triage/1.0; +https://agentic-swarm-marketplace.com)"
_HTTP_HEADERS = {"User-Agent": _UA, "Accept": "application/json"}

# EIP-1967: bytes32(uint256(keccak256('eip1967.proxy.implementation')) - 1)
_EIP1967_IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
# OpenZeppelin Unstructured Storage / FiatTokenProxy:
# keccak256("org.zeppelinos.proxy.implementation")
_ZOS_IMPL_SLOT = "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"
# EIP-1822 UUPS: keccak256("PROXIABLE")
_EIP1822_IMPL_SLOT = "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7"
_IMPLEMENTATION_SELECTOR = "0x5c60da1b"  # implementation()
_ZERO_ADDR = "0x" + ("0" * 40)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _chain_numeric(chain_id: str) -> str:
    raw = (chain_id or "").strip()
    if raw.startswith("eip155:"):
        raw = raw.split(":", 1)[1]
    return raw or "8453"


def _blockscout_base(chain_id: str) -> str:
    numeric = _chain_numeric(chain_id)
    if numeric == "8453":
        return _env("BLOCKSCOUT_BASE_URL", "https://base.blockscout.com").rstrip("/")
    if numeric == "1":
        return "https://eth.blockscout.com"
    return _env("BLOCKSCOUT_BASE_URL", "https://base.blockscout.com").rstrip("/")


def _http_get_json(url: str, timeout: int = 25) -> Any:
    """GET JSON with a browser-like User-Agent. Cloudflare blocks default python-requests."""
    r = requests.get(url, timeout=timeout, headers=_HTTP_HEADERS)
    r.raise_for_status()
    return r.json()


def _explorer_api_key() -> str:
    # Never log or return this to callers except as a query param to Etherscan.
    for key in (
        "ETHERSCAN_API_KEY",
        "ETHERSCAN_API_KEY_V2",
        "BASESCAN_API_KEY",
        "ETHERSCAN_V2_API_KEY",
    ):
        val = _env(key)
        if val:
            return val
    return ""


def _normalize_addr(value: str) -> str:
    addr = (value or "").strip()
    if addr.startswith("0x") and len(addr) == 42 and re.fullmatch(r"0x[0-9a-fA-F]{40}", addr):
        return "0x" + addr[2:]
    return ""


def _addr_from_storage(slot_value: str) -> str:
    raw = (slot_value or "").strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) < 40:
        return ""
    return _normalize_addr("0x" + raw[-40:])


def _concat_sourcify_sources(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    sources = payload.get("sources")
    if isinstance(sources, dict):
        for name, body in sources.items():
            if isinstance(body, dict):
                content = body.get("content") or ""
            else:
                content = body if isinstance(body, str) else ""
            if content:
                parts.append(f"// file: {name}\n{content}")
    if not parts:
        std = payload.get("stdJsonInput") or {}
        std_sources = std.get("sources") if isinstance(std, dict) else None
        if isinstance(std_sources, dict):
            for name, body in std_sources.items():
                content = (body or {}).get("content") if isinstance(body, dict) else body
                if content:
                    parts.append(f"// file: {name}\n{content}")
    return "\n\n".join(parts)


def _lookup_blockscout_v2(chain_id: str, address: str) -> dict[str, Any] | None:
    url = f"{_blockscout_base(chain_id)}/api/v2/smart-contracts/{address}"
    data = _http_get_json(url, timeout=25)
    if not isinstance(data, dict):
        return None
    src = (data.get("source_code") or "").strip()
    extra = data.get("additional_sources") or []
    if isinstance(extra, list):
        for item in extra:
            if isinstance(item, dict) and item.get("source_code"):
                path = item.get("file_path") or item.get("file_name") or "extra"
                src = f"{src}\n\n// file: {path}\n{item['source_code']}"
    impls: list[str] = []
    raw_impls = data.get("implementations") or []
    if isinstance(raw_impls, list):
        for row in raw_impls:
            if isinstance(row, dict):
                impls.append(_normalize_addr(row.get("address_hash") or row.get("address") or ""))
            elif isinstance(row, str):
                impls.append(_normalize_addr(row))
    impls = [a for a in impls if a]
    verified = bool(data.get("is_verified") or data.get("is_fully_verified") or src)
    return {
        "provider": "blockscout_v2",
        "verified": verified,
        "source": src,
        "contract_name": (data.get("name") or "").strip(),
        "proxy_type": data.get("proxy_type"),
        "implementations": impls,
        "reason": "ok" if verified else "unverified",
    }


def _lookup_blockscout_legacy(chain_id: str, address: str) -> dict[str, Any] | None:
    url = (
        f"{_blockscout_base(chain_id)}/api?module=contract"
        f"&action=getsourcecode&address={address}"
    )
    data = _http_get_json(url, timeout=25)
    res = data.get("result") if isinstance(data, dict) else None
    if isinstance(res, list) and res:
        row = res[0]
    elif isinstance(res, dict):
        row = res
    else:
        return None
    if not isinstance(row, dict):
        return None
    src = (row.get("SourceCode") or "").strip()
    name = (row.get("ContractName") or "").strip()
    impl = _normalize_addr(row.get("Implementation") or "")
    proxy_flag = str(row.get("Proxy") or "").strip()
    verified = bool(src)
    return {
        "provider": "blockscout_legacy",
        "verified": verified,
        "source": src,
        "contract_name": name,
        "proxy_type": "proxy" if proxy_flag in {"1", "true", "True"} or impl else None,
        "implementations": [impl] if impl else [],
        "reason": "ok" if verified else "unverified",
    }


def _lookup_sourcify(chain_id: str, address: str) -> dict[str, Any] | None:
    numeric = _chain_numeric(chain_id)
    url = f"https://sourcify.dev/server/v2/contract/{numeric}/{address}"
    try:
        data = _http_get_json(url, timeout=25)
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        if status == 404:
            return {
                "provider": "sourcify",
                "verified": False,
                "source": "",
                "contract_name": "",
                "proxy_type": None,
                "implementations": [],
                "reason": "unverified",
            }
        raise
    if not isinstance(data, dict):
        return None
    match = (data.get("match") or data.get("runtimeMatch") or "").lower()
    verified = match in {"exact_match", "match", "perfect", "partial", "partial_match"} or bool(
        data.get("sources") or data.get("stdJsonInput")
    )
    src = _concat_sourcify_sources(data)
    name = ""
    comp = data.get("compilation") if isinstance(data.get("compilation"), dict) else {}
    if isinstance(comp, dict):
        name = (comp.get("name") or comp.get("contractName") or "").strip()
    impls: list[str] = []
    proxy = data.get("proxyResolution") if isinstance(data.get("proxyResolution"), dict) else {}
    if isinstance(proxy, dict):
        for key in ("implementations", "implementation"):
            val = proxy.get(key)
            if isinstance(val, str):
                impls.append(_normalize_addr(val))
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        impls.append(_normalize_addr(item))
                    elif isinstance(item, dict):
                        impls.append(_normalize_addr(item.get("address") or item.get("address_hash") or ""))
        if proxy.get("isProxy") or proxy.get("proxyType") or impls:
            proxy_type = proxy.get("proxyType") or "proxy"
        else:
            proxy_type = None
    else:
        proxy_type = None
    impls = [a for a in impls if a]
    return {
        "provider": "sourcify",
        "verified": bool(verified and (src or match)),
        "source": src,
        "contract_name": name,
        "proxy_type": proxy_type,
        "implementations": impls,
        "reason": "ok" if verified else "unverified",
    }


def _lookup_etherscan_v2(chain_id: str, address: str) -> dict[str, Any] | None:
    key = _explorer_api_key()
    if not key:
        return None
    numeric = _chain_numeric(chain_id)
    url = (
        "https://api.etherscan.io/v2/api"
        f"?chainid={numeric}&module=contract&action=getsourcecode"
        f"&address={address}&apikey={key}"
    )
    data = _http_get_json(url, timeout=25)
    if not isinstance(data, dict):
        return None
    if str(data.get("status")) == "0":
        # Missing key / rate limit / not found — treat NOTOK "not verified" vs errors
        result = str(data.get("result") or data.get("message") or "")
        low = result.lower()
        if "not verified" in low or "contract source code not verified" in low:
            return {
                "provider": "etherscan_v2",
                "verified": False,
                "source": "",
                "contract_name": "",
                "proxy_type": None,
                "implementations": [],
                "reason": "unverified",
            }
        raise RuntimeError(f"etherscan_v2:{result[:180]}")
    res = data.get("result")
    row = res[0] if isinstance(res, list) and res else res
    if not isinstance(row, dict):
        return None
    src = (row.get("SourceCode") or "").strip()
    name = (row.get("ContractName") or "").strip()
    impl = _normalize_addr(row.get("Implementation") or "")
    proxy_flag = str(row.get("Proxy") or "").strip()
    return {
        "provider": "etherscan_v2",
        "verified": bool(src),
        "source": src,
        "contract_name": name,
        "proxy_type": "proxy" if proxy_flag in {"1", "true", "True"} or impl else None,
        "implementations": [impl] if impl else [],
        "reason": "ok" if src else "unverified",
    }


def _rpc_url(chain_id: str) -> str:
    numeric = _chain_numeric(chain_id)
    if numeric == "8453":
        return _env("RPC_URL_BASE", "https://base.publicnode.com")
    if numeric == "1":
        return _env("RPC_URL_ETH", "https://eth.llamarpc.com")
    return _env("RPC_URL_BASE", "https://base.publicnode.com")


def _rpc(chain_id: str, method: str, params: list[Any]) -> Any:
    url = _rpc_url(chain_id)
    r = requests.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=20,
        headers={**_HTTP_HEADERS, "Content-Type": "application/json"},
    )
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:200])
    return data.get("result")


def _implementation_from_rpc(chain_id: str, address: str) -> str:
    """Resolve a proxy implementation via eth_call and well-known storage slots."""
    addr = _normalize_addr(address)
    if not addr:
        return ""
    # implementation()
    try:
        raw = _rpc(chain_id, "eth_call", [{"to": addr, "data": _IMPLEMENTATION_SELECTOR}, "latest"])
        found = _addr_from_storage(raw or "")
        if found and found.lower() != _ZERO_ADDR:
            return found
    except Exception:
        pass
    for slot in (_EIP1967_IMPL_SLOT, _ZOS_IMPL_SLOT, _EIP1822_IMPL_SLOT):
        try:
            raw = _rpc(chain_id, "eth_getStorageAt", [addr, slot, "latest"])
            found = _addr_from_storage(raw or "")
            if found and found.lower() != _ZERO_ADDR:
                return found
        except Exception:
            continue
    return ""


def _collect_sources(chain_id: str, address: str) -> dict[str, Any]:
    """Try Blockscout v2, Blockscout legacy, Sourcify, then Etherscan V2 if a key exists."""
    errors: list[str] = []
    definitive_unverified = False
    last: dict[str, Any] | None = None
    providers = (
        _lookup_blockscout_v2,
        _lookup_blockscout_legacy,
        _lookup_sourcify,
        _lookup_etherscan_v2,
    )
    for fn in providers:
        try:
            result = fn(chain_id, address)
        except Exception as exc:
            name = getattr(fn, "__name__", type(fn).__name__)
            errors.append(f"{name}:{type(exc).__name__}:{exc}"[:180])
            continue
        if not result:
            continue
        last = result
        if result.get("verified") and (result.get("source") or result.get("implementations")):
            result["lookup_errors"] = errors
            return result
        if result.get("reason") == "unverified":
            definitive_unverified = True
        # Keep looking for a verified provider even after an unverified hit.
    if last and last.get("verified"):
        last["lookup_errors"] = errors
        return last
    if definitive_unverified:
        return {
            "provider": (last or {}).get("provider") or "none",
            "verified": False,
            "source": "",
            "contract_name": (last or {}).get("contract_name") or "",
            "proxy_type": (last or {}).get("proxy_type"),
            "implementations": (last or {}).get("implementations") or [],
            "reason": "unverified",
            "lookup_errors": errors,
        }
    return {
        "provider": "none",
        "verified": False,
        "source": "",
        "contract_name": "",
        "proxy_type": None,
        "implementations": [],
        "reason": "source_lookup_failed",
        "lookup_failed": True,
        "lookup_errors": errors,
    }


def _etherscan_compatible_source(chain_id: str, address: str) -> tuple[bool, str, str, str]:
    """Return (verified, source_concat, reason_if_empty, contract_name). Kept for callers/tests."""
    addr = _normalize_addr(address)
    if not addr:
        return False, "", "invalid_address", ""
    info = resolve_contract_source(chain_id, addr)
    return bool(info.get("verified")), info.get("source") or "", info.get("reason") or "", info.get("contract_name") or ""


def resolve_contract_source(chain_id: str, address: str) -> dict[str, Any]:
    """Fetch source and, if this is a proxy, the implementation source too."""
    addr = _normalize_addr(address)
    if not addr:
        return {
            "verified": False,
            "source": "",
            "reason": "invalid_address",
            "contract_name": "",
            "lookup_failed": False,
            "is_proxy": False,
            "implementation": "",
            "implementation_verified": False,
            "implementation_name": "",
            "proxy_type": None,
            "provider": "none",
        }
    primary = _collect_sources(chain_id, addr)
    impl = ""
    for cand in primary.get("implementations") or []:
        if _normalize_addr(cand) and _normalize_addr(cand).lower() != addr.lower():
            impl = _normalize_addr(cand)
            break
    if not impl:
        impl = _implementation_from_rpc(chain_id, addr)
    is_proxy = bool(primary.get("proxy_type") or impl)
    impl_info: dict[str, Any] | None = None
    if impl and impl.lower() != addr.lower():
        try:
            impl_info = _collect_sources(chain_id, impl)
        except Exception as exc:
            impl_info = {
                "verified": False,
                "source": "",
                "reason": f"implementation_lookup_failed:{exc}"[:180],
                "lookup_failed": True,
                "contract_name": "",
            }
    parts = []
    if primary.get("source"):
        parts.append(primary["source"])
    if impl_info and impl_info.get("source"):
        iname = impl_info.get("contract_name") or "implementation"
        parts.append(f"// implementation: {impl} {iname}\n{impl_info['source']}")
    source = "\n\n".join(parts)
    primary_verified = bool(primary.get("verified"))
    impl_verified = bool(impl_info and impl_info.get("verified"))
    lookup_failed = bool(primary.get("lookup_failed")) and not (impl_info and not impl_info.get("lookup_failed"))
    # A proxy is verified when the proxy, the implementation, or both are verified.
    verified = primary_verified or impl_verified
    if lookup_failed and not verified:
        reason = "source_lookup_failed"
    elif verified:
        reason = "ok"
    else:
        reason = (impl_info or {}).get("reason") or primary.get("reason") or "unverified"
    name = primary.get("contract_name") or ""
    if impl_info and impl_info.get("contract_name"):
        if name:
            name = f"{name}->{impl_info['contract_name']}"
        else:
            name = impl_info["contract_name"]
    return {
        "verified": verified,
        "source": source,
        "reason": reason,
        "contract_name": name,
        "lookup_failed": lookup_failed and not verified,
        "is_proxy": is_proxy,
        "implementation": impl,
        "implementation_verified": impl_verified,
        "implementation_name": (impl_info or {}).get("contract_name") or "",
        "proxy_type": primary.get("proxy_type"),
        "provider": primary.get("provider") or "none",
        "lookup_errors": list(primary.get("lookup_errors") or []),
    }


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
    """Legacy helper. Unverified is inconclusive, never malicious by itself."""
    return _verdict_from_signals(
        verified=verified,
        lookup_failed=False,
        high=high,
        med=med,
        hot_flags=[],
        phase6_flags=[],
        brand=brand,
    )


def _verdict_from_signals(
    *,
    verified: bool,
    lookup_failed: bool,
    high: int,
    med: int,
    hot_flags: list[str],
    phase6_flags: list[str],
    brand: list[str],
) -> tuple[int, str]:
    """MALICIOUS only for positive evidence. Lookup failure / unverified → INCONCLUSIVE."""
    positive_malicious = high > 0 or any(f.startswith("slither:") for f in hot_flags)
    # Known-bad operator intel can count as positive evidence when we actually matched it.
    if any("deployer_matches_phase6" in f or "known_eip7702_delegate" in f for f in phase6_flags):
        if high > 0 or any("deployer_matches_phase6" in f for f in phase6_flags):
            # deployer match alone is suspicious; combine with high findings for MALICIOUS
            pass
    if positive_malicious:
        score = min(100, max(70, high * 25 + med * 8 + 20 * len(hot_flags)))
        return score, "MALICIOUS"
    if lookup_failed or not verified:
        return 0, "INCONCLUSIVE"
    # Brand-term hits in *verified* source are not impersonation evidence.
    if med or phase6_flags:
        score = min(69, max(35, med * 8 + 8 * len(phase6_flags)))
        return score, "SUSPICIOUS"
    return 0, "SAFE"


def _contract_creator_address(chain_id: str, address: str) -> str | None:
    addr = _normalize_addr(address)
    if not addr:
        return None
    base = _blockscout_base(chain_id)
    url = f"{base}/api?module=contract&action=getcontractcreation&contractaddresses={addr}"
    try:
        j = _http_get_json(url, timeout=18)
    except Exception:
        return None
    res = j.get("result") if isinstance(j, dict) else None
    rows = res if isinstance(res, list) else [res] if isinstance(res, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c = (row.get("contractCreator") or row.get("contract_creator") or "").strip()
        if _normalize_addr(c):
            return _normalize_addr(c)
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
    addr = _normalize_addr(contract_address)
    if not addr:
        return {
            "riskScore": 0,
            "verdict": "INCONCLUSIVE",
            "topFlags": ["invalid_address"],
            "verified": False,
            "slitherHighCount": 0,
            "slitherMedCount": 0,
            "completedIn": int((time.time() - t0) * 1000),
            "reason": "invalid_address",
        }
    info = resolve_contract_source(chain_id, addr)
    verified = bool(info.get("verified"))
    lookup_failed = bool(info.get("lookup_failed"))
    source = info.get("source") or ""
    reason = info.get("reason") or ""
    cname = info.get("contract_name") or ""
    p6_flags, phase6_intel = _phase6_triage_intel(addr, chain_id, cname, verified)

    brands = _brand_flags(source) if (source and not verified) else []
    sj = _run_slither_json_on_source(source, timeout_sec=25) if (verified and source) else None
    hi, md, sflags = _count_slither_severity(sj)
    score, verdict = _verdict_from_signals(
        verified=verified,
        lookup_failed=lookup_failed,
        high=hi,
        med=md,
        hot_flags=sflags,
        phase6_flags=p6_flags,
        brand=brands,
    )
    if verdict != "INCONCLUSIVE" and verdict != "MALICIOUS":
        bumped = _apply_phase6_score_bump(score, p6_flags)
        if bumped >= 70 and hi > 0:
            score, verdict = bumped, "MALICIOUS"
        elif bumped >= 35 and p6_flags and verdict == "SAFE":
            score, verdict = bumped, "SUSPICIOUS"
        else:
            score = bumped if p6_flags else score

    flags: list[str] = []
    if lookup_failed:
        flags.append("source_lookup_failed")
    elif not verified:
        flags.append("unverified_source")
    if info.get("is_proxy"):
        flags.append("proxy")
        if info.get("implementation"):
            flags.append("proxy_implementation_resolved")
        if info.get("implementation") and not info.get("implementation_verified") and verified:
            flags.append("implementation_unverified")
    flags.extend(sflags)
    if not verified:
        flags.extend(brands)
    flags.extend(p6_flags)
    flags = list(dict.fromkeys(flags))[:14]

    out: dict[str, Any] = {
        "riskScore": score,
        "verdict": verdict,
        "topFlags": flags,
        "verified": verified,
        "slitherHighCount": hi,
        "slitherMedCount": md,
        "completedIn": int((time.time() - t0) * 1000),
        "reason": reason,
        "contractName": cname,
        "isProxy": bool(info.get("is_proxy")),
        "proxyType": info.get("proxy_type"),
        "implementation": info.get("implementation") or None,
        "implementationVerified": bool(info.get("implementation_verified")),
        "implementationName": info.get("implementation_name") or None,
        "sourceProvider": info.get("provider"),
        "phase6Intel": phase6_intel,
    }
    if lookup_failed:
        out["lookupErrors"] = (info.get("lookup_errors") or [])[:6]
    return out


def _eip7702_delegate_from_code(code: bytes) -> str | None:
    if len(code) == 23 and code[:3] == b"\xef\x01\x00":
        return "0x" + code[3:23].hex()
    return None


def _code_delegate_probe(address: str, chain_id: str) -> dict[str, Any]:
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(_rpc_url(chain_id)))
        ch = w3.eth.get_code(Web3.to_checksum_address(address))
        raw = bytes(ch)
        del_addr = _eip7702_delegate_from_code(raw)
        return {"bytecode_len": len(raw), "eip7702Delegate": del_addr}
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
        headers = {"Content-Type": "application/json"}
        try:
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
