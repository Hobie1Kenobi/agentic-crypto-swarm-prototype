"""
Shared JSON bundle: proof_bundle + external commerce + Celo Sepolia testnet reports.
Used by T54 seller (XRP) and api_seller_x402 (Base USDC / Bazaar).
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def proof_bundle_root(root: Path) -> Path:
    p = root / "artifacts" / "proof_bundle"
    if p.is_dir():
        return p
    return root / "proof_bundle"


def resolve_report_path(root: Path, rel: str) -> Path | None:
    if rel == "communication_trace.json":
        p = root / "artifacts" / "communication" / "communication_trace.json"
        if p.exists():
            return p
    ar = root / "artifacts" / "reports" / rel
    if ar.exists():
        return ar
    p2 = root / rel
    if p2.exists():
        return p2
    return None


def read_json_file(path: Path, max_bytes: int = 512_000) -> Any:
    if not path.exists():
        return None
    raw = path.read_bytes()[:max_bytes]
    return json.loads(raw.decode("utf-8"))


def read_jsonl_tail(path: Path, max_lines: int = 48) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").strip().split("\n")
    out: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def parse_csv_sample(path: Path, head: int = 5, tail: int = 30, max_rows: int = 800) -> dict[str, Any]:
    if not path.exists():
        return {"present": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return {"present": True, "headers": [], "row_count": 0, "sample_rows": []}
    header = rows[0]
    data_rows = rows[1:]
    truncated = len(data_rows) > max_rows
    sample = data_rows[:head] + data_rows[-tail:] if truncated else data_rows
    return {
        "present": True,
        "headers": header,
        "row_count": len(data_rows),
        "truncated": truncated,
        "sample_rows": sample,
    }


def project_evidence_minimal(e: dict[str, Any]) -> dict[str, Any]:
    xr = e.get("xrpl") if isinstance(e.get("xrpl"), dict) else {}
    task = e.get("task") if isinstance(e.get("task"), dict) else {}
    return {
        "cycle": e.get("cycle"),
        "status": e.get("status"),
        "start_time": e.get("start_time"),
        "xrpl_tx_hash": xr.get("tx_hash"),
        "task_id": task.get("task_id"),
        "task_template": (str(task.get("template", ""))[:240] if task.get("template") else None),
        "quoted_price_xrp": task.get("quoted_price_xrp"),
    }


def load_evidence_block(root: Path, depth: str) -> tuple[list[dict[str, Any]], list[str]]:
    ev_dir = proof_bundle_root(root) / "evidence"
    if not ev_dir.is_dir():
        return [], []
    files = sorted(ev_dir.glob("*.json"))
    max_files = 28 if depth == "full" else 14
    per_file_cap = 64_000 if depth == "full" else 14_000
    included: list[dict[str, Any]] = []
    artifacts: list[str] = []
    for p in files[:max_files]:
        try:
            raw = p.read_bytes()
            if len(raw) > per_file_cap:
                raw = raw[:per_file_cap]
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        artifacts.append(rel)
        if not isinstance(obj, dict):
            continue
        if depth == "full":
            included.append(obj)
        else:
            included.append(project_evidence_minimal(obj))
    return included, artifacts


def load_external_commerce_block(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    base = root / "external_commerce_data"
    for fname in (
        "federation-summary.json",
        "discovery-results.json",
        "providers.json",
        "provider_relationships.json",
    ):
        p = base / fname
        if not p.exists():
            continue
        key = fname.replace(".json", "")
        try:
            out[key] = read_json_file(p)
        except Exception:
            out[key] = {"error": "unreadable"}
    alt = root / "packages" / "agents" / "external_commerce_data"
    if not out.get("providers") and (alt / "providers.json").exists():
        try:
            out["providers_agents_pkg"] = read_json_file(alt / "providers.json")
        except Exception:
            pass
    t54s = base / "t54-xrpl-summary.json"
    if t54s.exists():
        try:
            out["t54_xrpl_summary"] = read_json_file(t54s)
        except Exception:
            pass
    return out


def load_celo_sepolia_block(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "chain": "celo-sepolia",
        "chain_id": 11142220,
        "explorer": "https://celo-sepolia.blockscout.com",
    }
    specs: list[tuple[str, str]] = [
        ("celo_sepolia_task_market_report.json", "task_market"),
        ("continuous_multi_rail_24h_report.json", "continuous_24h"),
        ("continuous_multi_rail_6h_report.json", "continuous_6h"),
        ("multi_rail_run_report.json", "multi_rail_run"),
        ("x402_agent_commerce_soak_report.json", "x402_soak"),
        ("realism_soak_report.json", "realism_soak"),
        ("celo_grant_tx_metrics_evidence.json", "tx_metrics_evidence"),
        ("live_xrpl_to_celo_proof_report.json", "live_xrpl_celo_proof"),
        ("hybrid_gnosis_celo_report.json", "hybrid_gnosis_celo"),
        ("public_adapter_run_report.json", "public_adapter"),
        ("customer_balance_demo_report.json", "customer_balance_demo"),
        ("communication_trace.json", "communication_trace"),
    ]
    for rel, key in specs:
        p = resolve_report_path(root, rel)
        if not p:
            continue
        try:
            out[key] = read_json_file(p, max_bytes=700_000)
        except Exception:
            out[key] = {"error": "unreadable", "path": rel}

    site = root / "docs" / "site-data.json"
    if site.exists():
        try:
            out["site_data"] = read_json_file(site, max_bytes=256_000)
        except Exception:
            out["site_data"] = None

    for rel, key in (
        ("continuous_multi_rail_24h_cycle_log.json", "continuous_24h_cycle_log"),
        ("continuous_multi_rail_cycle_log.json", "continuous_cycle_log"),
    ):
        p = resolve_report_path(root, rel)
        if not p:
            continue
        try:
            raw = read_json_file(p, max_bytes=1_200_000)
            if isinstance(raw, list):
                n = len(raw)
                out[key] = {
                    "entry_count": n,
                    "head": raw[:30],
                    "tail": raw[-30:] if n > 60 else [],
                }
            elif isinstance(raw, dict):
                out[key] = raw
        except Exception:
            pass

    return out


def build_public_data_bundle_dict(depth: str = "standard") -> dict[str, Any]:
    d = (depth or "standard").strip().lower()
    if d not in ("standard", "full"):
        d = "standard"
    root = repo_root()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    included: list[str] = []

    pb = proof_bundle_root(root)
    raw_summary = read_json_file(pb / "run-summary.json")
    if raw_summary is not None:
        included.append(str(pb.relative_to(root)).replace("\\", "/") + "/run-summary.json")
    if isinstance(raw_summary, dict):
        proof_run = raw_summary
    elif isinstance(raw_summary, list):
        proof_run = {"items": raw_summary[:200]}
    else:
        proof_run = None

    cycles = parse_csv_sample(pb / "cycles.csv")
    if cycles.get("present"):
        included.append(str(pb.relative_to(root)).replace("\\", "/") + "/cycles.csv")

    exc = parse_csv_sample(pb / "exceptions.csv", head=3, tail=15, max_rows=400)
    proof_exceptions = exc if exc.get("present") else None
    if proof_exceptions:
        included.append(str(pb.relative_to(root)).replace("\\", "/") + "/exceptions.csv")

    evidence, ev_art = load_evidence_block(root, d)
    included.extend(ev_art[:80])

    ext = load_external_commerce_block(root)
    if ext:
        included.extend(
            [
                "external_commerce_data/federation-summary.json",
                "external_commerce_data/discovery-results.json",
                "external_commerce_data/providers.json",
                "external_commerce_data/provider_relationships.json",
            ]
        )

    t54_pa = read_jsonl_tail(root / "external_commerce_data" / "t54-xrpl-payment-attempts.jsonl", max_lines=48)
    if t54_pa:
        included.append("external_commerce_data/t54-xrpl-payment-attempts.jsonl")

    inv = read_jsonl_tail(root / "external_commerce_data" / "external-invocations.jsonl", max_lines=48)
    if inv:
        included.append("external_commerce_data/external-invocations.jsonl")

    celo = load_celo_sepolia_block(root)
    included.extend(
        [
            "artifacts/reports/celo_sepolia_task_market_report.json",
            "artifacts/reports/continuous_multi_rail_24h_report.json",
            "docs/site-data.json",
        ]
    )

    return {
        "sku_id": "agent-commerce-data",
        "seller": "t54_xrpl",
        "generated_at": ts,
        "depth": d,
        "bundle_version": 2,
        "proof_run": proof_run,
        "proof_cycles": cycles,
        "proof_exceptions": proof_exceptions,
        "evidence": evidence,
        "external_commerce": ext,
        "t54_payment_attempts": t54_pa,
        "external_invocations": inv,
        "celo_sepolia": celo,
        "included_artifacts": sorted(set(included)),
        "disclaimer": (
            "Public operational artifacts and Celo Sepolia testnet reports only — no private keys or .env. "
            "Includes summarized cycle logs when large. Verify hashes on Blockscout / XRPL explorers."
        ),
    }
