import json
from pathlib import Path

import pytest
from web3 import Web3

from airdrop_claim.models import ClaimSpec, ClaimStatus
from airdrop_claim.routing import ChainRoute, RoutingConfig, contract_allowed
from airdrop_claim.store import ClaimQueueStore


def test_claim_spec_hex():
    s = ClaimSpec(
        chain_id=11142220,
        to="0x1234567890123456789012345678901234567890",
        data="0x",
        value_wei=0,
    )
    assert s.chain_id == 11142220


def test_store_roundtrip(tmp_path: Path):
    db = tmp_path / "q.sqlite"
    st = ClaimQueueStore(db_path=db)
    spec = ClaimSpec(
        chain_id=11142220,
        to="0x1234567890123456789012345678901234567890",
        data="0x",
        label="t",
    )
    cid = st.add_pending(spec, meta={"k": 1})
    row = st.get(cid)
    assert row is not None
    assert row.status == ClaimStatus.pending_approval
    st.update_status(cid, ClaimStatus.approved, approved_by="tester")
    row2 = st.get(cid)
    assert row2 and row2.status == ClaimStatus.approved


def test_allowlist():
    r = ChainRoute(allowed_contracts=["0x1234567890123456789012345678901234567890"])
    assert contract_allowed(r, "0x1234567890123456789012345678901234567890")


def test_encode_claim_uint256():
    from airdrop_claim.calldata_builders import encode_claim_uint256

    h = encode_claim_uint256(42)
    assert h.startswith("0x379607f5")


def test_encode_merkle_oz():
    from airdrop_claim.calldata_builders import encode_claim_oz_merkle

    h = encode_claim_oz_merkle(
        0,
        "0x1234567890123456789012345678901234567890",
        10**18,
        ["0x" + "00" * 32],
    )
    assert h.startswith("0x")
    assert len(h) > 10


def test_merge_routing_allowlist(tmp_path: Path):
    from airdrop_claim.pipeline import merge_routing_allowlist

    base = tmp_path / "r.json"
    base.write_text(
        json.dumps(
            {
                "version": 1,
                "routes": {
                    "11142220": {
                        "rpc_env_vars": ["CELO_SEPOLIA_RPC_URL"],
                        "signer_role": "AIRDROP_CLAIMANT",
                        "expected_signer_env": "AIRDROP_CLAIM_WALLET_ADDRESS",
                        "explorer_url": "https://example.com",
                        "allowed_contracts": [],
                        "max_gas": 100000,
                        "max_value_wei": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    m = merge_routing_allowlist(base, 11142220, "0x1234567890123456789012345678901234567890")
    assert m["routes"]["11142220"]["allowed_contracts"] == [
        Web3.to_checksum_address("0x1234567890123456789012345678901234567890")
    ]


def test_routing_loads_example():
    root = Path(__file__).resolve().parents[3]
    p = root / "packages" / "agents" / "config" / "airdrop_claim_routing.json"
    if not p.is_file():
        pytest.skip("routing file missing")
    data = json.loads(p.read_text(encoding="utf-8"))
    routes = {k: ChainRoute.model_validate(v) for k, v in (data.get("routes") or {}).items()}
    cfg = RoutingConfig(version=1, routes=routes)
    assert cfg.route_for_chain(11142220) is not None
