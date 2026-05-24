import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { createPublicClient, formatGwei, http } from "viem";
import { arbitrum, base, mainnet, optimism, polygon } from "viem/chains";
import { buildCongestion, buildForecast, buildQuote } from "./logic.js";
import {
  chainSchema,
  congestionQuerySchema,
  congestionResponseSchema,
  forecastQuerySchema,
  forecastResponseSchema,
  quoteQuerySchema,
  quoteResponseSchema,
  type Chain,
} from "./schemas.js";

const PORT = Number(process.env.PORT || process.env.LUCID_GAS_ORACLE_PORT || 8094);

const CHAINS = {
  ethereum: mainnet,
  base,
  optimism,
  arbitrum,
  polygon,
} as const;

const RPC: Record<Chain, string> = {
  ethereum: process.env.ETHEREUM_RPC_URL || "https://eth.llamarpc.com",
  base: process.env.BASE_RPC_URL || "https://mainnet.base.org",
  optimism: process.env.OPTIMISM_RPC_URL || "https://mainnet.optimism.io",
  arbitrum: process.env.ARBITRUM_RPC_URL || "https://arb1.arbitrum.io/rpc",
  polygon: process.env.POLYGON_RPC_URL || "https://polygon-rpc.com",
};

async function liveGwei(chain: Chain): Promise<number | undefined> {
  try {
    const client = createPublicClient({ chain: CHAINS[chain], transport: http(RPC[chain]) });
    const fees = await client.estimateFeesPerGas();
    const gas = fees.maxFeePerGas ?? fees.gasPrice;
    return gas ? Number(formatGwei(gas)) : undefined;
  } catch {
    return undefined;
  }
}

function paywall() {
  return async (c: any, next: () => Promise<void>) => {
    if (process.env.LUCID_GAS_ORACLE_REQUIRE_PAYMENT === "1") {
      const paid = c.req.header("x-402-payment") || c.req.header("X-402-Payment");
      if (!paid) {
        return c.json({ error: { code: "payment_required", message: "x402 payment required" } }, 402);
      }
    }
    await next();
  };
}

const app = new Hono();
const started = Date.now();

app.get("/health", (c) => c.json({ ok: true, service: "lucid-gas-oracle" }));

app.get("/v1/gas/quote", paywall(), async (c) => {
  const parsed = quoteQuerySchema.safeParse(c.req.query());
  if (!parsed.success) {
    return c.json({ error: { code: "invalid_request", message: parsed.error.message } }, 400);
  }
  const gwei = await liveGwei(parsed.data.chain);
  const body = buildQuote({ ...parsed.data, observedGwei: gwei });
  body.freshness_ms = Date.now() - started;
  const out = quoteResponseSchema.parse(body);
  return c.json(out);
});

app.get("/v1/gas/forecast", paywall(), async (c) => {
  const parsed = forecastQuerySchema.safeParse(c.req.query());
  if (!parsed.success) {
    return c.json({ error: { code: "invalid_request", message: parsed.error.message } }, 400);
  }
  const gwei = await liveGwei(parsed.data.chain);
  const body = buildForecast({ ...parsed.data, observedGwei: gwei });
  body.freshness_ms = Date.now() - started;
  const out = forecastResponseSchema.parse(body);
  return c.json(out);
});

app.get("/v1/gas/congestion", paywall(), async (c) => {
  const parsed = congestionQuerySchema.safeParse(c.req.query());
  if (!parsed.success) {
    return c.json({ error: { code: "invalid_request", message: parsed.error.message } }, 400);
  }
  const gwei = await liveGwei(parsed.data.chain);
  const body = buildCongestion({ chain: parsed.data.chain, observedGwei: gwei });
  body.freshness_ms = Date.now() - started;
  const out = congestionResponseSchema.parse(body);
  return c.json(out);
});

export { app };

const isMain = process.argv[1]?.replace(/\\/g, "/").endsWith("server.ts");
if (isMain) {
  console.log(`lucid-gas-oracle listening on http://127.0.0.1:${PORT}`);
  serve({ fetch: app.fetch, port: PORT });
}
