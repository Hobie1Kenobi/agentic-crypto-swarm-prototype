"""Ollama Cloud Pro — keep glm-5.3-flash:cloud reachable for PoCon, SEO, earning workers."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any

_LOG = logging.getLogger("swarm.ollama_cloud")

DEFAULT_CLOUD_MODEL = "glm-5.3-flash:cloud"


def cloud_model_name() -> str:
    return (
        (os.getenv("OLLAMA_MODEL") or "").strip()
        or (os.getenv("POCON_OLLAMA_MODEL") or "").strip()
        or DEFAULT_CLOUD_MODEL
    )


def base_url() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def _timeout_sec() -> float:
    try:
        return max(3.0, float(os.getenv("OLLAMA_TIMEOUT", "30")))
    except ValueError:
        return 30.0


def fetch_tags(*, timeout: float | None = None) -> dict[str, Any] | None:
    t = timeout if timeout is not None else min(_timeout_sec(), 15.0)
    try:
        with urllib.request.urlopen(f"{base_url()}/api/tags", timeout=t) as resp:
            if resp.status not in (200, 201, 204):
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        _LOG.debug("ollama tags unreachable: %s", exc)
        return None


def is_server_up(*, timeout: float | None = None) -> bool:
    return fetch_tags(timeout=timeout) is not None


def model_present(model: str | None = None) -> bool:
    model = (model or cloud_model_name()).strip()
    if not model:
        return False
    tags = fetch_tags()
    if not tags:
        return False
    base = model.split(":")[0]
    for entry in tags.get("models") or []:
        name = str((entry or {}).get("name") or "")
        if name == model or name.startswith(base + ":"):
            return True
    return False


def _try_start_ollama_app() -> bool:
    if os.getenv("OLLAMA_AUTO_START", "1").strip().lower() in {"0", "false", "no", "off"}:
        return False
    if os.name != "nt":
        return False
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except (FileNotFoundError, OSError) as exc:
        _LOG.warning("could not start ollama serve: %s", exc)
        return False


def pull_model(model: str | None = None, *, timeout_sec: int = 600) -> bool:
    model = (model or cloud_model_name()).strip()
    try:
        subprocess.run(
            ["ollama", "pull", model],
            check=True,
            timeout=timeout_sec,
            capture_output=True,
            text=True,
        )
        return model_present(model)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _LOG.warning("ollama pull %s failed: %s", model, exc)
        return False


def ensure_cloud_model(
    *,
    model: str | None = None,
    start_server: bool = True,
    pull_if_missing: bool = True,
    wait_sec: float = 12.0,
) -> dict[str, Any]:
    """Best-effort: running Ollama + cloud model available for get_llm()."""
    import time

    model = (model or cloud_model_name()).strip()
    out: dict[str, Any] = {
        "model": model,
        "base_url": base_url(),
        "server_up": False,
        "model_ready": False,
        "actions": [],
    }

    if not is_server_up(timeout=2.0):
        if start_server and _try_start_ollama_app():
            out["actions"].append("started_ollama_serve")
            deadline = time.time() + wait_sec
            while time.time() < deadline:
                if is_server_up(timeout=2.0):
                    break
                time.sleep(0.5)

    out["server_up"] = is_server_up()
    if not out["server_up"]:
        out["hint"] = "Run: ollama signin && ollama serve (or npm run ollama:ensure)"
        return out

    if model_present(model):
        out["model_ready"] = True
        return out

    if pull_if_missing:
        out["actions"].append(f"pull_{model}")
        out["model_ready"] = pull_model(model)
        if not out["model_ready"]:
            out["hint"] = f"Run: ollama pull {model} (requires ollama signin for cloud)"

    return out


def probe_invoke(model: str | None = None) -> dict[str, Any]:
    """Lightweight chat probe (validates cloud routing)."""
    model = (model or cloud_model_name()).strip()
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url()}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_timeout_sec()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = ((data.get("message") or {}).get("content") or "").strip()
            return {"ok": bool(content), "model": model, "snippet": content[:80]}
    except Exception as exc:
        return {"ok": False, "model": model, "error": str(exc)[:200]}
