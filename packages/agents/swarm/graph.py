from langgraph.graph import StateGraph, END

from .state import SwarmState
from .nodes import (
    strategist_node,
    ip_generator_node,
    deployer_node,
    finance_distributor_node,
)


def build_graph() -> StateGraph:
    builder = StateGraph(SwarmState)

    builder.add_node("strategist", strategist_node)
    builder.add_node("ip_generator", ip_generator_node)
    builder.add_node("deployer", deployer_node)
    builder.add_node("finance_distributor", finance_distributor_node)

    builder.set_entry_point("strategist")
    builder.add_edge("strategist", "ip_generator")
    builder.add_edge("ip_generator", "deployer")
    builder.add_edge("deployer", "finance_distributor")
    builder.add_conditional_edges("finance_distributor", _route_after_finance, {"end": END, "continue": "strategist"})

    return builder


def _route_after_finance(state: SwarmState) -> str:
    if state.get("done"):
        return "end"
    return "continue"


def get_compiled_graph():
    return build_graph().compile()
