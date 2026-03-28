from __future__ import annotations

import os
from typing import Any

from web3 import Web3

from .models import ClaimStatus
from .routing import (
    ChainRoute,
    contract_allowed,
    execution_enabled,
    load_routing,
    resolve_rpc_url,
)
from .store import ClaimQueueStore
from services.agent_executor import get_default_executor


def _checksum(addr: str) -> str:
    return Web3.to_checksum_address(addr)


def _verify_expected_signer(route: ChainRoute, executor: Any, role: str) -> None:
    env_name = route.expected_signer_env
    if not env_name:
        return
    expected = os.getenv(env_name, "").strip()
    if not expected:
        raise ValueError(f"Route requires {env_name} to match signer (set to your claim wallet address)")
    got = executor.get_sender_address(role)
    if _checksum(expected).lower() != _checksum(got).lower():
        raise ValueError(f"{env_name}={expected} does not match signer for role {role}: {got}")


def execute_claim(
    claim_id: str,
    *,
    store: ClaimQueueStore | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not dry_run and not execution_enabled():
        raise RuntimeError(
            "Execution disabled. Set AIRDROP_CLAIM_EXECUTION_ENABLED=1 after reviewing routing and allowlists."
        )

    st = store or ClaimQueueStore()
    row = st.get(claim_id)
    if not row:
        raise KeyError(f"Unknown claim id {claim_id}")
    if row.status != ClaimStatus.approved:
        raise RuntimeError(f"Claim {claim_id} is not approved (status={row.status.value})")

    spec = row.spec
    routing = load_routing()
    route = routing.route_for_chain(spec.chain_id)
    if route is None:
        raise RuntimeError(f"No routing entry for chain_id={spec.chain_id} in airdrop_claim_routing.json")

    rpc = resolve_rpc_url(route)
    if not rpc:
        raise RuntimeError(f"No RPC URL resolved for chain {spec.chain_id}; check rpc_env_vars on route")

    if not contract_allowed(route, spec.to):
        raise RuntimeError(
            f"Contract {spec.to} not in allowed_contracts for chain {spec.chain_id}. "
            "Add it to routing or set AIRDROP_CLAIM_ALLOW_UNLISTED=1 (dangerous)."
        )

    if spec.value_wei > int(route.max_value_wei):
        raise RuntimeError(f"value_wei {spec.value_wei} exceeds route max_value_wei {route.max_value_wei}")

    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        raise RuntimeError(f"RPC not connected: {rpc[:48]}...")

    role = spec.signer_role or route.signer_role
    executor = get_default_executor(w3, spec.chain_id)
    _verify_expected_signer(route, executor, role)

    to_addr = _checksum(spec.to)
    data = spec.data
    value = int(spec.value_wei)

    tx: dict[str, Any] = {
        "from": executor.get_sender_address(role),
        "to": to_addr,
        "value": value,
        "chainId": spec.chain_id,
        "data": data,
    }
    gas_limit = spec.gas_limit or route.max_gas
    est = w3.eth.estimate_gas(tx)
    if est > gas_limit:
        raise RuntimeError(f"Estimated gas {est} exceeds cap {gas_limit} (spec or route max_gas)")
    gas = min(est, gas_limit)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "chain_id": spec.chain_id,
            "from": tx["from"],
            "to": to_addr,
            "gas": gas,
            "value_wei": value,
        }

    st.update_status(claim_id, ClaimStatus.executing)
    try:
        sender = _checksum(tx["from"])
        try:
            nonce = w3.eth.get_transaction_count(sender, block_identifier="pending")
        except Exception:
            nonce = w3.eth.get_transaction_count(sender)
        tx_hash = executor.send_transaction(
            role,
            to=to_addr,
            value=value,
            data=data,
            gas=gas,
            nonce=nonce,
            chain_id=spec.chain_id,
        )
        st.update_status(claim_id, ClaimStatus.completed, tx_hash=tx_hash)
        explorer = ""
        exu = getattr(route, "explorer_url", None) or ""
        if exu:
            explorer = f"{exu.rstrip('/')}/tx/{tx_hash}"
        return {
            "ok": True,
            "dry_run": False,
            "tx_hash": tx_hash,
            "explorer_hint": explorer or None,
            "chain_id": spec.chain_id,
        }
    except Exception as e:
        err = str(e)
        st.update_status(claim_id, ClaimStatus.failed, error=err)
        raise
