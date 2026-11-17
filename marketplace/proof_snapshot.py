"""Build an honest, public settlement-proof snapshot for ASM payTo addresses.

House payers (self-funded test / catalog-refresh) are never blended with external
payers. Operator identity accounts are a third class. No secrets are collected.
"""
from __future__ import annotations

import json
import re
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable

SCHEMA_ID = "asm.proof.v1"
SITE = "https://www.agentic-swarm-marketplace.com"
API = "https://api.agentic-swarm-marketplace.com"
PAGE = f"{SITE}/proof/"
USER_AGENT = "ASM-proof-snapshot/1.0 (+https://www.agentic-swarm-marketplace.com/proof/)"

USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PAYTO_BASE = "0x408f39B19266022FeC03076091e59D1f4f163658"
PAYTO_CELO_NATIVE = "0xF00Ebb2F7704E35593cE5Bf9349921C8567c5fE4"
PAYTO_XRPL = "rHyLmYewCQABAx6MMRBBuYYUUYWve2E1Lf"
USDC_CELO = "0xcebA9300f2b948710d2653Dd7B07f33A8B32118C"

HOUSE_BASE = "0xEBd956F5c8C4b32752d87D62314F9431Dc0449e9"
HOUSE_CELO = "0x3430C51aD9476029a03bE8Da64c09b8BC930eBa6"
HOUSE_XRPL = "r4n6M6QLWoFQVGXJ5PeESJjwUARVT91MYJ"
OPERATOR_XRPL_IDENTITY = "rHTHaQ9EtuKkSSAoh9R1ViGt69J2ZMHQWq"

# Known automated directory/probe payers. These are real settled external calls,
# but they must not be presented as customers.
PROBE_PAYERS = {
    "xrpl": {
        "rM8kmmnz5qPMg7V3r7SHYXgDGvm8PhzLvM": {
            "name": "Lumi",
            "note": "Automated directory/probe calls, including a daily 1000-drop payment for /t54/hello (0.001 XRP).",
        }
    }
}
ROUNDHOUSE_MERCHANT_URL = f"https://roundhouseai.io/merchant/{PAYTO_BASE}"
ROUNDHOUSE_TX_URL = "https://roundhouseai.io/transactions"

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
XRPL_EPOCH_OFFSET = 946684800
FIRST_BASE_BLOCK = 50_017_000

BASE_RPCS = [
    "https://base.publicnode.com",
    "https://1rpc.io/base",
    "https://mainnet.base.org",
    "https://base.drpc.org",
]

