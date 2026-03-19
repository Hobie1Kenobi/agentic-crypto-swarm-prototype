from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

TraceBoundary = Literal[
    "real_external_integration",
    "contract_level_execution",
    "local_simulation",
    "mocked_external_replay",
    "real_xrpl_payment",
    "mock_xrpl_payment",
    "replayed_xrpl_payment",
    "real_celo_settlement",
]


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _out_dir() -> Path:
    p = (os.getenv("REPORT_OUTPUT_DIR") or "").strip()
    if p:
        out = Path(p)
        return out if out.is_absolute() else (_root() / out)
    return _root()


@dataclass
class TraceEvent:
    ts: float
    name: str
    boundary: TraceBoundary
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommunicationTrace:
    run_id: str
    market_mode: str
    public_chain_id: int | None
    public_rpc_url: str | None
    private_chain_id: int | None
    private_rpc_url: str | None
    external_source: str | None = None
    external_request_id: str | None = None
    external_tx_hash: str | None = None
    internal_task_id: int | None = None
    payment_rail: str | None = None
    payment_asset: str | None = None
    xrpl_tx_hash: str | None = None
    correlation: dict[str, Any] = field(default_factory=dict)
    events: list[TraceEvent] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)

    def add(self, name: str, boundary: TraceBoundary, **data: Any) -> None:
        self.events.append(TraceEvent(ts=time.time(), name=name, boundary=boundary, data=data))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["events"] = [asdict(e) for e in self.events]
        return d

    def write(self, basename: str = "communication_trace") -> tuple[Path, Path]:
        out = _out_dir()
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / f"{basename}.json"
        md_path = out / f"{basename}.md"

        json_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

        lines: list[str] = []
        lines.append("# Communication Trace")
        lines.append("")
        lines.append(f"- Run ID: `{self.run_id}`")
        lines.append(f"- Market mode: `{self.market_mode}`")
        if self.public_chain_id is not None:
            lines.append(f"- Public chain ID: `{self.public_chain_id}`")
        if self.private_chain_id is not None:
            lines.append(f"- Private chain ID: `{self.private_chain_id}`")
        if self.external_source:
            lines.append(f"- External source: `{self.external_source}`")
        if self.external_request_id:
            lines.append(f"- External request ID: `{self.external_request_id}`")
        if self.external_tx_hash:
            lines.append(f"- External tx hash: `{self.external_tx_hash}`")
        if self.internal_task_id is not None:
            lines.append(f"- Internal task ID: `{self.internal_task_id}`")
        if self.payment_rail:
            lines.append(f"- Payment rail: `{self.payment_rail}`")
        if self.payment_asset:
            lines.append(f"- Payment asset: `{self.payment_asset}`")
        if self.xrpl_tx_hash:
            lines.append(f"- XRPL tx hash: `{self.xrpl_tx_hash}`")
        lines.append("")
        lines.append("## Events")
        lines.append("")
        for e in self.events:
            lines.append(f"- `{e.name}` ({e.boundary}) @ `{int(e.ts)}`")
            if e.data:
                for k, v in e.data.items():
                    lines.append(f"  - **{k}**: `{v}`")
        lines.append("")
        if self.outcome:
            lines.append("## Outcome")
            lines.append("")
            for k, v in self.outcome.items():
                lines.append(f"- **{k}**: `{v}`")
            lines.append("")

        if self.correlation:
            lines.append("## Correlation")
            lines.append("")
            if isinstance(self.correlation.get("olas"), dict):
                ol = self.correlation.get("olas") or {}
                if ol.get("request_id"):
                    lines.append(f"- Olas request ID: `{ol.get('request_id')}`")
                if ol.get("tx_hash"):
                    lines.append(f"- Olas tx hash: `{ol.get('tx_hash')}`")
            if isinstance(self.correlation.get("private"), dict):
                pr = self.correlation.get("private") or {}
                if pr.get("task_id") is not None:
                    lines.append(f"- Internal task ID: `{pr.get('task_id')}`")
                txs = pr.get("tx_hashes") or []
                if isinstance(txs, list) and txs:
                    lines.append(f"- Internal tx count: `{len(txs)}`")
                    for t in txs:
                        if isinstance(t, dict) and t.get("tx_hash"):
                            lines.append(f"- {t.get('name')}: `{t.get('tx_hash')}`")
            if isinstance(self.correlation.get("xrpl_payment"), dict):
                xp = self.correlation.get("xrpl_payment") or {}
                if xp.get("tx_hash"):
                    lines.append(f"- XRPL payment tx: `{xp.get('tx_hash')}`")
                if xp.get("external_payment_id"):
                    lines.append(f"- XRPL payment ID: `{xp.get('external_payment_id')}`")
            lines.append("")

        has_real_xrpl = any(e.boundary == "real_xrpl_payment" for e in self.events)
        if has_real_xrpl and self.xrpl_tx_hash and self.outcome.get("ok"):
            lines.append("## Live Proof (XRPL → Celo Multi-Rail)")
            lines.append("")
            lines.append("This run achieved **live XRPL payment** + **live Celo settlement**. See presentation-grade proof:")
            lines.append("")
            lines.append("- **Proof report:** [live_xrpl_to_celo_proof_report.md](live_xrpl_to_celo_proof_report.md)")
            lines.append("- **Machine-readable:** [live_xrpl_to_celo_proof_report.json](live_xrpl_to_celo_proof_report.json)")
            lines.append("")
            xrpl_explorer = f"https://testnet.xrpl.org/transactions/{self.xrpl_tx_hash}"
            lines.append(f"| Rail | Status | Tx / Task |")
            lines.append(f"|------|--------|-----------|")
            lines.append(f"| XRPL (machine payments) | ✅ Verified | [{self.xrpl_tx_hash[:8]}...]({xrpl_explorer}) |")
            pr = self.correlation.get("private") or {}
            tx_count = len(pr.get("tx_hashes") or [])
            task_id = pr.get("task_id", self.internal_task_id)
            lines.append(f"| Celo (private settlement) | ✅ Finalized | Task {task_id}, {tx_count} txs |")
            lines.append("")

        md_path.write_text("\n".join(lines), encoding="utf-8")
        return json_path, md_path

