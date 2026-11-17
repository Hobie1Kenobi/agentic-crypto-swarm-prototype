"""Unit tests for marketplace.proof_snapshot — no network."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketplace.proof_snapshot import (  # noqa: E402
    HOUSE_BASE,
    HOUSE_CELO,
    HOUSE_XRPL,
    OPERATOR_XRPL_IDENTITY,
    PAYTO_BASE,
    annotate_payments,
    attach_skus,
    build_amount_catalog,
    build_snapshot,
    classify_payer,
    classify_payment,
    merge_payments,
    per_sku,
    summarize,
    _parse_roundhouse_day_html,
    _roundhouse_settlement_days,
)

LUMI_XRPL = "rM8kmmnz5qPMg7V3r7SHYXgDGvm8PhzLvM"


class ClassifyTests(unittest.TestCase):
    def test_house_wallets(self):
        self.assertEqual(classify_payer("base", HOUSE_BASE), "house")
        self.assertEqual(classify_payer("base", HOUSE_BASE.lower()), "house")
        self.assertEqual(classify_payer("celo", HOUSE_CELO), "house")
        self.assertEqual(classify_payer("xrpl", HOUSE_XRPL), "house")

    def test_operator_identity_not_external(self):
        self.assertEqual(classify_payer("xrpl", OPERATOR_XRPL_IDENTITY), "operator_identity")

    def test_external_and_unknown(self):
        self.assertEqual(classify_payer("base", "0x1111111111111111111111111111111111111111"), "external")
        self.assertEqual(classify_payer("xrpl", "rSomeOtherAccountXXXXXXXXXXXXXXXXX"), "external")
        self.assertEqual(classify_payer("base", None), "unknown")
        self.assertEqual(classify_payer("base", ""), "unknown")

    def test_house_not_confused_across_rails(self):
        self.assertEqual(classify_payer("xrpl", HOUSE_BASE), "external")
        self.assertEqual(classify_payer("base", HOUSE_XRPL), "external")


class CatalogAndSkuTests(unittest.TestCase):
    def test_unique_and_ambiguous_amounts(self):
        cat = build_amount_catalog(
            [
                {"sku_id": "hello", "price_drops": 1000},
                {"sku_id": "preflight", "price_drops": 4000},
                {"sku_id": "twin-a", "price_drops": 20000},
                {"sku_id": "twin-b", "price_drops": 20000},
            ],
            "xrpl",
        )
        self.assertEqual(cat["1000"], ["hello"])
        self.assertEqual(sorted(cat["20000"]), ["twin-a", "twin-b"])

        payments = [
            {"rail": "xrpl", "tx": "A", "amount_atomic": "1000"},
            {"rail": "xrpl", "tx": "B", "amount_atomic": "20000"},
            {"rail": "xrpl", "tx": "C", "amount_atomic": "99"},
        ]
        attach_skus(payments, {"xrpl": cat, "base": {}, "celo": {}})
        self.assertEqual(payments[0]["sku_id"], "hello")
        self.assertEqual(payments[0]["sku_id_source"], "unique_amount")
        self.assertIsNone(payments[1]["sku_id"])
        self.assertEqual(payments[1]["sku_id_source"], "ambiguous")
        self.assertIsNone(payments[2]["sku_id"])
        self.assertEqual(payments[2]["sku_id_source"], "unmapped")

    def test_usdc_price_strings(self):
        cat = build_amount_catalog(
            [{"sku_id": "agent-preflight-check", "price": "0.01 USDC"}],
            "base",
        )
        self.assertEqual(cat["10000"], ["agent-preflight-check"])

    def test_prior_sku_wins(self):
        cat = {"1000": ["hello"]}
        payments = [{"rail": "xrpl", "tx": "AA", "amount_atomic": "1000"}]
        attach_skus(payments, {"xrpl": cat, "base": {}, "celo": {}}, {("xrpl", "aa"): "custom-label"})
        self.assertEqual(payments[0]["sku_id"], "custom-label")
        self.assertEqual(payments[0]["sku_id_source"], "prior_snapshot")


class SummaryTests(unittest.TestCase):
    def test_house_not_blended_into_external(self):
        now = datetime(2026, 11, 16, 18, 0, tzinfo=timezone.utc)
        payments = [
            {"rail": "base", "tx": "1", "payer": HOUSE_BASE, "payer_class": "house",
             "time": "2026-11-16T17:00:00Z", "sku_id": "agent-preflight-check"},
            {"rail": "xrpl", "tx": "2", "payer": "rExternalBuyer1111111111111111111", "payer_class": "external",
             "time": "2026-11-16T16:00:00Z", "sku_id": "hello"},
            {"rail": "xrpl", "tx": "3", "payer": "rExternalBuyer1111111111111111111", "payer_class": "external",
             "time": "2026-10-01T16:00:00Z", "sku_id": "hello"},
            {"rail": "xrpl", "tx": "4", "payer": OPERATOR_XRPL_IDENTITY, "payer_class": "operator_identity",
             "time": "2026-11-10T16:00:00Z", "sku_id": "hello"},
        ]
        # Recompute classes as the builder would (after SKU mapping).
        payments = annotate_payments(payments)
        summary = summarize(payments, now=now)
        self.assertEqual(summary["external"]["payments"], 2)
        self.assertEqual(summary["external"]["unique_payers"], 1)
        self.assertEqual(summary["external"]["last_7d"], 1)
        self.assertEqual(summary["external"]["last_30d"], 1)
        self.assertEqual(summary["house"]["payments"], 1)
        self.assertEqual(summary["house"]["unique_payers"], 1)
        self.assertEqual(summary["operator_identity"]["payments"], 1)
        self.assertNotEqual(summary["external"]["payments"] + summary["house"]["payments"], summary["total_payments"])
        self.assertEqual(summary["total_payments"], 4)
        # External last-call is the recent external one, not the house payment.
        self.assertTrue(summary["external"]["last_call_at"].startswith("2026-11-16T16:00"))
        sku = per_sku(payments)
        hello = next(r for r in sku if r["sku_id"] == "hello")
        self.assertEqual(hello["external_calls"], 2)
        self.assertEqual(hello["house_calls"], 0)
        self.assertEqual(hello["operator_identity_calls"], 1)
        self.assertEqual(hello["unique_external_payers"], 1)

    def test_merge_prefers_payer_and_dedupes(self):
        a = [{"rail": "base", "tx": "0xAbC", "payer": None, "amount_atomic": "10000"}]
        b = [{"rail": "base", "tx": "0xabc", "payer": HOUSE_BASE, "sku_id": "agent-preflight-check"}]
        merged = merge_payments(a, b)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["payer"], HOUSE_BASE)
        self.assertEqual(merged[0]["sku_id"], "agent-preflight-check")
        self.assertEqual(merged[0]["amount_atomic"], "10000")



class ClassificationCleanupTests(unittest.TestCase):
    def test_lumi_probe_is_not_a_customer(self):
        self.assertEqual(classify_payer("xrpl", LUMI_XRPL), "automated_probe")
        self.assertEqual(
            classify_payment("xrpl", LUMI_XRPL, sku_id="hello", sku_id_source="unique_amount"),
            "automated_probe",
        )

    def test_dust_excluded_from_external(self):
        self.assertEqual(classify_payment("xrpl", "rDustPayer11111111111111111111111"), "dust")
        self.assertEqual(
            classify_payment("xrpl", "rDustPayer11111111111111111111111", sku_id=None, sku_id_source="unmapped"),
            "dust",
        )
        cat = build_amount_catalog(
            [{"sku_id": "hello", "price_drops": 1000}, {"sku_id": "preflight", "price_drops": 4000}],
            "xrpl",
        )
        payments = [
            {"rail": "xrpl", "tx": "d1", "payer": "rDustPayer11111111111111111111111", "amount_atomic": "1"},
            {"rail": "xrpl", "tx": "d10", "payer": "rDustPayer11111111111111111111111", "amount_atomic": "10"},
            {"rail": "xrpl", "tx": "hello1", "payer": LUMI_XRPL, "amount_atomic": "1000"},
            {"rail": "xrpl", "tx": "buy", "payer": "rCustomer111111111111111111111111", "amount_atomic": "4000"},
            {
                "rail": "base",
                "tx": "q1",
                "payer": "0xa1d1c0cf717402ff3651aa4873ccf96410b01978",
                "amount_atomic": "12000",
            },
            {"rail": "base", "tx": "hq", "payer": HOUSE_BASE, "amount_atomic": "12000"},
        ]
        attach_skus(
            payments,
            {
                "xrpl": cat,
                "base": build_amount_catalog([{"sku_id": "structured-query", "price": "0.012 USDC"}], "base"),
                "celo": {},
            },
        )
        payments = annotate_payments(payments)
        classes = {row["tx"]: row["payer_class"] for row in payments}
        self.assertEqual(classes["d1"], "dust")
        self.assertEqual(classes["d10"], "dust")
        self.assertEqual(classes["hello1"], "automated_probe")
        self.assertEqual(classes["buy"], "external")
        self.assertEqual(classes["q1"], "external")
        self.assertEqual(classes["hq"], "house")
        summary = summarize(payments, now=datetime(2026, 11, 16, tzinfo=timezone.utc))
        self.assertEqual(summary["external"]["payments"], 2)
        self.assertEqual(summary["external"]["unique_payers"], 2)
        self.assertEqual(summary["external"]["unique_payers_by_rail"]["xrpl"], 1)
        self.assertEqual(summary["external"]["unique_payers_by_rail"]["base"], 1)
        self.assertEqual(summary["external_sku_purchases"]["payments"], 2)
        self.assertEqual(summary["automated_probe"]["payments"], 1)
        self.assertEqual(summary["dust"]["payments"], 2)
        self.assertEqual(summary["house"]["payments"], 1)
        ext_payers = {row["payer"] for row in payments if row["payer_class"] == "external"}
        self.assertNotIn(LUMI_XRPL, ext_payers)
        self.assertNotIn("rDustPayer11111111111111111111111", ext_payers)

    def test_house_unmapped_stays_house(self):
        self.assertEqual(
            classify_payment("base", HOUSE_BASE, sku_id=None, sku_id_source="unmapped"),
            "house",
        )

    def test_roundhouse_calendar_and_row_parse(self):
        calendar = (
            '<button aria-label="No settlements on 2026-10-06"></button>'
            '<button aria-label="3 settlements · $0.11 on 2026-10-08"></button>'
            '<button aria-label="1 settlement · $0.01 on 2026-10-16"></button>'
        )
        self.assertEqual(_roundhouse_settlement_days(calendar), ["2026-10-08", "2026-10-16"])
        html = (
            "<tr>"
            '<td><a title="0x6a0b784cf4e3f79e0bca889e35a1b3aa1dc24518" '
            'href="/agents/0x6a0b784cf4e3f79e0bca889e35a1b3aa1dc24518">0x6a0b…4518</a>'
            '<span aria-label="0x6a0b784cf4e3f79e0bca889e35a1b3aa1dc24518 '
            'paid 0x408f39b19266022fec03076091e59d1f4f163658"></span></td>'
            '<td><span class="font-mono">$0.03</span></td>'
            '<td><span title="2026-10-08T05:39:41.000Z">39d ago</span></td>'
            '<td><a href="https://basescan.org/tx/'
            '0xded7acb70d8df72f4f0f400b4a13f5e1bdee993bce2d8fdd021abd0237163f67">tx</a></td>'
            "</tr>"
        )
        rows = _parse_roundhouse_day_html(html, "2026-10-08")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rail"], "base")
        self.assertEqual(rows[0]["tx"], "0xded7acb70d8df72f4f0f400b4a13f5e1bdee993bce2d8fdd021abd0237163f67")
        self.assertEqual(rows[0]["payer"].lower(), "0x6a0b784cf4e3f79e0bca889e35a1b3aa1dc24518")
        self.assertEqual(rows[0]["time"], "2026-10-08T05:39:41Z")
        self.assertEqual(rows[0]["amount_usd_display"], "0.03")
        self.assertEqual(rows[0]["source"], "base_roundhouse")


class SnapshotOfflineTests(unittest.TestCase):
    def test_offline_snapshot_keeps_classes_separate(self):
        settlements = {
            "receipts": [
                {
                    "rail": "base",
                    "sku_id": "structured-query",
                    "amount_atomic": 12000,
                    "tx": "0xaaa",
                    "payer": HOUSE_BASE,
                    "receiver": PAYTO_BASE,
                    "block": 1,
                    "time": "2026-08-17T21:00:00Z",
                },
                {
                    "rail": "base",
                    "sku_id": "structured-query",
                    "amount_atomic": 12000,
                    "tx": "0xbbb",
                    "payer": "0x2222222222222222222222222222222222222222",
                    "receiver": PAYTO_BASE,
                    "block": 2,
                    "time": "2026-08-18T21:00:00Z",
                },
            ]
        }
        snap = build_snapshot(
            repo_root=ROOT,
            live=False,
            settlements=settlements,
            include_health=False,
            include_preflight=False,
            now=datetime(2026, 8, 20, tzinfo=timezone.utc),
        )
        self.assertEqual(snap["schema"], "asm.proof.v1")
        self.assertEqual(snap["summary"]["house"]["payments"], 1)
        self.assertEqual(snap["summary"]["external"]["payments"], 1)
        self.assertEqual(snap["summary"]["external"]["unique_payers"], 1)
        self.assertIn("house_note", snap["honesty"])
        self.assertTrue(snap["honesty"]["house_note"].lower().startswith("house payments are self-funded"))
        # No private IPs or obvious secret keys in the payload.
        blob = str(snap).lower()
        self.assertNotIn("127.0.0.1", blob)
        self.assertNotIn("private_key", blob)
        self.assertNotIn("secret", blob)


if __name__ == "__main__":
    unittest.main()
