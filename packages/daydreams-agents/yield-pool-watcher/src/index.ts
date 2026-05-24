import { serve } from "@hono/node-server";
import { createAgentApp, paymentsFromEnv } from "@lucid-dreams/agent-kit";
import { z } from "zod";

const PORT = Number(process.env.PORT || process.env.YIELD_POOL_WATCHER_PORT || 8096);

type PoolSnapshot = {
  pool_id: string;
  protocol: string;
  chain: string;
  symbol: string;
  tvl_usd: number;
  apy: number;
  apy_base: number | null;
  apy_reward: number | null;
  updated_at: string;
};

type CachedSnapshot = {
  at: number;
  pools: Map<string, PoolSnapshot>;
};

const cache: CachedSnapshot = { at: 0, pools: new Map() };

const LLAMA_POOLS_URL = "https://yields.llama.fi/pools";

async function fetchAllPools(): Promise<PoolSnapshot[]> {
  const res = await fetch(LLAMA_POOLS_URL, {
    headers: { "User-Agent": "Swarm-Economy-YieldPoolWatcher/0.1" },
  });
  if (!res.ok) throw new Error(`DefiLlama yields API HTTP ${res.status}`);
  const json = (await res.json()) as { data?: Array<Record<string, unknown>> };
  const data = json.data ?? [];
  return data.map((p) => ({
    pool_id: String(p.pool ?? ""),
    protocol: String(p.project ?? ""),
    chain: String(p.chain ?? ""),
    symbol: String(p.symbol ?? ""),
    tvl_usd: Number(p.tvlUsd ?? 0),
    apy: Number(p.apy ?? 0),
    apy_base: p.apyBase != null ? Number(p.apyBase) : null,
    apy_reward: p.apyReward != null ? Number(p.apyReward) : null,
    updated_at: new Date().toISOString(),
  }));
}

function matchPool(
  pool: PoolSnapshot,
  protocolIds: string[],
  poolFilters: string[],
): boolean {
  const protoOk =
    !protocolIds.length ||
    protocolIds.some((id) => pool.protocol.toLowerCase().includes(id.toLowerCase()));
  const poolOk =
    !poolFilters.length ||
    poolFilters.some((f) => {
      const low = f.toLowerCase();
      return (
        pool.pool_id.toLowerCase() === low ||
        pool.symbol.toLowerCase().includes(low) ||
        pool.pool_id.toLowerCase().includes(low)
      );
    });
  return protoOk && poolOk;
}

function pctDelta(prev: number, next: number): number {
  if (prev === 0) return next === 0 ? 0 : 100;
  return Number((((next - prev) / prev) * 100).toFixed(4));
}

async function watchPools(input: {
  protocol_ids: string[];
  pools: string[];
  threshold_rules: {
    tvl_drop_pct?: number;
    apy_spike_pct?: number;
    apy_drop_pct?: number;
    tvl_spike_pct?: number;
  };
}) {
  const all = await fetchAllPools();
  const selected = all.filter((p) => matchPool(p, input.protocol_ids, input.pools));
  if (!selected.length) {
    throw new Error("No pools matched protocol_ids / pools filters");
  }

  const rules = {
    tvl_drop_pct: input.threshold_rules.tvl_drop_pct ?? 10,
    apy_spike_pct: input.threshold_rules.apy_spike_pct ?? 25,
    apy_drop_pct: input.threshold_rules.apy_drop_pct ?? 20,
    tvl_spike_pct: input.threshold_rules.tvl_spike_pct ?? 50,
  };

  const deltas: Array<{
    pool_id: string;
    tvl_delta_pct: number;
    apy_delta_pct: number;
    previous_tvl_usd: number | null;
    previous_apy: number | null;
  }> = [];

  const alerts: Array<{
    pool_id: string;
    type: string;
    message: string;
    severity: "info" | "warning" | "critical";
  }> = [];

  for (const pool of selected) {
    const prev = cache.pools.get(pool.pool_id);
    if (prev) {
      const tvlDelta = pctDelta(prev.tvl_usd, pool.tvl_usd);
      const apyDelta = pctDelta(prev.apy, pool.apy);
      deltas.push({
        pool_id: pool.pool_id,
        tvl_delta_pct: tvlDelta,
        apy_delta_pct: apyDelta,
        previous_tvl_usd: prev.tvl_usd,
        previous_apy: prev.apy,
      });

      if (tvlDelta <= -rules.tvl_drop_pct) {
        alerts.push({
          pool_id: pool.pool_id,
          type: "tvl_drop",
          message: `TVL dropped ${Math.abs(tvlDelta).toFixed(2)}% on ${pool.symbol}`,
          severity: tvlDelta <= -rules.tvl_drop_pct * 2 ? "critical" : "warning",
        });
      }
      if (tvlDelta >= rules.tvl_spike_pct) {
        alerts.push({
          pool_id: pool.pool_id,
          type: "tvl_spike",
          message: `TVL spiked ${tvlDelta.toFixed(2)}% on ${pool.symbol}`,
          severity: "info",
        });
      }
      if (apyDelta >= rules.apy_spike_pct) {
        alerts.push({
          pool_id: pool.pool_id,
          type: "apy_spike",
          message: `APY spiked ${apyDelta.toFixed(2)}% on ${pool.symbol}`,
          severity: "warning",
        });
      }
      if (apyDelta <= -rules.apy_drop_pct) {
        alerts.push({
          pool_id: pool.pool_id,
          type: "apy_drop",
          message: `APY dropped ${Math.abs(apyDelta).toFixed(2)}% on ${pool.symbol}`,
          severity: "warning",
        });
      }
    }
    cache.pools.set(pool.pool_id, pool);
  }
  cache.at = Date.now();

  return {
    pool_metrics: selected,
    deltas,
    alerts,
    threshold_rules: rules,
    cache_age_ms: cache.at ? Date.now() - cache.at : 0,
    watched_at: new Date().toISOString(),
  };
}

const inputSchema = z.object({
  protocol_ids: z.array(z.string()).default(["aerodrome", "uniswap", "curve"]),
  pools: z.array(z.string()).default([]),
  threshold_rules: z
    .object({
      tvl_drop_pct: z.number().optional(),
      apy_spike_pct: z.number().optional(),
      apy_drop_pct: z.number().optional(),
      tvl_spike_pct: z.number().optional(),
    })
    .default({}),
});

const payments = paymentsFromEnv({ defaultPrice: "1000" });

const { app, addEntrypoint } = createAgentApp(
  {
    name: "yield-pool-watcher",
    version: "0.1.0",
    description: "Track APY and TVL across pools and alert on sharp changes",
  },
  { payments, useConfigPayments: true },
);

addEntrypoint({
  key: "watch",
  description: "Monitor yield pool APY/TVL and emit threshold alerts",
  input: inputSchema,
  price: "1000",
  async handler({ input }) {
    const output = await watchPools(input);
    return {
      output,
      usage: { alerts: String(output.alerts.length), pools: String(output.pool_metrics.length) },
    };
  },
});

console.log(`yield-pool-watcher listening on http://127.0.0.1:${PORT}`);
serve({ fetch: app.fetch, port: PORT });
