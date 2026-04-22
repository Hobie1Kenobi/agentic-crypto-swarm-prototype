#!/usr/bin/env python3
"""
If repo .env defines PUBLIC_API_ORIGIN (https, no trailing slash), write cohesive public URLs
for MARKETPLACE_PUBLIC_BASE_URL, X402_SELLER_PUBLIC_URL, T54_SELLER_PUBLIC_BASE_URL, MCP_SSE_PUBLIC_URL
(and mirror to .env.mainnet when present).

Used on the production tunnel host so /.well-known/* and MCP hints advertise Cloudflare hostname
instead of ephemeral ngrok URLs. Exit 2 = applied; exit 0 = skipped (no PUBLIC_API_ORIGIN).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def _upsert_env(env_path: Path, key: str, value: str) -> None:
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    line = f"{key}={value}"
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pat.search(text):
        new = pat.sub(line, text)
    else:
        sep = "\n" if text and not text.endswith("\n") else ""
        new = text + sep + line + "\n"
    env_path.write_text(new, encoding="utf-8")


def _read_public_api_origin(env_path: Path) -> str:
    if not env_path.exists():
        return ""
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("PUBLIC_API_ORIGIN="):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            return v.rstrip("/")
    return ""


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    origin = _read_public_api_origin(env_path)
    if not origin:
        print("apply_public_api_origin: no PUBLIC_API_ORIGIN in .env; use ngrok sync instead")
        return 0
    if not origin.startswith("https://"):
        print("apply_public_api_origin: PUBLIC_API_ORIGIN must be https://...", file=sys.stderr)
        return 1

    pairs = {
        "MARKETPLACE_PUBLIC_BASE_URL": origin,
        "X402_SELLER_PUBLIC_URL": f"{origin}/x402/v1/query",
        "T54_SELLER_PUBLIC_BASE_URL": f"{origin}/t54",
        "MCP_SSE_PUBLIC_URL": f"{origin}/mcp",
    }
    for k, v in pairs.items():
        _upsert_env(env_path, k, v)
        print(f"Wrote {k}={v}")

    mainnet = root / ".env.mainnet"
    if mainnet.exists():
        for k, v in pairs.items():
            _upsert_env(mainnet, k, v)
        print("Mirrored public URL keys to .env.mainnet")

    print(f"apply_public_api_origin: cohesive URLs for {origin}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