HEALTH_TARGETS = [
    {"id": "base_seller", "url": f"{API}/health"},
    {"id": "base_well_known", "url": f"{API}/.well-known/x402.json"},
    {"id": "t54_seller", "url": f"{API}/t54/health"},
    {"id": "t54_well_known", "url": f"{API}/t54/.well-known/x402.json"},
    {"id": "celo_seller", "url": f"{API}/celo/health"},
    {"id": "mcp_origin", "url": f"{API}/mcp"},
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def norm_evm(addr: str | None) -> str:
    return (addr or "").strip().lower()


def is_house(rail: str, payer: str | None) -> bool:
    if not payer:
        return False
    if rail.startswith("base") and norm_evm(payer) == norm_evm(HOUSE_BASE):
        return True
    if rail.startswith("celo") and norm_evm(payer) == norm_evm(HOUSE_CELO):
        return True
    if rail == "xrpl" and payer == HOUSE_XRPL:
        return True
    return False


def is_operator_identity(rail: str, payer: str | None) -> bool:
    if not payer:
        return False
    if rail == "xrpl" and payer == OPERATOR_XRPL_IDENTITY:
        return True
    return False


def is_probe(rail: str, payer: str | None) -> bool:
    if not payer:
        return False
    family = "base" if rail.startswith("base") else "celo" if rail.startswith("celo") else rail
    table = PROBE_PAYERS.get(family) or {}
    if family in ("base", "celo"):
        return norm_evm(payer) in {norm_evm(k) for k in table}
    return payer in table


def probe_meta(rail: str, payer: str | None) -> dict[str, str] | None:
    if not is_probe(rail, payer):
        return None
    family = "base" if rail.startswith("base") else "celo" if rail.startswith("celo") else rail
    table = PROBE_PAYERS.get(family) or {}
    if family in ("base", "celo"):
        for key, meta in table.items():
            if norm_evm(key) == norm_evm(payer):
                return meta
        return None
    return table.get(payer or "")


def sku_is_priced(payment: dict[str, Any] | None, sku_id: str | None = None, sku_id_source: str | None = None) -> bool:
    """True when the payment matches a unique catalog SKU price."""
    if payment is not None:
        sku_id = payment.get("sku_id") if sku_id is None else sku_id
        sku_id_source = payment.get("sku_id_source") if sku_id_source is None else sku_id_source
    if not sku_id or sku_id == "unmapped":
        return False
    if sku_id_source in ("unmapped", "ambiguous"):
        return False
    return True


def classify_payer(rail: str, payer: str | None) -> str:
    """Wallet-only class: house | operator_identity | probe | external | unknown.

    Dust vs SKU-priced external is decided later by classify_payment once the
    amount has been mapped to a catalog price.
    """
    if not payer:
        return "unknown"
    if is_house(rail, payer):
        return "house"
    if is_operator_identity(rail, payer):
        return "operator_identity"
    if is_probe(rail, payer):
        return "automated_probe"
    return "external"


def classify_payment(rail: str, payer: str | None, sku_id: str | None = None, sku_id_source: str | None = None) -> str:
    """Final class used on the page and in headline counts.

    House and operator identity stay in their buckets even when the amount is
    unlabeled. Remaining payments that do not match a real SKU price are dust.
    Known automated directory/probe payers that *do* match a SKU price are
    labeled automated_probe, not customers. Headline external is SKU-priced
    external purchases only.
    """
    base = classify_payer(rail, payer)
    if base in ("house", "operator_identity", "unknown"):
        return base
    if not sku_is_priced(None, sku_id, sku_id_source):
        return "dust"
    if base == "automated_probe":
        return "automated_probe"
    return "external"


def explorer_tx(rail: str, tx: str) -> str:
    if rail.startswith("base"):
        return f"https://basescan.org/tx/{tx}"
    if rail.startswith("celo"):
        return f"https://celoscan.io/tx/{tx}"
    if rail == "xrpl":
        return f"https://xrpscan.com/tx/{tx}"
    return ""


def http_json(url: str, data: bytes | None = None, timeout: int = 30, headers: dict[str, str] | None = None) -> tuple[int | None, Any]:
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs)
    if data is not None and "Content-Type" not in {k.title(): v for k, v in hdrs.items()}:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return resp.status, None
            try:
                return resp.status, json.loads(raw.decode("utf-8", "replace"))
            except json.JSONDecodeError:
                return resp.status, raw.decode("utf-8", "replace")[:300]
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            body = ""
        return exc.code, body
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def http_text(url: str, timeout: int = 40) -> tuple[int | None, str | None, str | None]:
    """GET a public HTML page. Returns (status, text, error)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.status, raw.decode(charset, errors="replace"), None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, body or None, f"HTTP {exc.code}"
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def http_status(url: str, timeout: int = 15) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Drain a small amount only — never keep bodies that might include secrets.
            resp.read(2048)
            return {
                "url": url,
                "http_status": resp.status,
                "ok": 200 <= resp.status < 400,
                "latency_ms": int((time.time() - started) * 1000),
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "http_status": exc.code,
            "ok": (200 <= exc.code < 400) or exc.code in (405, 406),
            "latency_ms": int((time.time() - started) * 1000),
        }
    except Exception as exc:
        return {
            "url": url,
            "http_status": None,
            "ok": False,
            "error": type(exc).__name__,
            "latency_ms": int((time.time() - started) * 1000),
        }


def payment_key(p: dict[str, Any]) -> tuple[str, str]:
    return (str(p.get("rail") or ""), str(p.get("tx") or "").lower())


def map_sku(amount_atomic: str | int | None, catalog: dict[str, list[str]], prior: dict[str, str] | None = None, tx_key: tuple[str, str] | None = None) -> tuple[str | None, str]:
    """Map a unique catalog amount to a sku_id. Ambiguous or unknown amounts are unlabeled."""
    if prior and tx_key and tx_key in prior and prior[tx_key]:
        return prior[tx_key], "prior_snapshot"
    if amount_atomic is None or amount_atomic == "":
        return None, "unmapped"
    key = str(int(str(amount_atomic).strip()))
    matches = catalog.get(key) or []
    if len(matches) == 1:
        return matches[0], "unique_amount"
    if len(matches) > 1:
        return None, "ambiguous"
    return None, "unmapped"


def build_amount_catalog(resources: Iterable[dict[str, Any]], rail: str) -> dict[str, list[str]]:
    """amount_atomic string -> [sku_id, ...]."""
    out: dict[str, list[str]] = defaultdict(list)
    for res in resources:
        sku = res.get("sku_id") or res.get("id")
        if not sku:
            continue
        atomic = None
        if rail == "xrpl":
            if res.get("price_drops") is not None:
                atomic = str(int(res["price_drops"]))
            elif res.get("price") is not None and str(res.get("asset") or "").upper() in ("", "XRP"):
                # price like "4000" drops or "0.004 XRP" — only accept integer drops.
                raw = str(res.get("price")).split()[0]
                if raw.isdigit():
                    atomic = raw
        else:
            # USDC 6 decimals. Accept "0.01 USDC" or integer atomic already.
            if res.get("amount_atomic") is not None:
                atomic = str(int(res["amount_atomic"]))
            else:
                price = str(res.get("price") or "")
                # "0.01 USDC" / "$0.01" / "0.01"
                num = None
                for token in price.replace("$", "").replace(",", "").split():
                    try:
                        num = float(token)
                        break
                    except ValueError:
                        continue
                if num is not None:
                    atomic = str(int(round(num * 1_000_000)))
        if atomic is None:
            continue
        if sku not in out[atomic]:
            out[atomic].append(sku)
    return dict(out)


def summarize(payments: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    cut7 = now - timedelta(days=7)
    cut30 = now - timedelta(days=30)
    buckets = {"external": [], "house": [], "operator_identity": [], "automated_probe": [], "dust": [], "unknown": []}
    for p in payments:
        buckets.setdefault(p.get("payer_class") or "unknown", []).append(p)

    def _stats(rows: list[dict[str, Any]], track_unique: bool) -> dict[str, Any]:
        times = [parse_iso(r.get("time")) for r in rows]
        times_ok = [t for t in times if t is not None]
        last = max(times_ok) if times_ok else None
        by_rail: dict[str, int] = defaultdict(int)
        unique: set[str] = set()
        last7 = last30 = 0
        for r, t in zip(rows, times):
            rail = r.get("rail") or "unknown"
            by_rail[rail] += 1
            if track_unique and r.get("payer"):
                unique.add(str(r["payer"]).lower() if str(r["payer"]).startswith("0x") else str(r["payer"]))
            if t is not None and t >= cut7:
                last7 += 1
            if t is not None and t >= cut30:
                last30 += 1
        out = {
            "payments": len(rows),
            "last_7d": last7,
            "last_30d": last30,
            "last_call_at": iso(last),
            "by_rail": dict(by_rail),
        }
        if track_unique:
            out["unique_payers"] = len(unique)
            by_rail_unique: dict[str, set[str]] = defaultdict(set)
            for r in rows:
                if r.get("payer"):
                    ident = str(r["payer"]).lower() if str(r["payer"]).startswith("0x") else str(r["payer"])
                    by_rail_unique[r.get("rail") or "unknown"].add(ident)
            out["unique_payers_by_rail"] = {k: len(v) for k, v in by_rail_unique.items()}
        return out

    external = _stats(buckets["external"], True)
    return {
        "external": external,
        "external_sku_purchases": external,  # alias: headline count is SKU-priced external only
        "automated_probe": _stats(buckets.get("automated_probe") or [], True),
        "dust": _stats(buckets.get("dust") or [], True),
        "house": _stats(buckets["house"], True),
        "operator_identity": _stats(buckets.get("operator_identity") or [], True),
        "unknown": _stats(buckets.get("unknown") or [], False),
        "total_payments": len(payments),
    }


def per_sku(payments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    unlabeled = 0
    for p in payments:
        sku = p.get("sku_id") or "unmapped"
        rail = p.get("rail") or "unknown"
        if not p.get("sku_id"):
            unlabeled += 1
        groups[(rail, sku)].append(p)
    rows = []
    for (rail, sku), items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][1])):
        ext = [i for i in items if i.get("payer_class") == "external"]
        house = [i for i in items if i.get("payer_class") == "house"]
        op = [i for i in items if i.get("payer_class") == "operator_identity"]
        probes = [i for i in items if i.get("payer_class") == "automated_probe"]
        dust = [i for i in items if i.get("payer_class") == "dust"]
        ext_payers = {str(i.get("payer")) for i in ext if i.get("payer")}
        times = [parse_iso(i.get("time")) for i in items]
        times_ok = [t for t in times if t is not None]
        ext_times = [parse_iso(i.get("time")) for i in ext]
        ext_ok = [t for t in ext_times if t is not None]
        rows.append({
            "sku_id": sku,
            "rail": rail,
            "external_calls": len(ext),
            "house_calls": len(house),
            "operator_identity_calls": len(op),
            "automated_probe_calls": len(probes),
            "dust_calls": len(dust),
            "unique_external_payers": len(ext_payers),
            "last_external_at": iso(max(ext_ok) if ext_ok else None),
            "last_any_at": iso(max(times_ok) if times_ok else None),
        })
    return rows


def merge_payments(*groups: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for group in groups:
        for p in group:
            tx = (p.get("tx") or "").strip()
            rail = (p.get("rail") or "").strip()
            if not tx or not rail:
                continue
            key = (rail, tx.lower())
            if key not in merged:
                merged[key] = dict(p)
                continue
            # Prefer the record with a payer, sku, or more fields filled in.
            cur = merged[key]
            for field in ("payer", "sku_id", "time", "block", "resource", "amount_atomic", "sku_id_source"):
                if not cur.get(field) and p.get(field):
                    cur[field] = p[field]
            if p.get("payer_class") and (not cur.get("payer_class") or cur.get("payer_class") == "unknown"):
                cur["payer_class"] = p["payer_class"]
    rows = list(merged.values())
    rows.sort(key=lambda r: (r.get("time") or "", r.get("rail") or "", r.get("tx") or ""), reverse=True)
    return rows


def payments_from_settlements(data: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for r in data.get("receipts") or []:
        rail = r.get("rail") or "base"
        payer = r.get("payer") or None
        tx = r.get("tx") or ""
        if not tx:
            continue
        rec = {
            "rail": rail,
            "tx": tx,
            "explorer": r.get("explorer") or explorer_tx(rail, tx),
            "payer": payer,
            "payer_class": classify_payer(rail, payer),
            "receiver": r.get("receiver"),
            "asset": "USDC" if rail == "base" else r.get("asset"),
            "amount_atomic": r.get("amount_atomic"),
            "sku_id": r.get("sku_id"),
            "sku_id_source": "prior_snapshot" if r.get("sku_id") else "unmapped",
            "block": r.get("block"),
            "time": r.get("time") or r.get("timestamp"),
            "resource": r.get("resource"),
            "source": "prior_settlements_json",
        }
        out.append(rec)
    return out


def payments_from_prior_proof(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for p in data.get("payments") or []:
        if not p.get("tx"):
            continue
        q = dict(p)
        q["payer_class"] = classify_payer(q.get("rail") or "", q.get("payer"))
        q.setdefault("source", "prior_proof_json")
        rows.append(q)
    return rows


def _topic_address(addr: str) -> str:
    return "0x" + ("0" * 24) + addr[2:].lower()


def _decode_uint(data: str | None) -> str | None:
    if not data:
        return None
    hexdata = data[2:] if data.startswith("0x") else data
    if not hexdata:
        return None
    return str(int(hexdata, 16))


def _roundhouse_settlement_days(merchant_html: str) -> list[str]:
    """Parse calendar aria-labels like '6 settlements · $0.28 on 2026-06-02'."""
    days: list[str] = []
    for label in re.findall(r'aria-label="([^"]*)"', merchant_html):
        if re.search(r"no settlements on", label, re.I):
            continue
        m = re.search(r"(\d+)\s+settlements?.*?on\s+(\d{4}-\d{2}-\d{2})", label, re.I)
        if m and int(m.group(1)) > 0:
            days.append(m.group(2))
    return sorted(set(days))


def _parse_roundhouse_day_html(html: str, day: str) -> list[dict[str, Any]]:
    """Extract Base settlements from a Roundhouse day (or paginated day) table."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in re.finditer(
        r'href="(https://(basescan\.org|celoscan\.io|xrpscan\.com)/tx/([0-9a-zA-Z]+))"',
        html,
    ):
        host, tx = m.group(2), m.group(3)
        if host != "basescan.org":
            continue
        key = tx.lower()
        if not key.startswith("0x") or key in seen:
            continue
        start = html.rfind("<tr", 0, m.start())
        end = html.find("</tr>", m.end())
        row = html[start:end] if start >= 0 and end >= 0 else html[max(0, m.start() - 2500):m.end() + 200]
        paid = re.search(
            r'(?:aria-label|title)="(0x[a-fA-F0-9]{40})\s+paid\s+(0x[a-fA-F0-9]{40})"',
            row,
            re.I,
        )
        payer = paid.group(1) if paid else None
        receiver = paid.group(2) if paid else PAYTO_BASE
        if norm_evm(receiver) != norm_evm(PAYTO_BASE):
            continue
        time_m = re.search(r'title="(\d{4}-\d{2}-\d{2}T[^"]+)"', row)
        usd_m = re.search(r">\$([0-9]+(?:\.[0-9]+)?)<", row)
        ts = time_m.group(1) if time_m else None
        parsed = parse_iso(ts)
        rows.append({
            "rail": "base",
            "tx": tx if tx.startswith("0x") else "0x" + tx,
            "explorer": explorer_tx("base", tx),
            "payer": payer,
            "payer_class": classify_payer("base", payer),
            "receiver": PAYTO_BASE,
            "asset": "USDC",
            "amount_atomic": None,
            "amount_usd_display": usd_m.group(1) if usd_m else None,
            "block": None,
            "time": iso(parsed) if parsed else ts,
            "source": "base_roundhouse",
            "day": day,
        })
        seen.add(key)
    return rows


