from langgraph.graph import StateGraph, END

from .state import SwarmState
from .nodes import (
    strategist_node,
    ip_generator_node,
    deployer_node,
    task_market_demo_node,
    public_adapter_node,
    simulation_node,
    finance_distributor_node,
)
from config.market_mode import get_market_mode


def build_graph() -> StateGraph:
    builder = StateGraph(SwarmState)

    builder.add_node("strategist", strategist_node)
    builder.add_node("ip_generator", ip_generator_node)
    builder.add_node("deployer", deployer_node)
    builder.add_node("task_market_demo", task_market_demo_node)
    builder.add_node("public_adapter", public_adapter_node)
    builder.add_node("simulation", simulation_node)
    builder.add_node("finance_distributor", finance_distributor_node)

    builder.set_entry_point("strategist")
    builder.add_edge("strategist", "ip_generator")
    builder.add_edge("ip_generator", "deployer")
    builder.add_conditional_edges(
        "deployer",
        _route_after_deployer,
        {
            "task_market_demo": "task_market_demo",
            "public_adapter": "public_adapter",
        },
    )
    builder.add_edge("task_market_demo", "simulation")
    builder.add_edge("public_adapter", "simulation")
    builder.add_edge("simulation", "finance_distributor")
    builder.add_conditional_edges("finance_distributor", _route_after_finance, {"end": END, "continue": "strategist"})

    return builder


def _route_after_deployer(state: SwarmState) -> str:
    mode = get_market_mode()
    if mode in {"public_olas", "hybrid"}:
        return "public_adapter"
    return "task_market_demo"


def _route_after_finance(state: SwarmState) -> str:
    if state.get("done"):
        return "end"
    return "continue"


def get_compiled_graph():
    return build_graph().compile()
