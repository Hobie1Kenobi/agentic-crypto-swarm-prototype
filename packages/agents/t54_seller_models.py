"""
Structured JSON bodies for T54 x402 seller SKUs (validated before HTTP 200).
"""
from __future__ import annotations

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


class HelloResponse(BaseModel):
    sku_id: str = Field(default="hello")
    seller: str = Field(default="t54_xrpl")
    path: str
    message: str