def _usdc_transfer_to_payto(receipt: dict[str, Any]) -> tuple[str | None, str | None, int | None]:
    """Return (payer, amount_atomic, block) for a USDC Transfer to PAYTO_BASE."""
    block_hex = receipt.get("blockNumber")
    block = int(block_hex, 16) if isinstance(block_hex, str) and block_hex.startswith("0x") else None
    payto_topic = _topic_address(PAYTO_BASE).lower()
    usdc = USDC_BASE.lower()
    for lg in receipt.get("logs") or []:
        if (lg.get("address") or "").lower() != usdc:
            continue
        topics = [str(t).lower() for t in (lg.get("topics") or [])]
        if not topics or topics[0] != TRANSFER_TOPIC.lower():
            continue
        if len(topics) < 3 or topics[2] != payto_topic:
            continue
        payer = "0x" + topics[1][-40:] if len(topics) >= 2 else None
        return payer, _decode_uint(lg.get("data")), block
    return None, None, block


def _enrich_base_receipts(rows: list[dict[str, Any]]) -> int:
    """Fill amount_atomic, block, and payer from eth_getTransactionReceipt."""
    needed = [r for r in rows if r.get("tx") and (not r.get("amount_atomic") or not r.get("block"))]
    if not needed:
        return 0
    filled = 0
    rpc_i = 0
    for r in needed:
        receipt = None
        last_err = None
        for attempt in range(len(BASE_RPCS)):
            url = BASE_RPCS[(rpc_i + attempt) % len(BASE_RPCS)]
            try:
                body = _rpc(url, "eth_getTransactionReceipt", [r["tx"]], timeout=25)
            except Exception as exc:
                last_err = type(exc).__name__
                continue
            if isinstance(body, dict) and isinstance(body.get("result"), dict):
                receipt = body["result"]
                rpc_i = (rpc_i + attempt) % len(BASE_RPCS)
                break
            last_err = (body or {}).get("error") if isinstance(body, dict) else "no receipt"
        if not receipt:
            continue
        payer, amount, block = _usdc_transfer_to_payto(receipt)
        if payer and not r.get("payer"):
            r["payer"] = payer
            r["payer_class"] = classify_payer("base", payer)
        if amount:
            r["amount_atomic"] = amount
        if block:
            r["block"] = block
        if amount or block:
            filled += 1
        time.sleep(0.04)
    return filled


