#!/usr/bin/env python3
"""Backward-compatible alias — use `npm run t54:seller` or `scripts/t54_seller_server.py`."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_p = Path(__file__).resolve().parent / "t54_seller_server.py"
_spec = importlib.util.spec_from_file_location("t54_seller_server", _p)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
sys.exit(_mod.main())
