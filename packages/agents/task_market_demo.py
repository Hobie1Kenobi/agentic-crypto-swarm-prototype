from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from web3 import Web3
from dotenv import load_dotenv

from config.dual_chain import get_private_chain_config, get_private_marketplace_address
from services.agent_executor import get_default_executor
from swarm.llm import get_llm

from langchain_core.messages import HumanMessage, SystemMessage


CONSTITUTION = "Only ethical, non-harmful services; no gambling, no illegal content; sustainable compute usage simulation."
MAX_METADATA_LEN = 256

PROTOCOL_FEE_BPS = 1000  # 10%
FINANCE_FEE_BPS = 5000  # 50%

TASK_STATUS_NAMES = {
    0: "None",
    1: "Created",
    2: "Accepted",
    3: "Submitted",
    4: "Finalized",
    5: "Cancelled",
    6: "Expired",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _truncate(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[:max_len]


def _compute_score(response_text: str) -> int:
    # Keep the scoring deterministic/simple for demo purposes.
    resp = (response_text or "").strip()
    return min(100, max(0, len(resp) + (10 if "ethical" in resp.lower() else 0)))


def _should_load_env_local() -> bool:
    chain_id = os.getenv("CHAIN_ID", "").strip()
    rpc = os.getenv("RPC_URL", "").strip().lower()
    if os.getenv("USE_ENV_LOCAL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if chain_id == "31337":
        return True
    if rpc.startswith("http://127.0.0.1") or rpc.startswith("http://localhost"):
        return True

    # If the caller explicitly provided chain/RPC, trust it and don't auto-detect local.
    if chain_id or rpc:
        return False
    return False


def _load_env() -> None:
    # Safety: only load `.env.local` for local Anvil runs.
    root = _root()
    # Defensive: clear commonly-contaminated env vars so an IDE/session doesn't
    # accidentally override values from `.env` (load_dotenv does not unset keys).
    for k in [
        "MARKET_MODE",
        "CHAIN_NAME",
        "CHAIN_ID",
        "RPC_URL",
        "PRIVATE_KEY",
        "ROOT_STRATEGIST_PRIVATE_KEY",
        "IP_GENERATOR_PRIVATE_KEY",
        "DEPLOYER_PRIVATE_KEY",
        "FINANCE_DISTRIBUTOR_PRIVATE_KEY",
        "ROOT_STRATEGIST_ADDRESS",
        "IP_GENERATOR_ADDRESS",
        "DEPLOYER_ADDRESS",
        "FINANCE_DISTRIBUTOR_ADDRESS",
        "TREASURY_ADDRESS",
        "COMPUTE_MARKETPLACE_ADDRESS",
        "TASK_REQUESTER_ROLE",
        "TASK_WORKER_ROLE",
        "TASK_VALIDATOR_ROLE",
    ]:
        os.environ.pop(k, None)

    load_dotenv(root / ".env", override=True)
    loaded_local = False
    if _should_load_env_local() and (root / ".env.local").exists():
        load_dotenv(root / ".env.local", override=True)
        loaded_local = True

    # `python-dotenv` may preserve BOMs in the first key (e.g. `\ufeffRPC_URL`).
    # Normalize so downstream config helpers can reliably read `RPC_URL`.
    bom_key = "\ufeffRPC_URL"
    if loaded_local and bom_key in os.environ:
        os.environ["RPC_URL"] = os.environ[bom_key]
        # Clean up the BOM key so it doesn't leak into downstream logic.
        os.environ.pop(bom_key, None)


def _error_selector_map() -> dict[str, str]:
    """
    Map 4-byte custom error selectors to Solidity error names.
    Used to report reverts like `MinerAlreadyRegistered` by name.
    """

    # ComputeMarketplace.sol error signatures.
    sigs = [
        ("NotValidator", "NotValidator()"),
        ("MinerNotRegistered", "MinerNotRegistered()"),
        ("InvalidInput", "InvalidInput()"),
        ("TransferFailed", "TransferFailed()"),
        ("NoScores", "NoScores()"),
        ("NotRequester", "NotRequester()"),
        ("TaskNotFound", "TaskNotFound()"),
        ("InvalidTaskStatus", "InvalidTaskStatus(uint8)"),
        ("TaskIsExpired", "TaskIsExpired()"),
        ("WorkerNotAllowed", "WorkerNotAllowed()"),
        ("ResultAlreadySubmitted", "ResultAlreadySubmitted()"),
        ("NotWorker", "NotWorker()"),
        ("NotEnoughValidators", "NotEnoughValidators()"),
        ("MinerAlreadyRegistered", "MinerAlreadyRegistered()"),
        ("AlreadySubmitted", "AlreadySubmitted()"),
        ("InvalidScore", "InvalidScore()"),
        ("InsufficientPendingWithdrawal", "InsufficientPendingWithdrawal()"),
    ]
    out: dict[str, str] = {}
    for name, sig in sigs:
        selector = ("0x" + Web3.keccak(text=sig).hex()[:8]).lower()
        out[selector] = name
    return out


_CUSTOM_ERROR_BY_SELECTOR = None


def _decode_custom_error_name(exc: Exception) -> tuple[str | None, list[str]]:
    """
    Return (error_name, selectors_found).
    If decoding fails, error_name is None.
    """
    global _CUSTOM_ERROR_BY_SELECTOR
    if _CUSTOM_ERROR_BY_SELECTOR is None:
        _CUSTOM_ERROR_BY_SELECTOR = _error_selector_map()

    s = str(exc)
    selectors = re.findall(r"0x[a-fA-F0-9]{8}", s)
    selectors = [sel.lower() for sel in selectors]
    if not selectors:
        return None, []

    for sel in selectors:
        if sel in _CUSTOM_ERROR_BY_SELECTOR:
            return _CUSTOM_ERROR_BY_SELECTOR[sel], selectors
    return None, selectors


def _llm_answer(query: str) -> str:
    llm = get_llm()
    resp = llm.invoke(
        [
            SystemMessage(content=CONSTITUTION),
            HumanMessage(content=f"Answer this query in one or two sentences. Query: {query}. Output only the answer."),
        ]
    )
    return (resp.content or "").strip() or "Response generated."


def run_task_market_demo() -> dict[str, Any]:
    _load_env()
    private_cfg = get_private_chain_config()
    chain_id = private_cfg.chain_id
    rpc = private_cfg.rpc_url
    explorer_url = private_cfg.explorer_url
    native_symbol = private_cfg.native_symbol

    marketplace_addr = get_private_marketplace_address().strip()
    if not marketplace_addr:
        return {"ok": False, "error": "PRIVATE_MARKETPLACE_ADDRESS or COMPUTE_MARKETPLACE_ADDRESS not set"}

    w3 = Web3(Web3.HTTPProvider(rpc))
    connected = w3.is_connected()

    # Deterministic demo defaults.
    task_escrow_eth = float(os.getenv("TASK_ESCROW_ETH", "0.01"))
    min_validators = int(os.getenv("TASK_MIN_VALIDATORS", "1"))
    min_average_score = int(os.getenv("TASK_MIN_AVG_SCORE", "0"))
    deadline_seconds = int(os.getenv("TASK_DEADLINE_SECONDS", "3600"))
    worker_metadata = os.getenv("COMPUTE_WORKER_METADATA", os.getenv("COMPUTE_MINER_METADATA", "swarm-worker-1")).strip()

    task_query = os.getenv("COMPUTE_TASK_QUERY", "What is one ethical use of AI?").strip()
    task_metadata = os.getenv("COMPUTE_TASK_METADATA", "task-market-demo").strip()

    if len(task_query) > MAX_METADATA_LEN:
        task_query = _truncate(task_query, MAX_METADATA_LEN)
    if len(task_metadata) > MAX_METADATA_LEN:
        task_metadata = _truncate(task_metadata, MAX_METADATA_LEN)

    # Roles for the demo (must match the keys in signer executor).
    requester_role = os.getenv("TASK_REQUESTER_ROLE", "ROOT_STRATEGIST").strip() or "ROOT_STRATEGIST"
    worker_role = os.getenv("TASK_WORKER_ROLE", "IP_GENERATOR").strip() or "IP_GENERATOR"
    validator_role = os.getenv("TASK_VALIDATOR_ROLE", "DEPLOYER").strip() or "DEPLOYER"
    finance_role = "FINANCE_DISTRIBUTOR"
    owner_role = "OWNER"  # falls back to PRIVATE_KEY in SimpleSignerAgentExecutor

    result: dict[str, Any] = {
        "ok": connected,
        "chain_id": chain_id,
        "rpc": rpc,
        "explorer_url": explorer_url,
        "native_symbol": native_symbol,
        "compute_marketplace_address": marketplace_addr,
        "roles": {},
        "task": {},
        "warnings": [],
        "errors": [],
        "tx_hashes": [],
        "balances": {},
        "dry_run": not connected,
    }

    if not connected:
        # Still produce a useful dry-run report.
        answer = _llm_answer(task_query)
        score = _compute_score(answer)
        result["task"] = {
            "query": task_query,
            "task_metadata": task_metadata,
            "worker_metadata": worker_metadata,
            "expected_score": score,
            "escrow_eth": task_escrow_eth,
            "min_validators": min_validators,
            "min_average_score": min_average_score,
            "deadline_seconds": deadline_seconds,
        }

        _write_text(_root() / "task_market_demo_report.md", f"# Task Marketplace Demo (dry-run)\n\nRPC not connected ({rpc}).\n")
        return result

    executor = get_default_executor(w3, chain_id)
    requester_addr = w3.to_checksum_address(executor.get_sender_address(requester_role))
    worker_addr = w3.to_checksum_address(executor.get_sender_address(worker_role))
    validator_addr = w3.to_checksum_address(executor.get_sender_address(validator_role))
    finance_addr = w3.to_checksum_address(executor.get_sender_address(finance_role))
    owner_addr = w3.to_checksum_address(executor.get_sender_address(owner_role))

    # Ensure three distinct signers: requester, worker, validator.
    # If env keys accidentally point to the same EOA, pick alternate roles from keys we know.
    if len({requester_addr.lower(), worker_addr.lower(), validator_addr.lower()}) < 3:
        role_addr_cache: dict[str, str] = {
            requester_role: requester_addr,
            worker_role: worker_addr,
            validator_role: validator_addr,
            finance_role: finance_addr,
            "DEPLOYER": w3.to_checksum_address(executor.get_sender_address("DEPLOYER")),
            "IP_GENERATOR": w3.to_checksum_address(executor.get_sender_address("IP_GENERATOR")),
        }

        used = {requester_addr.lower()}
        if worker_addr.lower() in used:
            for alt_role in ["IP_GENERATOR", "FINANCE_DISTRIBUTOR", "DEPLOYER"]:
                alt_addr = role_addr_cache.get(alt_role)
                if alt_addr and alt_addr.lower() not in used:
                    worker_role = alt_role
                    worker_addr = alt_addr
                    used.add(worker_addr.lower())
                    break

        used = {requester_addr.lower(), worker_addr.lower()}
        if validator_addr.lower() in used:
            for alt_role in ["DEPLOYER", "IP_GENERATOR", "FINANCE_DISTRIBUTOR"]:
                alt_addr = role_addr_cache.get(alt_role)
                if alt_addr and alt_addr.lower() not in used:
                    validator_role = alt_role
                    validator_addr = alt_addr
                    used.add(validator_addr.lower())
                    break

    # Recompute in case we adjusted roles.
    requester_addr = w3.to_checksum_address(executor.get_sender_address(requester_role))
    worker_addr = w3.to_checksum_address(executor.get_sender_address(worker_role))
    validator_addr = w3.to_checksum_address(executor.get_sender_address(validator_role))

    # Public Celo RPCs can report slightly stale "pending" nonces.
    # Maintain a per-sender nonce cache so sequential txs don't accidentally reuse a nonce.
    nonce_cache: dict[str, int] = {}

    def _nonce(addr: str) -> int:
        addr_cs = w3.to_checksum_address(addr)
        key = addr_cs.lower()
        if key not in nonce_cache:
            nonce_cache[key] = w3.eth.get_transaction_count(addr_cs, "pending")
        return nonce_cache[key]

    result["roles"] = {
        "requester": {"role": requester_role, "address": requester_addr},
        "worker": {"role": worker_role, "address": worker_addr},
        "validator": {"role": validator_role, "address": validator_addr},
        "finance_distributor": {"role": finance_role, "address": finance_addr},
        "owner": {"role": owner_role},
    }

    abi = [
        {
            "inputs": [
                {"internalType": "string", "name": "taskMetadata", "type": "string"},
                {"internalType": "string", "name": "query", "type": "string"},
                {"internalType": "address", "name": "assignedWorker", "type": "address"},
                {"internalType": "uint256", "name": "minValidators", "type": "uint256"},
                {"internalType": "uint256", "name": "minAverageScore", "type": "uint256"},
                {"internalType": "uint256", "name": "deadlineAt", "type": "uint256"},
            ],
            "name": "createTask",
            "outputs": [{"internalType": "uint256", "name": "taskId", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "taskId", "type": "uint256"}],
            "name": "acceptTask",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "taskId", "type": "uint256"},
                {"internalType": "string", "name": "resultMetadata", "type": "string"},
            ],
            "name": "submitResult",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "taskId", "type": "uint256"},
                {"internalType": "uint256", "name": "score", "type": "uint256"},
                {"internalType": "bytes32", "name": "notesHash", "type": "bytes32"},
            ],
            "name": "submitTaskScore",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "taskId", "type": "uint256"}],
            "name": "finalizeTask",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "validator", "type": "address"}, {"internalType": "bool", "name": "allowed", "type": "bool"}],
            "name": "setValidatorAllowlist",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "string", "name": "metadata", "type": "string"}],
            "name": "registerAsMiner",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {"inputs": [], "name": "nextTaskId", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "treasury", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "financeDistributor", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "pendingWithdrawals", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "validators", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "miners", "outputs": [{"internalType": "address", "name": "addr", "type": "address"}, {"internalType": "string", "name": "metadata", "type": "string"}, {"internalType": "bool", "name": "registered", "type": "bool"}], "stateMutability": "view", "type": "function"},
        {
            "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "name": "tasks",
            "outputs": [
                {"internalType": "address", "name": "requester", "type": "address"},
                {"internalType": "address", "name": "assignedWorker", "type": "address"},
                {"internalType": "uint256", "name": "escrowWei", "type": "uint256"},
                {"internalType": "string", "name": "taskMetadata", "type": "string"},
                {"internalType": "string", "name": "query", "type": "string"},
                {"internalType": "bytes32", "name": "taskMetadataHash", "type": "bytes32"},
                {"internalType": "uint8", "name": "status", "type": "uint8"},
                {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                {"internalType": "uint256", "name": "acceptedAt", "type": "uint256"},
                {"internalType": "uint256", "name": "submittedAt", "type": "uint256"},
                {"internalType": "uint256", "name": "deadlineAt", "type": "uint256"},
                {"internalType": "uint256", "name": "minValidators", "type": "uint256"},
                {"internalType": "uint256", "name": "minAverageScore", "type": "uint256"},
                {"internalType": "uint256", "name": "scoreSum", "type": "uint256"},
                {"internalType": "uint256", "name": "submittedValidators", "type": "uint256"},
                {"internalType": "bytes32", "name": "resultHash", "type": "bytes32"},
                {"internalType": "string", "name": "resultMetadata", "type": "string"}
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {"inputs": [], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    ]

    contract = w3.eth.contract(address=w3.to_checksum_address(marketplace_addr), abi=abi)

    # Some RPC endpoints sporadically return empty data for eth_call; use retries + selector fallback.
    def _call_with_retries(fn_name: str) -> bytes:
        sel = "0x" + Web3.keccak(text=f"{fn_name}()").hex()[:8]
        last_err: Exception | None = None
        for _ in range(5):
            try:
                out = w3.eth.call({"to": w3.to_checksum_address(marketplace_addr), "data": sel})
                if out and len(out) >= 32:
                    return out
            except Exception as ee:  # pragma: no cover
                last_err = ee
            time.sleep(1)
        if last_err:
            raise last_err
        return b""

    treasury_addr = None
    finance_contract_addr = None
    for _ in range(3):
        try:
            treasury_addr = w3.to_checksum_address(contract.functions.treasury().call())
            finance_contract_addr = w3.to_checksum_address(contract.functions.financeDistributor().call())
            break
        except Exception:
            time.sleep(1)

    if not treasury_addr or not finance_contract_addr:
        raw_t = _call_with_retries("treasury")
        raw_f = _call_with_retries("financeDistributor")
        if not raw_t or not raw_f:
            raise ValueError("RPC returned empty data for treasury()/financeDistributor() after retries.")
        treasury_addr = w3.to_checksum_address("0x" + raw_t.hex()[-40:])
        finance_contract_addr = w3.to_checksum_address("0x" + raw_f.hex()[-40:])
        result["warnings"].append("eth_call fallback used for treasury/financeDistributor due to sporadic empty responses.")
    result["contracts"] = {
        "treasury": treasury_addr,
        "finance_distributor": finance_contract_addr,
    }

    # Presentation-grade hybrid: ensure worker and treasury are distinct if we can.
    # If the configured worker signer equals the onchain treasury, pick a different worker role
    # from the available signers (without changing the onchain contract config).
    if worker_addr.lower() == treasury_addr.lower():
        for alt_role in ["DEPLOYER", "IP_GENERATOR", "FINANCE_DISTRIBUTOR", "ROOT_STRATEGIST"]:
            try:
                alt_addr = w3.to_checksum_address(executor.get_sender_address(alt_role))
            except Exception:
                continue
            if alt_addr.lower() != treasury_addr.lower() and alt_addr.lower() != requester_addr.lower():
                worker_role = alt_role
                worker_addr = alt_addr
                result["warnings"].append(
                    f"worker signer matched treasury; switched worker_role to {alt_role} for demo separation."
                )
                result["roles"]["worker"] = {"role": worker_role, "address": worker_addr}
                break

    def _send(role: str, tx_build: dict[str, Any]) -> str:
        tx_hash = executor.send_transaction(
            role,
            to=tx_build["to"],
            value=tx_build.get("value", 0),
            data=tx_build["data"],
            gas=tx_build["gas"],
            nonce=tx_build["nonce"],
            chain_id=chain_id,
            gas_price=tx_build.get("gasPrice"),
        )
        # After a successful broadcast, advance our local nonce cache.
        sender = w3.to_checksum_address(executor.get_sender_address(role)).lower()
        used_nonce = tx_build.get("nonce")
        if used_nonce is not None:
            nonce_cache[sender] = int(used_nonce) + 1
        return tx_hash

    def _wait(tx_hash: str) -> None:
        w3.eth.wait_for_transaction_receipt(tx_hash)

    def _tx_hash_link(tx_hash: str) -> str:
        if not explorer_url:
            return tx_hash
        return f"{explorer_url}/tx/{tx_hash}"

    result["roles"]["treasury"] = {"role": "TREASURY", "address": treasury_addr}

    role_addresses = [requester_addr, worker_addr, validator_addr, treasury_addr, finance_contract_addr]
    unique_role_addrs = {w3.to_checksum_address(a).lower() for a in role_addresses}
    if len(unique_role_addrs) < 5:
        result["errors"].append({
            "step": "roles",
            "message": "Private demo requires five distinct addresses: requester, worker, validator, treasury, finance_distributor. Set TREASURY_PRIVATE_KEY and TREASURY_ADDRESS at deploy so treasury is distinct from the other four.",
        })
        return {**result, "ok": False, "error": "Five distinct role addresses required."}

    actors = role_addresses
    uniq_actors = list({a.lower(): a for a in actors}.values())
    for a in uniq_actors:
        result["balances"].setdefault("pre", {})[a] = w3.eth.get_balance(w3.to_checksum_address(a))

    # Register worker as miner (idempotent).
    result["task"]["worker_registered"] = False
    try:
        miner_info = contract.functions.miners(worker_addr).call()
        # (addr, metadata, registered)
        result["task"]["worker_registered"] = bool(miner_info[2])
    except Exception:
        # If we can't read state, we'll attempt the registration tx below.
        result["task"]["worker_registered"] = False

    if not result["task"]["worker_registered"]:
        metadata_to_use = _truncate(worker_metadata, MAX_METADATA_LEN)
        try:
            tx = contract.functions.registerAsMiner(metadata_to_use).build_transaction(
                {"from": worker_addr, "chainId": chain_id, "nonce": _nonce(worker_addr)}
            )
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = _send(worker_role, tx)
            result["tx_hashes"].append(
                {"name": "registerAsMiner", "role": worker_role, "tx_hash": tx_hash, "link": _tx_hash_link(tx_hash)}
            )
            _wait(tx_hash)
            result["task"]["worker_registered"] = True
        except Exception as e:
            err_name, selectors = _decode_custom_error_name(e)
            if err_name == "MinerAlreadyRegistered":
                result["warnings"].append("registerAsMiner: MinerAlreadyRegistered (non-fatal).")
                result["task"]["worker_registered"] = True
            else:
                result["errors"].append({"step": "registerAsMiner", "error_name": err_name, "selectors": selectors, "message": str(e)})
                return {**result, "ok": False, "error": str(e)}
    else:
        result["warnings"].append("registerAsMiner: already registered (skipped).")
        result["task"]["worker_registered"] = True

    # Allowlist validator (idempotent).
    result["task"]["validator_allowlisted"] = False
    try:
        allowed = contract.functions.validators(validator_addr).call()
        result["task"]["validator_allowlisted"] = bool(allowed)
    except Exception:
        result["task"]["validator_allowlisted"] = False

    if not result["task"]["validator_allowlisted"]:
        try:
            tx = contract.functions.setValidatorAllowlist(validator_addr, True).build_transaction(
                {"from": owner_addr, "chainId": chain_id, "nonce": _nonce(owner_addr)}
            )
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = _send(owner_role, tx)
            result["tx_hashes"].append(
                {"name": "setValidatorAllowlist", "role": owner_role, "tx_hash": tx_hash, "link": _tx_hash_link(tx_hash)}
            )
            _wait(tx_hash)
            result["task"]["validator_allowlisted"] = True
        except Exception as e:
            err_name, selectors = _decode_custom_error_name(e)
            result["errors"].append({"step": "setValidatorAllowlist", "error_name": err_name, "selectors": selectors, "message": str(e)})
            return {**result, "ok": False, "error": str(e)}
    else:
        result["warnings"].append("setValidatorAllowlist: already allowlisted (skipped).")
        result["task"]["validator_allowlisted"] = True

    # Create escrow task.
    escrow_wei = int(task_escrow_eth * 1e18)
    deadline_at = int(time.time()) + deadline_seconds
    before_next = contract.functions.nextTaskId().call()
    answer = _llm_answer(task_query)
    score = _compute_score(answer)

    result_metadata = _truncate(answer, MAX_METADATA_LEN)
    # Do not trust a single pre-read `nextTaskId` on public RPCs; it can be stale.
    # We'll recompute the task id after `createTask` confirms.
    task_id = int(before_next)

    tx = contract.functions.createTask(
        task_metadata,
        task_query,
        worker_addr,
        min_validators,
        min_average_score,
        deadline_at,
    ).build_transaction(
        {
            "from": requester_addr,
            "value": escrow_wei,
            "chainId": chain_id,
                "nonce": _nonce(requester_addr),
        }
    )
    try:
        tx_hash = _send(requester_role, tx)
        result["tx_hashes"].append(
            {"name": "createTask", "role": requester_role, "tx_hash": tx_hash, "link": _tx_hash_link(tx_hash)}
        )
        _wait(tx_hash)
        # Recompute the task id from on-chain state (nextTaskId increments after create).
        # Public RPCs can lag; poll until nextTaskId advances and the task is readable.
        next_id = None
        for _ in range(10):
            try:
                next_id = int(contract.functions.nextTaskId().call())
                if next_id > int(before_next):
                    cand = next_id - 1
                    # sanity: ensure task exists and matches requester
                    t = contract.functions.tasks(cand).call()
                    if str(t[0]).lower() == requester_addr.lower():
                        task_id = int(cand)
                        break
            except Exception:
                pass
            time.sleep(2)
        if next_id is None:
            task_id = int(before_next)
    except Exception as e:
        err_name, selectors = _decode_custom_error_name(e)
        result["errors"].append(
            {"step": "createTask", "error_name": err_name, "selectors": selectors, "message": str(e)}
        )
        return {**result, "ok": False, "error": f"createTask failed: {err_name or str(e)}"}

    # Accept -> submit result -> score -> finalize.
    tx = contract.functions.acceptTask(task_id).build_transaction(
        {"from": worker_addr, "chainId": chain_id, "nonce": _nonce(worker_addr), "gas": 8000000}
    )
    try:
        tx_hash = _send(worker_role, tx)
        result["tx_hashes"].append(
            {"name": "acceptTask", "role": worker_role, "tx_hash": tx_hash, "link": _tx_hash_link(tx_hash)}
        )
        _wait(tx_hash)
    except Exception as e:
        err_name, selectors = _decode_custom_error_name(e)
        result["errors"].append(
            {"step": "acceptTask", "error_name": err_name, "selectors": selectors, "message": str(e)}
        )
        return {**result, "ok": False, "error": f"acceptTask failed: {err_name or str(e)}"}

    tx = contract.functions.submitResult(task_id, result_metadata).build_transaction(
        {"from": worker_addr, "chainId": chain_id, "nonce": _nonce(worker_addr)}
    )
    try:
        tx["gas"] = w3.eth.estimate_gas(tx)
        tx_hash = _send(worker_role, tx)
        result["tx_hashes"].append(
            {"name": "submitResult", "role": worker_role, "tx_hash": tx_hash, "link": _tx_hash_link(tx_hash)}
        )
        _wait(tx_hash)
    except Exception as e:
        err_name, selectors = _decode_custom_error_name(e)
        result["errors"].append(
            {"step": "submitResult", "error_name": err_name, "selectors": selectors, "message": str(e)}
        )
        return {**result, "ok": False, "error": f"submitResult failed: {err_name or str(e)}"}

    # Wait until the task is in Submitted state before submitTaskScore.
    # Public RPCs can lag, and submitTaskScore will revert with InvalidTaskStatus if the
    # chain hasn't reflected submitResult yet.
    for _ in range(10):
        try:
            t = contract.functions.tasks(task_id).call()
            status_val = int(t[6])
            if status_val >= 3:  # Submitted or beyond
                break
        except Exception:
            pass
        time.sleep(2)

    notes_hash = Web3.keccak(text=f"task-market-demo:{task_id}:{score}")
    tx = contract.functions.submitTaskScore(task_id, score, notes_hash).build_transaction(
        {"from": validator_addr, "chainId": chain_id, "nonce": _nonce(validator_addr), "gas": 8000000}
    )
    try:
        tx_hash = _send(validator_role, tx)
        result["tx_hashes"].append(
            {"name": "submitTaskScore", "role": validator_role, "tx_hash": tx_hash, "link": _tx_hash_link(tx_hash)}
        )
        _wait(tx_hash)
    except Exception as e:
        err_name, selectors = _decode_custom_error_name(e)
        result["errors"].append(
            {"step": "submitTaskScore", "error_name": err_name, "selectors": selectors, "message": str(e)}
        )
        return {**result, "ok": False, "error": f"submitTaskScore failed: {err_name or str(e)}"}

    # Wait until the task has enough validator approvals to finalize.
    submitted_validators_check = 0
    for _ in range(5):
        try:
            t = contract.functions.tasks(task_id).call()
            submitted_validators_check = int(t[14])
            if submitted_validators_check >= min_validators:
                break
        except Exception:
            pass
        time.sleep(2)
    if submitted_validators_check < min_validators:
        result["errors"].append(
            {
                "step": "pre_finalize",
                "error_name": "NotEnoughValidators",
                "selectors": [],
                "message": f"submittedValidators={submitted_validators_check} < min_validators={min_validators}",
            }
        )
        result["ok"] = False
        return result

    tx = contract.functions.finalizeTask(task_id).build_transaction(
        {"from": validator_addr, "chainId": chain_id, "nonce": _nonce(validator_addr), "gas": 8000000}
    )
    try:
        tx["gas"] = w3.eth.estimate_gas(tx)
        tx_hash = _send(validator_role, tx)
        result["tx_hashes"].append(
            {"name": "finalizeTask", "role": validator_role, "tx_hash": tx_hash, "link": _tx_hash_link(tx_hash)}
        )
        _wait(tx_hash)
    except Exception as e:
        err_name, selectors = _decode_custom_error_name(e)
        result["errors"].append(
            {"step": "finalizeTask", "error_name": err_name, "selectors": selectors, "message": str(e)}
        )
        return {**result, "ok": False, "error": f"finalizeTask failed: {err_name or str(e)}"}

    # Settlement accounting (protocolFee / financeFee / workerPayout / requesterRefund).
    task_onchain = None
    task_status_val = -1
    # FinalizeTask should flip status to `Finalized`, but some public RPCs may lag.
    for _ in range(5):
        task_onchain = contract.functions.tasks(task_id).call()
        task_status_val = int(task_onchain[6])
        if task_status_val == 4:  # Finalized
            break
        time.sleep(2)
    task_status_name = TASK_STATUS_NAMES.get(task_status_val, str(task_status_val))
    submitted_validators = int(task_onchain[14])
    score_sum = int(task_onchain[13])
    min_avg_onchain = int(task_onchain[12])
    average_score = (score_sum // submitted_validators) if submitted_validators else 0

    # Contract formula:
    # protocolFee = escrow * 10%
    # financeFee  = escrow * 50%
    # workerPool  = escrow - protocolFee - financeFee = 40% of escrow
    # workerPayout = workerPool * averageScore / 100 (if averageScore >= minAverageScore)
    # requesterRefund = workerPool - workerPayout
    protocol_fee_wei = escrow_wei * PROTOCOL_FEE_BPS // 10000
    finance_fee_wei = escrow_wei * FINANCE_FEE_BPS // 10000
    worker_pool_wei = escrow_wei - protocol_fee_wei - finance_fee_wei

    if average_score < min_avg_onchain:
        worker_payout_expected_wei = 0
        requester_refund_expected_wei = worker_pool_wei
    else:
        worker_payout_expected_wei = (worker_pool_wei * average_score) // 100
        if worker_payout_expected_wei > worker_pool_wei:
            worker_payout_expected_wei = worker_pool_wei
        requester_refund_expected_wei = worker_pool_wei - worker_payout_expected_wei

    # Some RPC endpoints can be slightly delayed in reflecting state; poll briefly.
    # PendingWithdrawals are credited per-address, so if multiple logical buckets map to
    # the same address (e.g. treasury == financeDistributor), we must compare totals.
    bucket_by_addr = [
        (treasury_addr, protocol_fee_wei),
        (finance_contract_addr, finance_fee_wei),
        (worker_addr, worker_payout_expected_wei),
        (requester_addr, requester_refund_expected_wei),
    ]
    expected_totals_by_addr: dict[str, int] = {}
    addr_canonical: dict[str, str] = {}
    for addr, amt in bucket_by_addr:
        a = w3.to_checksum_address(addr).lower()
        expected_totals_by_addr[a] = expected_totals_by_addr.get(a, 0) + int(amt)
        addr_canonical[a] = w3.to_checksum_address(addr)

    pending_actual_by_addr: dict[str, int] = {k: 0 for k in expected_totals_by_addr.keys()}
    settlement_matches = False
    for _ in range(5):
        for a_lower, a in addr_canonical.items():
            pending_actual_by_addr[a_lower] = int(contract.functions.pendingWithdrawals(w3.to_checksum_address(a)).call())
        settlement_matches = all(
            pending_actual_by_addr[a_lower] == expected_totals_by_addr[a_lower]
            for a_lower in expected_totals_by_addr.keys()
        )
        if settlement_matches:
            break
        time.sleep(2)

    pending_created = {addr_canonical[a_lower]: pending_actual_by_addr[a_lower] for a_lower in addr_canonical.keys()}

    # Economic settlement breakdown (category-first, not just by address).
    categories = {
        "protocol_fee": {"address": treasury_addr, "expected_wei": int(protocol_fee_wei)},
        "finance_fee": {"address": finance_contract_addr, "expected_wei": int(finance_fee_wei)},
        "worker_payout": {"address": worker_addr, "expected_wei": int(worker_payout_expected_wei)},
        "requester_refund": {"address": requester_addr, "expected_wei": int(requester_refund_expected_wei)},
    }
    by_address: dict[str, Any] = {}
    for cat, info in categories.items():
        a = w3.to_checksum_address(info["address"])
        a_key = a.lower()
        by_address.setdefault(
            a,
            {
                "total_expected_wei": 0,
                "total_actual_pending_wei": int(contract.functions.pendingWithdrawals(a).call()),
                "categories": [],
            },
        )
        by_address[a]["total_expected_wei"] += int(info["expected_wei"])
        by_address[a]["categories"].append(
            {"category": cat, "expected_wei": int(info["expected_wei"])}
        )
    # Category "actual" is only unambiguous when the category's address is unique.
    # If multiple categories map to the same address, we report combined entitlement.
    addr_to_cats: dict[str, list[str]] = {}
    for cat, info in categories.items():
        addr_to_cats.setdefault(w3.to_checksum_address(info["address"]).lower(), []).append(cat)
    for cat, info in categories.items():
        a_lower = w3.to_checksum_address(info["address"]).lower()
        if len(addr_to_cats.get(a_lower, [])) == 1:
            info["actual_pending_wei"] = int(pending_actual_by_addr.get(a_lower, 0))
        else:
            info["actual_pending_wei"] = None
            info["note"] = "Combined entitlement with other categories at same address."

    result["task"].update(
        {
            "task_id": int(task_id),
            "task_status": {"value": task_status_val, "name": task_status_name},
            "escrow_wei": escrow_wei,
            "escrow_eth": escrow_wei / 1e18,
            "validator_approvals": submitted_validators,
            "average_score": average_score,
            "min_average_score": min_avg_onchain,
            "worker_payout_expected_wei": worker_payout_expected_wei,
            "worker_payout_actual_wei": pending_actual_by_addr[w3.to_checksum_address(worker_addr).lower()],
            "protocol_fee_wei": protocol_fee_wei,
            "protocol_fee_actual_wei": pending_actual_by_addr[w3.to_checksum_address(treasury_addr).lower()],
            "finance_fee_wei": finance_fee_wei,
            "finance_fee_actual_wei": pending_actual_by_addr[w3.to_checksum_address(finance_contract_addr).lower()],
            "requester_refund_expected_wei": requester_refund_expected_wei,
            "requester_refund_actual_wei": pending_actual_by_addr[w3.to_checksum_address(requester_addr).lower()],
            "pending_withdrawals_created": {
                a: w for a, w in pending_created.items()
            },
            "settlement": {
                "by_category": categories,
                "by_address": by_address,
            },
        }
    )
    result["task"]["settlement_matches_expected"] = settlement_matches
    # If we have a full settlement match, we can safely fill category-level "actual"
    # amounts even when multiple categories share the same address (we otherwise report
    # None because per-category onchain pending is not directly queryable).
    if settlement_matches:
        for _cat, info in categories.items():
            if info.get("actual_pending_wei") is None:
                info["actual_pending_wei"] = int(info.get("expected_wei") or 0)
                info["note"] = "Combined entitlement at same address; actual equals expected (settlement_matches_expected=true)."
    if not settlement_matches:
        result["warnings"].append("Settlement mismatch: pendingWithdrawals differ from expected formula.")
    # If settlement doesn't match, treat the demo as not fully successful.
    if not settlement_matches:
        result["ok"] = False

    # Withdraw created pending withdrawals (idempotent / non-fatal).
    signer_roles_by_address: dict[str, str] = {}
    treasury_role = "TREASURY"
    for role in [requester_role, worker_role, validator_role, finance_role, treasury_role, owner_role]:
        try:
            a = executor.get_sender_address(role).lower()
            if a in signer_roles_by_address:
                if signer_roles_by_address[a] == "OWNER" and role != "OWNER":
                    signer_roles_by_address[a] = role
            else:
                signer_roles_by_address[a] = role
        except Exception:
            pass

    withdrawals: dict[str, Any] = {}
    withdraw_addrs = [requester_addr, worker_addr, treasury_addr, finance_contract_addr]
    for a in list({x.lower(): x for x in withdraw_addrs}.values()):
        before = int(contract.functions.pendingWithdrawals(w3.to_checksum_address(a)).call())
        claim = {"pending_before_wei": before, "tx_hash": None, "error": None, "skipped": None, "pending_after_wei": None}

        if before == 0:
            claim["skipped"] = "no_pending"
            withdrawals[a] = claim
            continue

        claim_role = signer_roles_by_address.get(a.lower())
        if not claim_role:
            claim["skipped"] = "signer_not_available"
            withdrawals[a] = claim
            result["warnings"].append(f"withdraw({a}) skipped: signer not available for that address.")
            continue

        signer_addr = w3.to_checksum_address(executor.get_sender_address(claim_role))
        if signer_addr.lower() != w3.to_checksum_address(a).lower():
            claim["skipped"] = "signer_address_mismatch"
            withdrawals[a] = claim
            result["warnings"].append(f"withdraw({a}) skipped: signer_address_mismatch.")
            continue

        # Some RPC endpoints may show state updates slightly delayed.
        pending = before
        for _ in range(5):
            pending = int(contract.functions.pendingWithdrawals(w3.to_checksum_address(a)).call())
            if pending != 0:
                break
            time.sleep(2)
        if pending == 0:
            claim["skipped"] = "pending_disappeared"
            withdrawals[a] = claim
            continue

        try:
            tx = contract.functions.withdraw().build_transaction(
                {
                    "from": signer_addr,
                    "chainId": chain_id,
                    "nonce": _nonce(signer_addr),
                }
            )
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = _send(claim_role, tx)
            claim["tx_hash"] = tx_hash
            # Label withdrawal by the runtime role this address represents.
            runtime_role = "UNKNOWN"
            for rk, rv in (result.get("roles") or {}).items():
                if isinstance(rv, dict) and rv.get("address") and str(rv.get("address")).lower() == a.lower():
                    runtime_role = str(rv.get("role") or rk).upper()
                    break
            result["tx_hashes"].append(
                {
                    "name": "withdraw",
                    "role": runtime_role,
                    "signer_role": claim_role,
                    "who": a,
                    "tx_hash": tx_hash,
                    "link": _tx_hash_link(tx_hash),
                }
            )
            _wait(tx_hash)
            pending_after = int(contract.functions.pendingWithdrawals(w3.to_checksum_address(a)).call())
            for _ in range(5):
                if pending_after == 0:
                    break
                pending_after = int(contract.functions.pendingWithdrawals(w3.to_checksum_address(a)).call())
                if pending_after == 0:
                    break
                time.sleep(2)
            claim["pending_after_wei"] = pending_after
        except Exception as e:
            err_name, selectors = _decode_custom_error_name(e)
            claim["error"] = {"error_name": err_name, "selectors": selectors, "message": str(e)}
            claim["pending_after_wei"] = int(contract.functions.pendingWithdrawals(w3.to_checksum_address(a)).call())

        withdrawals[a] = claim

    result["withdrawals"] = withdrawals
    # If we had pending withdrawals but couldn't claim them (signer mismatch or missing signer),
    # treat as a demo failure so the report is not misleading.
    for a, c in withdrawals.items():
        if int(c.get("pending_before_wei") or 0) > 0 and c.get("tx_hash") is None:
            if c.get("skipped") in {"no_pending", "pending_disappeared"}:
                continue
            if c.get("error") is not None:
                result["ok"] = False
            if c.get("skipped") in {"signer_not_available", "signer_address_mismatch"}:
                result["ok"] = False
        if int(c.get("pending_before_wei") or 0) > 0 and c.get("tx_hash") is not None:
            if int(c.get("pending_after_wei") or 0) != 0:
                result["ok"] = False

    # Post balances.
    for a in uniq_actors:
        result["balances"].setdefault("post", {})[a] = w3.eth.get_balance(w3.to_checksum_address(a))

    # Report outputs.
    root = _root()
    out_manifest = {
        "chain_id": chain_id,
        "rpc": rpc,
        "compute_marketplace_address": marketplace_addr,
        "treasury_address": treasury_addr,
        "finance_distributor_address": finance_contract_addr,
        "roles": {k: v["address"] for k, v in result["roles"].items() if isinstance(v, dict) and "address" in v},
    }

    task_summary = f"""
Task Marketplace Demo (chain {chain_id})
TaskId: {task_id}
Escrow: {task_escrow_eth} {native_symbol}
Worker: {worker_addr}
Validator: {validator_addr}
Answer: {result_metadata}
Score: {score}
"""

    tx_lines: list[str] = []
    for entry in result["tx_hashes"]:
        if not entry.get("tx_hash"):
            tx_lines.append(f"- {entry.get('name')} ({entry.get('role')}): error: {entry.get('error')}")
            continue
        name = entry.get("name")
        role = entry.get("role")
        link = entry.get("link") or entry.get("tx_hash")
        tx_lines.append(f"- {name} [{role}]: `{entry['tx_hash']}` -> {link}")

    warnings_md = "\n".join([f"- {w}" for w in result.get("warnings", [])]) or "- (none)"
    errors_md = "\n".join(
        [
            "- {step}: {name}{sel}{msg}".format(
                step=e.get("step", "error"),
                name=e.get("error_name") or "UnknownError",
                sel=(" selectors=" + ", ".join(e.get("selectors", [])[:5])) if e.get("selectors") else "",
                msg=(" " + str(e.get("message", ""))).strip(),
            )
            for e in result.get("errors", [])
        ]
    ) or "- (none)"
    withdrawals_md = "\n".join(
        [
            f"- {addr}: before={c.get('pending_before_wei')} wei, after={c.get('pending_after_wei')} wei, tx={c.get('tx_hash') or c.get('skipped')}"
            for addr, c in (result.get("withdrawals") or {}).items()
        ]
    ) or "- (none)"

    task_info = result.get("task", {})
    task_status = task_info.get("task_status", {})
    task_status_name = task_status.get("name") or task_status.get("value") or "—"
    settlement_matches = task_info.get("settlement_matches_expected", False)

    md = f"""# Task Marketplace Demo Report
## Lifecycle Proof
- Chain ID: `{chain_id}`
- Marketplace: `{marketplace_addr}`
- TaskId: `{task_id}`
- Task status: `{task_status_name}`
- Escrow: `{task_escrow_eth}` {native_symbol} (`{escrow_wei}` wei)
- Requester: `{requester_addr}` (`{requester_role}`)
- Worker: `{worker_addr}` (`{worker_role}`)
- Validator: `{validator_addr}` (`{validator_role}`)
- Validator approvals: `{submitted_validators}`
- Score: `{score}`

## Settlement Accounting
- Protocol fee (10%): `{protocol_fee_wei / 1e18:.6f}` {native_symbol}
- Finance fee (50%): `{finance_fee_wei / 1e18:.6f}` {native_symbol}
- Worker payout: `{worker_payout_expected_wei / 1e18:.6f}` {native_symbol}
- Requester refund: `{requester_refund_expected_wei / 1e18:.6f}` {native_symbol}
- PendingWithdrawals matches expected: `{settlement_matches}`

## Pending Withdrawals Created/Claimed
- Withdrawals summary: (see JSON under `withdrawals`)
{withdrawals_md}

## Transaction Links
{chr(10).join(tx_lines)}

## Warnings (non-fatal)
{warnings_md}

## Errors
{errors_md}
"""

    _write_text(root / "task_market_demo_report.md", md)
    _write_json(root / "deployed_address_manifest.json", out_manifest)

    if chain_id == 31337:
        _write_text(root / "local_task_market_report.md", md)
        _write_json(root / "local_task_market_report.json", result)
        _write_json(root / "deployed_local_address_manifest.json", out_manifest)
    elif chain_id == 11142220:
        _write_json(root / "celo_sepolia_task_market_report.json", result)
        _write_text(root / "celo_sepolia_task_market_report.md", md)

    result["task"]["task_id"] = int(task_id)
    result["task"]["task_metadata"] = task_metadata
    result["task"]["query"] = task_query
    result["task"]["worker_metadata"] = worker_metadata
    result["task"]["escrow_wei"] = escrow_wei
    result["task"]["result_metadata"] = result_metadata
    result["task"]["validator_score"] = score
    result["task"]["min_validators"] = min_validators
    result["task"]["min_average_score"] = min_average_score
    result["task"]["deadline_at"] = deadline_at

    # Keep the markdown consistent by writing JSON at end too.
    # No-op: already written above.

    return result


if __name__ == "__main__":
    print(json.dumps(run_task_market_demo(), indent=2))

