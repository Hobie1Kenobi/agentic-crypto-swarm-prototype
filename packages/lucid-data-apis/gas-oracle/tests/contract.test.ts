import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildCongestion, buildForecast, buildQuote, inclusionCurve } from "../src/logic.js";
import {
  congestionResponseSchema,
  forecastResponseSchema,
  quoteResponseSchema,
} from "../src/schemas.js";

describe("contract schemas", () => {
  it("quote response matches schema", () => {
    const q = buildQuote({ chain: "base", urgency: "medium", targetBlocks: 3, txType: "contract" });
    quoteResponseSchema.parse(q);
  });

  it("forecast response matches schema", () => {
    forecastResponseSchema.parse(buildForecast({ chain: "optimism", horizonMinutes: 30 }));
  });

  it("congestion response matches schema", () => {
    congestionResponseSchema.parse(buildCongestion({ chain: "arbitrum" }));
  });
});

describe("business logic", () => {
  it("inclusion curve is monotonic", () => {
    const curve = inclusionCurve(1, "medium", 5);
    for (let i = 1; i < curve.length; i++) {
      assert.ok(curve[i]!.probability >= curve[i - 1]!.probability);
    }
  });

  it("high urgency quote >= low urgency quote", () => {
    const low = Number(buildQuote({ chain: "base", urgency: "low", targetBlocks: 3, txType: "contract" }).recommended_max_fee);
    const high = Number(buildQuote({ chain: "base", urgency: "high", targetBlocks: 3, txType: "contract" }).recommended_max_fee);
    assert.ok(high >= low);
  });

  it("forecast confidence degrades with horizon", () => {
    const f = buildForecast({ chain: "polygon", horizonMinutes: 60 });
    assert.ok(f.points[0]!.confidence >= f.points.at(-1)!.confidence);
  });
});

describe("integration", () => {
  it("paywall returns 402 when enabled", async () => {
    process.env.LUCID_GAS_ORACLE_REQUIRE_PAYMENT = "1";
    const { app } = await import("../src/server.js");
    const res = await app.request("/v1/gas/quote?chain=base");
    assert.equal(res.status, 402);
    delete process.env.LUCID_GAS_ORACLE_REQUIRE_PAYMENT;
  });

  it("quote endpoint returns 200 without paywall", async () => {
    delete process.env.LUCID_GAS_ORACLE_REQUIRE_PAYMENT;
    const { app } = await import("../src/server.js");
    const res = await app.request("/v1/gas/quote?chain=base&urgency=medium");
    assert.equal(res.status, 200);
    const json = await res.json();
    quoteResponseSchema.parse(json);
  });
});
