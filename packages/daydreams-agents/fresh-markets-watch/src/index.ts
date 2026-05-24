import { serve } from "@hono/node-server";
import { createAgentApp, paymentsFromEnv } from "@lucid-dreams/agent-kit";
import {
  type Address,
  createPublicClient,
  http,
  parseAbiItem,
  type PublicClient,
} from "viem";
import { base, baseSepolia } from "viem/chains";
import { z } from "zod";

const PORT = Number(process.env.PORT || process.env.FRESH_MARKETS_PORT || 8091);

const DEFAULT_FACTORIES: Record<string, Address[]> = {
  base: ["0x8909Dc15e40173Ff669927a763452D721Db57087"],
  "base-sepolia": ["0x4752ba5dbc23f44D87826276BF6Fd889b372c1C19"],
};

const CHAINS = {
  base,
  "base-sepolia": baseSepolia,
} as const;

const pairCreatedEvent = parseAbiItem(
  "event PairCreated(address indexed token0, address indexed token1, address pair, uint256)",
);

const reserveAbi = [
  {
    type: "function",
    name: "getReserves",
    stateMutability: "view",
    inputs: [],
    outputs: [
      { name: "reserve0", type: "uint112" },
      { name: "reserve1", type: "uint112" },
      { name: "blockTimestampLast", type: "uint32" },
    ],
  },
] as const;

function clientFor(chain: keyof typeof CHAINS): PublicClient {
  const rpc =
    chain === "base"
      ? process.env.BASE_RPC_URL || "https://mainnet.base.org"
      : process.env.BASE_SEPOLIA_RPC_URL || "https://sepolia.base.org";
  return createPublicClient({ chain: CHAINS[chain], transport: http(rpc) });
}

async function hasContractCode(client: PublicClient, address: Address): Promise<boolean> {
  const code = await client.getBytecode({ address });
  return Boolean(code && code !== "0x");
}

async function readInitLiquidity(
  client: PublicClient,
  pair: Address,
): Promise<string | null> {
  try {
    const reserves = await client.readContract({
      address: pair,
      abi: reserveAbi,
      functionName: "getReserves",
    });
    const [r0, r1] = reserves;
    return `${r0.toString()},${r1.toString()}`;
  } catch {
    return null;
  }
}

async function topHoldersPlaceholder(pair: Address): Promise<string[]> {
  return [pair];
}

async function scanPairs(input: {
  chain: keyof typeof CHAINS;
  factories: Address[];
  window_minutes: number;
}) {
  const client = clientFor(input.chain);
  const latest = await client.getBlockNumber();
  const blockTimeSec = input.chain === "base" ? 2 : 2;
  const blocksBack = BigInt(Math.max(10, Math.ceil((input.window_minutes * 60) / blockTimeSec)));
  const fromBlock = latest > blocksBack ? latest - blocksBack : 0n;

  const results: Array<{
    pair_address: Address;
    tokens: [Address, Address];
    init_liquidity: string | null;
    top_holders: string[];
    created_at: string;
    factory: Address;
  }> = [];

  for (const factory of input.factories) {
    if (!(await hasContractCode(client, factory))) {
      continue;
    }
    const logs = await client.getLogs({
      address: factory,
      event: pairCreatedEvent,
      fromBlock,
      toBlock: latest,
    });

    for (const log of logs) {
      const token0 = log.args.token0 as Address;
      const token1 = log.args.token1 as Address;
      const pair = log.args.pair as Address;
      if (!pair || !(await hasContractCode(client, pair))) {
        continue;
      }
      const block = await client.getBlock({ blockNumber: log.blockNumber });
      const initLiquidity = await readInitLiquidity(client, pair);
      results.push({
        pair_address: pair,
        tokens: [token0, token1],
        init_liquidity: initLiquidity,
        top_holders: await topHoldersPlaceholder(pair),
        created_at: new Date(Number(block.timestamp) * 1000).toISOString(),
        factory,
      });
    }
  }

  results.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
  return {
    chain: input.chain,
    window_minutes: input.window_minutes,
    from_block: fromBlock.toString(),
    to_block: latest.toString(),
    pairs: results,
  };
}

const inputSchema = z.object({
  chain: z.enum(["base", "base-sepolia"]).default("base"),
  factories: z.array(z.string().regex(/^0x[a-fA-F0-9]{40}$/)).optional(),
  window_minutes: z.number().int().min(1).max(1440).default(30),
});

const payments = paymentsFromEnv({ defaultPrice: "1000" });

const { app, addEntrypoint } = createAgentApp(
  {
    name: "fresh-markets-watch",
    version: "0.1.0",
    description: "List new AMM pairs or pools created within the last N minutes",
  },
  { payments, useConfigPayments: true },
);

addEntrypoint({
  key: "scan",
  description: "Scan AMM factory contracts for newly created pairs in a time window",
  input: inputSchema,
  price: "1000",
  async handler({ input }) {
    const chain = input.chain as keyof typeof CHAINS;
    const factories = (input.factories?.length
      ? input.factories
      : DEFAULT_FACTORIES[chain] || []) as Address[];
    if (!factories.length) {
      throw new Error(`No factories configured for chain ${chain}`);
    }
    const output = await scanPairs({
      chain,
      factories,
      window_minutes: input.window_minutes,
    });
    return {
      output,
      usage: { pairs_found: String(output.pairs.length) },
    };
  },
});

console.log(`fresh-markets-watch listening on http://127.0.0.1:${PORT}`);
serve({ fetch: app.fetch, port: PORT });
