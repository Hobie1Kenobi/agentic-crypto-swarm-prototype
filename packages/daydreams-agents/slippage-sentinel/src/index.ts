import { serve } from "@hono/node-server";
import { createAgentApp, paymentsFromEnv } from "@lucid-dreams/agent-kit";
import {
  type Address,
  createPublicClient,
  formatUnits,
  http,
  parseAbi,
  parseAbiItem,
  type PublicClient,
} from "viem";
import { base, baseSepolia } from "viem/chains";
import { z } from "zod";

const PORT = Number(process.env.PORT || process.env.SLIPPAGE_SENTINEL_PORT || 8092);

const CHAINS = { base, "base-sepolia": baseSepolia } as const;

const DEFAULT_FACTORIES: Record<keyof typeof CHAINS, Address> = {
  base: "0x8909Dc15e40173Ff669927a763452D721Db57087",
  "base-sepolia": "0x4752ba5dbc23f44D87826276BF6Fd889b372c1C19",
};

const factoryAbi = parseAbi([
  "function getPair(address tokenA, address tokenB) view returns (address pair)",
]);

const pairAbi = parseAbi([
  "function getReserves() view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)",
  "function token0() view returns (address)",
  "function token1() view returns (address)",
]);

const swapEvent = parseAbiItem(
  "event Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)",
);

function clientFor(chain: keyof typeof CHAINS): PublicClient {
  const rpc =
    chain === "base"
      ? process.env.BASE_RPC_URL || "https://mainnet.base.org"
      : process.env.BASE_SEPOLIA_RPC_URL || "https://sepolia.base.org";
  return createPublicClient({ chain: CHAINS[chain], transport: http(rpc) });
}

function percentile(values: number[], p: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[Math.max(0, idx)] ?? 0;
}

function v2AmountOut(
  amountIn: bigint,
  reserveIn: bigint,
  reserveOut: bigint,
): bigint {
  if (amountIn <= 0n || reserveIn <= 0n || reserveOut <= 0n) return 0n;
  const amountInWithFee = amountIn * 997n;
  const numerator = amountInWithFee * reserveOut;
  const denominator = reserveIn * 1000n + amountInWithFee;
  return numerator / denominator;
}

function bpsFromImpact(amountIn: bigint, spotOut: bigint, actualOut: bigint): number {
  if (spotOut <= 0n || actualOut <= 0n || amountIn <= 0n) return 500;
  const impact = Number(spotOut - actualOut) / Number(spotOut);
  return Math.max(0, Math.ceil(impact * 10_000));
}

async function resolvePair(
  client: PublicClient,
  factory: Address,
  tokenIn: Address,
  tokenOut: Address,
): Promise<Address | null> {
  const pair = (await client.readContract({
    address: factory,
    abi: factoryAbi,
    functionName: "getPair",
    args: [tokenIn, tokenOut],
  })) as Address;
  if (!pair || pair === "0x0000000000000000000000000000000000000000") return null;
  const code = await client.getBytecode({ address: pair });
  return code && code !== "0x" ? pair : null;
}

async function recentSwapSizes(
  client: PublicClient,
  pair: Address,
  tokenIn: Address,
  blocksBack: bigint,
): Promise<number[]> {
  const latest = await client.getBlockNumber();
  const fromBlock = latest > blocksBack ? latest - blocksBack : 0n;
  const token0 = (await client.readContract({
    address: pair,
    abi: pairAbi,
    functionName: "token0",
  })) as Address;
  const tokenInIsToken0 = token0.toLowerCase() === tokenIn.toLowerCase();

  const logs = await client.getLogs({
    address: pair,
    event: swapEvent,
    fromBlock,
    toBlock: latest,
  });

  const sizes: number[] = [];
  for (const log of logs) {
    const amountIn = tokenInIsToken0
      ? (log.args.amount0In as bigint)
      : (log.args.amount1In as bigint);
    if (amountIn > 0n) {
      sizes.push(Number(formatUnits(amountIn, 18)));
    }
  }
  return sizes;
}

