#!/usr/bin/env python3
"""
On-demand bridge: Celo (or XRPL→Celo) → Base/Base Sepolia USDC via LI.FI.
Fund once on Celo, no manual Base funding. Same wallet = same address on both chains.
"""
from __future__ import annotations

import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if (root / ".env").exists():
    from dotenv import load_dotenv
    load_dotenv(root / ".env", override=True)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _get_pk() -> tuple[str, str]:
    for k in [
        "ROOT_STRATEGIST_PRIVATE_KEY",
        "CELO_PRIVATE_KEY",
        "X402_BUYER_BASE_SEPOLIA_PRIVATE_KEY",
        "X402_BUYER_PRIVATE_KEY",
    ]:
        v = _env(k)
        if v and "0x" in v:
            return v, k
    return "", ""


def _get_celo_rpc(is_testnet: bool) -> str:
    if is_testnet:
        return _env("CELO_SEPOLIA_RPC_URL") or _env("PRIVATE_RPC_URL") or _env("RPC_URL") or "https://rpc.ankr.com/celo_sepolia"
    return _env("CELO_MAINNET_RPC_URL") or _env("CELO_RPC_URL") or "https://rpc.ankr.com/celo"


def bridge_usdc_to_base(
    amount_usdc: float,
    is_testnet: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Bridge USDC from Celo to Base via LI.FI. Same wallet address on both chains.
    Returns {"ok": bool, "tx_hash": str|None, "error": str|None, ...}.
    """
    pk, _ = _get_pk()
    if not pk or "0x" not in pk:
        return {"ok": False, "error": "no_celo_key", "hint": "Set ROOT_STRATEGIST_PRIVATE_KEY or CELO_PRIVATE_KEY in .env"}

    try:
        from eth_account import Account
        account = Account.from_key(pk)
        from_address = account.address
    except Exception as e:
        return {"ok": False, "error": str(e), "hint": "Invalid private key"}

    from_chain = 11142220 if is_testnet else 42220
    to_chain = 84532 if is_testnet else 8453
    from_amount_raw = str(int(amount_usdc * 1_000_000))

    import requests
    params = {
        "fromChain": str(from_chain),
        "toChain": str(to_chain),
        "fromToken": "USDC",
        "toToken": "USDC",
        "fromAmount": from_amount_raw,
        "fromAddress": from_address,
        "slippage": 0.005,
        "skipSimulation": "true",
    }
    try:
        r = requests.get("https://li.quest/v1/quote", params=params, timeout=30)
    except requests.RequestException as e:
        return {"ok": False, "error": str(e), "hint": "LI.FI unreachable or route not supported for this chain pair"}

    if r.status_code != 200:
        try:
            err_body = r.json()
            msg = err_body.get("message", err_body.get("error", r.text[:200]))
        except Exception:
            msg = r.text[:200]
        return {
            "ok": False,
            "error": f"LI.FI {r.status_code}: {msg}",
            "hint": "Celo->Base Sepolia may not be supported; try mainnet (Celo->Base) or fund Base directly",
        }

    try:
        step = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    tx_req = step.get("transactionRequest")
    if not tx_req:
        return {"ok": False, "error": "no_transaction_request", "step": step}

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "from_chain": from_chain,
            "to_chain": to_chain,
            "amount_usdc": amount_usdc,
            "from_address": from_address,
        }

    celo_rpc = _get_celo_rpc(is_testnet)
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(celo_rpc))
        if not w3.is_connected():
            return {"ok": False, "error": "celo_rpc_not_connected", "hint": f"Set CELO_*_RPC_URL or RPC_URL"}
    except Exception as e:
        return {"ok": False, "error": str(e), "hint": "web3 not available"}

    chain_id = int(tx_req.get("chainId", from_chain))
    if chain_id != from_chain:
        return {"ok": False, "error": f"chain_mismatch:{chain_id}"}

    approval_addr = (step.get("estimate") or {}).get("approvalAddress")
    from_token_obj = (step.get("action") or {}).get("fromToken", {})
    from_token_addr = from_token_obj.get("address", "") if isinstance(from_token_obj, dict) else ""
    is_native = not from_token_addr or from_token_addr == "0x0000000000000000000000000000000000000000"
    if approval_addr and from_token_addr and not is_native:
        try:
            token = w3.eth.contract(address=Web3.to_checksum_address(from_token_addr), abi=ERC20_ABI)
            allowance = token.functions.allowance(Web3.to_checksum_address(from_address), Web3.to_checksum_address(approval_addr)).call()
            required = int(from_amount_raw)
            if allowance < required:
                max_approve = 2**256 - 1
                approve_tx = token.functions.approve(Web3.to_checksum_address(approval_addr), max_approve)
                nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(from_address), "pending")
                built = approve_tx.build_transaction({
                    "from": from_address,
                    "chainId": chain_id,
                    "gas": 100_000,
                    "nonce": nonce,
                })
                signed = account.sign_transaction(built)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt["status"] != 1:
                    return {"ok": False, "error": "approval_tx_failed", "tx_hash": tx_hash.hex()}
        except Exception as e:
            return {"ok": False, "error": f"approval:{e}"}

    def _hex_to_int(v):
        if v is None:
            return 300000
        return int(v, 16) if isinstance(v, str) else int(v)

    gas_val = _hex_to_int(tx_req.get("gas") or tx_req.get("gasLimit")) or 300000
    tx_dict = {
        "from": from_address,
        "to": Web3.to_checksum_address(tx_req["to"]),
        "data": tx_req.get("data", "0x"),
        "value": _hex_to_int(tx_req.get("value", "0x0")),
        "chainId": chain_id,
        "gas": gas_val,
    }
    if "maxFeePerGas" in tx_req:
        tx_dict["maxFeePerGas"] = int(tx_req["maxFeePerGas"], 16) if isinstance(tx_req["maxFeePerGas"], str) else tx_req["maxFeePerGas"]
    if "maxPriorityFeePerGas" in tx_req:
        tx_dict["maxPriorityFeePerGas"] = int(tx_req["maxPriorityFeePerGas"], 16) if isinstance(tx_req["maxPriorityFeePerGas"], str) else tx_req["maxPriorityFeePerGas"]

    try:
        signed = account.sign_transaction(tx_dict)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        return {
            "ok": receipt["status"] == 1,
            "tx_hash": tx_hash.hex(),
            "from_chain": from_chain,
            "to_chain": to_chain,
            "amount_usdc": amount_usdc,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


BASE_SEPOLIA_USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
BASE_MAINNET_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]


def _get_base_rpc(is_testnet: bool) -> str:
    if is_testnet:
        return _env("BASE_SEPOLIA_RPC_URL") or "https://sepolia.base.org"
    return _env("BASE_MAINNET_RPC_URL") or _env("BASE_RPC") or "https://mainnet.base.org"


def get_usdc_balance_base(w3, address: str, is_testnet: bool) -> float:
    try:
        from web3 import Web3
        usdc_addr = BASE_SEPOLIA_USDC if is_testnet else BASE_MAINNET_USDC
        token = w3.eth.contract(address=Web3.to_checksum_address(usdc_addr), abi=ERC20_ABI)
        raw = token.functions.balanceOf(Web3.to_checksum_address(address)).call()
        return raw / 1_000_000
    except Exception:
        return 0.0


def ensure_base_sepolia_test_usdc(min_usdc: float = 0.05) -> dict:
    """
    For testnet: check Base Sepolia USDC balance. If low, print faucet links.
    No bridge (LI.FI dropped testnet). Same address as Celo key on Base Sepolia.
    """
    if _env("X402_DRY_RUN").lower() in {"1", "true", "yes"}:
        return {"ok": True, "skipped": "dry_run"}
    pk, _ = _get_pk()
    if not pk or "0x" not in pk:
        return {"ok": False, "error": "no_celo_key"}
    try:
        from eth_account import Account
        from web3 import Web3
        account = Account.from_key(pk)
        address = account.address
        rpc = _get_base_rpc(True)
        w3 = Web3(Web3.HTTPProvider(rpc))
        if not w3.is_connected():
            return {"ok": False, "error": "base_rpc_not_connected", "address": address}
        balance = get_usdc_balance_base(w3, address, True)
        if balance >= min_usdc:
            return {"ok": True, "balance_usdc": balance, "address": address}
        print(f"\n  [Base Sepolia] Address {address} has {balance:.4f} USDC (need {min_usdc})")
        print("  Faucets: Circle https://faucet.circle.com | Coinbase CDP https://portal.cdp.coinbase.com/products/faucet")
        if _env("X402_AUTO_PAUSE", "0") == "1":
            try:
                input("  Press Enter after funding... ")
            except EOFError:
                pass
        return {"ok": False, "balance_usdc": balance, "needs_funding": True, "address": address}
    except ImportError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ensure_base_usdc_for_x402(
    is_testnet: bool,
    min_usdc: float = 0.05,
    bridge_amount: float | None = None,
) -> dict:
    """
    Ensure our wallet has enough USDC on Base for x402.
    Testnet: uses faucet path (ensure_base_sepolia_test_usdc); no bridge.
    Mainnet: checks Base balance first, bridges only shortfall via LI.FI.
    Skips if X402_BRIDGE_ENABLED=0 or X402_DRY_RUN=1.
    """
    if _env("X402_DRY_RUN").lower() in {"1", "true", "yes"}:
        return {"ok": True, "skipped": "dry_run"}
    if is_testnet:
        return ensure_base_sepolia_test_usdc(min_usdc=min_usdc)
    if _env("X402_BRIDGE_ENABLED", "1").lower() in {"0", "false", "no"}:
        return {"ok": True, "skipped": "bridge_disabled"}
    pk, _ = _get_pk()
    if pk and "0x" in pk:
        try:
            from eth_account import Account
            from web3 import Web3
            addr = Account.from_key(pk).address
            w3 = Web3(Web3.HTTPProvider(_get_base_rpc(False)))
            if w3.is_connected():
                bal = get_usdc_balance_base(w3, addr, False)
                if bal >= min_usdc:
                    return {"ok": True, "skipped": "sufficient_balance", "balance_usdc": bal}
                shortfall = min_usdc - bal
                amount = bridge_amount or max(shortfall, 0.15)
            else:
                amount = bridge_amount or max(min_usdc, 1.0)
        except Exception:
            amount = bridge_amount or max(min_usdc, 1.0)
    else:
        amount = bridge_amount or max(min_usdc, 1.0)
    return bridge_usdc_to_base(amount_usdc=amount, is_testnet=False, dry_run=False)


if __name__ == "__main__":
    import sys
    testnet = "--mainnet" not in sys.argv
    dry = "--dry-run" in sys.argv
    amt = 0.05 if testnet else 1.0
    for a in sys.argv[1:]:
        if a in ("--mainnet", "--dry-run"):
            continue
        try:
            amt = float(a)
            break
        except ValueError:
            pass
    res = bridge_usdc_to_base(amt, is_testnet=testnet, dry_run=dry)
    import json
    print(json.dumps(res, default=str))
