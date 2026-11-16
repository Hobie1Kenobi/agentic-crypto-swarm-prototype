"""Unit tests for contract-triage source lookup and honest verdicts."""
from __future__ import annotations

import unittest
from unittest.mock import patch, Mock
import requests

from marketplace.skus import smart_contract_audit as sca

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_IMPL = "0x2Ce6311ddAE708829bc0784C967b7d77D19FD779"


class HttpHeaderTests(unittest.TestCase):
    def test_http_get_json_sends_user_agent(self):
        mock_resp = Mock()
        mock_resp.json.return_value = {"ok": True}
        mock_resp.raise_for_status = Mock()
        with patch.object(sca.requests, "get", return_value=mock_resp) as get:
            out = sca._http_get_json("https://base.blockscout.com/api/v2/smart-contracts/0xabc")
        self.assertEqual(out, {"ok": True})
        kwargs = get.call_args.kwargs
        ua = kwargs["headers"]["User-Agent"]
        self.assertTrue(ua)
        self.assertNotEqual(ua, "python-requests/2.x")
        self.assertIn("ASM-Triage", ua)


class VerdictLogicTests(unittest.TestCase):
    def test_lookup_failure_is_inconclusive_not_malicious(self):
        score, verdict = sca._verdict_from_signals(
            verified=False, lookup_failed=True, high=0, med=0,
            hot_flags=[], phase6_flags=[], brand=[],
        )
        self.assertEqual(verdict, "INCONCLUSIVE")
        self.assertEqual(score, 0)

    def test_unverified_without_evidence_is_inconclusive_not_malicious(self):
        score, verdict = sca._verdict_from_signals(
            verified=False, lookup_failed=False, high=0, med=0,
            hot_flags=[], phase6_flags=[], brand=["brand:reserve"],
        )
        self.assertEqual(verdict, "INCONCLUSIVE")
        self.assertNotEqual(verdict, "MALICIOUS")

    def test_legacy_risk_from_counts_unverified_is_inconclusive(self):
        score, verdict = sca._risk_from_counts(0, 0, ["brand:official"], False)
        self.assertEqual(verdict, "INCONCLUSIVE")
        self.assertEqual(score, 0)

    def test_slither_high_is_malicious(self):
        score, verdict = sca._verdict_from_signals(
            verified=True, lookup_failed=False, high=2, med=0,
            hot_flags=["slither:suicidal"], phase6_flags=[], brand=[],
        )
        self.assertEqual(verdict, "MALICIOUS")
        self.assertGreaterEqual(score, 70)

    def test_verified_clean_is_safe(self):
        score, verdict = sca._verdict_from_signals(
            verified=True, lookup_failed=False, high=0, med=0,
            hot_flags=[], phase6_flags=[], brand=["brand:reserve"],
        )
        self.assertEqual(verdict, "SAFE")
        self.assertEqual(score, 0)


