from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from .executor import execute_claim


def _run_execute(state: dict[str, Any]) -> dict[str, Any]:
    try:
        out = execute_claim(state["claim_id"], dry_run=bool(state.get("dry_run")))
        return {**state, "result": out}
    except Exception as e:
        return {**state, "error": str(e)}


def build_claim_execution_graph():
    g = StateGraph(dict)
    g.add_node("execute_claim", _run_execute)
    g.set_entry_point("execute_claim")
    g.add_edge("execute_claim", END)
    return g.compile()


def run_approved_claim(claim_id: str, *, dry_run: bool = False) -> dict[str, Any]:
    """LangGraph entry: executes a single approved claim (same checks as CLI)."""
    graph = build_claim_execution_graph()
    out = graph.invoke({"claim_id": claim_id, "dry_run": dry_run})
    if out.get("error"):
        raise RuntimeError(out["error"])
    return out.get("result") or {}
