import { createPublicClient, createWalletClient, http, type Chain, type Hex } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import type { AgentRole, IAgentExecutor, SendTransactionParams } from "./types.js";

const ROLE_ENV: Record<AgentRole, string> = {
  ROOT_STRATEGIST: "ROOT_STRATEGIST_PRIVATE_KEY",
  IP_GENERATOR: "IP_GENERATOR_PRIVATE_KEY",
  DEPLOYER: "DEPLOYER_PRIVATE_KEY",
  FINANCE_DISTRIBUTOR: "FINANCE_DISTRIBUTOR_PRIVATE_KEY",
};

function getPrivateKey(role: AgentRole): Hex {
  const key = process.env[ROLE_ENV[role]] || process.env.PRIVATE_KEY;
  if (!key || key.includes("your_")) throw new Error(`Missing key for ${role}: set ${ROLE_ENV[role]} or PRIVATE_KEY`);
  return key as Hex;
}

export function createSimpleSignerExecutor(chain: Chain, rpcUrl: string): IAgentExecutor {
  const publicClient = createPublicClient({ chain, transport: http(rpcUrl) });

  return {
    async getSenderAddress(role: AgentRole): Promise<Hex> {
      const account = privateKeyToAccount(getPrivateKey(role));
      return account.address;
    },

    async sendTransaction(role: AgentRole, params: SendTransactionParams): Promise<Hex> {
      const account = privateKeyToAccount(getPrivateKey(role));
      const walletClient = createWalletClient({
        account,
        chain,
        transport: http(rpcUrl),
      });
      const hash = await walletClient.sendTransaction({
        to: params.to,
        value: params.value ?? 0n,
        data: params.data ?? "0x",
        gas: params.gas,
        gasPrice: params.gasPrice,
        maxFeePerGas: params.maxFeePerGas,
        maxPriorityFeePerGas: params.maxPriorityFeePerGas,
        nonce: params.nonce,
        chainId: params.chainId,
      });
      return hash;
    },
  };
}
