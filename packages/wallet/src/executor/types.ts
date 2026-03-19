import type { Hex } from "viem";

export type AgentRole = "ROOT_STRATEGIST" | "IP_GENERATOR" | "DEPLOYER" | "FINANCE_DISTRIBUTOR";

export interface SendTransactionParams {
  to: Hex;
  value?: bigint;
  data?: Hex;
  gas?: bigint;
  gasPrice?: bigint;
  maxFeePerGas?: bigint;
  maxPriorityFeePerGas?: bigint;
  nonce?: number;
  chainId: number;
}

export interface IAgentExecutor {
  getSenderAddress(role: AgentRole): Promise<Hex>;
  sendTransaction(role: AgentRole, params: SendTransactionParams): Promise<Hex>;
}
