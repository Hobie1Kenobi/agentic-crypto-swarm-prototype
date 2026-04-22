"""Passive discovery JSON for /.well-known (x402 manifest, agent card, MCP hints).

Shared by api_seller_x402 (8043) and marketplace_api (8055) so either origin can serve
discovery when the reverse proxy routes the public API host to a single backend.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse


def get_public_api_base_url() -> str:
    """Canonical HTTPS origin for the public API host (no trailing slash)."""
    base = (os.getenv("MARKETPLACE_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if base:
        return base
    seller = (os.getenv("X402_SELLER_PUBLIC_URL") or "").strip()
    if seller:
        p = urlparse(seller)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    return "https://api.agentic-swarm-marketplace.com"


def get_seller_pay_to() -> str:
    explicit = (os.getenv("X402_SELLER_PAY_TO") or "").strip()
    if explicit.startswith("0x") and len(explicit) == 42:
        return explicit
    pk = (os.getenv("ROOT_STRATEGIST_PRIVATE_KEY") or os.getenv("X402_BUYER_BASE_MAINNET_PRIVATE_KEY") or "").strip()
    if pk and "0x" in pk:
        try:
            from eth_account import Account

            return Account.from_key(pk).address
        except Exception:
            pass
    return ""


def build_x402_manifest(pay_to: str) -> dict:
    return {
        "version": "2",
        "seller": {
            "name": "Agentic Swarm Marketplace",
            "description": (
                "Multi-rail agent commerce platform. Smart contract security audits, x402 commerce "
                "intelligence, airdrop threat screening, research briefs, and compliance reviews. "
                "Pays via USDC on Base or XRP on XRPL."
            ),
            "url": "https://agentic-swarm-marketplace.com",
            "payTo": pay_to,
        },
        "resources": [
            {
                "path": "/x402/v1/contract-triage",
                "method": "GET",
                "price": "0.01 USDC",
                "network": "eip155:8453",
                "description": "Fast smart contract malicious pattern triage. Risk score + verdict in 30s.",
            },
            {
                "path": "/x402/v1/contract-audit",
                "method": "GET",
                "price": "0.50 USDC",
                "network": "eip155:8453",
                "description": "Full 5-phase EVM contract security audit. Slither + Echidna + on-chain intel.",
            },
            {
                "path": "/x402/v1/contract-monitor",
                "method": "POST",
                "price": "5.00 USDC",
                "network": "eip155:8453",
                "description": "30-day contract monitoring subscription. Webhook alerts on threats.",
            },
            {
                "path": "/x402/v1/airdrop-intelligence",
                "method": "GET",
                "price": "0.09 USDC",
                "network": "eip155:8453",
                "description": "Airdrop scam screening with Farm Score, EIP-7702 detection, risk flags.",
            },
            {
                "path": "/x402/v1/query",
                "method": "GET",
                "price": "0.01 USDC",
                "network": "eip155:8453",
                "description": "Constitution-safe structured Q&A with source attribution.",
            },
            {
                "path": "/x402/v1/agent-commerce-data",
                "method": "GET",
                "price": "0.05 USDC",
                "network": "eip155:8453",
                "description": "Premium x402 commerce intelligence bundle with catalog snapshot and earning playbooks.",
            },
        ],
    }


def build_agent_card_manifest() -> dict:
    return {
        "name": "Agentic Swarm Marketplace",
        "description": (
            "Multi-rail agent commerce platform specializing in smart contract security auditing, "
            "airdrop threat intelligence, x402 commerce data, and compliance review. "
            "Available on Base (USDC) and XRPL (XRP). MCP-compatible."
        ),
        "url": "https://api.agentic-swarm-marketplace.com",
        "version": "2.0",
        "provider": {
            "name": "Agentic Swarm Marketplace",
            "url": "https://agentic-swarm-marketplace.com",
        },
        "capabilities": {"streaming": False, "pushNotifications": True},
        "skills": [
            {
                "id": "smart-contract-audit",
                "name": "Smart Contract Security Audit",
                "description": (
                    "Full EVM contract security audit: Slither static analysis, Echidna fuzz testing, "
                    "deployer profiling, EIP-7702 delegate detection, money flow tracing, holder concentration analysis."
                ),
                "tags": ["security", "evm", "smart-contract", "audit", "slither", "echidna", "base", "defi"],
            },
            {
                "id": "airdrop-threat-detection",
                "name": "Airdrop Threat Detection",
                "description": (
                    "Detects malicious airdrop contracts: honeypots, rug mechanics, trust-borrowing brand names, "
                    "coordinated deployer wallets, thin liquidity traps."
                ),
                "tags": ["airdrop", "scam", "threat-detection", "web3-security", "honeypot", "rug-pull"],
            },
            {
                "id": "contract-triage",
                "name": "Contract Triage",
                "description": "Fast 30-second malicious pattern screen returning risk score and verdict.",
                "tags": ["triage", "screening", "fast", "risk-score"],
            },
            {
                "id": "contract-monitoring",
                "name": "Contract Monitoring",
                "description": (
                    "Continuous 30-day webhook-based monitoring for admin key movement, liquidity breaches, "
                    "and new threat findings."
                ),
                "tags": ["monitoring", "alerts", "webhook", "continuous"],
            },
            {
                "id": "x402-commerce-intelligence",
                "name": "x402 Commerce Intelligence",
                "description": "Live x402 catalog data, agent earning playbooks, median price analysis, Bazaar discovery keywords.",
                "tags": ["x402", "commerce", "marketplace", "agent-economics"],
            },
        ],
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "securitySchemes": {"x402": {"type": "x402", "network": "eip155:8453", "facilitator": "https://x402.org/facilitator"}},
    }


def build_mcp_manifest() -> dict:
    return {
        "mcp_endpoint": "https://api.agentic-swarm-marketplace.com/mcp",
        "mcp_sse": "https://api.agentic-swarm-marketplace.com/mcp/sse",
        "version": "1.23",
        "tools": [
            "contract_triage",
            "contract_audit",
            "contract_monitor_subscribe",
            "airdrop_intelligence",
            "structured_query",
            "research_brief",
            "agent_commerce_data",
        ],
    }


LINKSET_JSON_MEDIA_TYPE = (
    'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"'
)


def build_api_catalog_linkset() -> dict:
    """RFC 9727 API catalog in RFC 9264 Linkset JSON (Appendix A.1 style)."""
    base = get_public_api_base_url()
    return {
        "linkset": [
            {
                "anchor": base,
                "service-desc": [
                    {
                        "href": f"{base}/openapi.json",
                        "type": "application/json",
                    }
                ],
                "service-doc": [
                    {
                        "href": f"{base}/docs",
                        "type": "text/html",
                    }
                ],
                "status": [
                    {
                        "href": f"{base}/health",
                        "type": "application/json",
                    }
                ],
            }
        ]
    }
