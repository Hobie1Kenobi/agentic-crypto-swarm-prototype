from swarm.state import SwarmState


def test_swarm_state_typed_dict_keys():
    state: SwarmState = {}
    state["goal"] = "test goal"
    state["tasks"] = ["task1", "task2"]
    state["tx_hashes"] = []
    assert state["goal"] == "test goal"
    assert len(state["tasks"]) == 2
    assert state["tx_hashes"] == []


def test_swarm_state_optional_keys():
    state: SwarmState = {
        "goal": "x",
        "tasks": [],
        "ip_output": "prompt",
        "deploy_status": "deployed",
        "simulation_summary": "10 users",
        "treasury_balance_wei": 1000,
        "profit_so_far_wei": 500,
        "tx_hashes": ["0xabc"],
        "done": True,
    }
    assert state.get("ip_output") == "prompt"
    assert state.get("deploy_status") == "deployed"
    assert state.get("simulation_summary") == "10 users"
    assert state.get("treasury_balance_wei") == 1000
    assert state.get("profit_so_far_wei") == 500
    assert state.get("done") is True


def test_swarm_state_partial():
    state: SwarmState = {"goal": "only goal"}
    assert state["goal"] == "only goal"
    assert state.get("tasks") is None
    assert state.get("tx_hashes") is None
