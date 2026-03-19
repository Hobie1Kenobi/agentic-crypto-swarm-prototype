import { createPublicClient, http, type Chain, type Hex } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { toSimpleSmartAccount } from "permissionless/accounts";
import { createSmartAccountClient } from "permissionless";
import { createPimlicoClient } from "permissionless/clients/pimlico";
import { entryPoint07Address } from "viem/account-abstraction";
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

export function createAAAgentExecutor(
  chain: Chain,
  rpcUrl: string,
  bundlerUrl: string
): IAgentExecutor {
  const publicClient = createPublicClient({ chain, transport: http(rpcUrl) });
  const paymasterClient = createPimlicoClient({
    entryPoint: { address: entryPoint07Address, version: "0.7" },
    transport: http(bundlerUrl),
  });

  async function getSmartAccountClient(role: AgentRole) {
    const owner = privateKeyToAccount(getPrivateKey(role));
    const account = await toSimpleSmartAccount({
      client: publicClient,
      owner,
      entryPoint: { address: entryPoint07Address, version: "0.7" },
    });
    return createSmartAccountClient({
      account,
      chain,
      bundlerTransport: http(bundlerUrl),
      paymaster: paymasterClient,
      userOperation: {
        estimateFeesPerGas: async () => (await paymasterClient.getUserOperationGasPrice()).fast,
      },
    });
  }

  return {
    async getSenderAddress(role: AgentRole): Promise<Hex> {
      const client = await getSmartAccountClient(role);
      return client.account.address;
    },

    async sendTransaction(role: AgentRole, params: SendTransactionParams): Promise<Hex> {
      const client = await getSmartAccountClient(role);
      const hash = await client.sendTransaction({
        to: params.to,
        value: params.value ?? 0n,
        data: params.data ?? "0x",
        gas: params.gas,
      });
      return hash;
    },
  };
}
