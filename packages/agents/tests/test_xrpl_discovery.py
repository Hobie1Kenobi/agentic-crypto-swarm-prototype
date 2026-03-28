from xrpl_discovery.validate import is_valid_classic_address, validate_discovery_hit
from xrpl_discovery.xrpl_filter import is_xrpl_related_item, optional_keyword_hits


def test_valid_r_address():
    assert is_valid_classic_address("rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh")


def test_invalid_r_address():
    assert not is_valid_classic_address("0x1234567890123456789012345678901234567890")


def test_xrpl_item_network():
    item = {
        "resource": "https://example.com/x402",
        "accepts": [{"network": "xrpl:0", "asset": "XRP"}],
    }
    assert is_xrpl_related_item(item)


def test_xrpl_item_negative():
    item = {"resource": "https://example.com/evm", "accepts": [{"network": "eip155:1"}]}
    assert not is_xrpl_related_item(item)


def test_optional_keywords():
    blob = "hello xrp payment facilitator"
    assert optional_keyword_hits(blob, ["payment"]) == ["payment"]
    assert optional_keyword_hits(blob, []) == []


def test_validate_hit():
    assert validate_discovery_hit({"resource": "https://x"}) == []
    assert validate_discovery_hit({"resource": ""}) != []
