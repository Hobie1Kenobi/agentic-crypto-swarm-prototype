#!/usr/bin/env python3
"""
Run the T54 XRPL x402 seller (seller side only — no buyer keys).

  pip install fastapi uvicorn x402-xrpl python-dotenv

  npm run t54:seller
  # or: python scripts/t54_seller_server.py

Bind publicly (e.g. ngrok): T54_SELLER_HOST=0.0.0.0
Set T54_SELLER_PUBLIC_URL=https://your-host/x402/v1/query for discovery (optional).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)


def main() -> int:
    try:
        import uvicorn
        from t54_seller_app import create_t54_seller_app
    except ImportError as e:
        print("Install: pip install fastapi uvicorn x402-xrpl python-dotenv", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1

    host = (os.getenv("T54_SELLER_HOST") or os.getenv("T54_LOCAL_MERCHANT_HOST") or "127.0.0.1").strip()
    port = int(os.getenv("T54_SELLER_PORT") or os.getenv("T54_LOCAL_MERCHANT_PORT") or "8765")

    app = create_t54_seller_app()
    print(f"T54 XRPL x402 seller — http://{host}:{port}/health  (paid routes: GET /health lists SKUs)")
    if os.getenv("T54_SELLER_PUBLIC_URL"):
        print(f"  Public URL (for buyers / env): {os.getenv('T54_SELLER_PUBLIC_URL')}")
    uvicorn.run(app, host=host, port=port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
