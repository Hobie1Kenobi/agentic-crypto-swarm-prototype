from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.skus import preflight_check as pf


USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ASM_PAYTO = "0x408f39B19266022FeC03076091e59D1f4f163658"
RANDOM = "0x1111111111111111111111111111111111111111"
XRPL_ASM = "rHyLmYewCQABAx6MMRBBuYYUUYWve2E1Lf"


class ParseTests(unittest.TestCase):
    def test_requires_contract_or_payto(self):
        target, err = pf.parse_preflight_request({})
        self.assertIsNone(target)
        self.assertEqual(err["error"], "missing_or_invalid_target")

    def test_resource_alone_is_400(self):
        target, err = pf.parse_preflight_request({"resource": "https://example.com/x402"})
        self.assertIsNone(target)
        self.assertEqual(err["error"], "missing_or_invalid_target")

    def test_invalid_evm(self):
        _, err = pf.parse_preflight_request({"contractAddress": "0x123"})
        self.assertEqual(err["error"], "invalid_contractAddress")

    def test_xrpl_in_contract_field_is_rejected(self):
        _, err = pf.parse_preflight_request({"contractAddress": XRPL_ASM})
        self.assertEqual(err["error"], "invalid_contractAddress")

    def test_invalid_payto(self):
        _, err = pf.parse_preflight_request({"payTo": "not-an-address"})
        self.assertEqual(err["error"], "invalid_payTo")

    def test_unsupported_network(self):
        _, err = pf.parse_preflight_request({"contractAddress": USDC, "network": "eip155:1"})
        self.assertEqual(err["error"], "unsupported_network")

    def test_target_alias_and_aliases(self):
        target, err = pf.parse_preflight_request({"address": USDC, "seller": ASM_PAYTO})
        self.assertIsNone(err)
        self.assertEqual(target["contractAddress"], USDC)
        self.assertEqual(target["payTo"], ASM_PAYTO)
        self.assertIn("eip155:8453", target["networks"])

    def test_xrpl_payto(self):
        target, err = pf.parse_preflight_request({"payTo": XRPL_ASM, "network": "xrpl:0"})
        self.assertIsNone(err)
        self.assertEqual(target["payTo"], XRPL_ASM)
        self.assertEqual(target["networks"], ["xrpl:mainnet"])


class VerdictTests(unittest.TestCase):
    def test_lookup_failure_is_inconclusive_not_risky(self):
        reasons = [
            {"severity": "inconclusive", "reason": "fetch failed", "lookup_failed": True},
        ]
        verdict, score, texts, failed = pf._score_and_verdict(reasons)
        self.assertEqual(verdict, "INCONCLUSIVE")
        self.assertEqual(score, 0)
        self.assertTrue(failed)
        self.assertNotEqual(verdict, "RISKY")

    def test_positive_risk_is_risky(self):
        reasons = [
            {"severity": "risky", "reason": "GlobalFreeze set", "lookup_failed": False},
        ]
        verdict, score, _, failed = pf._score_and_verdict(reasons)
        self.assertEqual(verdict, "RISKY")
        self.assertGreaterEqual(score, 60)
        self.assertFalse(failed)

    def test_verified_safe_only(self):
        reasons = [{"severity": "safe", "reason": "verified USDC", "lookup_failed": False}]
        verdict, score, _, failed = pf._score_and_verdict(reasons)
        self.assertEqual(verdict, "SAFE")
        self.assertEqual(score, 0)
        self.assertFalse(failed)

    def test_safe_plus_lookup_failure_is_inconclusive(self):
        reasons = [
            {"severity": "safe", "reason": "verified", "lookup_failed": False},
            {"severity": "inconclusive", "reason": "toml failed", "lookup_failed": True},
        ]
        verdict, score, _, failed = pf._score_and_verdict(reasons)
        self.assertEqual(verdict, "INCONCLUSIVE")
        self.assertEqual(score, 0)
        self.assertTrue(failed)


def _safe_triage(addr, chain="eip155:8453"):
    return {
        "verdict": "SAFE",
        "riskScore": 0,
        "verified": True,
        "reason": "ok",
        "contractName": "FiatTokenProxy->FiatTokenV2_2",
        "isProxy": True,
        "implementation": "0x2Ce6311ddAE708829bc0784C967b7d77D19FD779",
        "sourceProvider": "blockscout_v2",
        "topFlags": ["proxy"],
        "slitherHighCount": 0,
        "lookupFailed": False,
    }


def _unverified_triage(addr, chain="eip155:8453"):
    return {
        "verdict": "INCONCLUSIVE",
        "riskScore": 0,
        "verified": False,
        "reason": "unverified",
        "contractName": "",
        "isProxy": False,
        "implementation": None,
        "sourceProvider": "sourcify",
        "topFlags": ["unverified_source"],
        "slitherHighCount": 0,
        "lookupFailed": False,
    }