async function estimateSlippage(input: {
  chain: keyof typeof CHAINS;
  token_in: Address;
  token_out: Address;
  amount_in: bigint;
  route_hint?: string;
}) {
  const client = clientFor(input.chain);
  const factory =
    (input.route_hint?.match(/^0x[a-fA-F0-9]{40}$/)?.[0] as Address | undefined) ||
    DEFAULT_FACTORIES[input.chain];

  const pair = await resolvePair(client, factory, input.token_in, input.token_out);
  if (!pair) {
    throw new Error(`No V2 pair found for ${input.token_in} / ${input.token_out} on ${input.chain}`);
  }

  const [reserve0, reserve1] = await client.readContract({
    address: pair,
    abi: pairAbi,
    functionName: "getReserves",
  });
  const token0 = (await client.readContract({
    address: pair,
    abi: pairAbi,
    functionName: "token0",
  })) as Address;
  const tokenInIsToken0 = token0.toLowerCase() === input.token_in.toLowerCase();
  const reserveIn = tokenInIsToken0 ? reserve0 : reserve1;
  const reserveOut = tokenInIsToken0 ? reserve1 : reserve0;

  const amountOut = v2AmountOut(input.amount_in, reserveIn, reserveOut);
  const spotNumerator = input.amount_in * reserveOut;
  const spotOut = reserveIn > 0n ? spotNumerator / reserveIn : 0n;
  const impactBps = bpsFromImpact(input.amount_in, spotOut, amountOut);

  const swapSizes = await recentSwapSizes(client, pair, input.token_in, 5000n);
  const p95 = percentile(swapSizes, 95);
  const amountInFloat = Number(formatUnits(input.amount_in, 18));
  const sizeRatio = p95 > 0 ? amountInFloat / p95 : 1;
  const volatilityBuffer = Math.min(300, Math.ceil(sizeRatio * 50));

  const minSafeSlipBps = Math.min(3000, impactBps + volatilityBuffer + 30);

  return {
    chain: input.chain,
    route_hint: input.route_hint || factory,
    pair,
    min_safe_slip_bps: minSafeSlipBps,
    pool_depths: {
      reserve_in: reserveIn.toString(),
      reserve_out: reserveOut.toString(),
      token_in: input.token_in,
      token_out: input.token_out,
    },
    recent_trade_size_p95: p95,
    diagnostics: {
      price_impact_bps: impactBps,
      volatility_buffer_bps: volatilityBuffer,
      expected_amount_out: amountOut.toString(),
      sample_swaps: swapSizes.length,
    },
  };
}

const inputSchema = z.object({
  chain: z.enum(["base", "base-sepolia"]).default("base"),
  token_in: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
  token_out: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
  amount_in: z.union([z.string(), z.number()]),
  route_hint: z.string().optional(),
});

const payments = paymentsFromEnv({ defaultPrice: "1000" });

const { app, addEntrypoint } = createAgentApp(
  {
    name: "slippage-sentinel",
    version: "0.1.0",
    description: "Estimate safe slippage tolerance for a swap route",
  },
  { payments, useConfigPayments: true },
);

addEntrypoint({
  key: "estimate",
  description: "Suggest minimum safe slippage (bps) for a token swap route",
  input: inputSchema,
  price: "1000",
  async handler({ input }) {
    const amountIn =
      typeof input.amount_in === "number"
        ? BigInt(Math.floor(input.amount_in * 1e18))
        : BigInt(input.amount_in);
    const output = await estimateSlippage({
      chain: input.chain as keyof typeof CHAINS,
      token_in: input.token_in as Address,
      token_out: input.token_out as Address,
      amount_in: amountIn,
      route_hint: input.route_hint,
    });
    return {
      output,
      usage: { min_safe_slip_bps: String(output.min_safe_slip_bps) },
    };
  },
});

console.log(`slippage-sentinel listening on http://127.0.0.1:${PORT}`);
serve({ fetch: app.fetch, port: PORT });
