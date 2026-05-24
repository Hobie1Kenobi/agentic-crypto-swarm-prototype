import { serve } from "@hono/node-server";
import { createAgentApp, paymentsFromEnv } from "@lucid-dreams/agent-kit";
import {
  type Address,
  createPublicClient,
  encodeFunctionData,
  formatUnits,
  http,
  maxUint256,
  parseAbi,
  parseAbiItem,
  type PublicClient,
} from "viem";
import { arbitrum, base, baseSepolia, optimism, polygon } from "viem/chains";
import { z } from "zod";

const PORT = Number(process.env.PORT || process.env.APPROVAL_RISK_AUDITOR_PORT || 8095);

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

const STALE_DAYS = Number(process.env.APPROVAL_STALE_DAYS || 180);
const BLOCKS_BACK = BigInt(Number(process.env.APPROVAL_SCAN_BLOCKS || 2_000_000));

const erc20Abi = parseAbi([
  "function allowance(address owner, address spender) view returns (uint256)",
  "function approve(address spender, uint256 amount) returns (bool)",
  "function symbol() view returns (string)",
  "function decimals() view returns (uint8)",
]);

const approvalEvent = parseAbiItem(
  "event Approval(address indexed owner, address indexed spender, uint256 value)",
);

function clientFor(chain: ChainKey): PublicClient {
  return createPublicClient({
    chain: CHAINS[chain],
    transport: http(RPC_URLS[chain]),
  });
}

function isUnlimited(amount: bigint): boolean {
  return amount >= maxUint256 / 2n;
}

type ApprovalRow = {
  chain: ChainKey;
  token: Address;
  spender: Address;
  allowance: string;
  symbol: string | null;
  decimals: number;
  last_block: string;
  last_seen_at: string;
};

async function scanChain(chain: ChainKey, wallet: Address): Promise<ApprovalRow[]> {
  const client = clientFor(chain);
  const latest = await client.getBlockNumber();
  const fromBlock = latest > BLOCKS_BACK ? latest - BLOCKS_BACK : 0n;

  const logs = await client.getLogs({
    event: approvalEvent,
    args: { owner: wallet },
    fromBlock,
    toBlock: latest,
  });

  const latestByKey = new Map<string, (typeof logs)[number]>();
  for (const log of logs) {
    const token = log.address.toLowerCase();
    const spender = String(log.args.spender).toLowerCase();
    const key = `${token}:${spender}`;
    const prev = latestByKey.get(key);
    if (!prev || (log.blockNumber ?? 0n) >= (prev.blockNumber ?? 0n)) {
      latestByKey.set(key, log);
    }
  }

  const rows: ApprovalRow[] = [];
  for (const log of latestByKey.values()) {
    const token = log.address;
    const spender = log.args.spender as Address;
    let allowance = 0n;
    let symbol: string | null = null;
    let decimals = 18;
    try {
      allowance = (await client.readContract({
        address: token,
        abi: erc20Abi,
        functionName: "allowance",
        args: [wallet, spender],
      })) as bigint;
      if (allowance === 0n) continue;
      symbol = (await client.readContract({
        address: token,
        abi: erc20Abi,
        functionName: "symbol",
      })) as string;
      decimals = Number(
        await client.readContract({
          address: token,
          abi: erc20Abi,
          functionName: "decimals",
        }),
      );
    } catch {
      continue;
    }

    const block = await client.getBlock({ blockNumber: log.blockNumber! });
    rows.push({
      chain,
      token,
      spender,
      allowance: allowance.toString(),
      symbol,
      decimals,
      last_block: log.blockNumber!.toString(),
      last_seen_at: new Date(Number(block.timestamp) * 1000).toISOString(),
    });
  }
  return rows;
}

function riskFlags(row: ApprovalRow, nowSec: number) {
  const allowance = BigInt(row.allowance);
  const flags: string[] = [];
  if (isUnlimited(allowance)) flags.push("unlimited");
  const ageDays = (nowSec - Date.parse(row.last_seen_at) / 1000) / 86400;
  if (ageDays >= STALE_DAYS) flags.push("stale");
  if (allowance > 0n && !isUnlimited(allowance)) {
    const human = Number(formatUnits(allowance, row.decimals));
    if (human > 1_000_000) flags.push("high_allowance");
  }
  return flags;
}

function revokeTxData(row: ApprovalRow) {
  const data = encodeFunctionData({
    abi: erc20Abi,
    functionName: "approve",
    args: [row.spender, 0n],
  });
  return {
    chain: row.chain,
    to: row.token,
    data,
    value: "0",
  };
}

async function auditWallet(wallet: Address, chains: ChainKey[]) {
  const nowSec = Math.floor(Date.now() / 1000);
  const allRows = (
    await Promise.all(chains.map((chain) => scanChain(chain, wallet)))
  ).flat();

  const approvals = allRows.map((row) => ({
    chain: row.chain,
    token: row.token,
    spender: row.spender,
    symbol: row.symbol,
    allowance: row.allowance,
    allowance_human: formatUnits(BigInt(row.allowance), row.decimals),
    last_block: row.last_block,
    last_seen_at: row.last_seen_at,
  }));

  const risk_flags = allRows.map((row) => ({
    token: row.token,
    spender: row.spender,
    chain: row.chain,
    flags: riskFlags(row, nowSec),
  }));

  const risky = risk_flags.filter((r) => r.flags.length > 0);
  const revoke_tx_data = allRows
    .filter((row) => riskFlags(row, nowSec).length > 0)
    .map(revokeTxData);

  return {
    wallet,
    chains,
    approvals,
    risk_flags: risky,
    revoke_tx_data,
    summary: {
      total_approvals: approvals.length,
      risky_count: risky.length,
      scanned_at: new Date().toISOString(),
    },
  };
}

const inputSchema = z.object({
  wallet: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
  chains: z
    .array(z.enum(["base", "base-sepolia", "optimism", "arbitrum", "polygon"]))
    .min(1)
    .default(["base"]),
});

const payments = paymentsFromEnv({ defaultPrice: "1000" });

const { app, addEntrypoint } = createAgentApp(
  {
    name: "approval-risk-auditor",
    version: "0.1.0",
    description: "Flag unlimited or stale ERC-20 approvals and build revoke calls",
  },
  { payments, useConfigPayments: true },
);

addEntrypoint({
  key: "audit",
  description: "Scan wallet token approvals and return risk flags plus revoke calldata",
  input: inputSchema,
  price: "1000",
  async handler({ input }) {
    const output = await auditWallet(input.wallet as Address, input.chains as ChainKey[]);
    return {
      output,
      usage: { risky_count: String(output.summary.risky_count) },
    };
  },
});

console.log(`approval-risk-auditor listening on http://127.0.0.1:${PORT}`);
serve({ fetch: app.fetch, port: PORT });
