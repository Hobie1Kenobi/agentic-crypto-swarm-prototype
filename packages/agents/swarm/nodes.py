import os
import sqlite3
import subprocess
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


def task_market_demo_node(state: SwarmState) -> SwarmState:
    if state.get("marketplace_done"):
        return {"marketplace_summary": state.get("marketplace_summary") or "Marketplace demo already completed", "marketplace_done": True}

    try:
        from task_market_demo import run_task_market_demo

        demo = run_task_market_demo()
        tx_hashes = [e.get("tx_hash") for e in demo.get("tx_hashes", []) if e.get("tx_hash")]
        ok = bool(demo.get("ok"))
        summary = demo.get("error") or (f"Task marketplace demo txs: {len(tx_hashes)}" if ok else "Task marketplace demo failed")
        return {
            "marketplace_summary": summary,
            "marketplace_done": ok,
            "marketplace_tx_hashes": tx_hashes,
            "tx_hashes": tx_hashes,
        }
    except Exception as e:
        return {"marketplace_summary": f"Task marketplace demo error: {e}", "marketplace_done": False}


def public_adapter_node(state: SwarmState) -> SwarmState:
    if state.get("public_adapter_done"):
        return {
            "public_adapter_summary": state.get("public_adapter_summary") or "Public adapter already completed",
            "public_adapter_done": True,
        }

    try:
        from services.public_market_adapter import run_public_adapter_demo

        prompt = os.getenv("PUBLIC_ADAPTER_PROMPT", "What is one ethical use of AI?").strip()
        force_hybrid = os.getenv("MARKET_MODE", "").strip().lower() == "hybrid"
        out = run_public_adapter_demo(prompt, force_hybrid=force_hybrid)
        resp = out.get("public_response") or {}
        tx_hashes = resp.get("tx_hashes") or []

        ok = bool(resp.get("ok"))
        summary = f"Public adapter ok={ok} boundary={resp.get('boundary')}"
        return {
            "public_adapter_summary": summary,
            "public_adapter_done": ok,
            "public_adapter_external_request_id": resp.get("external_request_id"),
            "public_adapter_internal_task_id": resp.get("internal_task_id"),
            "public_adapter_tx_hashes": tx_hashes,
            "tx_hashes": tx_hashes,
        }
    except Exception as e:
        return {"public_adapter_summary": f"Public adapter error: {e}", "public_adapter_done": False}

def simulation_node(state: SwarmState) -> SwarmState:
    root = Path(__file__).resolve().parents[2]
    for _ in range(5):
        if (root / "foundry.toml").exists() or (root / ".env.example").exists():
            break
        root = root.parent
    log_path = root / "simulation_log.txt"
    try:
        proc = subprocess.run(
            [os.environ.get("PYTHON", "python"), "simulation_run.py"],
            cwd=root / "packages" / "agents",
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=600,
        )
        summary_lines = []
        tx_hashes = list(state.get("tx_hashes", []))
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "tx:" in line:
                    part = line.split("tx:")[-1].strip().split()
                    if part:
                        h = part[0]
                        if h.startswith("0x"):
                            tx_hashes.append(h)
                        elif len(h) == 64 and all(c in "0123456789abcdef" for c in h.lower()):
                            tx_hashes.append("0x" + h)
                if "Total paid:" in line or "Tx hashes:" in line or "Distribution tx:" in line:
                    summary_lines.append(line.strip())
        summary = "; ".join(summary_lines) if summary_lines else (proc.stdout or "")[:500]
        return {"simulation_summary": summary, "tx_hashes": tx_hashes}
    except subprocess.TimeoutExpired:
        return {"simulation_summary": "Simulation timed out (600s)"}
    except Exception as e:
        return {"simulation_summary": f"Simulation error: {e}"}


def _get_rpc() -> str:
    from config.chains import get_rpc as _cfg_rpc
    return _cfg_rpc()


def finance_distributor_node(state: SwarmState) -> SwarmState:
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(_get_rpc()))
        addr = os.getenv("FINANCE_DISTRIBUTOR_ADDRESS") or os.getenv("TREASURY_ADDRESS")
        if addr:
            bal = w3.eth.get_balance(addr)
            threshold_eth = float(os.getenv("SIMULATION_PROFIT_THRESHOLD_ETH", "0.05"))
            threshold = int(threshold_eth * 1e18)
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
