import os
from pathlib import Path
import json

_ROOT = Path(__file__).resolve().parents[3]
for _ in range(5):
    if (_ROOT / "foundry.toml").exists() or (_ROOT / ".env.example").exists():
        break
    _ROOT = _ROOT.parent

_CHAINS_PATH = _ROOT / "config" / "chains.json"
_CHAINS_DATA = None


def _load_chains():
    global _CHAINS_DATA
    if _CHAINS_DATA is not None:
        return _CHAINS_DATA
    if _CHAINS_PATH.exists():
        _CHAINS_DATA = json.loads(_CHAINS_PATH.read_text(encoding="utf-8"))
    else:
        _CHAINS_DATA = {"chains": {}, "defaultChain": "celo-sepolia", "defaultLocalChain": "anvil"}
    return _CHAINS_DATA


def _chain_by_id(chain_id: int):
    data = _load_chains()
    for key, c in data.get("chains", {}).items():
        if c.get("chainId") == chain_id:
            return key, c
    return None, None


def get_chain_config():
    data = _load_chains()
    chain_name = os.getenv("CHAIN_NAME", "").strip().lower().replace(" ", "-") or None
    chain_id_str = os.getenv("CHAIN_ID", "").strip()
    if chain_id_str and chain_id_str.isdigit():
        chain_id = int(chain_id_str)
        if chain_name and chain_name in data.get("chains", {}):
            return data["chains"][chain_name]
        key, cfg = _chain_by_id(chain_id)
        if cfg:
            return cfg
        return {"chainId": chain_id, "name": f"Chain {chain_id}", "rpcUrl": "", "explorerUrl": "", "nativeSymbol": "ETH", "rpcEnvVars": ["RPC_URL"]}
    if chain_name and chain_name in data.get("chains", {}):
        return data["chains"][chain_name]
    default = data.get("defaultChain", "celo-sepolia")
    return data.get("chains", {}).get(default, {})


def get_chain_id() -> int:
    cfg = get_chain_config()
    return int(cfg.get("chainId", 11142220))


def get_rpc() -> str:
    rpc = os.getenv("RPC_URL", "").strip()
    if rpc and "your_" not in rpc:
        return rpc
    cfg = get_chain_config()
    for env_key in cfg.get("rpcEnvVars", ["RPC_URL"]):
        val = os.getenv(env_key, "").strip()
        if env_key == "ALCHEMY_API_KEY" and val and "your_" not in val:
            tpl = cfg.get("alchemyTemplate")
            if tpl:
                return tpl.format(key=val)
        if val and "your_" not in val and env_key != "ALCHEMY_API_KEY":
            return val
    return cfg.get("rpcUrl", "https://rpc.ankr.com/celo_sepolia")


def get_explorer_url() -> str:
    return get_chain_config().get("explorerUrl", "https://celo-sepolia.blockscout.com")


def get_native_symbol() -> str:
    return get_chain_config().get("nativeSymbol", "CELO")
