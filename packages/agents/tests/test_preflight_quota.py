from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# packages/agents/tests -> packages/agents on path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import preflight_quota as q  # noqa: E402


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"PREFLIGHT_QUOTA_DIR": self.tmp.name, "PREFLIGHT_FREE_DAILY_QUOTA": "5"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_five_then_denied(self):
        ip = "203.0.113.10"
        for i in range(5):
            row = q.try_consume(ip, day="2026-11-16", limit=5)
            self.assertTrue(row["allowed"], row)
            self.assertEqual(row["used"], i + 1)
            self.assertEqual(row["remaining"], 5 - (i + 1))
        denied = q.try_consume(ip, day="2026-11-16", limit=5)
        self.assertFalse(denied["allowed"])
        self.assertEqual(denied["used"], 5)
        self.assertEqual(denied["remaining"], 0)
        # A 6th consume must not increment
        again = q.try_consume(ip, day="2026-11-16", limit=5)
        self.assertEqual(again["used"], 5)

    def test_different_ips_have_separate_buckets(self):
        a = q.try_consume("203.0.113.10", day="2026-11-16", limit=5)
        b = q.try_consume("203.0.113.11", day="2026-11-16", limit=5)
        self.assertTrue(a["allowed"] and b["allowed"])
        self.assertNotEqual(a["bucket"], b["bucket"])
        self.assertEqual(b["used"], 1)

    def test_client_header_does_not_replace_ip(self):
        # extract_caller_ip ignores a spoofable client id; bucket is IP-only.
        headers = {"x-asm-client-id": "totally-new", "cf-connecting-ip": "198.51.100.9"}
        ip = q.extract_caller_ip(headers)
        self.assertEqual(ip, "198.51.100.9")
        other = q.extract_caller_ip({"cf-connecting-ip": "198.51.100.9", "x-asm-client-id": "other"})
        self.assertEqual(q.caller_bucket(ip), q.caller_bucket(other))

    def test_xff_uses_first_public_hop(self):
        ip = q.extract_caller_ip({"x-forwarded-for": "1.2.3.4, 10.0.0.1"})
        self.assertEqual(ip, "1.2.3.4")

    def test_cf_connecting_ip_wins(self):
        ip = q.extract_caller_ip({"cf-connecting-ip": "198.51.100.20", "x-forwarded-for": "1.1.1.1"})
        self.assertEqual(ip, "198.51.100.20")

    def test_inspect_does_not_consume(self):
        q.try_consume("203.0.113.50", day="2026-11-16", limit=5)
        mid = q.inspect("203.0.113.50", day="2026-11-16", limit=5)
        self.assertEqual(mid["used"], 1)
        mid2 = q.inspect("203.0.113.50", day="2026-11-16", limit=5)
        self.assertEqual(mid2["used"], 1)


if __name__ == "__main__":
    unittest.main()
