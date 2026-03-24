#!/usr/bin/env python3
"""
Read ngrok local API (http://127.0.0.1:4040) and set T54_SELLER_PUBLIC_BASE_URL in repo .env.

Requires: ngrok running with default web UI (e.g. ngrok http 8765).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    try:
        raw = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5).read()
    except (urllib.error.URLError, TimeoutError) as e:
        print("ngrok API not reachable (is ngrok running on 4040?)", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1
    data = json.loads(raw.decode("utf-8"))
    tunnels = data.get("tunnels") or []
    if not tunnels:
        print("no tunnels in ngrok response", file=sys.stderr)
        return 1
    base = (tunnels[0].get("public_url") or "").strip().rstrip("/")
    if not base.startswith("https://"):
        print("unexpected public_url", file=sys.stderr)
        return 1
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    key = "T54_SELLER_PUBLIC_BASE_URL"
    line = f"{key}={base}"
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pat.search(text):
        new = pat.sub(line, text)
    else:
        sep = "\n" if text and not text.endswith("\n") else ""
        new = text + sep + line + "\n"
    env_path.write_text(new, encoding="utf-8")
    print(f"Wrote {key} to .env (origin only; paths added by discovery).")
    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
