import { config } from "dotenv";
import { createPublicClient, defineChain, http, type Chain, type Hex } from "viem";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { toSimpleSmartAccount } from "permissionless/accounts";
import { entryPoint07Address } from "viem/account-abstraction";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { join } from "path";

const anvil = defineChain({ id: 31337, name: "Anvil", nativeCurrency: { decimals: 18, name: "Ether", symbol: "ETH" }, rpcUrls: { default: { http: ["http://127.0.0.1:8545"] } } });
const celoSepolia = defineChain({ id: 11142220, name: "Celo Sepolia", nativeCurrency: { decimals: 18, name: "CELO", symbol: "CELO" }, rpcUrls: { default: { http: ["https://rpc.ankr.com/celo_sepolia"] } } });
const celo = defineChain({ id: 42220, name: "Celo", nativeCurrency: { decimals: 18, name: "CELO", symbol: "CELO" }, rpcUrls: { default: { http: ["https://rpc.ankr.com/celo"] } } });

function getChain(): Chain {
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
  if (chainId === 11142220) return process.env.CELO_SEPOLIA_RPC_URL || "https://rpc.ankr.com/celo_sepolia";
  if (chainId === 42220) return process.env.CELO_MAINNET_RPC_URL || "https://rpc.ankr.com/celo";
  if (chainId === 84532) return process.env.ALCHEMY_API_KEY ? `https://base-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}` : "https://sepolia.base.org";
  return "https://rpc.ankr.com/celo_sepolia";
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

const AGENTS = ["ROOT_STRATEGIST", "IP_GENERATOR", "DEPLOYER", "FINANCE_DISTRIBUTOR"] as const;

function getEnvPath(): string {
  const root = findProjectRoot();
  return join(root, ".env");
}

function ensureGitignoreHasEnv(): void {
  const gitignorePath = join(findProjectRoot(), ".gitignore");
  if (!existsSync(gitignorePath)) return;
  let content = readFileSync(gitignorePath, "utf-8");
  if (!content.includes(".env") && !content.includes("/.env")) {
    content += "\n# Secrets (do not commit)\n.env\n.env.local\n.env.*.local\n";
    writeFileSync(gitignorePath, content);
    console.log("Updated .gitignore to exclude .env");
  }
}

function loadExistingEnv(path: string): Record<string, string> {
  const out: Record<string, string> = {};
  if (!existsSync(path)) return out;
  const raw = readFileSync(path, "utf-8");
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "").trim();
  }
  return out;
}

function writeEnv(path: string, updates: Record<string, string>): void {
  const existing = loadExistingEnv(path);
  const merged = { ...existing, ...updates };
  const lines: string[] = [];
  const keys = [...new Set([...Object.keys(existing), ...Object.keys(updates)])];
  for (const k of keys) {
    const v = merged[k];
    if (v !== undefined && v !== "") lines.push(`${k}=${v}`);
  }
  writeFileSync(path, lines.join("\n") + "\n", "utf-8");
  ensureGitignoreHasEnv();
}

async function main() {
  const envPath = getEnvPath();
  const chain = getChain();
  const rpcUrl = getRpcUrl();

  const publicClient = createPublicClient({
    chain,
    transport: http(rpcUrl),
  });

  const updates: Record<string, string> = {};
  const addresses: string[] = [];

  for (const agent of AGENTS) {
    const pkKey = `${agent}_PRIVATE_KEY`;
    const addrKey = `${agent}_ADDRESS`;
    const existingPk = process.env[pkKey] || loadExistingEnv(envPath)[pkKey];
    const privateKey = (existingPk as Hex) || generatePrivateKey();

    const owner = privateKeyToAccount(privateKey as Hex);
    const account = await toSimpleSmartAccount({
      client: publicClient,
      owner,
      entryPoint: { address: entryPoint07Address, version: "0.7" },
    });

    updates[pkKey] = privateKey;
    updates[addrKey] = account.address;
    addresses.push(`${agent}: ${account.address}`);
  }

  writeEnv(envPath, updates);

  console.log("Created 4 agent smart accounts. Addresses:");
  addresses.forEach((a) => console.log("  ", a));
  console.log("\nSecrets saved to", envPath);
  console.log(".gitignore excludes .env");
}

main().catch(console.error);
