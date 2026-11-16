"""Simple abuse-resistant daily free quota for the preflight SKU.

Default: 5 free calls per UTC day per caller. The caller key is a hash of the
client IP (preferred: CF-Connecting-IP, then X-Real-IP, then the last
X-Forwarded-For hop, then the socket peer). A client-supplied id is never
enough on its own — rotating a header must not mint a new bucket.

Counts are stored as JSON files under artifacts/preflight_quota/ (or
PREFLIGHT_QUOTA_DIR). IPs are not written in plaintext.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from contextvars import ContextVar
from typing import Any

current_quota: ContextVar[dict[str, Any] | None] = ContextVar("asm_preflight_quota", default=None)

DEFAULT_LIMIT = 5
PREFLIGHT_PATH = "/x402/v1/preflight"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "foundry.toml").exists() or (p / ".env.example").exists():
            return p
    return here.parents[2]


def quota_dir() -> Path:
    override = (os.getenv("PREFLIGHT_QUOTA_DIR") or "").strip()
    if override:
        return Path(override)
    return _repo_root() / "artifacts" / "preflight_quota"


def daily_limit() -> int:
    raw = (os.getenv("PREFLIGHT_FREE_DAILY_QUOTA") or "").strip()
    if not raw:
        return DEFAULT_LIMIT
    try:
        n = int(raw)
        return max(0, min(n, 1000))
    except ValueError:
        return DEFAULT_LIMIT


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def extract_caller_ip(headers: Any, peer: str | None = None) -> str:
    def _h(name: str) -> str:
        if headers is None:
            return ""
        try:
            val = headers.get(name) or headers.get(name.lower()) or ""
        except Exception:
            val = ""
        return str(val).strip()

    ip = (
        _h("cf-connecting-ip")
        or _h("CF-Connecting-IP")
        or _h("true-client-ip")
        or _h("True-Client-IP")
        or _h("x-real-ip")
        or _h("X-Real-IP")
    )
    if not ip:
        xff = _h("x-forwarded-for") or _h("X-Forwarded-For")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        # Prefer the original client (first non-private hop). Last hop often changes
        # between Cloudflare / tunnel addresses and would mint a new quota bucket
        # on every request.
        def _private(v: str) -> bool:
            a = v.lower().split("%")[0]
            return (
                a in {"unknown", "localhost"}
                or a.startswith("127.")
                or a.startswith("10.")
                or a.startswith("192.168.")
                or a.startswith("172.16.")
                or a.startswith("::1")
                or a.startswith("fc")
                or a.startswith("fd")
            )
        for cand in parts:
            if not _private(cand):
                ip = cand
                break
        if not ip and parts:
            ip = parts[0]
    if not ip:
        ip = (peer or "").strip()
    return ip or "unknown"


def caller_bucket(ip: str) -> str:
    raw = (ip or "unknown").strip().lower()
    return hashlib.sha256(f"asm-preflight-v1|{raw}".encode("utf-8")).hexdigest()[:24]


def _lock_and_update(path: Path, mutator) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Open a sidecar lock so Windows and POSIX can share the same scheme.
    with open(lock_path, "a+", encoding="utf-8") as lock_f:
        _acquire(lock_f)
        try:
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            else:
                data = {}
            if not isinstance(data, dict):
                data = {}
            result, data = mutator(data)
            fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as out:
                    json.dump(data, out, indent=2)
                    out.write("\n")
                os.replace(tmp, path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            return result
        finally:
            _release(lock_f)


def _acquire(fh) -> None:
    try:
        import fcntl

        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        return
    except (ImportError, OSError):
        pass
    try:
        import msvcrt

        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
    except Exception:
        # Best-effort: still mutate; uniqueness is not guaranteed under contention.
        return


def _release(fh) -> None:
    try:
        import fcntl

        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return
    except (ImportError, OSError):
        pass
    try:
        import msvcrt

        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception:
        return


def inspect(ip: str, *, day: str | None = None, limit: int | None = None) -> dict[str, Any]:
    day = day or utc_day()
    resolved = daily_limit() if limit is None else int(limit)
    return _inspect(ip, day, resolved)


def _inspect(ip: str, day: str, limit: int) -> dict[str, Any]:
    path = quota_dir() / f"{day}.json"
    bucket = caller_bucket(ip)
    used = 0
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            used = int(((data or {}).get("callers") or {}).get(bucket) or 0)
        except Exception:
            used = 0
    remaining = max(0, limit - used)
    return {
        "allowed": used < limit,
        "used": used,
        "remaining": remaining,
        "limit": limit,
        "day": day,
        "bucket": bucket,
    }


def try_consume(ip: str, *, day: str | None = None, limit: int | None = None) -> dict[str, Any]:
    """Atomically consume one free slot. If the daily cap is already hit, allowed=False and used is unchanged."""
    day = day or utc_day()
    limit = daily_limit() if limit is None else int(limit)
    path = quota_dir() / f"{day}.json"
    bucket = caller_bucket(ip)

    def _mutate(data: dict[str, Any]):
        if data.get("day") != day:
            data = {"day": day, "callers": {}}
        callers = data.setdefault("callers", {})
        used = int(callers.get(bucket) or 0)
        if used >= limit:
            result = {
                "allowed": False,
                "used": used,
                "remaining": 0,
                "limit": limit,
                "day": day,
                "bucket": bucket,
            }
            return result, data
        used += 1
        callers[bucket] = used
        result = {
            "allowed": True,
            "used": used,
            "remaining": max(0, limit - used),
            "limit": limit,
            "day": day,
            "bucket": bucket,
        }
        return result, data

    return _lock_and_update(path, _mutate)


def caller_ip_from_request(request: Any) -> str:
    headers = getattr(request, "headers", None)
    peer = None
    client = getattr(request, "client", None)
    if client is not None:
        peer = getattr(client, "host", None) or (client[0] if isinstance(client, (tuple, list)) else None)
    return extract_caller_ip(headers, peer)


def caller_ip_from_mcp_context(context: Any) -> str:
    """Best-effort IP from a FastMCP Context; falls back to 'mcp-unknown'."""
    headers = {}
    peer = None
    try:
        req = getattr(context, "request_context", None)
        request = getattr(req, "request", None) if req is not None else None
        if request is None and context is not None:
            request = getattr(context, "request", None)
        if request is not None:
            headers = getattr(request, "headers", {}) or {}
            client = getattr(request, "client", None)
            if client is not None:
                peer = getattr(client, "host", None)
    except Exception:
        headers = {}
    ip = extract_caller_ip(headers, peer)
    if ip == "unknown":
        return "mcp-unknown"
    return ip
