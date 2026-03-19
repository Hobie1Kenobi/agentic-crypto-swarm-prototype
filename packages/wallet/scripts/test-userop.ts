import { createPublicClient, createWalletClient, defineChain, http, parseEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { toSimpleSmartAccount } from "permissionless/accounts";
import { createSmartAccountClient } from "permissionless";
import { createPimlicoClient } from "permissionless/clients/pimlico";
import { entryPoint07Address } from "viem/account-abstraction";
import { config } from "dotenv";
import { existsSync } from "fs";
import { join } from "path";

const anvil = defineChain({ id: 31337, name: "Anvil", nativeCurrency: { decimals: 18, name: "Ether", symbol: "ETH" }, rpcUrls: { default: { http: ["http://127.0.0.1:8545"] } } });
const celoSepolia = defineChain({ id: 11142220, name: "Celo Sepolia", nativeCurrency: { decimals: 18, name: "CELO", symbol: "CELO" }, rpcUrls: { default: { http: ["https://rpc.ankr.com/celo_sepolia"] } } });
const celo = defineChain({ id: 42220, name: "Celo", nativeCurrency: { decimals: 18, name: "CELO", symbol: "CELO" }, rpcUrls: { default: { http: ["https://rpc.ankr.com/celo"] } } });

function getChain() {
  const chainId = process.env.CHAIN_ID ? parseInt(process.env.CHAIN_ID, 10) : 11142220;
  if (chainId === 31337) return anvil;
  if (chainId === 11142220) return celoSepolia;
  if (chainId === 42220) return celo;
  if (chainId === 84532) return baseSepolia;
  return celoSepolia;
}
function getRpcUrl(): string {
  const rpc = process.env.RPC_URL || process.env.CELO_SEPOLIA_RPC_URL || process.env.CELO_MAINNET_RPC_URL || process.env.CELO_RPC_URL;
  if (rpc && !rpc.includes("your_")) return rpc;
  const chainId = process.env.CHAIN_ID ? parseInt(process.env.CHAIN_ID, 10) : 11142220;
  if (chainId === 31337) return "http://127.0.0.1:8545";
  if (chainId === 11142220) return "https://rpc.ankr.com/celo_sepolia";
  if (chainId === 42220) return "https://rpc.ankr.com/celo";
  if (chainId === 84532) return process.env.ALCHEMY_API_KEY ? `https://base-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}` : "https://sepolia.base.org";
  return "https://rpc.ankr.com/celo_sepolia";
}
function getExplorerUrl(): string {
  const chainId = process.env.CHAIN_ID ? parseInt(process.env.CHAIN_ID, 10) : 11142220;
  if (process.env.EXPLORER_URL) return process.env.EXPLORER_URL;
  if (chainId === 31337) return "";
  if (chainId === 11142220) return "https://celo-sepolia.blockscout.com";
  if (chainId === 42220) return "https://explorer.celo.org";
  if (chainId === 84532) return "https://sepolia.basescan.org";
  return "https://celo-sepolia.blockscout.com";
}

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
  const chain = getChain();
  const rpcUrl = getRpcUrl();
  const chainId = chain.id;
  const pimlicoKey = process.env.PIMLICO_API_KEY;
  const bundlerUrlEnv = process.env.BUNDLER_RPC_URL;
  const pk = process.env.ROOT_STRATEGIST_PRIVATE_KEY;

  if (!pk) {
    console.error("Run create-accounts first to generate ROOT_STRATEGIST_PRIVATE_KEY");
    process.exit(1);
  }

  const bundlerUrl = bundlerUrlEnv || (pimlicoKey && chainId === 84532 ? `https://api.pimlico.io/v2/84532/rpc?apikey=${pimlicoKey}` : null);

  const publicClient = createPublicClient({
    chain,
    transport: http(rpcUrl),
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
    chain,
    bundlerTransport: http(bundlerUrl!),
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
  const explorer = getExplorerUrl();
  if (explorer) console.log("Explorer:", explorer + "/tx/" + txHash);
}

main().catch(console.error);
