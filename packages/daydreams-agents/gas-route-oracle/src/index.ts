import { serve } from "@hono/node-server";
import { createAgentApp, paymentsFromEnv } from "@lucid-dreams/agent-kit";
import {
  createPublicClient,
  formatEther,
  formatGwei,
  http,
  type PublicClient,
} from "viem";
import { arbitrum, base, baseSepolia, optimism, polygon } from "viem/chains";
import { z } from "zod";

const PORT = Number(process.env.PORT || process.env.GAS_ROUTE_ORACLE_PORT || 8093);

const CHAINS = {
  base,
  "base-sepolia": baseSepolia,
  optimism,
  arbitrum,
  polygon,
} as const;

type ChainKey = keyof typeof CHAINS;

const RPC_URLS: Record<ChainKey, string> = {
  base: process.env.BASE_RPC_URL || "https://mainnet.base.org",
  "base-sepolia": process.env.BASE_SEPOLIA_RPC_URL || "https://sepolia.base.org",
  optimism: process.env.OPTIMISM_RPC_URL || "https://mainnet.optimism.io",
  arbitrum: process.env.ARBITRUM_RPC_URL || "https://arb1.arbitrum.io/rpc",
  polygon: process.env.POLYGON_RPC_URL || "https://polygon-rpc.com",
};

const NATIVE_USD: Record<ChainKey, number> = {
  base: Number(process.env.ETH_USD_PRICE || 3500),
  "base-sepolia": Number(process.env.ETH_USD_PRICE || 3500),
  optimism: Number(process.env.ETH_USD_PRICE || 3500),
  arbitrum: Number(process.env.ETH_USD_PRICE || 3500),
  polygon: Number(process.env.MATIC_USD_PRICE || 0.45),
};

const BASELINE_GWEI: Record<ChainKey, number> = {
  base: 0.05,
  "base-sepolia": 0.01,
  optimism: 0.02,
  arbitrum: 0.05,
  polygon: 30,
};

function clientFor(chain: ChainKey): PublicClient {
  return createPublicClient({
    chain: CHAINS[chain],
    transport: http(RPC_URLS[chain]),
  });
}

function busyLevel(gwei: number, baseline: number): "low" | "medium" | "high" {
  const ratio = baseline > 0 ? gwei / baseline : 1;
  if (ratio <= 1.25) return "low";
  if (ratio <= 2.5) return "medium";
  return "high";
}

async function quoteChain(input: {
  chain: ChainKey;
  calldata_size_bytes: number;
  gas_units_est: bigint;
}) {
  const client = clientFor(input.chain);
  const fees = await client.estimateFeesPerGas();
  const gasPrice = fees.maxFeePerGas ?? fees.gasPrice ?? 0n;
  const priority = fees.maxPriorityFeePerGas ?? 0n;
  const calldataGas = BigInt(Math.max(0, input.calldata_size_bytes)) * 16n;
  const totalGas = input.gas_units_est + calldataGas;
  const feeWei = totalGas * gasPrice;
  const gwei = Number(formatGwei(gasPrice));
  const native = Number(formatEther(feeWei));
  const usd = native * NATIVE_USD[input.chain];

  return {
    chain: input.chain,
    fee_native: formatEther(feeWei),
    fee_usd: Number(usd.toFixed(4)),
    busy_level: busyLevel(gwei, BASELINE_GWEI[input.chain]),
    tip_hint: formatGwei(priority > 0n ? priority : gasPrice / 10n),
    diagnostics: {
      gas_price_gwei: gwei,
      total_gas_units: totalGas.toString(),
      max_fee_per_gas: gasPrice.toString(),
      calldata_gas: calldataGas.toString(),
    },
  };
}

async function pickBestRoute(input: {
  chain_set: ChainKey[];
  calldata_size_bytes: number;
  gas_units_est: bigint;
}) {
  const quotes = await Promise.all(
    input.chain_set.map((chain) =>
      quoteChain({
        chain,
        calldata_size_bytes: input.calldata_size_bytes,
        gas_units_est: input.gas_units_est,
      }),
    ),
  );
  quotes.sort((a, b) => a.fee_usd - b.fee_usd);
  const best = quotes[0];
  if (!best) {
    throw new Error("No chains could be quoted");
  }
  return {
    ...best,
    alternatives: quotes.slice(1),
    quoted_at: new Date().toISOString(),
  };
}

const inputSchema = z.object({
  chain_set: z
    .array(z.enum(["base", "base-sepolia", "optimism", "arbitrum", "polygon"]))
    .min(1)
    .default(["base", "optimism", "arbitrum"]),
  calldata_size_bytes: z.number().int().min(0).max(1_000_000).default(0),
  gas_units_est: z.union([z.string(), z.number()]).default(150_000),
});

const payments = paymentsFromEnv({ defaultPrice: "1000" });

const { app, addEntrypoint } = createAgentApp(
  {
    name: "gasroute-oracle",
    version: "0.1.0",
    description: "Choose cheapest chain and timing hint for swaps or contract calls",
  },
  { payments, useConfigPayments: true },
);

addEntrypoint({
  key: "route",
  description: "Return best chain and fee estimate for a given gas load",
  input: inputSchema,
  price: "1000",
  async handler({ input }) {
    const gasUnits =
      typeof input.gas_units_est === "number"
        ? BigInt(Math.floor(input.gas_units_est))
        : BigInt(input.gas_units_est);
    const output = await pickBestRoute({
      chain_set: input.chain_set as ChainKey[],
      calldata_size_bytes: input.calldata_size_bytes,
      gas_units_est: gasUnits,
    });
    return {
      output,
      usage: { chain: output.chain, fee_usd: String(output.fee_usd) },
    };
  },
});

console.log(`gas-route-oracle listening on http://127.0.0.1:${PORT}`);
serve({ fetch: app.fetch, port: PORT });
