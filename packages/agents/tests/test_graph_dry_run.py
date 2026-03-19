import os
import pytest


def test_graph_compiles():
    from swarm.graph import build_graph, get_compiled_graph
    graph = build_graph()
    assert graph is not None
    compiled = get_compiled_graph()
    assert compiled is not None


def test_route_after_finance_returns_end_when_done():
    from swarm.graph import build_graph, _route_after_finance
    from swarm.state import SwarmState
    state: SwarmState = {"goal": "x", "tasks": [], "tx_hashes": [], "done": True}
    assert _route_after_finance(state) == "end"
    state2: SwarmState = {"goal": "x", "tasks": [], "done": False}
    assert _route_after_finance(state2) == "continue"


def test_route_after_deployer_private_default(monkeypatch):
    monkeypatch.delenv("MARKET_MODE", raising=False)
    from swarm.graph import _route_after_deployer
    from swarm.state import SwarmState
    state: SwarmState = {"goal": "x", "tasks": [], "tx_hashes": []}
    assert _route_after_deployer(state) == "task_market_demo"


def test_route_after_deployer_public(monkeypatch):
    monkeypatch.setenv("MARKET_MODE", "public_olas")
    from swarm.graph import _route_after_deployer
    from swarm.state import SwarmState
    state: SwarmState = {"goal": "x", "tasks": [], "tx_hashes": []}
    assert _route_after_deployer(state) == "public_adapter"


def test_deployer_node_no_revenue_address(monkeypatch):
    monkeypatch.delenv("REVENUE_SERVICE_ADDRESS", raising=False)
    from swarm.nodes import deployer_node
    from swarm.state import SwarmState
    state: SwarmState = {"goal": "g", "tasks": []}
    out = deployer_node(state)
    assert "deploy_status" in out
    assert "Run:" in out["deploy_status"] or "run" in out["deploy_status"].lower()


def test_deployer_node_with_revenue_address(monkeypatch):
    monkeypatch.setenv("REVENUE_SERVICE_ADDRESS", "0x0000000000000000000000000000000000000001")
    import importlib
    import swarm.nodes as nodes_mod
    importlib.reload(nodes_mod)
    from swarm.state import SwarmState
    state: SwarmState = {"goal": "g", "tasks": []}
    out = nodes_mod.deployer_node(state)
    assert out["deploy_status"] == "Contract deployed at 0x0000000000000000000000000000000000000001"


def test_finance_distributor_node_returns_dict_when_no_address(monkeypatch):
    monkeypatch.delenv("FINANCE_DISTRIBUTOR_ADDRESS", raising=False)
    monkeypatch.delenv("TREASURY_ADDRESS", raising=False)
    import importlib
    import swarm.nodes as nodes_mod
    importlib.reload(nodes_mod)
    from swarm.state import SwarmState
    state: SwarmState = {"goal": "g", "tasks": [], "tx_hashes": ["0x1"]}
    out = nodes_mod.finance_distributor_node(state)
    assert isinstance(out, dict)
    assert "done" in out
