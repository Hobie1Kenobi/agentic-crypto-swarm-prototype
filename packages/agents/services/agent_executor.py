from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from web3 import Web3

AGENT_ENV_KEYS = {
    "ROOT_STRATEGIST": "ROOT_STRATEGIST_PRIVATE_KEY",
    "IP_GENERATOR": "IP_GENERATOR_PRIVATE_KEY",
    "DEPLOYER": "DEPLOYER_PRIVATE_KEY",
    "FINANCE_DISTRIBUTOR": "FINANCE_DISTRIBUTOR_PRIVATE_KEY",
    "TREASURY": "TREASURY_PRIVATE_KEY",
    "AIRDROP_CLAIMANT": "AIRDROP_CLAIMANT_PRIVATE_KEY",
}

AgentRole = str


class AgentExecutor(ABC):
    @abstractmethod
    def get_sender_address(self, role: AgentRole) -> str:
        pass

    @abstractmethod
    def send_transaction(
        self,
        role: AgentRole,
        to: str,
        value: int = 0,
        data: bytes | str = b"",
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        nonce: Optional[int] = None,
        chain_id: Optional[int] = None,
    ) -> str:
        pass


class SimpleSignerAgentExecutor(AgentExecutor):
    def __init__(self, w3: Web3, chain_id: int):
        self._w3 = w3
        self._chain_id = chain_id

    def _key_for_role(self, role: AgentRole) -> str:
        env_key = AGENT_ENV_KEYS.get(role) or f"{role}_PRIVATE_KEY"
        key = os.getenv(env_key)
        # Dual-chain "concept" keys: allow WORKER_PRIVATE_KEY / VALIDATOR_PRIVATE_KEY
        # to transparently feed the existing internal role names.
        if not key:
            if role == "IP_GENERATOR":
                key = os.getenv("WORKER_PRIVATE_KEY")
            elif role == "DEPLOYER":
                key = os.getenv("VALIDATOR_PRIVATE_KEY")
        key = key or os.getenv("PRIVATE_KEY")
        if not key or "your_" in key:
            raise ValueError(f"Missing key for {role}: set {env_key} or PRIVATE_KEY")
        return key

    def get_sender_address(self, role: AgentRole) -> str:
        from eth_account import Account
        key = self._key_for_role(role)
        return Account.from_key(key).address

    def send_transaction(
        self,
        role: AgentRole,
        to: str,
        value: int = 0,
        data: bytes | str = b"",
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        nonce: Optional[int] = None,
        chain_id: Optional[int] = None,
    ) -> str:
        from eth_account import Account
        key = self._key_for_role(role)
        acct = Account.from_key(key)
        to_checksum = Web3.to_checksum_address(to)
        tx: dict[str, Any] = {
            "from": acct.address,
            "to": to_checksum,
            "value": value,
            "chainId": chain_id if chain_id is not None else self._chain_id,
            "nonce": nonce if nonce is not None else self._w3.eth.get_transaction_count(acct.address),
        }
        if data:
            if isinstance(data, str) and data.startswith("0x"):
                tx["data"] = data
            elif isinstance(data, bytes):
                tx["data"] = "0x" + data.hex()
            else:
                tx["data"] = data if isinstance(data, str) else "0x"
        if gas is not None:
            tx["gas"] = gas
        if gas_price is not None:
            tx["gasPrice"] = gas_price
        if "gas" not in tx:
            tx["gas"] = self._w3.eth.estimate_gas(tx)
        # Ensure we always set a fee field for signer txs.
        # Without explicit `gasPrice`, some networks may reject/interpret the tx cost incorrectly.
        if "gasPrice" not in tx:
            tx["gasPrice"] = self._w3.eth.gas_price
        signed = acct.sign_transaction(tx)
        h = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return h.hex()


class AAAgentExecutor(AgentExecutor):
    def get_sender_address(self, role: AgentRole) -> str:
        raise NotImplementedError(
            "AA mode not configured. Set BUNDLER_RPC_URL (and optionally a Celo bundler) to use AAAgentExecutor."
        )

    def send_transaction(
        self,
        role: AgentRole,
        to: str,
        value: int = 0,
        data: bytes | str = b"",
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        nonce: Optional[int] = None,
        chain_id: Optional[int] = None,
    ) -> str:
        raise NotImplementedError(
            "AA mode not configured. Use SimpleSignerAgentExecutor or set BUNDLER_RPC_URL for ERC-4337."
        )


def get_default_executor(w3: Web3, chain_id: Optional[int] = None) -> AgentExecutor:
    if chain_id is None:
        from config.chains import get_chain_id
        chain_id = get_chain_id()
    return SimpleSignerAgentExecutor(w3, chain_id)
