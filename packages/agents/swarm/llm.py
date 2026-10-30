import logging
import os
import re
import urllib.request
from dataclasses import dataclass

from langchain_ollama import ChatOllama

_LOG = logging.getLogger("swarm.llm")
_STUB_AFTER_AUTH_FAIL = False


@dataclass
class _DeterministicResponse:
    content: str


def _ollama_invoke_unusable(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "status code: 403",
            "status code: 410",
            "requires a subscription",
            "upgrade for access",
            "unauthorized",
            "401",
            "http error 410",
        )
    )


class _FallbackOnErrorLLM:
    """Use the primary LLM until invoke fails with a billing/auth error, then stub."""

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback
        self._use_fallback = False

    def invoke(self, messages, *args, **kwargs):
        global _STUB_AFTER_AUTH_FAIL
        if self._use_fallback or _STUB_AFTER_AUTH_FAIL:
            return self._fallback.invoke(messages, *args, **kwargs)
        try:
            return self._primary.invoke(messages, *args, **kwargs)
        except Exception as exc:
            if not _ollama_invoke_unusable(exc):
                raise
            _LOG.warning("ollama invoke failed (%s) — using deterministic stub", exc)
            self._use_fallback = True
            _STUB_AFTER_AUTH_FAIL = True
            return self._fallback.invoke(messages, *args, **kwargs)


class _DeterministicLLM:
    """
    Minimal local fallback for when Ollama is unreachable.

    This is used to keep orchestration/simulation repeatable in CI or on machines
    without Ollama running.
    """

    def invoke(self, messages, *args, **kwargs):
        # `messages` is a list of HumanMessage/SystemMessage-like objects.
        joined = "\n".join(getattr(m, "content", "") for m in messages)

        if "Decompose this goal" in joined or "Tasks:" in joined and "IP-Generator" in joined:
            return _DeterministicResponse(
                content=(
                    "1. IP-Generator: Generate an ethical pay-per-query prompt template.\n"
                    "2. Deployer: Ensure AgentRevenueService is deployed and REVENUE_SERVICE_ADDRESS is set.\n"
                    "3. Finance-Distributor: Monitor finance balance and distribute when threshold is met."
                )
            )

        if "Create a short algorithmic oracle" in joined:
            return _DeterministicResponse(
                content=(
                    "Answer the query in one or two sentences. Keep it ethical and non-harmful. "
                    "Do not include disallowed content."
                )
            )

        m = re.search(r"simulated user (\d+)", joined)
        if m:
            user_id = int(m.group(1))
            return _DeterministicResponse(content=f"simulated_response_user_{user_id}")

        # Default: keep it short and safe for pay-per-query.
        return _DeterministicResponse(content="Response generated.")


def _ollama_reachable(base_url: str) -> bool:
    # `/api/tags` is lightweight and fails fast if the server isn't up.
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=1.5) as resp:
            return resp.status in (200, 201, 204)
    except Exception:
        return False


def _strict_ollama_required() -> bool:
    return os.getenv("OLLAMA_STRICT", "").strip().lower() in {"1", "true", "yes", "on"}


def get_llm():
    # Force deterministic output for local/CI runs.
    if os.getenv("LLM_DRY_RUN", "").strip() in {"1", "true", "TRUE", "yes", "on"}:
        return _DeterministicLLM()
    if _STUB_AFTER_AUTH_FAIL:
        return _DeterministicLLM()

    from swarm.ollama_cloud import base_url as ollama_base
    from swarm.ollama_cloud import cloud_model_name, ensure_cloud_model, is_server_up

    model = cloud_model_name()
    base_url = ollama_base()

    if os.getenv("OLLAMA_ENSURE_ON_USE", "1").strip().lower() not in {"0", "false", "no", "off"}:
        status = ensure_cloud_model(model=model, start_server=True, pull_if_missing=True)
        if not status.get("model_ready") and status.get("hint"):
            _LOG.warning("ollama cloud not ready (%s): %s", model, status.get("hint"))

    if not is_server_up():
        msg = f"Ollama unreachable at {base_url}; run npm run ollama:ensure"
        if _strict_ollama_required():
            raise RuntimeError(msg)
        _LOG.warning("%s — using deterministic LLM stub", msg)
        return _DeterministicLLM()

    if not _ollama_reachable(base_url):
        if _strict_ollama_required():
            raise RuntimeError(f"Ollama tags slow at {base_url}")
        _LOG.warning("ollama tags probe failed at %s — using stub", base_url)
        return _DeterministicLLM()

    try:
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "180"))
    except ValueError:
        timeout = 180.0
    primary = ChatOllama(
        model=model,
        base_url=base_url,
        temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.3") or "0.3"),
        timeout=timeout,
    )
    if _strict_ollama_required():
        return primary
    return _FallbackOnErrorLLM(primary, _DeterministicLLM())


def get_llm_probe_info() -> dict[str, str]:
    from swarm.ollama_cloud import base_url as ollama_base
    from swarm.ollama_cloud import cloud_model_name

    return {"model": cloud_model_name(), "base_url": ollama_base()}
