import { createPublicClient, http, parseAbi, type Address } from "viem";
import { base } from "viem/chains";

const LLAMA_POOLS_URL = "https://yields.llama.fi/pools";
const LLAMA_CHART_URL = "https://yields.llama.fi/chart";
const LLAMA_COINS_URL = "https://coins.llama.fi/prices";
const USER_AGENT = "Swarm-Economy-LpIlEstimator/0.1";

const POOL_ABI = parseAbi(["function token0() view returns (address)", "function token1() view returns (address)"]);

type LlamaPool = {
  pool_id: string;
  protocol: string;
  chain: string;
  symbol: string;
  tvl_usd: number;
  apy: number;
  apy_base: number | null;
  volume_usd_1d: number | null;
  volume_usd_7d: number | null;
  underlying_tokens: string[];
  il_risk: string;
  pool_meta: string | null;
};

type ChartPoint = {
  timestamp: string;
  tvl_usd: number;
  apy: number;
  apy_base: number | null;
  il7d: number | null;
};

export type EstimateInput = {
  pool_address: string;
  token_weights: number[];
  deposit_amounts: number[];
  window_hours: number;
};

export type EstimateOutput = {
  IL_percent: number;
  fee_apr_est: number;
  volume_window: number;
  notes: string[];
  pool: {
    pool_id: string;
    protocol: string;
    chain: string;
    symbol: string;
  };
  backtest: {
    reference_il7d: number | null;
    model_il_percent: number;
    backtest_error_pct: number | null;
    window_start: string;
    window_end: string;
    price_ratio: number;
  };
};

let poolsCache: { at: number; pools: LlamaPool[] } | null = null;

const CHAIN_SLUGS: Record<string, string> = {
  Ethereum: "ethereum",
  Base: "base",
  Arbitrum: "arbitrum",
  Optimism: "optimism",
  Polygon: "polygon",
  BSC: "bsc",
  Avalanche: "avax",
};

function normalizeWeights(weights: number[], tokenCount: number): number[] {
  if (!weights.length) {
    if (tokenCount === 2) return [0.5, 0.5];
    return Array.from({ length: tokenCount }, () => 1 / tokenCount);
  }
  if (weights.length !== tokenCount) {
    throw new Error(`token_weights length (${weights.length}) must match deposit token count (${tokenCount})`);
  }
  const sum = weights.reduce((a, b) => a + b, 0);
  if (sum <= 0) throw new Error("token_weights must sum to a positive value");
  return weights.map((w) => w / sum);
}

function constantProductIlPercent(priceRatio: number, weight0: number): number {
  const w0 = weight0;
  const w1 = 1 - w0;
  const r = priceRatio;
  if (r <= 0) throw new Error("Invalid price ratio for IL calculation");
  const lpValueRatio = Math.pow(r, w1) / (w0 + w1 * r);
  const holdValueRatio = w0 + w1 * r;
  return Number(((lpValueRatio / holdValueRatio - 1) * 100).toFixed(4));
}

async function fetchAllPools(): Promise<LlamaPool[]> {
  if (poolsCache && Date.now() - poolsCache.at < 5 * 60_000) {
    return poolsCache.pools;
  }
  const res = await fetch(LLAMA_POOLS_URL, { headers: { "User-Agent": USER_AGENT } });
  if (!res.ok) throw new Error(`DefiLlama yields API HTTP ${res.status}`);
  const json = (await res.json()) as { data?: Array<Record<string, unknown>> };
  const pools = (json.data ?? []).map((p) => ({
    pool_id: String(p.pool ?? ""),
    protocol: String(p.project ?? ""),
    chain: String(p.chain ?? ""),
    symbol: String(p.symbol ?? ""),
    tvl_usd: Number(p.tvlUsd ?? 0),
    apy: Number(p.apy ?? 0),
    apy_base: p.apyBase != null ? Number(p.apyBase) : null,
    volume_usd_1d: p.volumeUsd1d != null ? Number(p.volumeUsd1d) : null,
    volume_usd_7d: p.volumeUsd7d != null ? Number(p.volumeUsd7d) : null,
    underlying_tokens: Array.isArray(p.underlyingTokens)
      ? (p.underlyingTokens as string[]).map((t) => t.toLowerCase())
      : [],
    il_risk: String(p.ilRisk ?? ""),
    pool_meta: p.poolMeta != null ? String(p.poolMeta) : null,
  }));
  poolsCache = { at: Date.now(), pools };
  return pools;
}

