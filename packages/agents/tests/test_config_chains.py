import os
import json
import pytest
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
chains_path = repo_root / "config" / "chains.json"


def _reload_chains():
    import importlib
    import config.chains as chains_mod
    importlib.reload(chains_mod)
    return chains_mod


@pytest.fixture(autouse=True)
def clear_chains_cache(monkeypatch):
    import config.chains as chains_mod
    monkeypatch.setattr(chains_mod, "_CHAINS_DATA", None)


def test_get_chain_id_default(monkeypatch):
    monkeypatch.delenv("CHAIN_ID", raising=False)
    monkeypatch.delenv("CHAIN_NAME", raising=False)
    from config.chains import get_chain_id
    assert get_chain_id() == 11142220


def test_get_chain_id_from_env(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "42220")
    _reload_chains()
    from config.chains import get_chain_id
    assert get_chain_id() == 42220


def test_get_chain_id_anvil(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "31337")
    _reload_chains()
    from config.chains import get_chain_id
    assert get_chain_id() == 31337


def test_get_chain_config_by_name(monkeypatch):
    monkeypatch.setenv("CHAIN_NAME", "celo-sepolia")
    monkeypatch.delenv("CHAIN_ID", raising=False)
    _reload_chains()
    from config.chains import get_chain_config
    cfg = get_chain_config()
    assert cfg.get("chainId") == 11142220
    assert cfg.get("nativeSymbol") == "CELO"


def test_get_chain_config_by_id(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "11142220")
    monkeypatch.delenv("CHAIN_NAME", raising=False)
    _reload_chains()
    from config.chains import get_chain_config
    cfg = get_chain_config()
    assert cfg.get("chainId") == 11142220


def test_get_rpc_default(monkeypatch):
    monkeypatch.delenv("RPC_URL", raising=False)
    monkeypatch.delenv("CELO_SEPOLIA_RPC_URL", raising=False)
    monkeypatch.delenv("CHAIN_ID", raising=False)
    monkeypatch.delenv("CHAIN_NAME", raising=False)
    _reload_chains()
    from config.chains import get_rpc
    rpc = get_rpc()
    assert rpc.startswith("http")
    assert len(rpc) > 10


def test_get_rpc_from_env(monkeypatch):
    monkeypatch.setenv("RPC_URL", "https://custom.rpc.example")
    _reload_chains()
    from config.chains import get_rpc
    assert get_rpc() == "https://custom.rpc.example"


def test_get_rpc_ignores_placeholder(monkeypatch):
    monkeypatch.setenv("RPC_URL", "https://your_rpc_here")
    _reload_chains()
    from config.chains import get_rpc
    rpc = get_rpc()
    assert "your_rpc_here" not in rpc


def test_get_native_symbol_celo_sepolia(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "11142220")
    _reload_chains()
    from config.chains import get_native_symbol
    assert get_native_symbol() == "CELO"


def test_get_native_symbol_anvil(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "31337")
    _reload_chains()
    from config.chains import get_native_symbol
    assert get_native_symbol() == "ETH"


def test_get_explorer_url(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "11142220")
    _reload_chains()
    from config.chains import get_explorer_url
    url = get_explorer_url()
    assert "blockscout" in url or "explorer" in url
