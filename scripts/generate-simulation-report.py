#!/usr/bin/env python3
"""
Generate simulation_report.json and simulation_report.md from simulation_log.txt.
Optionally fetches on-chain balances if RPC and addresses are available.
Usage: python scripts/generate-simulation-report.py [--log PATH] [--output-dir PATH] [--rpc URL] [--chain-id N]
"""
import argparse
import json
import os
import re
from pathlib import Path


def find_root() -> Path:
    p = Path(__file__).resolve().parent.parent
    return p


def load_env(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        # Be tolerant of BOMs and whitespace (Windows editors often add a BOM).
        line = line.strip()
        line = line.lstrip("\ufeff")
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if m:
            out[m[1]] = m[2].strip().strip('"').strip("'")
    return out


def parse_log(content: str) -> dict:
    data = {
        "chain_id": None,
        "rpc": None,
        "total_paid_eth": None,
        "num_users": None,
        "tx_hashes": [],
        "distribution_tx": None,
        "threshold_met": False,
        "elapsed_seconds": None,
        "revenue_summary_lines": [],
        "errors": [],
    }
    def _extract_hashes(s: str) -> list[str]:
        # Some logs print `tx: <64hex>` (no 0x). Normalize to 0x-prefixed 32-byte hashes.
        matches = re.findall(r"(0x[a-fA-F0-9]{64}|[a-fA-F0-9]{64})", s)
        out: list[str] = []
        for m in matches:
            h = m if m.startswith("0x") else ("0x" + m)
            out.append(h)
        return out

    for line in content.splitlines():
        if "Chain ID:" in line:
            m = re.search(r"Chain ID:\s*(\d+)", line)
            if m:
                data["chain_id"] = int(m.group(1))
            m = re.search(r"RPC:\s*(\S+)", line)
            if m:
                data["rpc"] = m.group(1).rstrip("...")
        if "Total paid:" in line:
            m = re.search(r"Total paid:\s*([\d.]+)\s*ETH", line)
            if m:
                data["total_paid_eth"] = float(m.group(1))
        if "tx:" in line:
            hashes = _extract_hashes(line)
            if hashes:
                if "Distribution" in line:
                    data["distribution_tx"] = hashes[0]
                else:
                    data["tx_hashes"].extend(hashes)

        if "Threshold met" in line or "Distribution tx:" in line:
            data["threshold_met"] = True
        if "Distribution tx:" in line:
            hashes = _extract_hashes(line)
            if hashes:
                data["distribution_tx"] = hashes[0]
        if "Simulation finished in" in line:
            m = re.search(r"(\d+\.?\d*)\s*s", line)
            if m:
                data["elapsed_seconds"] = float(m.group(1))
        if "--- Revenue summary ---" in line or "Total paid:" in line or "Protocol fee" in line or "Distributable" in line or "Tx hashes:" in line:
            data["revenue_summary_lines"].append(line.strip())
    if not data["tx_hashes"]:
        # If tx lines didn't parse, try a fallback regex for any 64-hex hashes.
        for line in content.splitlines():
            if "tx:" in line:
                hashes = _extract_hashes(line)
                data["tx_hashes"].extend(hashes)
    return data


def fetch_balances(rpc: str, addresses: dict, chain_id: int) -> dict:
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc))
        if not w3.is_connected():
            return {}
        out = {}
        for key, addr in addresses.items():
            if not addr or addr == "0x0000000000000000000000000000000000000000":
                continue
            try:
                bal = w3.eth.get_balance(Web3.to_checksum_address(addr))
                out[key] = {"wei": str(bal), "eth": round(bal / 1e18, 6)}
            except Exception:
                pass
        return out
    except Exception:
        return {}