def fetch_base_usdc_roundhouse() -> tuple[list[dict[str, Any]], str | None]:
    """Full Base USDC history to PAYTO_BASE via public Roundhouse pages + receipt enrichment.

    Keyless: merchant calendar and day tables are public HTML. Amounts come from
    the USDC Transfer log on the transaction receipt (public Base RPC), not from
    a paid Roundhouse API.
    """
    status, html, err = http_text(ROUNDHOUSE_MERCHANT_URL, timeout=45)
    if not html or status != 200:
        return [], err or f"Roundhouse merchant HTTP {status}"
    days = _roundhouse_settlement_days(html)
    if not days:
        return [], "no settlement days parsed from Roundhouse merchant calendar"
    rows: list[dict[str, Any]] = []
    page_notes: list[str] = []
    seen: set[str] = set()
    for day in days:
        page = 1
        empty_pages = 0
        while page <= 30:
            qs = {"q": PAYTO_BASE, "day": day}
            if page > 1:
                qs["page"] = str(page)
            url = ROUNDHOUSE_TX_URL + "?" + urllib.parse.urlencode(qs)
            st, body, e = http_text(url, timeout=40)
            if not body or st != 200:
                page_notes.append(f"{day} page {page}: {e or st}")
                break
            found = _parse_roundhouse_day_html(body, day)
            new = [r for r in found if r["tx"].lower() not in seen]
            if not new:
                empty_pages += 1
                break
            for r in new:
                seen.add(r["tx"].lower())
            rows.extend(new)
            page += 1
            time.sleep(0.12)
        time.sleep(0.05)
    filled = _enrich_base_receipts(rows)
    missing_amt = sum(1 for r in rows if not r.get("amount_atomic"))
    note = (
        f"Roundhouse public index: {len(days)} settlement days, {len(rows)} Base USDC "
        f"transfers, {filled} receipts enriched"
        + (f"; {missing_amt} still missing amount_atomic" if missing_amt else "")
        + (("; " + "; ".join(page_notes[:6])) if page_notes else "")
        + "."
    )
    return rows, note


def fetch_base_usdc_blockscout() -> tuple[list[dict[str, Any]], str | None]:

    url = (
        "https://base.blockscout.com/api"
        f"?module=account&action=tokentx&address={PAYTO_BASE}"
        f"&contractaddress={USDC_BASE}&sort=desc&page=1&offset=10000"
    )
    status, body = http_json(url, timeout=40)
    if status != 200 or not isinstance(body, dict) or str(body.get("status")) != "1":
        v2 = (
            "https://base.blockscout.com/api/v2/addresses/"
            f"{PAYTO_BASE}/token-transfers?type=ERC-20&filter=to"
        )
        status2, body2 = http_json(v2, timeout=40)
        if status2 != 200 or not isinstance(body2, dict) or "items" not in body2:
            err = None
            if isinstance(body, str):
                err = f"blockscout {status}: {body[:120]}"
            elif isinstance(body, dict):
                err = f"blockscout {status}: {body.get('message') or body.get('result')}"
            else:
                err = f"blockscout {status}"
            return [], err
        rows = []
        for it in body2.get("items") or []:
            token = ((it.get("token") or {}).get("address") or (it.get("token") or {}).get("address_hash") or "")
            if norm_evm(token) and norm_evm(token) != norm_evm(USDC_BASE):
                continue
            to_addr = (it.get("to") or {}).get("hash") if isinstance(it.get("to"), dict) else it.get("to")
            if norm_evm(to_addr) != norm_evm(PAYTO_BASE):
                continue
            frm = (it.get("from") or {}).get("hash") if isinstance(it.get("from"), dict) else it.get("from")
            tx = it.get("transaction_hash") or it.get("tx_hash") or ""
            ts = it.get("timestamp")
            rec_time = None
            if isinstance(ts, str) and ("T" in ts or ts.endswith("Z")):
                rec_time = ts
            elif ts:
                rec_time = str(ts)
            total = it.get("total")
            if isinstance(total, dict):
                amount = total.get("value")
            else:
                amount = it.get("value") if it.get("value") is not None else total
            rows.append({
                "rail": "base",
                "tx": tx,
                "explorer": explorer_tx("base", tx),
                "payer": frm,
                "payer_class": classify_payer("base", frm),
                "receiver": PAYTO_BASE,
                "asset": "USDC",
                "amount_atomic": amount,
                "block": int(it["block_number"]) if it.get("block_number") else None,
                "time": rec_time,
                "source": "base_blockscout_v2",
            })
        return rows, None
    rows = []
    for it in body.get("result") or []:
        if norm_evm(it.get("to")) != norm_evm(PAYTO_BASE):
            continue
        if it.get("contractAddress") and norm_evm(it.get("contractAddress")) != norm_evm(USDC_BASE):
            continue
        ts = it.get("timeStamp")
        rec_time = iso(datetime.fromtimestamp(int(ts), tz=timezone.utc)) if ts and str(ts).isdigit() else None
        tx = it.get("hash")
        payer = it.get("from")
        rows.append({
            "rail": "base",
            "tx": tx,
            "explorer": explorer_tx("base", tx),
            "payer": payer,
            "payer_class": classify_payer("base", payer),
            "receiver": PAYTO_BASE,
            "asset": "USDC",
            "amount_atomic": it.get("value"),
            "block": int(it["blockNumber"]) if it.get("blockNumber") else None,
            "time": rec_time,
            "source": "base_blockscout",
        })
    return rows, None


