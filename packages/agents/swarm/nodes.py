import os
import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from .state import SwarmState
from .llm import get_llm

CONSTITUTION = "Only ethical, non-harmful services; no gambling, no illegal content; sustainable compute usage simulation."


def _db_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    for _ in range(5):
        if (root / "foundry.toml").exists() or (root / ".env.example").exists():
            return root / "swarm_state.db"
        root = root.parent
    return Path("swarm_state.db")


def _persist(state: SwarmState) -> None:
    db = _db_path()
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS swarm_runs (
            id INTEGER PRIMARY KEY,
            goal TEXT,
            tasks TEXT,
            ip_output TEXT,
            deploy_status TEXT,
            treasury_balance_wei INTEGER,
            profit_so_far_wei INTEGER,
            tx_hashes TEXT,
            done INTEGER,
            created_at DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute(
        "INSERT INTO swarm_runs (goal, tasks, ip_output, deploy_status, treasury_balance_wei, profit_so_far_wei, tx_hashes, done) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            state.get("goal"),
            ",".join(state.get("tasks", [])),
            state.get("ip_output"),
            state.get("deploy_status"),
            state.get("treasury_balance_wei"),
            state.get("profit_so_far_wei"),
            ",".join(state.get("tx_hashes", [])),
            1 if state.get("done") else 0,
        ),
    )
    conn.commit()
    conn.close()


def strategist_node(state: SwarmState) -> SwarmState:
    goal = state.get("goal", "maximize sustainable revenue via AI service")
    llm = get_llm()
    resp = llm.invoke(
        [
            SystemMessage(content=f"Constitution: {CONSTITUTION}"),
            HumanMessage(
                content=f"Decompose this goal into 3-5 concrete tasks for a swarm of agents: {goal}. "
                "Tasks: IP-Generator creates oracle/prompt logic, Deployer ensures revenue contract is live, Finance-Distributor monitors treasury and distributes profits."
            ),
        ]
    )
    tasks = [t.strip() for t in resp.content.split("\n") if t.strip() and t.strip()[0].isdigit() or t.strip().startswith("-")]
    if not tasks:
        tasks = [t.strip() for t in resp.content.split("\n") if t.strip()]
    return {"tasks": tasks[:5], "goal": goal}


def ip_generator_node(state: SwarmState) -> SwarmState:
    tasks = state.get("tasks", [])
    llm = get_llm()
    resp = llm.invoke(
        [
            SystemMessage(content=f"Constitution: {CONSTITUTION}"),
            HumanMessage(
                content="Create a short algorithmic oracle or AI query prompt template (1-3 sentences) for a pay-per-query service. "
                "It must be ethical, non-harmful, and sustainable. Output only the prompt/template."
            ),
        ]
    )
    ip_output = resp.content.strip()
    _persist({**state, "ip_output": ip_output})
    return {"ip_output": ip_output}


def deployer_node(state: SwarmState) -> SwarmState:
    revenue_addr = os.getenv("REVENUE_SERVICE_ADDRESS", "")
    if revenue_addr:
        return {"deploy_status": f"Contract deployed at {revenue_addr}"}
    return {
        "deploy_status": "Run: forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast. Set REVENUE_SERVICE_ADDRESS in .env after deployment."
    }


def finance_distributor_node(state: SwarmState) -> SwarmState:
    try:
        from web3 import Web3

        rpc = os.getenv("RPC_URL") or (
            f"https://base-sepolia.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY', '')}"
        )
        if not rpc or "your_" in rpc:
            rpc = "https://sepolia.base.org"
        w3 = Web3(Web3.HTTPProvider(rpc))
        addr = os.getenv("FINANCE_DISTRIBUTOR_ADDRESS") or os.getenv("TREASURY_ADDRESS")
        if addr:
            bal = w3.eth.get_balance(addr)
            threshold = int(0.05 * 1e18)
            done = bal >= threshold
            return {
                "treasury_balance_wei": bal,
                "profit_so_far_wei": bal,
                "done": done,
            }
    except Exception as e:
        return {"deploy_status": str(e), "done": False}
    return {"done": False}


def should_continue(state: SwarmState) -> str:
    if state.get("done"):
        return "end"
    return "continue"
