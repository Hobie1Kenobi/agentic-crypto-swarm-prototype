"""Coinbase Bazaar discovery extension metadata for Base x402 routes."""
from __future__ import annotations

from typing import Any

from config.base_x402_skus import MarketplaceSku, load_base_x402_skus, sku_by_id


def _declare(sku: MarketplaceSku) -> dict[str, Any] | None:
    try:
        from x402.extensions.bazaar import declare_discovery_extension
        from x402.extensions.bazaar.resource_service import OutputConfig
    except ImportError:
        return None

    example_in = sku.example_request or {}
    return declare_discovery_extension(
        input=example_in,
        input_schema=sku.input_schema or {"type": "object", "properties": {}},
        output=OutputConfig(example=sku.example_response or {"sku_id": sku.id}),
    )


def _by_id(sku_id: str) -> dict[str, Any] | None:
    sku = sku_by_id(sku_id)
    if not sku:
        # catalog may be empty during import edge cases; rebuild once
        for row in load_base_x402_skus():
            if row.id == sku_id:
                return _declare(row)
        return None
    return _declare(sku)


def bazaar_query() -> dict[str, Any] | None:
    return _by_id("structured-query")


def bazaar_research_brief() -> dict[str, Any] | None:
    return _by_id("research-brief")


def bazaar_constitution_audit() -> dict[str, Any] | None:
    return _by_id("constitution-audit-lite")


def bazaar_agent_commerce_data() -> dict[str, Any] | None:
    return _by_id("agent-commerce-data")


def bazaar_airdrop_intelligence() -> dict[str, Any] | None:
    return _by_id("airdrop-intelligence-report")


def bazaar_contract_triage() -> dict[str, Any] | None:
    return _by_id("contract-triage")


def bazaar_contract_audit() -> dict[str, Any] | None:
    return _by_id("contract-audit")


def bazaar_contract_monitor() -> dict[str, Any] | None:
    return _by_id("contract-monitor")


def bazaar_ecosystem_pulse() -> dict[str, Any] | None:
    return _by_id("ecosystem-pulse")


def bazaar_celo_agent_data() -> dict[str, Any] | None:
    return _by_id("celo-agent-data")


def bazaar_intake_resale() -> dict[str, Any] | None:
    return _by_id("intake-resale-pack")


def bazaar_commerce_product_search() -> dict[str, Any] | None:
    return _by_id("commerce-product-search")


def bazaar_commerce_product_evidence() -> dict[str, Any] | None:
    return _by_id("commerce-product-evidence")


def bazaar_commerce_supplier_trust() -> dict[str, Any] | None:
    return _by_id("commerce-supplier-trust")


def bazaar_commerce_compatibility_check() -> dict[str, Any] | None:
    return _by_id("commerce-compatibility-check")


def bazaar_commerce_quote_comparison() -> dict[str, Any] | None:
    return _by_id("commerce-quote-comparison")


def bazaar_commerce_compliance_check() -> dict[str, Any] | None:
    return _by_id("commerce-compliance-check")


def bazaar_commerce_purchase_readiness() -> dict[str, Any] | None:
    return _by_id("commerce-purchase-readiness")


def bazaar_procurement_readiness() -> dict[str, Any] | None:
    return _by_id("procurement-readiness")


def bazaar_specification_normalizer() -> dict[str, Any] | None:
    return _by_id("specification-normalizer")


def bazaar_quote_completeness_audit() -> dict[str, Any] | None:
    return _by_id("quote-completeness-audit")


def bazaar_rfp_requirement_extractor() -> dict[str, Any] | None:
    return _by_id("rfp-requirement-extractor")


def bazaar_bid_fit_score() -> dict[str, Any] | None:
    return _by_id("bid-fit-score")


def bazaar_bom_risk_audit() -> dict[str, Any] | None:
    return _by_id("bom-risk-audit")


def bazaar_purchase_readiness_package() -> dict[str, Any] | None:
    return _by_id("purchase-readiness-package")
