"""
Single source of truth for Base USDC x402 marketplace SKUs.

Route registration, /.well-known/x402.json, recommendations, and audit:x402
must derive from this catalog to prevent price/path drift.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def public_api_origin() -> str:
    for key in ("PUBLIC_API_ORIGIN", "MARKETPLACE_PUBLIC_BASE_URL", "X402_SELLER_PUBLIC_URL"):
        raw = _env(key)
        if not raw:
            continue
        if "/x402/" in raw:
            raw = raw.split("/x402/")[0]
        return raw.rstrip("/")
    return "https://api.agentic-swarm-marketplace.com"


def _price_usd(env_name: str, default: str) -> float:
    raw = _env(env_name, default).lstrip("$").strip()
    try:
        return float(raw)
    except ValueError:
        return float(default.lstrip("$"))


def _format_usd_amount(amount: float) -> str:
    """USDC display with enough decimals to keep SKU prices unique."""
    if amount >= 1:
        return f"{amount:.2f}"
    text = f"{amount:.6f}".rstrip("0").rstrip(".")
    if "." not in text:
        return f"{amount:.2f}"
    return text


def _price_str(amount: float) -> str:
    return f"${_format_usd_amount(amount)}"


NetworkId = Literal["eip155:8453"]
SkuStatus = Literal["active", "beta", "deprecated"]
HttpMethod = Literal["GET", "POST"]


@dataclass(frozen=True)
class MarketplaceSku:
    id: str
    name: str
    version: str
    method: HttpMethod
    path: str
    description: str
    price_usd: float
    network: NetworkId
    asset: str
    receiver_env: str
    tags: tuple[str, ...]
    use_cases: tuple[str, ...]
    expected_latency_ms: int
    status: SkuStatus
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    example_request: dict[str, Any] = field(default_factory=dict)
    example_response: dict[str, Any] = field(default_factory=dict)
    price_env: str = ""
    mime_type: str = "application/json"

    @property
    def full_resource_url(self) -> str:
        return f"{public_api_origin()}{self.path}"

    @property
    def route_key(self) -> str:
        return f"{self.method} {self.path}"

    def price_accepts(self) -> str:
        return _price_str(self.price_usd)

    def manifest_price(self) -> str:
        return f"{_format_usd_amount(self.price_usd)} USDC"


USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
NETWORK: NetworkId = "eip155:8453"


def load_base_x402_skus(*, receiver: str = "") -> list[MarketplaceSku]:
    """Build the live Base SKU catalog using current env price overrides."""
    _ = receiver  # receiver is injected at route/manifest time; kept for API symmetry
    skus = [
        MarketplaceSku(
            id="structured-query",
            name="Constitution-safe Query",
            version="1.0.0",
            method="GET",
            path="/x402/v1/query",
            description=(
                "Returns a constitution-safe short-form answer to an agent question with "
                "source attribution. Use for lightweight Q&A before purchasing deeper research."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE", "0.012"),
            price_env="X402_SELLER_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("query", "llm", "entry"),
            use_cases=("quick agent Q&A", "capability probe"),
            expected_latency_ms=800,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Natural-language question"},
                    "depth": {"type": "string", "enum": ["brief", "standard"], "default": "brief"},
                },
                "required": ["q"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "answer": {"type": "string"},
                    "confidence": {"type": "number"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["answer"],
            },
            example_request={"q": "What is x402 micropayment settlement?"},
            example_response={
                "query": "What is x402 micropayment settlement?",
                "answer": "x402 settles HTTP 402 challenges with on-chain payments.",
                "confidence": 0.85,
                "sources": ["agentic-swarm-x402"],
            },
        ),
        MarketplaceSku(
            id="research-brief",
            name="Research Brief",
            version="1.0.0",
            method="GET",
            path="/x402/v1/research-brief",
            description=(
                "Produces a multi-section research brief with executive summary, findings, and "
                "citations for agent due-diligence pipelines."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_RESEARCH", "0.06"),
            price_env="X402_SELLER_PRICE_RESEARCH",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("research", "llm"),
            use_cases=("topic research", "due diligence"),
            expected_latency_ms=2500,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["topic"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "sku_id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "sections": {"type": "array"},
                },
                "required": ["sku_id", "summary"],
            },
            example_request={"topic": "Agent commerce rails on Base"},
            example_response={
                "sku_id": "research-brief",
                "title": "Agent commerce rails on Base",
                "summary": "Base USDC x402 enables pay-per-request agent APIs.",
                "sections": [],
            },
        ),
        MarketplaceSku(
            id="constitution-audit-lite",
            name="Constitution Audit Lite",
            version="1.0.0",
            method="GET",
            path="/x402/v1/constitution-audit",
            description=(
                "Heuristic ethics and constitution-style review of a prompt excerpt. Returns "
                "pass/fail, violation flags, and severity for agent policy screening."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_CONSTITUTION", "0.03"),
            price_env="X402_SELLER_PRICE_CONSTITUTION",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("compliance", "ethics"),
            use_cases=("prompt screening", "policy gates"),
            expected_latency_ms=1200,
            status="active",
            input_schema={
                "type": "object",
                "properties": {"prompt_snippet": {"type": "string"}},
                "required": ["prompt_snippet"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "sku_id": {"type": "string"},
                    "pass_": {"type": "boolean"},
                    "flags": {"type": "array"},
                },
            },
            example_request={"prompt_snippet": "Summarize ethical agent commerce norms."},
            example_response={"sku_id": "constitution-audit-lite", "flags": []},
        ),
        MarketplaceSku(
            id="agent-commerce-data",
            name="Agent Commerce Data Bundle",
            version="1.0.0",
            method="GET",
            path="/x402/v1/agent-commerce-data",
            description=(
                "Premium machine-readable x402 commerce intelligence bundle: catalog snapshot, "
                "median pricing signals, earning playbooks, and ecosystem JSON for agents optimizing "
                "marketplace presence."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_COMMERCE", "0.07"),
            price_env="X402_SELLER_PRICE_COMMERCE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "catalog", "intelligence"),
            use_cases=("marketplace optimization", "pricing research"),
            expected_latency_ms=1500,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "depth": {"type": "string", "enum": ["standard", "full"], "default": "standard"}
                },
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "proof_run": {"type": "object"}},
                "required": ["sku_id"],
            },
            example_request={"depth": "standard"},
            example_response={"sku_id": "agent-commerce-data", "proof_run": {}},
        ),
        MarketplaceSku(
            id="ecosystem-pulse",
            name="Ecosystem Pulse",
            version="1.0.0",
            method="GET",
            path="/x402/v1/ecosystem-pulse",
            description=(
                "Returns a current machine-readable PoCon operational snapshot of Agentic Swarm "
                "Marketplace activity: oracle prices, worker status, bazaar readiness, intake "
                "inventory, and signal flags. Intended for autonomous agents monitoring whether to "
                "purchase deeper marketplace intelligence. Optional fresh=1 rebuilds from live feeds."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_PULSE", "0.04"),
            price_env="X402_SELLER_PRICE_PULSE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("pulse", "monitoring", "entry", "pocon"),
            use_cases=("scheduled monitoring", "discovery probe", "ops telemetry"),
            expected_latency_ms=400,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "fresh": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "1 rebuilds pulse from live feeds",
                    }
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "sku_id": {"type": "string"},
                    "generated_at": {"type": "string"},
                    "headline": {"type": "string"},
                    "summary": {"type": "string"},
                    "sections": {"type": "array", "items": {"type": "string"}},
                    "signals": {"type": "array"},
                    "recommended_next_actions": {"type": "array"},
                },
                "required": ["sku_id", "headline", "summary", "sections"],
            },
            example_request={},
            example_response={
                "sku_id": "ecosystem-pulse",
                "generated_at": "2026-07-22T00:00:00Z",
                "headline": "Marketplace operational",
                "summary": "Oracle live; workers idle.",
                "sections": ["oracle", "workers"],
                "signals": [],
            },
        ),
        MarketplaceSku(
            id="airdrop-intelligence-report",
            name="Airdrop Intelligence",
            version="1.0.0",
            method="GET",
            path="/x402/v1/airdrop-intelligence",
            description=(
                "Constitution-first airdrop and incentive screening with Farm Score 0-100, risk "
                "flags, and optional EVM contract triage. No on-chain claim execution."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_AIRDROP", "0.09"),
            price_env="X402_SELLER_PRICE_AIRDROP",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("airdrop", "security", "intel"),
            use_cases=("scam filter", "farm score"),
            expected_latency_ms=2000,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "context": {"type": "string"},
                    "contractAddress": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "farm_score": {"type": "number"}},
                "required": ["sku_id"],
            },
            example_request={"topic": "Base meme airdrop screening"},
            example_response={"sku_id": "airdrop-intelligence-report", "farm_score": 42},
        ),
        MarketplaceSku(
            id="contract-triage",
            name="Contract Triage",
            version="1.0.0",
            method="GET",
            path="/x402/v1/contract-triage",
            description=(
                "Fast EVM smart-contract malicious-pattern triage. Returns risk score, verdict, "
                "top flags, and Phase-6 counterparty intel within ~30s for a single address."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_TRIAGE", "0.02"),
            price_env="X402_SELLER_PRICE_TRIAGE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("security", "audit", "triage"),
            use_cases=("pre-trade screen", "wallet risk"),
            expected_latency_ms=3000,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "contractAddress": {"type": "string"},
                    "chainId": {"type": "string", "default": "eip155:8453"},
                },
                "required": ["contractAddress"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "riskScore": {"type": "number"},
                    "verdict": {"type": "string"},
                    "topFlags": {"type": "array"},
                },
                "required": ["riskScore", "verdict"],
            },
            example_request={"contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
            example_response={"riskScore": 12, "verdict": "SAFE", "topFlags": []},
        ),
        MarketplaceSku(
            id="contract-audit",
            name="Contract Deep Audit",
            version="1.0.0",
            method="GET",
            path="/x402/v1/contract-audit",
            description=(
                "Full 5-phase EVM contract security audit for up to 3 addresses: Slither, Echidna "
                "fork fuzzing, deployer profiling, money-flow tracing, and holder concentration."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_DEEP_AUDIT", "0.49"),
            price_env="X402_SELLER_PRICE_DEEP_AUDIT",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("security", "audit", "deep"),
            use_cases=("full diligence", "protocol review"),
            expected_latency_ms=120000,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "addresses": {"type": "string", "description": "Comma-separated addresses"},
                    "chainId": {"type": "string", "default": "eip155:8453"},
                },
                "required": ["addresses"],
            },
            output_schema={"type": "object", "properties": {"contracts": {"type": "array"}}},
            example_request={"addresses": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
            example_response={"contracts": []},
        ),
        MarketplaceSku(
            id="contract-monitor",
            name="Contract Monitor Subscription",
            version="1.0.0",
            method="POST",
            path="/x402/v1/contract-monitor",
            description=(
                "30-day continuous monitoring subscription for up to 10 EVM addresses with webhook "
                "alerts on admin movement, claim changes, liquidity breaches, and new critical findings."
            ),
            price_usd=_price_usd("X402_SELLER_PRICE_MONITOR", "4.99"),
            price_env="X402_SELLER_PRICE_MONITOR",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("security", "monitoring", "subscription"),
            use_cases=("position watch", "protocol ops"),
            expected_latency_ms=2000,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "addresses": {"type": "array", "items": {"type": "string"}},
                    "webhookUrl": {"type": "string"},
                    "thresholds": {"type": "object"},
                    "durationDays": {"type": "integer", "default": 30},
                },
                "required": ["addresses", "webhookUrl"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "subscriptionId": {"type": "string"},
                    "expiresAt": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            example_request={
                "addresses": ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
                "webhookUrl": "https://example.com/hooks/asm",
                "durationDays": 30,
            },
            example_response={
                "subscriptionId": "sub_example",
                "expiresAt": "2026-08-21T00:00:00Z",
                "status": "active",
            },
        ),
        MarketplaceSku(
            id="celo-agent-data",
            name="Celo Agent Data Bundle",
            version="1.0.0",
            method="GET",
            path="/x402/v1/celo-agent-data",
            description=(
                "Public Celo Sepolia soak/proof and x402 commerce JSON bundle settled in Base USDC. "
                "Use when an agent needs verifiable Celo-rail evidence packaged for buyers."
            ),
            price_usd=_price_usd("X402_SELLER_DATA_PRICE", "0.08"),
            price_env="X402_SELLER_DATA_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("celo", "commerce", "proof"),
            use_cases=("celo evidence pack", "soak proofs"),
            expected_latency_ms=1200,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "depth": {"type": "string", "enum": ["standard", "full"], "default": "standard"}
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "sku_id": {"type": "string"},
                    "listing_id": {"type": "string"},
                    "rail": {"type": "string"},
                },
                "required": ["sku_id"],
            },
            example_request={"depth": "standard"},
            example_response={
                "sku_id": "agent-commerce-data",
                "listing_id": "celo-agent-data",
                "rail": "base_x402_usdc",
            },
        ),
        MarketplaceSku(
            id="intake-resale-pack",
            name="Intake Resale Pack",
            version="1.0.0",
            method="GET",
            path="/x402/v1/intake-resale",
            description=(
                "Replays a minted intake bundle by pack_id (same artifact files as the T54 rail), "
                "settled in Base USDC."
            ),
            price_usd=_price_usd("X402_INTAKE_RESALE_PRICE", "0.05"),
            price_env="X402_INTAKE_RESALE_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("intake", "resale"),
            use_cases=("pack replay", "artifact delivery"),
            expected_latency_ms=500,
            status="active",
            input_schema={
                "type": "object",
                "properties": {"pack_id": {"type": "string"}},
                "required": ["pack_id"],
            },
            output_schema={
                "type": "object",
                "properties": {"pack_id": {"type": "string"}, "bundle": {"type": "object"}},
            },
            example_request={"pack_id": "00000000-0000-0000-0000-000000000000"},
            example_response={"pack_id": "00000000-0000-0000-0000-000000000000", "bundle": {}},
        ),
        # --- LCG Agentic Commerce Exchange ladder (cyber/cloud/software vertical) ---
        MarketplaceSku(
            id="commerce-product-search",
            name="Commerce Product Search",
            version="1.0.0",
            method="GET",
            path="/x402/v1/commerce/product-search",
            description=(
                "Returns normalized technology product candidates for LCG procurement workflows "
                "(cybersecurity, cloud, SaaS). Distinguishes catalog vs estimated vs quoted prices. "
                "Demo catalog seeded for tests — not live distributor inventory."
            ),
            price_usd=_price_usd("X402_COMMERCE_SEARCH_PRICE", "0.11"),
            price_env="X402_COMMERCE_SEARCH_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "procurement", "lcg", "search"),
            use_cases=("buyer agent product discovery", "procurement shortlist"),
            expected_latency_ms=400,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "results": {"type": "array"}},
                "required": ["sku_id"],
            },
            example_request={"q": "endpoint", "category": "cybersecurity-software"},
            example_response={"sku_id": "commerce-product-search", "count": 1, "results": []},
        ),
        MarketplaceSku(
            id="commerce-product-evidence",
            name="Product Evidence Pack",
            version="1.0.0",
            method="GET",
            path="/x402/v1/commerce/product-evidence",
            description=(
                "Returns source-attributed product evidence, specifications, and confidence for a "
                "catalog product ID. Partial verification is labeled — never invents manufacturer claims."
            ),
            price_usd=_price_usd("X402_COMMERCE_EVIDENCE_PRICE", "0.16"),
            price_env="X402_COMMERCE_EVIDENCE_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "evidence", "lcg"),
            use_cases=("spec verification", "due diligence"),
            expected_latency_ms=500,
            status="active",
            input_schema={
                "type": "object",
                "properties": {"productId": {"type": "string"}},
                "required": ["productId"],
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "evidence": {"type": "array"}},
                "required": ["sku_id"],
            },
            example_request={"productId": "prod_wasabi_hot_cloud_storage"},
            example_response={"sku_id": "commerce-product-evidence", "evidence": []},
        ),
        MarketplaceSku(
            id="commerce-supplier-trust",
            name="Supplier Trust Check",
            version="1.0.0",
            method="GET",
            path="/x402/v1/commerce/supplier-trust",
            description=(
                "Returns supplier relationship status, risk indicators, and authorization evidence "
                "flags for LCG orchestration. Mock suppliers are explicitly labeled."
            ),
            price_usd=_price_usd("X402_COMMERCE_TRUST_PRICE", "0.26"),
            price_env="X402_COMMERCE_TRUST_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "supplier", "trust", "lcg"),
            use_cases=("counterparty screening", "reseller verification"),
            expected_latency_ms=400,
            status="active",
            input_schema={
                "type": "object",
                "properties": {"supplierId": {"type": "string"}},
                "required": ["supplierId"],
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "trustScore": {"type": "number"}},
                "required": ["sku_id"],
            },
            example_request={"supplierId": "sup_mock_distributor_a"},
            example_response={"sku_id": "commerce-supplier-trust", "trustScore": 35},
        ),
        MarketplaceSku(
            id="commerce-compatibility-check",
            name="Compatibility Check",
            version="1.0.0",
            method="GET",
            path="/x402/v1/commerce/compatibility-check",
            description=(
                "Heuristic check whether a product's recorded specifications satisfy structured "
                "buyer requirements. Not a substitute for engineering sign-off."
            ),
            price_usd=_price_usd("X402_COMMERCE_COMPAT_PRICE", "1.10"),
            price_env="X402_COMMERCE_COMPAT_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "compatibility", "lcg"),
            use_cases=("requirements fit", "configuration gate"),
            expected_latency_ms=500,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "productId": {"type": "string"},
                    "requirements": {"type": "string", "description": "JSON object string"},
                },
                "required": ["productId"],
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "result": {"type": "string"}},
                "required": ["sku_id"],
            },
            example_request={"productId": "prod_wasabi_hot_cloud_storage", "requirements": "{\"api\":\"S3\"}"},
            example_response={"sku_id": "commerce-compatibility-check", "result": "confirmed_fit"},
        ),
        MarketplaceSku(
            id="commerce-quote-comparison",
            name="Quote Comparison",
            version="1.0.0",
            method="GET",
            path="/x402/v1/commerce/quote-comparison",
            description=(
                "Requests mock supplier quotes for a product and ranks them by total and expiration. "
                "Uses demo adapters only — not live distributor pricing."
            ),
            price_usd=_price_usd("X402_COMMERCE_QUOTE_PRICE", "2.40"),
            price_env="X402_COMMERCE_QUOTE_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "quotes", "lcg"),
            use_cases=("multi-quote compare", "sourcing shortlist"),
            expected_latency_ms=800,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "productId": {"type": "string"},
                    "quantity": {"type": "integer", "default": 1},
                },
                "required": ["productId"],
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "comparison": {"type": "object"}},
                "required": ["sku_id"],
            },
            example_request={"productId": "prod_microsoft_365_e3", "quantity": 50},
            example_response={"sku_id": "commerce-quote-comparison", "quoteIds": []},
        ),
        MarketplaceSku(
            id="commerce-compliance-check",
            name="Procurement Compliance Check",
            version="1.0.0",
            method="GET",
            path="/x402/v1/commerce/compliance-check",
            description=(
                "Evaluates a quote against configurable procurement requirements and returns "
                "likely_compliant / exception_identified / evidence_missing. Not legal advice."
            ),
            price_usd=_price_usd("X402_COMMERCE_COMPLIANCE_PRICE", "5.25"),
            price_env="X402_COMMERCE_COMPLIANCE_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "compliance", "lcg"),
            use_cases=("quote completeness", "exception surfacing"),
            expected_latency_ms=600,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "quoteId": {"type": "string"},
                    "requirements": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {"sku_id": {"type": "string"}, "result": {"type": "string"}},
                "required": ["sku_id"],
            },
            example_request={"quoteId": "qte_example"},
            example_response={"sku_id": "commerce-compliance-check", "result": "evidence_missing"},
        ),
        MarketplaceSku(
            id="commerce-purchase-readiness",
            name="Purchase Readiness Package",
            version="1.0.0",
            method="GET",
            path="/x402/v1/commerce/purchase-readiness",
            description=(
                "Produces an approval-oriented package: evidence + mock quote comparison + next-step "
                "mandate/handoff guidance. Live ordering remains disabled."
            ),
            price_usd=_price_usd("X402_COMMERCE_READINESS_PRICE", "9.50"),
            price_env="X402_COMMERCE_READINESS_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("commerce", "readiness", "lcg"),
            use_cases=("approval package", "handoff prep"),
            expected_latency_ms=1200,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "productId": {"type": "string"},
                    "quantity": {"type": "integer", "default": 1},
                },
                "required": ["productId"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "sku_id": {"type": "string"},
                    "liveOrderingEnabled": {"type": "boolean"},
                },
                "required": ["sku_id"],
            },
            example_request={"productId": "prod_egnyte_business", "quantity": 25},
            example_response={
                "sku_id": "commerce-purchase-readiness",
                "liveOrderingEnabled": False,
            },
        ),
        # --- LCG Procurement Intelligence (buyer-supplied; no live distributor data) ---
        MarketplaceSku(
            id="procurement-readiness",
            name="LCG Procurement Readiness Scan",
            version="1.0.0",
            method="POST",
            path="/x402/v1/procurement-readiness",
            description=(
                "Analyzes a technology purchase request, RFQ excerpt, bill of materials, or procurement "
                "requirement and returns a machine-readable readiness score, missing specifications, "
                "ambiguities, commercial risks, and recommended next actions. Designed for autonomous "
                "purchasing agents, VARs, MSPs, resellers, and procurement teams. Does not claim live "
                "pricing or inventory unless verified distributor data is explicitly included."
            ),
            price_usd=_price_usd("X402_LCG_PROCUREMENT_READINESS_PRICE", "0.10"),
            price_env="X402_LCG_PROCUREMENT_READINESS_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("lcg", "procurement", "readiness", "rfq", "compliance"),
            use_cases=("purchase requirement diagnosis", "agent discovery entry"),
            expected_latency_ms=400,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "purchase_type": {"type": "string"},
                    "requirements_text": {"type": "string"},
                    "buyer_type": {"type": "string", "enum": ["commercial", "government", "public", "sled", "federal"]},
                    "delivery_region": {"type": "string"},
                    "required_by": {"type": "string"},
                    "quote_text": {"type": "string"},
                    "bom": {"type": "array"},
                },
                "required": ["requirements_text"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "sku": {"type": "string"},
                    "confidence": {"type": "number"},
                    "result": {"type": "object"},
                },
                "required": ["sku", "result"],
            },
            example_request={
                "purchase_type": "hardware",
                "requirements_text": "Need 25 business laptops with 16GB RAM, 512GB SSD, Windows 11 Pro, 3-year warranty",
                "buyer_type": "commercial",
                "delivery_region": "US-TX",
                "required_by": "2026-09-15",
            },
            example_response={
                "sku": "procurement-readiness",
                "confidence": 0.8,
                "result": {"readiness_score": 74, "pass_fail": "pass"},
                "evidence_basis": {"live_distributor_data_used": False},
            },
        ),
        MarketplaceSku(
            id="specification-normalizer",
            name="Product Specification Normalizer",
            version="1.0.0",
            method="POST",
            path="/x402/v1/specification-normalizer",
            description=(
                "Converts inconsistent technology product descriptions into structured procurement fields "
                "(category, CPU class, RAM, storage, OS, warranty, quantity, approved-equivalent flags, "
                "unresolved fields). Buyer-supplied text only; not live catalog data."
            ),
            price_usd=_price_usd("X402_LCG_SPEC_NORMALIZER_PRICE", "0.15"),
            price_env="X402_LCG_SPEC_NORMALIZER_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("lcg", "procurement", "normalization", "bom"),
            use_cases=("normalize vendor request language", "prep for quoting"),
            expected_latency_ms=350,
            status="active",
            input_schema={
                "type": "object",
                "properties": {"description": {"type": "string"}, "requirements_text": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "properties": {"sku": {"type": "string"}, "result": {"type": "object"}},
                "required": ["sku"],
            },
            example_request={"description": "Dell or equivalent laptop, i5, 16 GB RAM, 3-year warranty"},
            example_response={"sku": "specification-normalizer", "result": {"normalized": {"ram_gb": 16}}},
        ),
        MarketplaceSku(
            id="quote-completeness-audit",
            name="Quote Completeness Audit",
            version="1.0.0",
            method="POST",
            path="/x402/v1/quote-completeness-audit",
            description=(
                "Audits a supplier quote (structured JSON or text) for line-total consistency, missing MPNs, "
                "freight/tax/expiration/warranty/payment-term gaps, substitutions, and service coverage. "
                "Returns completeness score and categorized issues. Not a live price check."
            ),
            price_usd=_price_usd("X402_LCG_QUOTE_AUDIT_PRICE", "0.25"),
            price_env="X402_LCG_QUOTE_AUDIT_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("lcg", "procurement", "quote", "audit"),
            use_cases=("quote QA before approval", "purchasing decision support"),
            expected_latency_ms=400,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "quote_text": {"type": "string"},
                    "quote": {"type": "object"},
                    "line_items": {"type": "array"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {"sku": {"type": "string"}, "result": {"type": "object"}},
                "required": ["sku"],
            },
            example_request={
                "quote": {
                    "lineItems": [
                        {"description": "M365 E3", "quantity": 50, "unitPrice": 34.5, "extendedPrice": 1725}
                    ]
                }
            },
            example_response={"sku": "quote-completeness-audit", "result": {"completeness_score": 70, "pass_fail": "fail"}},
        ),
        MarketplaceSku(
            id="rfp-requirement-extractor",
            name="RFP Technology Requirement Extractor",
            version="1.0.0",
            method="POST",
            path="/x402/v1/rfp-requirement-extractor",
            description=(
                "Extracts structured mandatory requirements, deliverables, quantities, brands/equivalents, "
                "deadlines, evaluation factors, forms, certifications, and clarification questions from RFQ/RFP/SOW text. "
                "Informational procurement aid — not legal advice."
            ),
            price_usd=_price_usd("X402_LCG_RFP_EXTRACTOR_PRICE", "0.50"),
            price_env="X402_LCG_RFP_EXTRACTOR_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("lcg", "procurement", "rfp", "rfq"),
            use_cases=("solicitation parsing", "proposal prep"),
            expected_latency_ms=500,
            status="active",
            input_schema={
                "type": "object",
                "properties": {"rfp_text": {"type": "string"}, "text": {"type": "string"}},
                "required": ["rfp_text"],
            },
            output_schema={
                "type": "object",
                "properties": {"sku": {"type": "string"}, "result": {"type": "object"}},
                "required": ["sku"],
            },
            example_request={"rfp_text": "Vendor shall provide 100 laptops. Delivery US-TX by 2026-09-15. Section 508 required."},
            example_response={"sku": "rfp-requirement-extractor", "result": {"mandatory_requirements": []}},
        ),
        MarketplaceSku(
            id="bid-fit-score",
            name="Bid Fit Score",
            version="1.0.0",
            method="POST",
            path="/x402/v1/bid-fit-score",
            description=(
                "Scores opportunity fit for a VAR/MSP/reseller/government contractor using opportunity requirements, "
                "capabilities, certifications, geography, partner access, and constraints. Returns pursue/no-go style "
                "recommendation with gaps and partner dependencies. Not a guarantee of award."
            ),
            price_usd=_price_usd("X402_LCG_BID_FIT_PRICE", "1.00"),
            price_env="X402_LCG_BID_FIT_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("lcg", "procurement", "bid", "fit"),
            use_cases=("go/no-go", "reseller opportunity triage"),
            expected_latency_ms=450,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "opportunity_requirements": {"type": "string"},
                    "company_capabilities": {"type": "array", "items": {"type": "string"}},
                    "certifications": {"type": "array", "items": {"type": "string"}},
                    "geography": {"type": "string"},
                    "partner_access": {"type": "array", "items": {"type": "string"}},
                    "performance_constraints": {"type": "string"},
                },
                "required": ["opportunity_requirements"],
            },
            output_schema={
                "type": "object",
                "properties": {"sku": {"type": "string"}, "result": {"type": "object"}},
                "required": ["sku"],
            },
            example_request={
                "opportunity_requirements": "SLED laptop refresh; TD SYNNEX or D&H fulfillment preferred",
                "certifications": ["vosb"],
                "partner_access": ["d&h", "td synnex"],
                "geography": "US-TX",
            },
            example_response={"sku": "bid-fit-score", "result": {"fit_score": 86, "recommendation": "pursue"}},
        ),
        MarketplaceSku(
            id="bom-risk-audit",
            name="Technology BOM Risk Audit",
            version="1.0.0",
            method="POST",
            path="/x402/v1/bom-risk-audit",
            description=(
                "Analyzes a technology bill of materials for incomplete configs, missing licenses/support/optics, "
                "duplicates, EOL risks, and quantity gaps. Labels findings as confirmed, inferred, or requiring "
                "manufacturer/distributor verification. No live stock claims."
            ),
            price_usd=_price_usd("X402_LCG_BOM_RISK_PRICE", "2.50"),
            price_env="X402_LCG_BOM_RISK_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("lcg", "procurement", "bom", "risk"),
            use_cases=("BOM QA", "configuration risk"),
            expected_latency_ms=600,
            status="active",
            input_schema={
                "type": "object",
                "properties": {"bom": {"type": "array"}, "line_items": {"type": "array"}, "text": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "properties": {"sku": {"type": "string"}, "result": {"type": "object"}},
                "required": ["sku"],
            },
            example_request={
                "bom": [
                    {"description": "48-port switch", "quantity": 2},
                    {"description": "48-port switch", "quantity": 2},
                ]
            },
            example_response={"sku": "bom-risk-audit", "result": {"risk_score": 70, "pass_fail": "pass"}},
        ),
        MarketplaceSku(
            id="purchase-readiness-package",
            name="Purchase Readiness Package",
            version="1.0.0",
            method="POST",
            path="/x402/v1/purchase-readiness-package",
            description=(
                "Premium LCG package combining normalized requirements, compliance matrix, quote deficiencies, "
                "supplier questions, approval checklist, draft supplier inquiry, and machine-readable purchase "
                "request. Marks distributor lookups as credentials_required until D&H/TD SYNNEX APIs are wired. "
                "Live ordering remains disabled."
            ),
            price_usd=_price_usd("X402_LCG_PURCHASE_PACKAGE_PRICE", "10.00"),
            price_env="X402_LCG_PURCHASE_PACKAGE_PRICE",
            network=NETWORK,
            asset=USDC_BASE,
            receiver_env="X402_SELLER_PAY_TO",
            tags=("lcg", "procurement", "package", "handoff"),
            use_cases=("approval package", "supplier outreach prep"),
            expected_latency_ms=900,
            status="active",
            input_schema={
                "type": "object",
                "properties": {
                    "requirements_text": {"type": "string"},
                    "purchase_type": {"type": "string"},
                    "buyer_type": {"type": "string"},
                    "delivery_region": {"type": "string"},
                    "required_by": {"type": "string"},
                    "quote": {"type": "object"},
                    "bom": {"type": "array"},
                },
                "required": ["requirements_text"],
            },
            output_schema={
                "type": "object",
                "properties": {"sku": {"type": "string"}, "result": {"type": "object"}},
                "required": ["sku"],
            },
            example_request={
                "requirements_text": "50 Microsoft 365 E3 seats, 12-month term, US delivery",
                "buyer_type": "commercial",
            },
            example_response={
                "sku": "purchase-readiness-package",
                "result": {"liveOrderingEnabled": False},
            },
        ),
    ]
    return [s for s in skus if s.status != "deprecated"]


def sku_by_path(path: str, method: str = "GET") -> MarketplaceSku | None:
    method_u = method.upper()
    skus = load_base_x402_skus()
    for sku in skus:
        if sku.path == path and sku.method == method_u:
            return sku
    # HEAD probes and GET-first crawlers should still map to the paid SKU.
    if method_u == "HEAD":
        for sku in skus:
            if sku.path == path and sku.method == "GET":
                return sku
        for sku in skus:
            if sku.path == path and sku.method == "POST":
                return sku
    if method_u == "GET":
        for sku in skus:
            if sku.path == path and sku.method == "POST":
                return sku
    return None


def sku_by_id(sku_id: str) -> MarketplaceSku | None:
    for sku in load_base_x402_skus():
        if sku.id == sku_id:
            return sku
    return None


def build_manifest_resources(pay_to: str) -> list[dict[str, Any]]:
    rows = []
    for sku in load_base_x402_skus():
        rows.append(
            {
                "path": sku.path,
                "method": sku.method,
                "price": sku.manifest_price(),
                "network": sku.network,
                "description": sku.description,
                "sku_id": sku.id,
                "asset": sku.asset,
                "payTo": pay_to,
                "accepted_methods": (
                    ["GET", "HEAD"] if sku.method == "GET" else ["POST", "GET", "HEAD"]
                ),
                "input_schema": sku.input_schema,
                "output_schema": sku.output_schema,
                "example_request": sku.example_request,
                "example_response": sku.example_response,
                "expected_latency_ms": sku.expected_latency_ms,
                "tags": list(sku.tags),
                "use_cases": list(sku.use_cases),
                "resource": sku.full_resource_url,
            }
        )
    return rows


def recommended_next_actions_for(sku_id: str) -> list[dict[str, Any]]:
    """Machine-readable upsell path from entry SKUs. Never auto-purchases."""
    catalog = {s.id: s for s in load_base_x402_skus()}
    origin = public_api_origin()

    def _row(target_id: str, when_to_use: str) -> dict[str, Any] | None:
        s = catalog.get(target_id)
        if not s:
            return None
        return {
            "resource": f"{origin}{s.path}",
            "sku": s.id,
            "description": s.description,
            "price_usd": s.price_usd,
            "method": s.method,
            "when_to_use": when_to_use,
        }

    mapping: dict[str, list[tuple[str, str]]] = {
        "ecosystem-pulse": [
            (
                "agent-commerce-data",
                "Use when the pulse shows idle workers or empty listings and you need catalog/pricing playbooks.",
            ),
            (
                "contract-triage",
                "Use when a signal mentions a contract address that needs a fast risk screen.",
            ),
            (
                "airdrop-intelligence-report",
                "Use when incentive/airdrop activity appears and you need Farm Score screening.",
            ),
        ],
        "structured-query": [
            (
                "research-brief",
                "Use when the short answer is insufficient and you need a multi-section brief.",
            ),
            (
                "agent-commerce-data",
                "Use when the question is about marketplace pricing, catalogs, or earning strategy.",
            ),
        ],
        "agent-commerce-data": [
            (
                "contract-audit",
                "Use when commerce research identifies a contract that needs full security diligence.",
            ),
            (
                "contract-monitor",
                "Use when you will hold exposure and need 30-day webhook monitoring.",
            ),
        ],
        "celo-agent-data": [
            (
                "agent-commerce-data",
                "Use for broader multi-rail commerce intelligence beyond the Celo evidence pack.",
            ),
        ],
        "contract-triage": [
            (
                "contract-audit",
                "Use when triage verdict is SUSPICIOUS/MALICIOUS or confidence is too low for a decision.",
            ),
            (
                "contract-monitor",
                "Use after accepting a contract to watch admin/liquidity/claim changes for 30 days.",
            ),
        ],
        "commerce-product-search": [
            (
                "commerce-product-evidence",
                "Use when a candidate product needs source-attributed specifications before quoting.",
            ),
            (
                "commerce-supplier-trust",
                "Use when evaluating whether a listed supplier is mock vs authorized.",
            ),
        ],
        "commerce-product-evidence": [
            (
                "commerce-compatibility-check",
                "Use when buyer requirements must be checked against recorded specs.",
            ),
            (
                "commerce-quote-comparison",
                "Use when ready to collect and rank supplier quotes for the product.",
            ),
        ],
        "commerce-quote-comparison": [
            (
                "commerce-compliance-check",
                "Use when the preferred quote must be checked for requirement gaps.",
            ),
            (
                "commerce-purchase-readiness",
                "Use to assemble an approval-ready package for LCG human review/handoff.",
            ),
        ],
        "procurement-readiness": [
            (
                "quote-completeness-audit",
                "Use after receiving a supplier quote.",
            ),
            (
                "specification-normalizer",
                "Use when requirement language is inconsistent and must be structured before RFQ.",
            ),
            (
                "bid-fit-score",
                "Use for go/no-go when the buyer is a reseller or public-sector pursuer.",
            ),
        ],
        "specification-normalizer": [
            (
                "procurement-readiness",
                "Use to score overall requirement completeness after normalization.",
            ),
            (
                "bom-risk-audit",
                "Use when a multi-line BOM needs configuration risk analysis.",
            ),
        ],
        "quote-completeness-audit": [
            (
                "purchase-readiness-package",
                "Use to produce the full approval and supplier-inquiry package.",
            ),
            (
                "commerce-quote-comparison",
                "Use when multiple supplier quotes are available to rank.",
            ),
        ],
        "rfp-requirement-extractor": [
            (
                "procurement-readiness",
                "Use to score readiness of the extracted requirement set.",
            ),
            (
                "bid-fit-score",
                "Use to decide pursue vs no-go against capabilities and certifications.",
            ),
        ],
        "bid-fit-score": [
            (
                "procurement-readiness",
                "Use when pursuing — diagnose requirement gaps before outreach.",
            ),
            (
                "purchase-readiness-package",
                "Use to generate the machine-readable purchase and supplier inquiry package.",
            ),
        ],
        "bom-risk-audit": [
            (
                "quote-completeness-audit",
                "Use once supplier quotes arrive for the BOM.",
            ),
            (
                "purchase-readiness-package",
                "Use to package risks into an approval checklist.",
            ),
        ],
        "purchase-readiness-package": [
            (
                "commerce-supplier-trust",
                "Use when evaluating a named supplier before handoff (still not live inventory).",
            ),
        ],
    }
    out: list[dict[str, Any]] = []
    for target, when in mapping.get(sku_id, []):
        row = _row(target, when)
        if row:
            out.append(row)
    return out
