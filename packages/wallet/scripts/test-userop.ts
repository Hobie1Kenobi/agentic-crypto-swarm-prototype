import { createPublicClient, createWalletClient, http, parseEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { toSimpleSmartAccount } from "permissionless/accounts";
import { createSmartAccountClient } from "permissionless";
import { createPimlicoClient } from "permissionless/clients/pimlico";
import { entryPoint07Address } from "viem/account-abstraction";
import { config } from "dotenv";
import { existsSync } from "fs";
import { join } from "path";

function findProjectRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 5; i++) {
    if (existsSync(join(dir, "foundry.toml")) || existsSync(join(dir, ".env.example"))) return dir;
    dir = join(dir, "..");
  }
  return process.cwd();
}
config({ path: join(findProjectRoot(), ".env") });

async function main() {
  const rpcUrl = process.env.RPC_URL || (process.env.ALCHEMY_API_KEY
    ? `https://base-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`
    : null);
  const pimlicoKey = process.env.PIMLICO_API_KEY;
  const pk = process.env.ROOT_STRATEGIST_PRIVATE_KEY;

  if (!pk) {
    console.error("Run create-accounts first to generate ROOT_STRATEGIST_PRIVATE_KEY");
    process.exit(1);
  }

  const bundlerUrl = pimlicoKey
    ? `https://api.pimlico.io/v2/84532/rpc?apikey=${pimlicoKey}`
    : null;

  const publicClient = createPublicClient({
    chain: baseSepolia,
    transport: http(rpcUrl || "https://base-sepolia.g.alchemy.com/v2/demo"),
  });

  const owner = privateKeyToAccount(pk as `0x${string}`);
  const account = await toSimpleSmartAccount({
    client: publicClient,
    owner,
    entryPoint: { address: entryPoint07Address, version: "0.7" },
  });

  console.log("Smart account:", account.address);

  if (!bundlerUrl) {
    console.log("Set PIMLICO_API_KEY to send a real UserOp. Skipping tx.");
    return;
  }

  const paymasterClient = createPimlicoClient({
    entryPoint: { address: entryPoint07Address, version: "0.7" },
    transport: http(bundlerUrl),
  });

  const smartAccountClient = createSmartAccountClient({
    account,
    chain: baseSepolia,
    bundlerTransport: http(bundlerUrl),
    paymaster: paymasterClient,
    userOperation: {
      estimateFeesPerGas: async () => (await paymasterClient.getUserOperationGasPrice()).fast,
    },
  });

  const txHash = await smartAccountClient.sendTransaction({
    to: account.address,
    value: 0n,
    data: "0x",
  });

  console.log("UserOp tx:", txHash);
  console.log("Explorer: https://sepolia.basescan.org/tx/" + txHash);
}

main().catch(console.error);
