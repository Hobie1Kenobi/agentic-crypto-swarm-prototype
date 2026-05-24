import type { Chain } from "./schemas.js";

const BASE_GWEI: Record<Chain, number> = {
  ethereum: 25,
  base: 0.05,
  optimism: 0.02,
  arbitrum: 0.05,
  polygon: 35,
};

const URGENCY_MULT: Record<string, number> = {
  low: 1,
  medium: 1.15,
  high: 1.35,
};

export function inclusionCurve(baseGwei: number, urgency: string, targetBlocks: number) {
  const lambda = urgency === "high" ? 0.9 : urgency === "medium" ? 0.65 : 0.45;
  const curve = [];
  for (let blocks = 1; blocks <= Math.max(targetBlocks, 5); blocks++) {
    const probability = Number((1 - Math.exp(-lambda * blocks)).toFixed(4));
    curve.push({ blocks, probability });
  }
  return curve;
}

export function congestionFromGwei(gwei: number, baseline: number): "low" | "medium" | "high" | "critical" {
  const ratio = baseline > 0 ? gwei / baseline : 1;
  if (ratio <= 1.2) return "low";
  if (ratio <= 2) return "medium";
  if (ratio <= 3.5) return "high";
  return "critical";
}

export function buildQuote(input: {
  chain: Chain;
  urgency: string;
  targetBlocks: number;
  txType: string;
  observedGwei?: number;
}) {
  const baseline = BASE_GWEI[input.chain];
  const gwei = (input.observedGwei ?? baseline) * URGENCY_MULT[input.urgency];
  const priority = gwei * 0.15;
  const maxFee = gwei + priority;
  const txMult = input.txType === "swap" ? 1.1 : input.txType === "contract" ? 1.05 : 1;
  const adjusted = maxFee * txMult;
  const congestion = congestionFromGwei(gwei, baseline);
  return {
    chain: input.chain,
    recommended_max_fee: adjusted.toFixed(6),
    priority_fee: priority.toFixed(6),
    inclusion_probability_curve: inclusionCurve(gwei, input.urgency, input.targetBlocks),
    congestion_state: congestion,
    confidence_score: input.observedGwei ? 0.92 : 0.75,
    freshness_ms: 0,
  };
}

export function buildForecast(input: { chain: Chain; horizonMinutes: number; observedGwei?: number }) {
  const baseline = BASE_GWEI[input.chain];
  const start = input.observedGwei ?? baseline;
  const step = start * 0.01;
  const points = [];
  for (let minute = 0; minute <= input.horizonMinutes; minute += 5) {
    const drift = Math.sin(minute / 10) * step * 2;
    points.push({
      minute,
      max_fee_gwei: Number((start + drift).toFixed(6)),
      confidence: Number(Math.max(0.4, 0.95 - minute / (input.horizonMinutes * 2)).toFixed(3)),
    });
  }
  const trend = points.at(-1)!.max_fee_gwei > points[0]!.max_fee_gwei ? "rising" : points.at(-1)!.max_fee_gwei < points[0]!.max_fee_gwei ? "falling" : "stable";
  return {
    chain: input.chain,
    horizon_minutes: input.horizonMinutes,
    trend: trend as "rising" | "stable" | "falling",
    points,
    confidence_score: input.observedGwei ? 0.88 : 0.7,
    freshness_ms: 0,
  };
}

export function buildCongestion(input: { chain: Chain; observedGwei?: number }) {
  const baseline = BASE_GWEI[input.chain];
  const gwei = input.observedGwei ?? baseline;
  return {
    chain: input.chain,
    congestion_state: congestionFromGwei(gwei, baseline),
    pending_tx_estimate: Math.round(gwei * 1000),
    base_fee_gwei: Number(gwei.toFixed(6)),
    confidence_score: input.observedGwei ? 0.9 : 0.72,
    freshness_ms: 0,
  };
}
