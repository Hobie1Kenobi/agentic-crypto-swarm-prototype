"""Passive discovery JSON for /.well-known (x402 manifest, agent card, MCP hints).

Shared by api_seller_x402 (8043) and marketplace_api (8055) so either origin can serve
discovery when the reverse proxy routes the public API host to a single backend.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
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


def get_public_site_origin() -> str:
    """HTTPS origin for marketing / policy pages (vendor UCP spec URLs must match this host)."""
    base = (os.getenv("PUBLIC_SITE_ORIGIN") or "").strip().rstrip("/")
    if base:
        return base
    return "https://agentic-swarm-marketplace.com"


UCP_PROTOCOL_VERSION = "2026-04-08"


def build_ucp_profile() -> dict:
    """Universal Commerce Protocol business profile for /.well-known/ucp (UCP discovery)."""
    api = get_public_api_base_url()
    site = get_public_site_origin()
    v = UCP_PROTOCOL_VERSION
    spec = f"https://ucp.dev/{v}/specification/overview"
    ns = "com.agentic_swarm_marketplace"
    return {
        "ucp": {
            "version": v,
            "services": {
                f"{ns}.api": [
                    {
                        "version": v,
                        "spec": spec,
                        "transport": "rest",
                        "endpoint": api,
                        "schema": f"{api}/openapi.json",
                    },
                    {
                        "version": v,
                        "spec": spec,
                        "transport": "a2a",
                        "endpoint": f"{api}/.well-known/agent-card.json",
                    },
                ]
            },
            "capabilities": {
                f"{ns}.api.paid_skus": [
                    {
                        "version": v,
                        "spec": f"{site}/",
                        "schema": f"{api}/openapi.json",
                    }
                ]
            },
        }
    }


def build_acp_discovery() -> dict:
    """Agentic Commerce Protocol discovery for /.well-known/acp.json (passive agent discovery)."""
    api = get_public_api_base_url()
    ver = (os.getenv("ACP_PROTOCOL_VERSION") or "2026-04-17").strip()
    return {
        "protocol": {"name": "acp", "version": ver},
        "api_base_url": api,
        "supported_transports": ["rest", "mcp"],
        "capabilities": {
            "services": {
                "x402_http_skus": {
                    "description": "Per-route HTTP APIs with x402 settlement (Base USDC); resource list and prices in /.well-known/x402.json",
                    "catalog_url": f"{api}/.well-known/x402.json",
                    "rest_base_url": api,
                },
                "mcp_streamable_http": {
                    "description": "Model Context Protocol: Streamable HTTP and SSE tools for audits, intelligence, and commerce helpers",
                    "mcp_server_card_url": f"{api}/.well-known/mcp/server-card.json",
                    "mcp_endpoint": f"{api}/mcp",
                },
                "stripe_marketplace_orders": {
                    "description": "Marketplace orders and MPP discovery (OpenAPI, POST /v1/orders)",
                    "openapi_url": f"{api}/openapi.json",
                    "orders_path": "/v1/orders",
                },
            }
        },
    }


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


MCP_SERVER_CARD_SCHEMA_URL = (
    "https://static.modelcontextprotocol.io/schemas/mcp-server-card/v1.json"
)


def build_mcp_manifest() -> dict:
    base = get_public_api_base_url()
    return {
        "mcp_endpoint": f"{base}/mcp",
        "mcp_sse": f"{base}/mcp/sse",
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


def build_mcp_server_card() -> dict:
    """SEP-1649 MCP Server Card for /.well-known/mcp/server-card.json (draft SEP-2127 shape)."""
    base = get_public_api_base_url()
    proto = (os.getenv("MCP_PROTOCOL_VERSION") or "2025-06-18").strip()
    impl_ver = (os.getenv("MCP_SERVER_IMPLEMENTATION_VERSION") or "1.23.0").strip()
    return {
        "$schema": MCP_SERVER_CARD_SCHEMA_URL,
        "version": "1.0",
        "protocolVersion": proto,
        "serverInfo": {
            "name": "agentic-swarm-marketplace",
            "title": "Agentic Swarm Marketplace",
            "version": impl_ver,
        },
        "description": (
            "MCP HTTP tools for contract triage and audit, airdrop intelligence, research briefs, and x402 commerce data. "
            "Primary transport: Streamable HTTP at /mcp; SSE at /mcp/sse. Paid REST SKUs: /.well-known/x402.json."
        ),
        "documentationUrl": f"{base}/docs",
        "transport": {
            "type": "streamable-http",
            "endpoint": "/mcp",
        },
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True, "subscribe": False},
            "prompts": {"listChanged": False},
        },
        "tools": ["dynamic"],
        "resources": ["dynamic"],
        "instructions": (
            f"Connect with Streamable HTTP to {base}/mcp (or SSE at {base}/mcp/sse). "
            "Use /.well-known/mcp.json for legacy hint JSON; x402-paid HTTP APIs are listed in /.well-known/x402.json."
        ),
    }


def build_mcp_server_cards_list() -> list[dict]:
    """JSON array for /.well-known/mcp/server-cards.json (multiple cards per host)."""
    return [build_mcp_server_card()]


AGENT_SKILLS_DISCOVERY_SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def agent_skills_content_root() -> Path:
    override = (os.getenv("AGENT_SKILLS_CONTENT_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (_repo_root() / "documentation" / "agent-skills").resolve()


def _skill_dir_name_ok(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name))


def _parse_skill_md_description(md_path: Path) -> str:
    default = md_path.parent.name.replace("-", " ")
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return default
    if not text.startswith("---"):
        for ln in text.splitlines():
            s = ln.strip()
            if s and not s.startswith("#"):
                return s[:500]
        return default
    end = text.find("\n---", 3)
    if end == -1:
        return default
    fm = text[3:end]
    for line in fm.splitlines():
        line = line.strip()
        if line.startswith("description:"):
            val = line.split("description:", 1)[1].strip()
            if val.startswith('"') and val.endswith('"') and len(val) >= 2:
                val = val[1:-1]
            return val[:500] or default
    return default


def build_agent_skills_index() -> dict:
    """Agent Skills Discovery RFC v0.2.0 index for /.well-known/agent-skills/index.json."""
    root = agent_skills_content_root()
    skills: list[dict] = []
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            if not _skill_dir_name_ok(d.name):
                continue
            md = d / "SKILL.md"
            if not md.is_file():
                continue
            body = md.read_bytes()
            digest = "sha256:" + hashlib.sha256(body).hexdigest()
            skills.append(
                {
                    "name": d.name,
                    "type": "skill-md",
                    "description": _parse_skill_md_description(md),
                    "url": f"/.well-known/agent-skills/{d.name}/SKILL.md",
                    "digest": digest,
                }
            )
    return {"$schema": AGENT_SKILLS_DISCOVERY_SCHEMA, "skills": skills}


def agent_skill_markdown_path(skill_name: str) -> Path | None:
    """Resolved path to SKILL.md if valid and present; else None."""
    if not _skill_dir_name_ok(skill_name):
        return None
    root = agent_skills_content_root()
    try:
        root_r = root.resolve()
    except OSError:
        return None
    p = (root_r / skill_name / "SKILL.md").resolve()
    try:
        p.relative_to(root_r)
    except ValueError:
        return None
    if p.is_file():
        return p
    return None


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


def oauth_issuer() -> str:
    o = (os.getenv("OAUTH_ISSUER") or "").strip().rstrip("/")
    return o or get_public_api_base_url()


def oauth_resource_identifier() -> str:
    """RFC 9728 resource — HTTPS identifier for this protected API (no fragment)."""
    r = (os.getenv("OAUTH_RESOURCE_IDENTIFIER") or "").strip().rstrip("/")
    return r or get_public_api_base_url()


def oauth_authorization_servers_list() -> list[str]:
    raw = (os.getenv("OAUTH_AUTHORIZATION_SERVERS") or "").strip()
    if raw:
        return [x.strip().rstrip("/") for x in raw.split(",") if x.strip()]
    return [oauth_issuer()]


def oauth_authorization_token_jwks_urls(issuer: str) -> tuple[str, str, str]:
    auth = (os.getenv("OAUTH_AUTHORIZATION_ENDPOINT") or "").strip()
    token = (os.getenv("OAUTH_TOKEN_ENDPOINT") or "").strip()
    jwks = (os.getenv("OAUTH_JWKS_URI") or "").strip()
    if auth and token and jwks:
        return auth, token, jwks
    return (
        f"{issuer}/oauth/authorize",
        f"{issuer}/oauth/token",
        f"{issuer}/.well-known/jwks.json",
    )


def build_jwks_document() -> dict:
    raw = (os.getenv("OAUTH_JWKS_JSON") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get("keys"), list):
                return data
        except json.JSONDecodeError:
            pass
    return {"keys": []}


def build_oauth_authorization_server_metadata() -> dict:
    """RFC 8414 authorization server metadata (for /.well-known/oauth-authorization-server)."""
    iss = oauth_issuer()
    auth_ep, token_ep, jwks_uri = oauth_authorization_token_jwks_urls(iss)
    return {
        "issuer": iss,
        "authorization_endpoint": auth_ep,
        "token_endpoint": token_ep,
        "jwks_uri": jwks_uri,
        "grant_types_supported": [
            "authorization_code",
            "client_credentials",
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "private_key_jwt",
        ],
        "scopes_supported": ["openid", "profile", "email"],
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
    }


def build_openid_configuration() -> dict:
    """OpenID Connect Discovery 1.0 provider metadata (/.well-known/openid-configuration)."""
    meta = dict(build_oauth_authorization_server_metadata())
    meta["subject_types_supported"] = ["public"]
    meta["id_token_signing_alg_values_supported"] = ["RS256"]
    return meta


def build_oauth_protected_resource_metadata() -> dict:
    """RFC 9728 OAuth 2.0 Protected Resource Metadata (/.well-known/oauth-protected-resource)."""
    as_meta = build_oauth_authorization_server_metadata()
    return {
        "resource": oauth_resource_identifier(),
        "authorization_servers": oauth_authorization_servers_list(),
        "scopes_supported": list(as_meta.get("scopes_supported") or ["openid", "profile", "email"]),
        "bearer_methods_supported": ["header"],
    }


def oauth_stub_unavailable_payload() -> dict:
    return {
        "error": "oauth_not_available",
        "error_description": (
            "This host does not issue OAuth or OIDC tokens. "
            "Paid API access uses HTTP 402 x402; see /.well-known/x402.json."
        ),
        "x402_discovery": "/.well-known/x402.json",
    }
