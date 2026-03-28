from __future__ import annotations

from web3 import Web3


def function_selector(signature: str) -> bytes:
    return bytes(Web3.keccak(text=signature)[:4])


def encode_claim_oz_merkle(
    index: int,
    account: str,
    amount: int,
    merkle_proof: list[str],
) -> str:
    """
    OpenZeppelin-style Merkle distributor: claim(uint256 index, address account, uint256 amount, bytes32[] proof).
    """
    from eth_abi import encode

    acct = Web3.to_checksum_address(account)
    proof_bytes: list[bytes] = []
    for p in merkle_proof:
        h = p.strip()
        if h.startswith("0x"):
            h = h[2:]
        proof_bytes.append(bytes.fromhex(h))
    body = encode(["uint256", "address", "uint256", "bytes32[]"], [index, acct, amount, proof_bytes])
    sel = function_selector("claim(uint256,address,uint256,bytes32[])")
    return "0x" + sel.hex() + body.hex()


def encode_claim_uint256(amount: int) -> str:
    """claim(uint256) — matches MockClaimDistributor.sol and similar simple distributors."""
    from eth_abi import encode

    body = encode(["uint256"], [amount])
    sel = function_selector("claim(uint256)")
    return "0x" + sel.hex() + body.hex()


def encode_claim_simple_merkle(
    amount: int,
    merkle_proof: list[str],
) -> str:
    """
    Alternate pattern: claim(uint256 amount, bytes32[] proof) — verify against your contract ABI before use.
    """
    from eth_abi import encode

    proof_bytes: list[bytes] = []
    for p in merkle_proof:
        h = p.strip()
        if h.startswith("0x"):
            h = h[2:]
        proof_bytes.append(bytes.fromhex(h))
    body = encode(["uint256", "bytes32[]"], [amount, proof_bytes])
    sel = function_selector("claim(uint256,bytes32[])")
    return "0x" + sel.hex() + body.hex()
