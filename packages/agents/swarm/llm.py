import os
import re
import urllib.request
from dataclasses import dataclass

from langchain_ollama import ChatOllama


@dataclass
class _DeterministicResponse:
    content: str


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


def get_llm():
    # Force deterministic output for local/CI runs.
    if os.getenv("LLM_DRY_RUN", "").strip() in {"1", "true", "TRUE", "yes", "on"}:
        return _DeterministicLLM()

    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    if not _ollama_reachable(base_url):
        return _DeterministicLLM()

    # Ollama is reachable; use the real model.
    return ChatOllama(model=model, base_url=base_url, temperature=0.3)
