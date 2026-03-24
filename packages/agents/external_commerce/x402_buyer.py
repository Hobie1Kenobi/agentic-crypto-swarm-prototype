"""
x402 buyer — HTTP 402 flow via official x402 client (handles v1/v2).
"""
from __future__ import annotations

import os
from typing import Any

import requests


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


def _get_pk(env_keys: list[str]) -> str:
    for k in env_keys:
        v = os.getenv(k, "").strip()
        if v and "0x" in v:
            return v
    return ""


class X402Buyer:
    def __init__(
        self,
        facilitator_url: str | None = None,
        network: str | None = None,
        private_key_env: str | None = None,
        dry_run: bool = False,
    ):
        self.facilitator_url = facilitator_url or _env("X402_TEST_FACILITATOR_URL", "https://x402.org/facilitator")
        self.network = network or _env("X402_ALLOWED_NETWORKS", "eip155:84532").split(",")[0].strip()
        self.private_key_env = private_key_env or "X402_BUYER_BASE_SEPOLIA_PRIVATE_KEY"
        self._key_envs = [
            self.private_key_env,
            "X402_BUYER_PRIVATE_KEY",
            "ROOT_STRATEGIST_PRIVATE_KEY",
        ]
        self.dry_run = dry_run or _truthy(_env("X402_DRY_RUN"))
        self._session: requests.Session | None = None
        self._plain_session = requests.Session()

    def _get_session(self) -> requests.Session:
        if self.dry_run:
            return self._plain_session
        pk = _get_pk(self._key_envs)
        if not pk:
            return self._plain_session
        try:
            from eth_account import Account
            from x402 import x402ClientSync
            from x402.http.clients import x402_requests
            from x402.mechanisms.evm import EthAccountSigner
            from x402.mechanisms.evm.exact.register import register_exact_evm_client

            account = Account.from_key(pk)
            client = x402ClientSync()
            register_exact_evm_client(client, EthAccountSigner(account))
            return x402_requests(client)
        except ImportError:
            return self._plain_session
        except Exception:
            return self._plain_session

    def invoke(
        self,
        resource_url: str,
        method: str = "GET",
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: float = 30,
    ) -> tuple[int, dict[str, Any] | None, str | None]:
        """
        Call external x402 resource. Uses x402_requests for automatic 402 handling.
        Returns (status_code, response_json, error).
        """
        try:
            session = self._get_session()
            if method.upper() == "GET":
                r = session.get(resource_url, params=params or {}, timeout=timeout)
            else:
                r = session.post(resource_url, json=json_body or {}, timeout=timeout)
            ct = r.headers.get("content-type") or ""
            if "application/json" in ct:
                try:
                    data = r.json()
                except Exception:
                    data = {"raw": r.text[:500]}
            else:
                data = {"raw": r.text[:500]}
            if r.status_code == 402:
                pk = _get_pk(self._key_envs)
                if not pk or "0x" not in pk:
                    return 402, data, "payment_required_but_no_buyer_key"
                return 402, data, "payment_preparation_failed"
            if r.status_code != 200:
                return r.status_code, data, f"http_{r.status_code}"
            return r.status_code, data, None
        except requests.RequestException as e:
            return 0, None, str(e)
        except Exception as e:
            err = str(e)
            return 0, None, err
