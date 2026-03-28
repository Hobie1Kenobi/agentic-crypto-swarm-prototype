from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class ProductSpec:
    product_id: str
    name: str
    price_usd_min: Decimal


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


@dataclass(frozen=True)
class MarketplaceConfig:
    http_enabled: bool
    orders_dir: Path
    dashboard_bundle_price_usd: Decimal
    webhook_secret: str | None
    bundle_zip_path: Path | None
    public_base_url: str

    @classmethod
    def from_env(cls) -> MarketplaceConfig:
        root = _repo_root()
        orders = _env("MARKETPLACE_ORDERS_DIR") or "marketplace/orders"
        od = Path(orders)
        if not od.is_absolute():
            od = root / od
        raw = _env("MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD", "49.00")
        try:
            price = Decimal(str(raw))
        except Exception:
            price = Decimal("49.00")
        http = _env("MARKETPLACE_HTTP_ENABLED", "0").lower() in ("1", "true", "yes")
        wh = _env("STRIPE_WEBHOOK_SECRET") or None
        bz = _env("MARKETPLACE_BUNDLE_ZIP_PATH")
        bundle_path: Path | None = None
        if bz:
            bp = Path(bz)
            bundle_path = bp if bp.is_absolute() else (root / bp)
        pub = _env("MARKETPLACE_PUBLIC_BASE_URL", "").rstrip("/")
        return cls(
            http_enabled=http,
            orders_dir=od,
            dashboard_bundle_price_usd=price,
            webhook_secret=wh,
            bundle_zip_path=bundle_path,
            public_base_url=pub,
        )


def product_dashboard_bundle() -> ProductSpec:
    return ProductSpec(
        product_id="x402_strategy_dashboard_bundle",
        name="x402 Strategy Dashboard (operator bundle)",
        price_usd_min=Decimal("0.50"),
    )