def _failed_triage(addr, chain="eip155:8453"):
    return {
        "verdict": "INCONCLUSIVE",
        "riskScore": 0,
        "verified": False,
        "reason": "fetch_error:403",
        "sourceProvider": "blockscout_v2",
        "topFlags": [],
        "slitherHighCount": 0,
        "lookupFailed": True,
    }


class RunPreflightTests(unittest.TestCase):
    @patch.object(pf, "_triage", side_effect=_safe_triage)
    def test_usdc_is_safe(self, _tri):
        out = pf.run_preflight({"contractAddress": USDC})
        self.assertEqual(out["schema"], pf.SCHEMA_ID)
        self.assertEqual(out["verdict"], "SAFE")
        self.assertEqual(out["riskScore"], 0)
        self.assertFalse(out["lookupFailed"])
        self.assertEqual(out["target"]["contractAddress"], USDC)
        self.assertTrue(out["timestamp"].endswith("Z"))

    @patch.object(pf, "lookup_evm_address", return_value={"ok": True, "lookup_failed": False, "is_contract": False, "source": "blockscout_v2_address"})
    @patch.object(pf, "_triage", side_effect=_safe_triage)
    def test_usdc_and_known_payto_is_safe(self, _tri, _lookup):
        out = pf.run_preflight({"contractAddress": USDC, "payTo": ASM_PAYTO})
        self.assertEqual(out["verdict"], "SAFE")
        self.assertFalse(out["lookupFailed"])

    @patch.object(pf, "_triage", side_effect=_unverified_triage)
    def test_unverified_is_inconclusive(self, _tri):
        out = pf.run_preflight({"contractAddress": RANDOM})
        self.assertEqual(out["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(out["verdict"], "RISKY")
        self.assertEqual(out["riskScore"], 0)

    @patch.object(pf, "_triage", side_effect=_failed_triage)
    def test_triage_lookup_failure_is_inconclusive(self, _tri):
        out = pf.run_preflight({"contractAddress": USDC})
        self.assertEqual(out["verdict"], "INCONCLUSIVE")
        self.assertTrue(out["lookupFailed"])
        self.assertNotEqual(out["verdict"], "RISKY")

    @patch.object(pf, "lookup_xrpl_toml")
    @patch.object(pf, "lookup_xrpl_account")
    def test_xrpl_global_freeze_is_risky(self, acct, toml):
        acct.return_value = {
            "ok": True,
            "exists": True,
            "flags": ["lsfGlobalFreeze"],
            "domain": "",
            "sources": ["xrplcluster_account_info"],
            "lookup_failed": False,
        }
        toml.return_value = {"ok": False, "present": False}
        out = pf.run_preflight({"payTo": XRPL_ASM, "network": "xrpl:mainnet"})
        self.assertEqual(out["verdict"], "RISKY")
        self.assertGreaterEqual(out["riskScore"], 60)

    @patch.object(pf, "lookup_xrpl_toml")
    @patch.object(pf, "lookup_xrpl_account")
    def test_xrpl_toml_mismatch_is_risky(self, acct, toml):
        acct.return_value = {
            "ok": True,
            "exists": True,
            "flags": [],
            "domain": "evil.example",
            "sources": ["xrplcluster_account_info"],
            "lookup_failed": False,
        }
        toml.return_value = {
            "ok": True,
            "present": True,
            "listed": False,
            "source": "xrp_ledger_toml",
            "url": "https://evil.example/.well-known/xrp-ledger.toml",
        }
        out = pf.run_preflight({"payTo": XRPL_ASM})
        self.assertEqual(out["verdict"], "RISKY")

    @patch.object(pf, "lookup_xrpl_account")
    def test_xrpl_lookup_failure_is_inconclusive(self, acct):
        acct.return_value = {
            "ok": False,
            "lookup_failed": True,
            "reason": "ConnectTimeout",
            "sources": ["xrplcluster_account_info"],
        }
        out = pf.run_preflight({"payTo": XRPL_ASM})
        self.assertEqual(out["verdict"], "INCONCLUSIVE")
        self.assertTrue(out["lookupFailed"])
        self.assertNotEqual(out["verdict"], "RISKY")

    def test_http_resource_is_risky(self):
        with patch.object(pf, "_triage", side_effect=_safe_triage):
            out = pf.run_preflight({"contractAddress": USDC, "resource": "http://example.com/pay"})
        self.assertEqual(out["verdict"], "RISKY")


class HttpHeaderTests(unittest.TestCase):
    def test_user_agent_present(self):
        self.assertIn("ASM-Preflight", pf.HTTP_HEADERS["User-Agent"])


if __name__ == "__main__":
    unittest.main()
