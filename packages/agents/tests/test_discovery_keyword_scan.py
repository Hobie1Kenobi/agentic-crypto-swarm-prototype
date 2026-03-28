from external_commerce.discovery_keyword_scan import item_search_blob, match_keywords


def test_match_keywords_basic():
    blob = "This is a testnet reward quest for participants."
    got = match_keywords(blob, ["testnet", "reward", "nope"])
    assert set(got) == {"testnet", "reward"}


def test_match_keywords_case_insensitive():
    assert match_keywords("AIRDROP", ["airdrop"]) == ["airdrop"]


def test_item_search_blob_flattens():
    item = {
        "resource": "https://example.com/api",
        "accepts": [{"payTo": "0xabc", "description": "claim bonus"}],
        "metadata": {"x": "merkle"},
    }
    b = item_search_blob(item)
    assert "https://example.com/api" in b
    assert "claim" in b
    assert "merkle" in b
