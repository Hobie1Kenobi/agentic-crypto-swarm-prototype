"""Airdrop scout: standalone report + model validation."""
from __future__ import annotations



def test_generate_airdrop_report_validates(monkeypatch):
    monkeypatch.setenv("LLM_DRY_RUN", "1")
    from airdrop_scout.report import generate_airdrop_report
    from t54_seller_models import AirdropIntelligenceReportResponse

    d = generate_airdrop_report("test topic", "ctx")
    m = AirdropIntelligenceReportResponse.model_validate(d)
    assert m.sku_id == "airdrop-intelligence-report"
    assert m.topic == "test topic"
    assert isinstance(m.opportunities, list)


def test_handler_matches_model(monkeypatch):
    monkeypatch.setenv("LLM_DRY_RUN", "1")
    from t54_seller_handlers import run_airdrop_intelligence_report

    r = run_airdrop_intelligence_report("hello", None)
    assert r.generated_at
    assert len(r.opportunities) >= 1