def _rpc(url: str, method: str, params: list[Any], timeout: int = 30) -> dict[str, Any]:
    status, body = http_json(
        url,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        timeout=timeout,
        headers={"Content-Type": "application/json"},
    )
    if not isinstance(body, dict):
        return {"error": {"message": f"http {status}: {body}"}}
    return body


def fetch_base_usdc_rpc(from_block: int | None = None, to_block: int | None = None, max_chunks: int = 80, recent_blocks: int | None = 4_000_000) -> tuple[list[dict[str, Any]], str | None]:
    topic_to = _topic_address(PAYTO_BASE)
    last_err = None
    head = None
    rpc_url = None
    for url in BASE_RPCS:
        body = _rpc(url, "eth_blockNumber", [])
        if body.get("result"):
            head = int(body["result"], 16)
            rpc_url = url
            break
        last_err = str((body.get("error") or body))[:200]
    if head is None or rpc_url is None:
        return [], last_err or "base rpc unavailable"

    start = from_block or FIRST_BASE_BLOCK
    end = to_block or head
    if start < FIRST_BASE_BLOCK:
        start = FIRST_BASE_BLOCK
    if start > end:
        return [], None

    ranges: list[tuple[int, int]] = []
    if recent_blocks and end - start > recent_blocks:
        recent_start = max(start, end - recent_blocks)
        ranges.append((recent_start, end))
        if recent_start > start:
            ranges.append((start, recent_start - 1))
    else:
        ranges.append((start, end))

    rows: list[dict[str, Any]] = []
    chunks = 0
    last_scanned = start - 1
    for range_start, range_end in ranges:
        window = 50_000
        cursor = range_start
        while cursor <= range_end and chunks < max_chunks:
            chunk_end = min(cursor + window - 1, range_end)
            params = [{
                "address": USDC_BASE,
                "fromBlock": hex(cursor),
                "toBlock": hex(chunk_end),
                "topics": [TRANSFER_TOPIC, None, topic_to],
            }]
            body = _rpc(rpc_url, "eth_getLogs", params, timeout=40)
            if body.get("error"):
                msg = str(body["error"])
                last_err = msg[:200]
                if window > 2_000:
                    window = max(2_000, window // 2)
                    time.sleep(0.25)
                    continue
                advanced = False
                for alt in BASE_RPCS:
                    if alt == rpc_url:
                        continue
                    body2 = _rpc(alt, "eth_getLogs", params, timeout=40)
                    if body2.get("result") is not None:
                        body = body2
                        rpc_url = alt
                        advanced = True
                        break
                if not advanced:
                    cursor = chunk_end + 1
                    last_scanned = chunk_end
                    chunks += 1
                    time.sleep(0.2)
                    continue
            logs = body.get("result") or []
            for lg in logs:
                topics = lg.get("topics") or []
                payer = None
                if len(topics) >= 2:
                    payer = "0x" + topics[1][-40:]
                tx = lg.get("transactionHash")
                block_hex = lg.get("blockNumber")
                block = int(block_hex, 16) if block_hex else None
                rows.append({
                    "rail": "base",
                    "tx": tx,
                    "explorer": explorer_tx("base", tx),
                    "payer": payer,
                    "payer_class": classify_payer("base", payer),
                    "receiver": PAYTO_BASE,
                    "asset": "USDC",
                    "amount_atomic": _decode_uint(lg.get("data")),
                    "block": block,
                    "time": None,
                    "source": "base_rpc_getLogs",
                })
            cursor = chunk_end + 1
            last_scanned = chunk_end
            chunks += 1
            if window < 50_000:
                window = min(50_000, window * 2)
            time.sleep(0.05)

    blocks = sorted({r["block"] for r in rows if r.get("block")})
    stamps: dict[int, str] = {}
    for i, blk in enumerate(blocks):
        if i >= 200:
            break
        body = _rpc(rpc_url, "eth_getBlockByNumber", [hex(blk), False], timeout=20)
        result = body.get("result") or {}
        ts_hex = result.get("timestamp") if isinstance(result, dict) else None
        if ts_hex:
            stamps[blk] = iso(datetime.fromtimestamp(int(ts_hex, 16), tz=timezone.utc))
        time.sleep(0.03)
    for r in rows:
        if r.get("block") in stamps:
            r["time"] = stamps[r["block"]]
    note = None
    if last_scanned < end:
        note = (
            "Recent Base USDC transfers near chain head were scanned. "
            f"Historical backfill last completed block {last_scanned} of {end}; "
            "some mid-history Base payments may be missing until a later refresh."
        )
    elif last_err and not rows:
        note = last_err
    return rows, note


def fetch_base_usdc_etherscan() -> tuple[list[dict[str, Any]], str | None]:
    key = (os.getenv("ETHERSCAN_API_KEY") or os.getenv("BASESCAN_API_KEY") or "").strip()
    if not key:
        return [], "no etherscan key in env (optional)"
    # Never log or return the key.
    qs = urllib.parse.urlencode({
        "chainid": "8453",
        "module": "account",
        "action": "tokentx",
        "address": PAYTO_BASE,
        "contractaddress": USDC_BASE,
        "sort": "desc",
        "page": "1",
        "offset": "10000",
        "apikey": key,
    })
    status, body = http_json(f"https://api.etherscan.io/v2/api?{qs}", timeout=40)
    if status != 200 or not isinstance(body, dict) or str(body.get("status")) != "1":
        msg = "etherscan v2 failed"
        if isinstance(body, dict):
            result = body.get("result")
            if isinstance(result, str) and "apikey" not in result.lower() and "token" not in result.lower():
                msg = f"etherscan v2: {body.get('message')}: {result[:160]}"
            else:
                msg = f"etherscan v2: {body.get('message')}"
        return [], msg
    rows = []
    for it in body.get("result") or []:
        if norm_evm(it.get("to")) != norm_evm(PAYTO_BASE):
            continue
        ts = it.get("timeStamp")
        rec_time = iso(datetime.fromtimestamp(int(ts), tz=timezone.utc)) if ts and str(ts).isdigit() else None
        tx = it.get("hash")
        payer = it.get("from")
        rows.append({
            "rail": "base",
            "tx": tx,
            "explorer": explorer_tx("base", tx),
            "payer": payer,
            "payer_class": classify_payer("base", payer),
            "receiver": PAYTO_BASE,
            "asset": "USDC",
            "amount_atomic": it.get("value"),
            "block": int(it["blockNumber"]) if it.get("blockNumber") else None,
            "time": rec_time,
            "source": "base_etherscan_v2",
        })
    return rows, None


def fetch_xrpl_payments() -> tuple[list[dict[str, Any]], str | None]:
    payload = json.dumps({
        "method": "account_tx",
        "params": [{
            "account": PAYTO_XRPL,
            "ledger_index_min": -1,
            "ledger_index_max": -1,
            "binary": False,
            "forward": False,
            "limit": 400,
        }],
    }).encode()
    status, body = http_json("https://xrplcluster.com/", data=payload, timeout=45)
    if status != 200 or not isinstance(body, dict):
        return [], f"xrplcluster {status}"
    result = body.get("result") or {}
    if result.get("status") not in (None, "success"):
        return [], f"xrplcluster status {result.get('status')}"
    rows = []
    for wrap in result.get("transactions") or []:
        tx = wrap.get("tx") or wrap.get("tx_json") or {}
        meta = wrap.get("meta") or {}
        if tx.get("TransactionType") != "Payment":
            continue
        if tx.get("Destination") != PAYTO_XRPL:
            continue
        tes = (meta.get("TransactionResult") if isinstance(meta, dict) else None) or ""
        if tes and tes != "tesSUCCESS":
            continue
        amount = tx.get("Amount")
        delivered = meta.get("delivered_amount") or meta.get("DeliveredAmount") or amount
        drops = None
        if isinstance(delivered, str) and delivered.isdigit():
            drops = delivered
        elif isinstance(delivered, dict) and str(delivered.get("currency", "XRP")).upper() == "XRP":
            # Some APIs convert drops incorrectly; prefer raw string Amount.
            if isinstance(amount, str) and amount.isdigit():
                drops = amount
            else:
                try:
                    # If value looks like whole XRP, convert; if already drops-like int keep it.
                    val = delivered.get("value")
                    drops = str(int(val)) if val is not None and "." not in str(val) else None
                except (TypeError, ValueError):
                    drops = None
        elif isinstance(amount, str) and amount.isdigit():
            drops = amount
        payer = tx.get("Account")
        hx = tx.get("hash") or wrap.get("hash")
        ripple_date = tx.get("date")
        rec_time = iso(datetime.fromtimestamp(int(ripple_date) + XRPL_EPOCH_OFFSET, tz=timezone.utc)) if ripple_date is not None else None
        rows.append({
            "rail": "xrpl",
            "tx": hx,
            "explorer": explorer_tx("xrpl", hx),
            "payer": payer,
            "payer_class": classify_payer("xrpl", payer),
            "receiver": PAYTO_XRPL,
            "asset": "XRP",
            "amount_atomic": drops,
            "block": tx.get("ledger_index") or wrap.get("ledger_index"),
            "time": rec_time,
            "source": "xrpl_account_tx",
        })
    return rows, None


def fetch_celo_native() -> tuple[list[dict[str, Any]], str | None]:
    url = (
        "https://celo.blockscout.com/api?module=account&action=txlist"
        f"&address={PAYTO_CELO_NATIVE}&sort=desc&page=1&offset=10000"
    )
    status, body = http_json(url, timeout=40)
    if status != 200 or not isinstance(body, dict):
        return [], f"celo txlist {status}"
    if str(body.get("status") or "1") == "0" and body.get("message") not in ("OK", "No transactions found"):
        return [], f"celo txlist: {body.get('message')}"
    rows = []
    for it in body.get("result") or []:
        if norm_evm(it.get("to")) != norm_evm(PAYTO_CELO_NATIVE):
            continue
        if int(it.get("value") or "0") <= 0:
            continue
        if str(it.get("isError") or "0") not in ("0", ""):
            continue
        ts = it.get("timeStamp")
        rec_time = iso(datetime.fromtimestamp(int(ts), tz=timezone.utc)) if ts and str(ts).isdigit() else None
        tx = it.get("hash")
        payer = it.get("from")
        rows.append({
            "rail": "celo",
            "tx": tx,
            "explorer": explorer_tx("celo", tx),
            "payer": payer,
            "payer_class": classify_payer("celo", payer),
            "receiver": PAYTO_CELO_NATIVE,
            "asset": "CELO",
            "amount_atomic": it.get("value"),
            "block": int(it["blockNumber"]) if it.get("blockNumber") else None,
            "time": rec_time,
            "source": "celo_blockscout_txlist",
        })
    return rows, None


def fetch_celo_usdc() -> tuple[list[dict[str, Any]], str | None]:
    url = (
        "https://celo.blockscout.com/api?module=account&action=tokentx"
        f"&address={PAYTO_BASE}&sort=desc&page=1&offset=10000"
    )
    status, body = http_json(url, timeout=40)
    if status != 200 or not isinstance(body, dict):
        return [], f"celo tokentx {status}"
    rows = []
    for it in body.get("result") or []:
        if norm_evm(it.get("to")) != norm_evm(PAYTO_BASE):
            continue
        symbol = (it.get("tokenSymbol") or "").upper()
        if symbol and symbol not in ("USDC", "CUSD"):
            # still include USDC-like 6 decimal stablecoins even if unnamed when contract matches
            if norm_evm(it.get("contractAddress")) != norm_evm(USDC_CELO):
                continue
        ts = it.get("timeStamp")
        rec_time = iso(datetime.fromtimestamp(int(ts), tz=timezone.utc)) if ts and str(ts).isdigit() else None
        tx = it.get("hash")
        payer = it.get("from")
        rows.append({
            "rail": "celo",
            "tx": tx,
            "explorer": explorer_tx("celo", tx),
            "payer": payer,
            "payer_class": classify_payer("celo", payer),
            "receiver": PAYTO_BASE,
            "asset": symbol or "USDC",
            "amount_atomic": it.get("value"),
            "block": int(it["blockNumber"]) if it.get("blockNumber") else None,
            "time": rec_time,
            "source": "celo_blockscout_tokentx",
        })
    return rows, None


def fetch_live_catalogs() -> tuple[dict[str, dict[str, list[str]]], list[str]]:
    catalogs: dict[str, dict[str, list[str]]] = {"base": {}, "xrpl": {}, "celo": {}}
    notes: list[str] = []
    status, body = http_json(f"{API}/.well-known/x402.json", timeout=20)
    if status == 200 and isinstance(body, dict):
        catalogs["base"] = build_amount_catalog(body.get("resources") or [], "base")
    else:
        notes.append(f"base catalog fetch failed ({status})")
    status, body = http_json(f"{API}/t54/health", timeout=20)
    if status == 200 and isinstance(body, dict):
        catalogs["xrpl"] = build_amount_catalog(body.get("skus") or [], "xrpl")
    else:
        status2, body2 = http_json(f"{API}/t54/.well-known/x402.json", timeout=20)
        if status2 == 200 and isinstance(body2, dict):
            catalogs["xrpl"] = build_amount_catalog(body2.get("resources") or [], "xrpl")
        else:
            notes.append(f"t54 catalog fetch failed ({status})")
    return catalogs, notes


def attach_skus(payments: list[dict[str, Any]], catalogs: dict[str, dict[str, list[str]]], prior_skus: dict[tuple[str, str], str] | None = None) -> None:
    for p in payments:
        rail = p.get("rail") or ""
        cat = catalogs.get("base") if rail == "base" else catalogs.get("xrpl") if rail == "xrpl" else catalogs.get("celo") or {}
        sku, src = map_sku(p.get("amount_atomic"), cat, prior_skus, (rail, str(p.get("tx") or "").lower()))
        if sku and not p.get("sku_id"):
            p["sku_id"] = sku
            p["sku_id_source"] = src
        elif p.get("sku_id") and not p.get("sku_id_source"):
            p["sku_id_source"] = "prior_snapshot"
        elif not p.get("sku_id"):
            p["sku_id"] = None
            p["sku_id_source"] = src


def probe_health() -> dict[str, Any]:
    endpoints = []
    for t in HEALTH_TARGETS:
        result = http_status(t["url"])
        result["id"] = t["id"]
        endpoints.append(result)
    return {"probed_at": iso(utcnow()), "endpoints": endpoints}


def preflight_engine_sample() -> dict[str, Any]:
    note = "Produced by the preflight engine in this snapshot job. Not a paid buyer call."
    try:
        from marketplace.skus.preflight_check import run_preflight
        result = run_preflight({"contractAddress": USDC_BASE, "network": "eip155:8453"})
        if isinstance(result, tuple):
            result = result[0] if result else {}
        if not isinstance(result, dict):
            return {"source": "engine_snapshot", "note": note, "error": "unexpected_result_type"}
        keep = {k: result.get(k) for k in (
            "verdict", "riskScore", "risk_score", "contractName", "contract_name",
            "verified", "isProxy", "is_proxy", "implementation", "sourceProvider",
            "source_provider", "reasons", "schema", "schema_id",
        ) if k in result or result.get(k) is not None}
        # Prefer a tight public subset.
        sample = {
            "verdict": result.get("verdict"),
            "riskScore": result.get("riskScore") if "riskScore" in result else result.get("risk_score"),
            "contractName": result.get("contractName") or result.get("contract_name"),
            "verified": result.get("verified"),
            "isProxy": result.get("isProxy") if "isProxy" in result else result.get("is_proxy"),
            "implementation": result.get("implementation"),
            "sourceProvider": result.get("sourceProvider") or result.get("source_provider"),
            "reasons": result.get("reasons") or result.get("reason"),
        }
        return {
            "source": "engine_snapshot",
            "note": note,
            "checked_at": iso(utcnow()),
            "request": {"contractAddress": USDC_BASE, "network": "eip155:8453"},
            "result": sample,
        }
    except Exception as exc:
        return {
            "source": "engine_snapshot",
            "note": note,
            "error": type(exc).__name__,
            "checked_at": iso(utcnow()),
        }


def annotate_payments(payments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for p in payments:
        p["payer_class"] = classify_payment(
            p.get("rail") or "",
            p.get("payer"),
            p.get("sku_id"),
            p.get("sku_id_source"),
        )
        if p.get("tx") and not p.get("explorer"):
            p["explorer"] = explorer_tx(p.get("rail") or "", p["tx"])
        meta = probe_meta(p.get("rail") or "", p.get("payer"))
        if meta and p.get("payer_class") == "automated_probe":
            p["probe_name"] = meta.get("name")
            p["probe_note"] = meta.get("note")
    return payments



def fill_missing_block_times(payments: list[dict[str, Any]], cap: int = 80) -> int:
    """Stamp payments that have a block number but no time, using a public RPC."""
    needed = []
    seen: set[tuple[str, int]] = set()
    for p in payments:
        if p.get("time") or not p.get("block"):
            continue
        rail = p.get("rail") or ""
        if not rail.startswith("base") and not rail.startswith("celo"):
            continue
        key = (rail, int(p["block"]))
        if key in seen:
            continue
        seen.add(key)
        needed.append(key)
        if len(needed) >= cap:
            break
    if not needed:
        return 0
    rpc_for = {
        "base": BASE_RPCS,
        "celo": ["https://forno.celo.org", "https://rpc.ankr.com/celo"],
    }
    stamps: dict[tuple[str, int], str] = {}
    for rail, blk in needed:
        prefix = "base" if rail.startswith("base") else "celo"
        for url in rpc_for[prefix]:
            body = _rpc(url, "eth_getBlockByNumber", [hex(blk), False], timeout=20)
            result = body.get("result") or {}
            ts_hex = result.get("timestamp") if isinstance(result, dict) else None
            if ts_hex:
                stamps[(rail, blk)] = iso(datetime.fromtimestamp(int(ts_hex, 16), tz=timezone.utc))
                break
        time.sleep(0.03)
    filled = 0
    for p in payments:
        if p.get("time") or not p.get("block"):
            continue
        key = (p.get("rail") or "", int(p["block"]))
        # map celo/base variants
        if key in stamps:
            p["time"] = stamps[key]
            filled += 1
        else:
            alt = None
            if key[0].startswith("base"):
                alt = stamps.get(("base", key[1]))
            elif key[0].startswith("celo"):
                alt = stamps.get(("celo", key[1]))
            if alt:
                p["time"] = alt
                filled += 1
    return filled


def build_snapshot(
    *,
    repo_root: Path,
    live: bool = True,
    prior: dict[str, Any] | None = None,
    settlements: dict[str, Any] | None = None,
    extra_payments: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
    include_health: bool = True,
    include_preflight: bool = True,
) -> dict[str, Any]:
    now = now or utcnow()
    coverage_ok: list[str] = []
    coverage_failed: list[dict[str, str]] = []
    notes: list[str] = []
    groups: list[list[dict[str, Any]]] = []

    if settlements:
        groups.append(payments_from_settlements(settlements))
        coverage_ok.append("prior_settlements_json")
    if prior:
        groups.append(payments_from_prior_proof(prior))
        coverage_ok.append("prior_proof_json")
    if extra_payments:
        groups.append(extra_payments)

    catalogs: dict[str, dict[str, list[str]]] = {"base": {}, "xrpl": {}, "celo": {}}
    if live:
        fetched_cats, cat_notes = fetch_live_catalogs()
        catalogs = fetched_cats
        notes.extend(cat_notes)
        for label, fn in (
            ("xrpl_account_tx", fetch_xrpl_payments),
            ("celo_blockscout_txlist", fetch_celo_native),
            ("celo_blockscout_tokentx", fetch_celo_usdc),
            ("base_roundhouse", fetch_base_usdc_roundhouse),
            ("base_blockscout", fetch_base_usdc_blockscout),
            ("base_etherscan_v2", fetch_base_usdc_etherscan),
        ):
            try:
                rows, err = fn()
            except Exception as exc:
                coverage_failed.append({"source": label, "error": type(exc).__name__})
                continue
            if err and not rows:
                coverage_failed.append({"source": label, "error": err[:240]})
            if rows:
                groups.append(rows)
                coverage_ok.append(label)
                if err:
                    notes.append(err)
        # When Roundhouse already supplied the full Base history, only scan a
        # short recent RPC window for any transfers not yet indexed there.
        # Otherwise walk a larger recent window as a fallback backfill.
        roundhouse_ok = "base_roundhouse" in coverage_ok
        rpc_recent = 200_000 if roundhouse_ok else 4_000_000
        rpc_chunks = 40 if roundhouse_ok else 120
        try:
            rows, err = fetch_base_usdc_rpc(
                from_block=FIRST_BASE_BLOCK,
                max_chunks=rpc_chunks,
                recent_blocks=rpc_recent,
            )
        except Exception as exc:
            coverage_failed.append({"source": "base_rpc_getLogs", "error": type(exc).__name__})
        else:
            if rows:
                groups.append(rows)
                coverage_ok.append("base_rpc_getLogs")
            if err:
                if rows and roundhouse_ok and "mid-history" in err:
                    notes.append(
                        "Base RPC scanned a short recent window only. "
                        "The Roundhouse public index already supplied the full Base USDC history to the payTo address."
                    )
                else:
                    (coverage_failed if not rows else notes).append(
                        {"source": "base_rpc_getLogs", "error": err[:240]} if not rows else err
                    )

    payments = annotate_payments(merge_payments(*groups))
    if live:
        try:
            fill_missing_block_times(payments)
        except Exception:
            pass
    prior_skus = {}
    for g in groups:
        for p in g:
            if p.get("sku_id") and p.get("tx"):
                prior_skus[(p.get("rail") or "", str(p["tx"]).lower())] = p["sku_id"]
    attach_skus(payments, catalogs, prior_skus)
    payments = annotate_payments(payments)

    health = probe_health() if live and include_health else None
    preflight = preflight_engine_sample() if live and include_preflight else None

    snapshot = {
        "schema": SCHEMA_ID,
        "name": "Agentic Swarm Marketplace",
        "updated_at": iso(now),
        "site": SITE,
        "api": API,
        "page": PAGE,
        "refresh": {
            "schedule": "Regenerate with python scripts/generate_proof_json.py and deploy the docs/ snapshot on GitHub Pages.",
            "workflow_pending": "scripts/github-workflows/proof-refresh.yml",
            "note": "The page loads this snapshot file. If a later refresh fails or HOJO is down, the last committed snapshot remains on GitHub Pages. A 6-hour GitHub Action is staged at scripts/github-workflows/proof-refresh.yml pending a token with the workflow scope.",
        },
        "honesty": {
            "house_note": "House payments are self-funded test and catalog-refresh payments by the operator. They are not third-party customers.",
            "operator_identity_note": "The published XRPL merchant identity account is listed separately. It is not a house test buyer and is not counted as an external payer.",
            "sku_mapping_note": "sku_id is inferred when a settled amount uniquely matches a live catalog price, or taken from a prior annotated snapshot. Ambiguous or unknown amounts stay unlabeled.",
            "probe_note": "Automated directory/probe calls are real settled external payments from known recurring probes (for example Lumi paying 0.001 XRP for /t54/hello daily). They are listed separately and are not counted as customers.",
            "dust_note": "Unsolicited or dust transfers are incoming payments whose amount does not uniquely match a live SKU price (for example 1-drop or 10-drop XRPL transfers). They are excluded from the external SKU-purchase headline.",
            "unverified": "This page only reports on-chain payments to the published payTo addresses and the health of public HTTPS endpoints. No unverified volume or customer claims.",
        },
        "pay_to": {
            "base_usdc": {
                "address": PAYTO_BASE,
                "chain": "eip155:8453",
                "asset": "USDC",
                "explorer": f"https://basescan.org/address/{PAYTO_BASE}",
            },
            "celo_native": {
                "address": PAYTO_CELO_NATIVE,
                "chain": "eip155:42220",
                "asset": "CELO",
                "explorer": f"https://celoscan.io/address/{PAYTO_CELO_NATIVE}",
            },
            "xrpl": {
                "address": PAYTO_XRPL,
                "network": "xrpl:0",
                "asset": "XRP",
                "explorer": f"https://xrpscan.com/account/{PAYTO_XRPL}",
            },
        },
        "classifiers": {
            "house": {
                "base": [HOUSE_BASE],
                "celo": [HOUSE_CELO],
                "xrpl": [HOUSE_XRPL],
            },
            "operator_identity": {
                "xrpl": [OPERATOR_XRPL_IDENTITY],
            },
            "automated_probe": {
                rail: list(accounts.keys()) for rail, accounts in PROBE_PAYERS.items()
            },
        },
        "summary": summarize(payments, now=now),
        "per_sku": per_sku(payments),
        "payments": payments,
        "health": health,
        "preflight_sample": preflight,
        "coverage": {
            "sources_ok": coverage_ok,
            "sources_failed": coverage_failed,
            "notes": notes,
        },
    }
    return snapshot


def default_paths(repo_root: Path) -> dict[str, Path]:
    docs = repo_root / "docs" / "proof"
    return {
        "output": docs / "proof.json",
        "prior": docs / "proof.json",
        "settlements": docs / "settlements.json",
    }


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_snapshot(snapshot: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
