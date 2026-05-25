import {
  type Address,
  createPublicClient,
  formatUnits,
  http,
  parseAbi,
  type PublicClient,
} from "viem";
import { base, baseSepolia } from "viem/chains";

export const CHAINS = { base, "base-sepolia": baseSepolia } as const;
export type ChainKey = keyof typeof CHAINS;

export type DexVenue = { name: string; factory: Address };

export const DEX_VENUES: Record<ChainKey, DexVenue[]> = {
  base: [
    { name: "baseswap-v2", factory: "0x8909Dc15e40173Ff669927a763452D721Db57087" },
    { name: "sushiswap-v2", factory: "0x71524B4f93c576FC86F4088CB1D148856573AE57" },
    { name: "pancakeswap-v2", factory: "0x02a84f1d3E738Fe2c47CB093Bc0aab1A40BEE852" },
  ],
  "base-sepolia": [
    { name: "uniswap-v2", factory: "0x4752ba5dbc23f44D87826276BF6Fd889b372c1C19" },
  ],
};

const factoryAbi = parseAbi([
  "function getPair(address tokenA, address tokenB) view returns (address pair)",
]);

const pairAbi = parseAbi([
  "function getReserves() view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)",
  "function token0() view returns (address)",
]);

export function clientFor(chain: ChainKey): PublicClient {
  const rpc =
    chain === "base"
      ? process.env.BASE_RPC_URL || "https://mainnet.base.org"
      : process.env.BASE_SEPOLIA_RPC_URL || "https://sepolia.base.org";
  return createPublicClient({ chain: CHAINS[chain], transport: http(rpc) });
}

export function v2AmountOut(amountIn: bigint, reserveIn: bigint, reserveOut: bigint): bigint {
  if (amountIn <= 0n || reserveIn <= 0n || reserveOut <= 0n) return 0n;
  const amountInWithFee = amountIn * 997n;
  const numerator = amountInWithFee * reserveOut;
  const denominator = reserveIn * 1000n + amountInWithFee;
  return numerator / denominator;
}

export async function quoteV2Swap(
  client: PublicClient,
  factory: Address,
  tokenIn: Address,
  tokenOut: Address,
  amountIn: bigint,
): Promise<{ pair: Address; amountOut: bigint; reserveIn: bigint; reserveOut: bigint } | null> {
  const pair = (await client.readContract({
    address: factory,
    abi: factoryAbi,
    functionName: "getPair",
    args: [tokenIn, tokenOut],
  })) as Address;
  if (!pair || pair === "0x0000000000000000000000000000000000000000") return null;
  const code = await client.getBytecode({ address: pair });
  if (!code || code === "0x") return null;

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
  const tokenInIsToken0 = token0.toLowerCase() === tokenIn.toLowerCase();
  const reserveIn = tokenInIsToken0 ? reserve0 : reserve1;
  const reserveOut = tokenInIsToken0 ? reserve1 : reserve0;
  const amountOut = v2AmountOut(amountIn, reserveIn, reserveOut);
  if (amountOut <= 0n) return null;
  return { pair, amountOut, reserveIn, reserveOut };
}

export function spreadBps(best: bigint, reference: bigint): number {
  if (reference <= 0n || best <= reference) return 0;
  return Math.floor(Number(((best - reference) * 10_000n) / reference));
}

export function gasCostBps(gasCostWei: bigint, notionalWei: bigint): number {
  if (notionalWei <= 0n) return 0;
  return Math.ceil(Number((gasCostWei * 10_000n) / notionalWei));
}

export function formatAmount(amount: bigint, decimals = 18): string {
  return formatUnits(amount, decimals);
}
