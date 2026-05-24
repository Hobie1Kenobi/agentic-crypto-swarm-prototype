import { z } from "zod";

export const chainSchema = z.enum(["base", "optimism", "arbitrum", "polygon", "ethereum"]);

export const quoteQuerySchema = z.object({
  chain: chainSchema,
  urgency: z.enum(["low", "medium", "high"]).default("medium"),
  targetBlocks: z.coerce.number().int().min(1).max(50).default(3),
  txType: z.enum(["transfer", "swap", "contract"]).default("contract"),
});

export const forecastQuerySchema = z.object({
  chain: chainSchema,
  horizonMinutes: z.coerce.number().int().min(5).max(120).default(30),
});

export const congestionQuerySchema = z.object({
  chain: chainSchema,
});

export const quoteResponseSchema = z.object({
  chain: chainSchema,
  recommended_max_fee: z.string(),
  priority_fee: z.string(),
  inclusion_probability_curve: z.array(
    z.object({
      blocks: z.number(),
      probability: z.number(),
    }),
  ),
  congestion_state: z.enum(["low", "medium", "high", "critical"]),
  confidence_score: z.number(),
  freshness_ms: z.number(),
});

export const forecastResponseSchema = z.object({
  chain: chainSchema,
  horizon_minutes: z.number(),
  trend: z.enum(["rising", "stable", "falling"]),
  points: z.array(
    z.object({
      minute: z.number(),
      max_fee_gwei: z.number(),
      confidence: z.number(),
    }),
  ),
  confidence_score: z.number(),
  freshness_ms: z.number(),
});

export const congestionResponseSchema = z.object({
  chain: chainSchema,
  congestion_state: z.enum(["low", "medium", "high", "critical"]),
  pending_tx_estimate: z.number(),
  base_fee_gwei: z.number(),
  confidence_score: z.number(),
  freshness_ms: z.number(),
});

export type Chain = z.infer<typeof chainSchema>;
