import { serve } from "@hono/node-server";
import { createAgentApp, paymentsFromEnv } from "@lucid-dreams/agent-kit";
import { z } from "zod";
import { estimateImpermanentLoss } from "./il.js";

const PORT = Number(process.env.PORT || process.env.LP_IL_ESTIMATOR_PORT || 8103);

const inputSchema = z.object({
  pool_address: z
    .string()
    .min(1)
    .describe("DefiLlama pool UUID, on-chain LP pool address (0x…), or underlying token address"),
  token_weights: z
    .array(z.number().nonnegative())
    .default([0.5, 0.5])
    .describe("Normalized token weights for constant-product IL model"),
  deposit_amounts: z
    .array(z.number().nonnegative())
    .default([])
    .describe("Simulated deposit amounts per token (same order as pool tokens)"),
  window_hours: z
    .number()
    .int()
    .min(1)
    .max(8760)
    .default(168)
    .describe("Historical lookback window in hours"),
});

const payments = paymentsFromEnv({ defaultPrice: "1000" });

const { app, addEntrypoint } = createAgentApp(
  {
    name: "lp-il-estimator",
    version: "0.1.0",
    description: "Estimate impermanent loss and fee APR for LP positions using DefiLlama history",
  },
  { payments, useConfigPayments: true },
);

addEntrypoint({
  key: "estimate",
  description:
    "Compute IL_percent, fee_apr_est, volume_window, and notes from pool history and token price ratio",
  input: inputSchema,
  price: "1000",
  async handler({ input }) {
    const output = await estimateImpermanentLoss(input);
    return {
      output: {
        IL_percent: output.IL_percent,
        fee_apr_est: output.fee_apr_est,
        volume_window: output.volume_window,
        notes: output.notes,
        pool: output.pool,
        backtest: output.backtest,
      },
      usage: { window_hours: String(input.window_hours) },
    };
  },
});

console.log(`lp-il-estimator listening on http://127.0.0.1:${PORT}`);
serve({ fetch: app.fetch, port: PORT });