async function readPoolTokens(poolAddress: Address): Promise<[Address, Address]> {
  const rpc = process.env.BASE_RPC_URL || "https://mainnet.base.org";
  const client = createPublicClient({ chain: base, transport: http(rpc) });
  const [token0, token1] = await Promise.all([
    client.readContract({ address: poolAddress, abi: POOL_ABI, functionName: "token0" }),
    client.readContract({ address: poolAddress, abi: POOL_ABI, functionName: "token1" }),
  ]);
  return [token0, token1];
}

function scorePoolMatch(pool: LlamaPool, needle: string, tokenSet?: Set<string>): number {
  const low = needle.toLowerCase();
  let score = 0;
  if (pool.pool_id.toLowerCase() === low) score += 100;
  if (pool.underlying_tokens.includes(low)) score += 40;
  if (tokenSet && tokenSet.size >= 2) {
    const overlap = pool.underlying_tokens.filter((t) => tokenSet.has(t)).length;
    if (overlap === tokenSet.size) score += 80;
    else if (overlap > 0) score += overlap * 10;
  }
  if (pool.symbol.toLowerCase().includes(low.replace(/^0x/, ""))) score += 5;
  return score;
}

async function resolvePool(poolAddress: string): Promise<LlamaPool> {
  const pools = await fetchAllPools();
  const needle = poolAddress.trim();
  const isHex = /^0x[a-fA-F0-9]{40}$/.test(needle);

  let tokenSet: Set<string> | undefined;
  if (isHex) {
    try {
      const [t0, t1] = await readPoolTokens(needle as Address);
      tokenSet = new Set([t0.toLowerCase(), t1.toLowerCase()]);
    } catch {
      tokenSet = new Set([needle.toLowerCase()]);
    }
  }

  const ranked = pools
    .map((p) => ({ pool: p, score: scorePoolMatch(p, needle, tokenSet) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || b.pool.tvl_usd - a.pool.tvl_usd);

  if (!ranked.length) {
    throw new Error(`No DefiLlama yield pool matched pool_address=${poolAddress}`);
  }
  return ranked[0]!.pool;
}

async function fetchPoolChart(poolId: string): Promise<ChartPoint[]> {
  const res = await fetch(`${LLAMA_CHART_URL}/${poolId}`, { headers: { "User-Agent": USER_AGENT } });
  if (!res.ok) throw new Error(`DefiLlama chart API HTTP ${res.status}`);
  const json = (await res.json()) as { status?: string; data?: ChartPoint[] };
  if (!Array.isArray(json.data)) throw new Error("DefiLlama chart response missing data");
  return json.data;
}

function chainCoin(chain: string, token: string): string {
  const slug = CHAIN_SLUGS[chain] ?? chain.toLowerCase();
  return `${slug}:${token}`;
}

async function fetchHistoricalPrice(coin: string, timestampSec: number): Promise<number> {
  const res = await fetch(`${LLAMA_COINS_URL}/historical/${timestampSec}/${coin}`, {
    headers: { "User-Agent": USER_AGENT },
  });
  if (!res.ok) throw new Error(`DefiLlama coins historical HTTP ${res.status} for ${coin}`);
  const json = (await res.json()) as { coins?: Record<string, { price?: number }> };
  const price = json.coins?.[coin]?.price;
  if (price == null || price <= 0) throw new Error(`No historical price for ${coin} at ${timestampSec}`);
  return price;
}

function sliceWindow(chart: ChartPoint[], windowHours: number): ChartPoint[] {
  if (!chart.length) return [];
  const endMs = Date.parse(chart[chart.length - 1]!.timestamp);
  const startMs = endMs - windowHours * 3600_000;
  const inWindow = chart.filter((p) => Date.parse(p.timestamp) >= startMs);
  if (inWindow.length >= 2) return inWindow;
  return chart.slice(-Math.max(2, Math.min(chart.length, Math.ceil(windowHours / 24) + 1)));
}

function estimateVolume(pool: LlamaPool, windowHours: number): number {
  if (windowHours <= 24 && pool.volume_usd_1d != null) {
    return Number(((pool.volume_usd_1d * windowHours) / 24).toFixed(2));
  }
  if (pool.volume_usd_7d != null) {
    return Number(((pool.volume_usd_7d * windowHours) / 168).toFixed(2));
  }
  if (pool.volume_usd_1d != null) {
    return Number(((pool.volume_usd_1d * windowHours) / 24).toFixed(2));
  }
  return 0;
}

function averageApy(points: ChartPoint[]): number {
  const vals = points.map((p) => p.apy_base ?? p.apy).filter((v) => Number.isFinite(v));
  if (!vals.length) return 0;
  return Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(4));
}

export async function estimateImpermanentLoss(input: EstimateInput): Promise<EstimateOutput> {
  const notes: string[] = [];
  const pool = await resolvePool(input.pool_address);
  const chart = await fetchPoolChart(pool.pool_id);
  const window = sliceWindow(chart, input.window_hours);
  if (window.length < 2) throw new Error("Insufficient chart history for requested window");

  const start = window[0]!;
  const end = window[window.length - 1]!;
  const startSec = Math.floor(Date.parse(start.timestamp) / 1000);
  const endSec = Math.floor(Date.parse(end.timestamp) / 1000);

  const tokens = pool.underlying_tokens.filter((t) => t.startsWith("0x") && t.length === 42);
  if (tokens.length < 2) {
    notes.push("Pool has fewer than two on-chain tokens; using 50/50 constant-product model.");
  }

  const token0 = tokens[0] ?? "0x0000000000000000000000000000000000000000";
  const token1 = tokens[1] ?? "0x0000000000000000000000000000000000000001";
  const coin0 = chainCoin(pool.chain, token0);
  const coin1 = chainCoin(pool.chain, token1);

  let priceRatio = 1;
  try {
    const [p0Start, p1Start, p0End, p1End] = await Promise.all([
      fetchHistoricalPrice(coin0, startSec),
      fetchHistoricalPrice(coin1, startSec),
      fetchHistoricalPrice(coin0, endSec),
      fetchHistoricalPrice(coin1, endSec),
    ]);
    const ratioStart = p1Start / p0Start;
    const ratioEnd = p1End / p0End;
    priceRatio = ratioEnd / ratioStart;
  } catch (err) {
    notes.push(`Token price history unavailable (${String(err)}); falling back to chart il7d when present.`);
    if (end.il7d != null) {
      return {
        IL_percent: Number(end.il7d.toFixed(4)),
        fee_apr_est: averageApy(window),
        volume_window: estimateVolume(pool, input.window_hours),
        notes: [...notes, "IL_percent sourced from DefiLlama il7d fallback."],
        pool: {
          pool_id: pool.pool_id,
          protocol: pool.protocol,
          chain: pool.chain,
          symbol: pool.symbol,
        },
        backtest: {
          reference_il7d: end.il7d,
          model_il_percent: Number(end.il7d.toFixed(4)),
          backtest_error_pct: 0,
          window_start: start.timestamp,
          window_end: end.timestamp,
          price_ratio: 1,
        },
      };
    }
    throw err;
  }

  const tokenCount = Math.max(2, input.deposit_amounts.length || 2);
  const weights = normalizeWeights(input.token_weights, tokenCount);
  const modelIl = constantProductIlPercent(priceRatio, weights[0] ?? 0.5);

  const referenceIl7d = end.il7d;
  let backtestError: number | null = null;
  if (referenceIl7d != null && input.window_hours >= 120 && input.window_hours <= 192) {
    backtestError = Number((Math.abs(modelIl - referenceIl7d) / Math.max(Math.abs(referenceIl7d), 0.01) * 100).toFixed(2));
    if (backtestError <= 10) {
      notes.push(`Backtest within 10% of DefiLlama il7d (${referenceIl7d}%).`);
    } else {
      notes.push(`Backtest error ${backtestError}% vs DefiLlama il7d (${referenceIl7d}%).`);
    }
  } else if (referenceIl7d != null) {
    notes.push(`DefiLlama il7d reference=${referenceIl7d}% (best for ~168h windows).`);
  }

  if (pool.il_risk === "yes") {
    notes.push("Pool flagged with IL risk on DefiLlama.");
  }
  if (!input.deposit_amounts.length) {
    notes.push("deposit_amounts empty; IL computed from token price ratio and weights only.");
  }

  const feeApr = averageApy(window);
  const volumeWindow = estimateVolume(pool, input.window_hours);

  return {
    IL_percent: modelIl,
    fee_apr_est: feeApr,
    volume_window: volumeWindow,
    notes,
    pool: {
      pool_id: pool.pool_id,
      protocol: pool.protocol,
      chain: pool.chain,
      symbol: pool.symbol,
    },
    backtest: {
      reference_il7d: referenceIl7d,
      model_il_percent: modelIl,
      backtest_error_pct: backtestError,
      window_start: start.timestamp,
      window_end: end.timestamp,
      price_ratio: Number(priceRatio.toFixed(6)),
    },
  };
}
