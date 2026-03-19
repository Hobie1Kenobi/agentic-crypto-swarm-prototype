from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Literal


OlasChainConfig = Literal["gnosis", "base", "polygon", "optimism"]


@dataclass(frozen=True)
class OlasSendResult:
    ok: bool
    request_id: str | None
    tx_hash: str | None
    result: Any | None
    boundary: str
    error: str | None = None
    chain_config: str | None = None
    tool: str | None = None


def _olas_enabled() -> bool:
    return (os.getenv("OLAS_ENABLED", "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _chain_config() -> str:
    # Dual-chain model: default live Olas attempts should use Gnosis (not Base).
    return (os.getenv("OLAS_CHAIN_CONFIG", "") or "gnosis").strip().lower()


def _priority_mech() -> str:
    return (os.getenv("OLAS_PRIORITY_MECH_ADDRESS", "") or "").strip()


def _tool() -> str:
    return (os.getenv("OLAS_TOOL", "") or "openai-gpt-4o-2024-05-13").strip()


def _timeout_s() -> int:
    try:
        return int((os.getenv("OLAS_DELIVERY_TIMEOUT_SEC", "") or "180").strip())
    except Exception:
        return 180


def _private_key() -> str:
    return (os.getenv("OLAS_EOA_PRIVATE_KEY", "") or "").strip()

def _resolve_mechx_exe() -> str | None:
    # 1) Explicit env override
    p = (os.getenv("OLAS_MECHX_PATH", "") or "").strip()
    if p and Path(p).exists():
        return p
    # 2) Repo-local isolated venv created by `scripts/install-olas-mech-client.ps1`
    root = Path(__file__).resolve().parents[3]
    candidate = root / ".venv-olas" / "Scripts" / "mechx.exe"
    if candidate.exists():
        return str(candidate)
    # 3) Fallback to PATH
    return "mechx"


def send_olas_mech_request(prompt: str) -> OlasSendResult:
    """
    Best-effort live integration via `mech-client` (MarketplaceService).

    If deps/credentials are missing or chain config unsupported, we return a clear boundary + error.
    """
    if not _olas_enabled():
        return OlasSendResult(
            ok=False,
            request_id=None,
            tx_hash=None,
            result=None,
            boundary="mocked_external_replay",
            error="OLAS_ENABLED is not set (set OLAS_ENABLED=1 to attempt live).",
            chain_config=_chain_config(),
            tool=_tool(),
        )

    chain_cfg = _chain_config()
    if chain_cfg not in {"gnosis", "base", "polygon", "optimism"}:
        return OlasSendResult(
            ok=False,
            request_id=None,
            tx_hash=None,
            result=None,
            boundary="mocked_external_replay",
            error=f"Unsupported OLAS_CHAIN_CONFIG={chain_cfg}. mech-client supports: gnosis, base, polygon, optimism.",
            chain_config=chain_cfg,
            tool=_tool(),
        )

    pk = _private_key()
    if not pk or "your_" in pk:
        return OlasSendResult(
            ok=False,
            request_id=None,
            tx_hash=None,
            result=None,
            boundary="mocked_external_replay",
            error="Missing OLAS_EOA_PRIVATE_KEY (EOA used to pay/send on Olas chain).",
            chain_config=chain_cfg,
            tool=_tool(),
        )

    mech_addr = _priority_mech()
    if not mech_addr:
        return OlasSendResult(
            ok=False,
            request_id=None,
            tx_hash=None,
            result=None,
            boundary="mocked_external_replay",
            error="Missing OLAS_PRIORITY_MECH_ADDRESS (target Mech contract).",
            chain_config=chain_cfg,
            tool=_tool(),
        )

    tool = _tool()
    timeout = _timeout_s()

    try:
        # Programmatic mech-client usage pulls an older web3 via aea-ledger-ethereum, which conflicts with this repo.
        # So we integrate using the official CLI (`mechx`) and parse its output.
        #
        # mechx requires a private key text file (--key); create with restrictive permissions.
        fd, key_path = tempfile.mkstemp(suffix=".txt", text=True)
        try:
            os.write(fd, pk.encode("utf-8"))
            os.close(fd)
            fd = None
            try:
                os.chmod(key_path, 0o600)
            except (OSError, AttributeError):
                pass
            env = os.environ.copy()
            env["MECHX_PRIVATE_KEY_PATH"] = key_path
            env["MECHX_DELIVERY_TIMEOUT"] = str(timeout)

            mechx = _resolve_mechx_exe()
            if not mechx:
                return OlasSendResult(
                    ok=False,
                    request_id=None,
                    tx_hash=None,
                    result=None,
                    boundary="mocked_external_replay",
                    error="mechx executable not found. Run `scripts/install-olas-mech-client.ps1` to install in isolated venv.",
                    chain_config=chain_cfg,
                    tool=tool,
                )

            cmd = [
                mechx,
                "--client-mode",
                "request",
                "--prompts",
                prompt,
                "--priority-mech",
                mech_addr,
                "--tools",
                tool,
                "--chain-config",
                chain_cfg,
                "--key",
                key_path,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=max(60, timeout + 30))
            out = (proc.stdout or "") + "\n" + (proc.stderr or "")

            if proc.returncode != 0:
                return OlasSendResult(
                    ok=False,
                    request_id=None,
                    tx_hash=None,
                    result=None,
                    boundary="mocked_external_replay",
                    error=f"mechx failed (exit {proc.returncode}): {out.strip()[:800]}",
                    chain_config=chain_cfg,
                    tool=tool,
                )

            # Best-effort parse.
            tx_hash = None
            m = re.search(r"(0x[a-fA-F0-9]{64})", out)
            if m:
                tx_hash = m.group(1)

            # Request ID can be big int; capture first long digit sequence following 'Request' markers.
            req_id = None
            m2 = re.search(r"Request\\s*ID\\s*[:=]\\s*(\\d+)", out, flags=re.IGNORECASE)
            if m2:
                req_id = m2.group(1)

            result = None
            m3 = re.search(r"Result\\s*[:=]\\s*(.+)", out, flags=re.IGNORECASE)
            if m3:
                result = m3.group(1).strip()

            return OlasSendResult(
                ok=True,
                request_id=req_id,
                tx_hash=tx_hash,
                result=result,
                boundary="real_external_integration",
                chain_config=chain_cfg,
                tool=tool,
            )
        finally:
            try:
                os.unlink(key_path)
            except OSError:
                pass
    except Exception as e:
        return OlasSendResult(
            ok=False,
            request_id=None,
            tx_hash=None,
            result=None,
            boundary="mocked_external_replay",
            error=f"Live Olas mech-client call failed: {e}",
            chain_config=_chain_config(),
            tool=_tool(),
        )