class TriageContractTests(unittest.TestCase):
    def test_invalid_address_inconclusive(self):
        out = sca.triage_contract("not-an-address")
        self.assertEqual(out["verdict"], "INCONCLUSIVE")
        self.assertEqual(out["reason"], "invalid_address")
        self.assertFalse(out["verified"])

    def test_lookup_error_does_not_become_malicious(self):
        failed = {
            "verified": False,
            "source": "",
            "reason": "source_lookup_failed",
            "contract_name": "",
            "lookup_failed": True,
            "is_proxy": False,
            "implementation": "",
            "implementation_verified": False,
            "implementation_name": "",
            "proxy_type": None,
            "provider": "none",
            "lookup_errors": ["blockscout:HTTPError:403"],
        }
        with patch.object(sca, "resolve_contract_source", return_value=failed), \
             patch.object(sca, "_phase6_triage_intel", return_value=([], {})):
            out = sca.triage_contract(USDC)
        self.assertEqual(out["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(out["verdict"], "MALICIOUS")
        self.assertIn("source_lookup_failed", out["topFlags"])
        self.assertFalse(out["verified"])
        self.assertEqual(out["riskScore"], 0)

    def test_confirmed_unverified_is_inconclusive(self):
        unverified = {
            "verified": False,
            "source": "",
            "reason": "unverified",
            "contract_name": "",
            "lookup_failed": False,
            "is_proxy": False,
            "implementation": "",
            "implementation_verified": False,
            "implementation_name": "",
            "proxy_type": None,
            "provider": "sourcify",
            "lookup_errors": [],
        }
        with patch.object(sca, "resolve_contract_source", return_value=unverified), \
             patch.object(sca, "_phase6_triage_intel", return_value=([], {})):
            out = sca.triage_contract("0x1111111111111111111111111111111111111111")
        self.assertEqual(out["verdict"], "INCONCLUSIVE")
        self.assertIn("unverified_source", out["topFlags"])
        self.assertNotEqual(out["verdict"], "MALICIOUS")

    def test_verified_proxy_is_not_malicious(self):
        info = {
            "verified": True,
            "source": "// FiatTokenProxy\ncontract FiatTokenProxy {}",
            "reason": "ok",
            "contract_name": "FiatTokenProxy->FiatTokenV2_2",
            "lookup_failed": False,
            "is_proxy": True,
            "implementation": USDC_IMPL,
            "implementation_verified": True,
            "implementation_name": "FiatTokenV2_2",
            "proxy_type": "eip1967_oz",
            "provider": "blockscout_v2",
            "lookup_errors": [],
        }
        with patch.object(sca, "resolve_contract_source", return_value=info), \
             patch.object(sca, "_phase6_triage_intel", return_value=([], {})), \
             patch.object(sca, "_run_slither_json_on_source", return_value=None):
            out = sca.triage_contract(USDC)
        self.assertTrue(out["verified"])
        self.assertEqual(out["verdict"], "SAFE")
        self.assertNotEqual(out["verdict"], "MALICIOUS")
        self.assertTrue(out["isProxy"])
        self.assertEqual(out["implementation"].lower(), USDC_IMPL.lower())
        self.assertTrue(out["implementationVerified"])
        self.assertIn("proxy", out["topFlags"])


class CollectSourcesTests(unittest.TestCase):
    def test_falls_back_after_blockscout_403(self):
        def boom(*_a, **_k):
            err = requests.HTTPError("403 Client Error: Forbidden")
            err.response = Mock(status_code=403)
            raise err

        sourcify = {
            "provider": "sourcify",
            "verified": True,
            "source": "contract USDC {}",
            "contract_name": "FiatTokenProxy",
            "proxy_type": "eip1967_oz",
            "implementations": [USDC_IMPL],
            "reason": "ok",
        }
        with patch.object(sca, "_lookup_blockscout_v2", side_effect=boom), \
             patch.object(sca, "_lookup_blockscout_legacy", side_effect=boom), \
             patch.object(sca, "_lookup_sourcify", return_value=sourcify), \
             patch.object(sca, "_lookup_etherscan_v2", return_value=None):
            out = sca._collect_sources("eip155:8453", USDC)
        self.assertTrue(out["verified"])
        self.assertEqual(out["provider"], "sourcify")
        self.assertTrue(any("403" in e or "HTTPError" in e for e in out["lookup_errors"]))

    def test_all_providers_failing_is_lookup_failed(self):
        def boom(*_a, **_k):
            raise requests.HTTPError("403 Client Error: Forbidden")

        with patch.object(sca, "_lookup_blockscout_v2", side_effect=boom), \
             patch.object(sca, "_lookup_blockscout_legacy", side_effect=boom), \
             patch.object(sca, "_lookup_sourcify", side_effect=boom), \
             patch.object(sca, "_lookup_etherscan_v2", return_value=None):
            out = sca._collect_sources("eip155:8453", USDC)
        self.assertTrue(out["lookup_failed"])
        self.assertEqual(out["reason"], "source_lookup_failed")
        self.assertFalse(out["verified"])


class ProxyResolutionTests(unittest.TestCase):
    def test_resolve_uses_explorer_implementation_and_merges_source(self):
        proxy = {
            "provider": "blockscout_v2",
            "verified": True,
            "source": "contract FiatTokenProxy {}",
            "contract_name": "FiatTokenProxy",
            "proxy_type": "eip1967_oz",
            "implementations": [USDC_IMPL],
            "reason": "ok",
            "lookup_errors": [],
        }
        impl = {
            "provider": "blockscout_v2",
            "verified": True,
            "source": "contract FiatTokenV2_2 {}",
            "contract_name": "FiatTokenV2_2",
            "proxy_type": None,
            "implementations": [],
            "reason": "ok",
            "lookup_errors": [],
        }

        def collect(chain, address):
            if address.lower() == USDC.lower():
                return dict(proxy)
            if address.lower() == USDC_IMPL.lower():
                return dict(impl)
            return {"verified": False, "source": "", "reason": "unverified", "contract_name": "",
                    "proxy_type": None, "implementations": [], "lookup_errors": []}

        with patch.object(sca, "_collect_sources", side_effect=collect), \
             patch.object(sca, "_implementation_from_rpc", return_value=""):
            out = sca.resolve_contract_source("eip155:8453", USDC)
        self.assertTrue(out["verified"])
        self.assertTrue(out["is_proxy"])
        self.assertEqual(out["implementation"].lower(), USDC_IMPL.lower())
        self.assertTrue(out["implementation_verified"])
        self.assertIn("FiatTokenV2_2", out["source"])
        self.assertIn("FiatTokenProxy", out["contract_name"])

    def test_storage_slot_helper_extracts_address(self):
        slot = "0x0000000000000000000000002ce6311ddae708829bc0784c967b7d77d19fd779"
        self.assertEqual(sca._addr_from_storage(slot).lower(), USDC_IMPL.lower())


if __name__ == "__main__":
    unittest.main()
