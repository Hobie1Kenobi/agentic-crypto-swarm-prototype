import type { Chain } from "viem";
import type { IAgentExecutor } from "./types.js";
import { createSimpleSignerExecutor } from "./SimpleSignerExecutor.js";
import { createAAAgentExecutor } from "./AAAgentExecutor.js";

export type { AgentRole, IAgentExecutor, SendTransactionParams } from "./types.js";
export { createSimpleSignerExecutor } from "./SimpleSignerExecutor.js";
export { createAAAgentExecutor } from "./AAAgentExecutor.js";

export function getDefaultExecutor(chain: Chain, rpcUrl: string): IAgentExecutor {
  const bundlerUrl = process.env.BUNDLER_RPC_URL
    || (process.env.PIMLICO_API_KEY && chain.id === 84532
      ? `https://api.pimlico.io/v2/84532/rpc?apikey=${process.env.PIMLICO_API_KEY}`
      : null);
  if (bundlerUrl) {
    return createAAAgentExecutor(chain, rpcUrl, bundlerUrl);
  }
  return createSimpleSignerExecutor(chain, rpcUrl);
}
