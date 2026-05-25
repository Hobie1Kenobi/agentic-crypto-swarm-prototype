import { serve } from "@hono/node-server";
import { createAgentApp, paymentsFromEnv } from "@lucid-dreams/agent-kit";
import { type Address } from "viem";
import { z } from "zod";
import {
  type ChainKey,
  clientFor,
  DEX_VENUES,
  formatAmount,
  gasCostBps,
  quoteV2Swap,
  spreadBps,
} from "./dex.js";

const PORT = Number(
  process.env.PORT || process.env.CROSS_DEX_ARBITRAGE_PORT || 8104,
);

const DEX_FEE_BPS_PER_SWAP = 30;
const ARB_SWAP_COUNT = 2;

type RouteQuote = {
  chain: ChainKey;
  dex: string;
  factory: Address;
  pair: Address;
  amount_in: string;
  amount_out: string;
  price_impact_bps: number;
};

async function scanCrossDex(input: {
  token_in: Address;
  token_out: Address;
  amount_in: bigint;
  chains: ChainKey[];
  min_net_spread_bps: number;
}) {
  const routes: RouteQuote[] = [];

  for (const chain of input.chains) {
    const client = clientFor(chain);
    for (const venue of DEX_VENUES[chain]) {
      const quote = await quoteV2Swap(
        client,
        venue.factory,
        input.token_in,
        input.token_out,
        input.amount_in,
      );
      if (!quote) continue;

      const spotNumerator = input.amount_in * quote.reserveOut;
      const spotOut = quote.reserveIn > 0n ? spotNumerator / quote.reserveIn : 0n;
      const impactBps =
        spotOut > 0n
          ? Math.max(0, Math.ceil(Number(((spotOut - quote.amountOut) * 10_000n) / spotOut)))
          : 0;

      routes.push({
        chain,
        dex: venue.name,
        factory: venue.factory,
        pair: quote.pair,
        amount_in: input.amount_in.toString(),
        amount_out: quote.amountOut.toString(),
        price_impact_bps: impactBps,
      });
    }
  }

  routes.sort((a, b) => (BigInt(b.amount_out) > BigInt(a.amount_out) ? 1 : -1));

  const best = routes[0];
  const second = routes[1];
  const worst = routes[routes.length - 1];

  const grossSpreadBps =
    best && second ? spreadBps(BigInt(best.amount_out), BigInt(second.amount_out)) : 0;
  const crossVenueSpreadBps =
    best && worst && routes.length > 1
      ? spreadBps(BigInt(best.amount_out), BigInt(worst.amount_out))
      : 0;

  const primaryChain = (best?.chain ?? input.chains[0]) as ChainKey;
  const client = clientFor(primaryChain);
  const gasPrice = await client.getGasPrice();
  const gasUnits = 180_000n * BigInt(ARB_SWAP_COUNT);
  const gasCostWei = gasPrice * gasUnits;
  const dexFeeBps = DEX_FEE_BPS_PER_SWAP * ARB_SWAP_COUNT;
  const gasBps = gasCostBps(gasCostWei, input.amount_in);
  const totalCostBps = dexFeeBps + gasBps;
  const netSpreadBps = Math.max(0, grossSpreadBps - totalCostBps);

  const profitable = routes.length >= 2 && netSpreadBps >= input.min_net_spread_bps;

  return {
    profitable,
    best_route: best ?? null,
    alt_routes: routes.slice(1),
    net_spread_bps: netSpreadBps,
    gross_spread_bps: grossSpreadBps,
    cross_venue_spread_bps: crossVenueSpreadBps,
    est_fill_cost: {
      gas_wei: gasCostWei.toString(),
      gas_price_wei: gasPrice.toString(),
      gas_units: gasUnits.toString(),
      gas_cost_bps: gasBps,
      dex_fee_bps: dexFeeBps,
      total_cost_bps: totalCostBps,
    },
    scanned: {
      chains: input.chains,
      venues_checked: input.chains.reduce((n, c) => n + DEX_VENUES[c].length, 0),
      quotes_found: routes.length,
    },
    diagnostics: {
      amount_in_human: formatAmount(input.amount_in),
      token_in: input.token_in,
      token_out: input.token_out,
    },
  };
}

const inputSchema = z.object({
  token_in: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
  token_out: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
  amount_in: z.union([z.string(), z.number()]),
  chains: z
    .array(z.enum(["base", "base-sepolia"]))
    .default(["base"]),
  min_net_spread_bps: z.number().int().min(0).max(10_000).default(0),
});

const payments = paymentsFromEnv({ defaultPrice: "1000" });

const { app, addEntrypoint } = createAgentApp(
  {
    name: "cross-dex-arbitrage-alert",
    version: "0.1.0",
    description: "Detect cross-DEX token price spreads after fees and gas",
  },
  { payments, useConfigPayments: true },
);

addEntrypoint({
  key: "scan",
  description:
    "Scan Uniswap V2-style DEX venues for cross-DEX spreads; returns best route, alts, net spread bps, and fill cost",
  input: inputSchema,
  price: "1000",
  async handler({ input }) {
    const amountIn =
      typeof input.amount_in === "number"
        ? BigInt(Math.floor(input.amount_in * 1e18))
        : BigInt(input.amount_in);

    const output = await scanCrossDex({
      token_in: input.token_in as Address,
      token_out: input.token_out as Address,
      amount_in: amountIn,
      chains: input.chains as ChainKey[],
      min_net_spread_bps: input.min_net_spread_bps,
    });

    return {
      output,
      usage: { net_spread_bps: String(output.net_spread_bps) },
    };
  },
});

console.log(`cross-dex-arbitrage-alert listening on http://127.0.0.1:${PORT}`);
serve({ fetch: app.fetch, port: PORT });
