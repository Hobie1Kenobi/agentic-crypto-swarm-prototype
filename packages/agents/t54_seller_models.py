"""
Structured JSON bodies for T54 x402 seller SKUs (validated before HTTP 200).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StructuredQueryResponse(BaseModel):
    sku_id: str = Field(default="structured-query")
    seller: str = Field(default="t54_xrpl")
    query: str
    answer: str
    constitution_safe: bool = True


class ResearchSource(BaseModel):
    label: str = Field(description="Short label for the source slot (e.g. user-provided, general knowledge)")
    note: str = Field(default="", description="What this slot represents")


class ResearchBriefResponse(BaseModel):
    sku_id: str = Field(default="research-brief")
    seller: str = Field(default="t54_xrpl")
    topic: str
    title: str
    sections: list[str] = Field(min_length=1, description="Ordered sections of the brief")
    sources: list[ResearchSource] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Not financial advice. No live web or social feeds unless you supplied URLs in context."
    )


class ConstitutionAuditLiteResponse(BaseModel):
    sku_id: str = Field(default="constitution-audit-lite")
    seller: str = Field(default="t54_xrpl")
    input_summary: str
    jailbreak_risk: str = Field(description="low|medium|high")
    ethical_alignment_notes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Heuristic LLM review only — not a substitute for security or legal review."
    )


class AirdropOpportunity(BaseModel):
    name: str
    farm_score: int = Field(ge=0, le=100, description="0-100 screening score")
    rationale: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    constitution_pass: bool = True


class AirdropIntelligenceReportResponse(BaseModel):
    sku_id: str = Field(default="airdrop-intelligence-report")
    seller: str = Field(default="t54_xrpl")
    topic: str
    generated_at: str
    farm_score_threshold: int = Field(default=75, description="Default gate for follow-up review")
    opportunities: list[AirdropOpportunity] = Field(default_factory=list)
    scan_summary: str = ""
    notes: str = ""
    disclaimer: str = Field(
        default="Heuristic LLM screening only — not financial advice. "
        "No chain execution is performed by this endpoint."
    )


class HelloResponse(BaseModel):
    sku_id: str = Field(default="hello")
    seller: str = Field(default="t54_xrpl")
    path: str
    message: str


class AgentCommerceDataResponse(BaseModel):
    sku_id: str = Field(default="agent-commerce-data")
    seller: str = Field(default="t54_xrpl")
    generated_at: str
    depth: str = Field(description="standard | full")
    bundle_version: int = 2
    proof_run: dict[str, Any] | None = None
    proof_cycles: dict[str, Any] = Field(
        default_factory=dict,
        description="CSV-derived cycle table: headers, row_count, sample_rows",
    )
    proof_exceptions: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-cycle proof excerpts (fuller when depth=full)",
    )
    external_commerce: dict[str, Any] = Field(
        default_factory=dict,
        description="Federation summary, discovery snapshot, providers, relationships",
    )
    t54_payment_attempts: list[dict[str, Any]] = Field(default_factory=list)
    external_invocations: list[dict[str, Any]] = Field(default_factory=list)
    celo_sepolia: dict[str, Any] = Field(
        default_factory=dict,
        description="Celo Sepolia testnet reports, soak metrics, site-data, cycle logs (when present on server)",
    )
    included_artifacts: list[str] = Field(
        default_factory=list,
        description="Logical names of datasets included in this response",
    )
    disclaimer: str = Field(
        default="Public operational and proof artifacts only — no private keys or .env contents. "
        "On-chain addresses appear as in public explorers."
    )
