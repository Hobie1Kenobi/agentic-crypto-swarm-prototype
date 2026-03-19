from services.request_normalizer import normalize_olas_request


def test_normalize_olas_request_prompt_and_tool():
    task = normalize_olas_request({"prompt": "hi", "tool": "openai-gpt-4o", "request_id": "123", "chain_config": "base"})
    assert task.query == "hi"
    assert "public_adapter:olas:" in task.task_metadata
    assert task.external_request_id == "123"
    assert task.external_source == "olas"