def main():
    root = find_root()
    parser = argparse.ArgumentParser(description="Generate simulation report from log")
    parser.add_argument("--log", type=Path, default=root / "simulation_log.txt", help="Path to simulation_log.txt")
    parser.add_argument("--output-dir", type=Path, default=root, help="Directory for simulation_report.json and .md")
    parser.add_argument("--rpc", type=str, default="", help="RPC URL for balance fetch")
    parser.add_argument("--chain-id", type=int, default=None)
    args = parser.parse_args()

    # For local Anvil runs we prefer `.env.local` (it contains deterministic keys and local addresses).
    # For public testnets (e.g. Celo Sepolia) we must prefer `.env` so we don't accidentally use Anvil keys.
    env_path = root / ".env.local"
    if not env_path.exists():
        env_path = root / ".env"
    if args.chain_id is not None and args.chain_id != 31337:
        env_path = root / ".env"
    env = load_env(env_path)

    log_path = args.log
    if not log_path.is_absolute():
        log_path = root / log_path
    if not log_path.exists():
        report = {"error": "simulation_log.txt not found", "path": str(log_path)}
        out_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "simulation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (out_dir / "simulation_report.md").write_text("# Simulation Report\n\nNo simulation log found.\n", encoding="utf-8")
        print("No log found; wrote placeholder report.")
        return

    content = log_path.read_text(encoding="utf-8")
    data = parse_log(content)

    rpc = args.rpc or env.get("RPC_URL", "")
    chain_id = args.chain_id if args.chain_id is not None else data.get("chain_id")
    if not chain_id and env.get("CHAIN_ID"):
        chain_id = int(env["CHAIN_ID"])

    addresses = {
        "revenue_contract": env.get("REVENUE_SERVICE_ADDRESS"),
        "finance_distributor": env.get("FINANCE_DISTRIBUTOR_ADDRESS"),
        "beneficiary": env.get("BENEFICIARY_ADDRESS"),
    }
    balances = {}
    if rpc and any(addresses.values()):
        balances = fetch_balances(rpc, addresses, chain_id or 31337)

    report = {
        "chain_id": chain_id or data.get("chain_id"),
        "rpc": data.get("rpc") or rpc or "(none)",
        "revenue_service_address": env.get("REVENUE_SERVICE_ADDRESS"),
        "finance_distributor_address": env.get("FINANCE_DISTRIBUTOR_ADDRESS"),
        "beneficiary_address": env.get("BENEFICIARY_ADDRESS"),
        "total_paid_eth": data.get("total_paid_eth"),
        "num_txs": len(data["tx_hashes"]),
        "tx_hashes": data["tx_hashes"],
        "distribution_tx": data.get("distribution_tx"),
        "threshold_met": data.get("threshold_met", False),
        "elapsed_seconds": data.get("elapsed_seconds"),
        "balances": balances,
    }

    out_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "simulation_report.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {json_path}")

    lines = [
        "# Simulation Report",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Chain ID | {report['chain_id'] or '—'} |",
        f"| Total paid (ETH) | {report['total_paid_eth']} |",
        f"| Number of txs | {report['num_txs']} |",
        f"| Distribution tx | {report['distribution_tx'] or '—'} |",
        f"| Threshold met | {report['threshold_met']} |",
        f"| Elapsed (s) | {report['elapsed_seconds']} |",
        "",
        "## Addresses",
        "",
        f"- Revenue service: `{report['revenue_service_address'] or '—'}`",
        f"- Finance distributor: `{report['finance_distributor_address'] or '—'}`",
        f"- Beneficiary: `{report['beneficiary_address'] or '—'}`",
        "",
        "## Balances (post-run)",
        "",
    ]
    if report.get("balances"):
        for key, b in report["balances"].items():
            lines.append(f"- **{key}**: {b['eth']} ETH")
        lines.append("")
    else:
        lines.append("(RPC not available or no addresses)")
        lines.append("")
    lines.append("## Tx hashes")
    lines.append("")
    for h in report["tx_hashes"]:
        lines.append(f"- `{h}`")
    if report.get("distribution_tx"):
        lines.append(f"- Distribution: `{report['distribution_tx']}`")
    lines.append("")

    md_path = out_dir / "simulation_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
