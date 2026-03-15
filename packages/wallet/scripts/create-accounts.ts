import { config } from "dotenv";
import { createPublicClient, http, type Hex } from "viem";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { toSimpleSmartAccount } from "permissionless/accounts";
import { entryPoint07Address } from "viem/account-abstraction";
import { readFileSync, writeFileSync, existsSync } from "fs";
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

const RPC_URLS = [
  () => process.env.ALCHEMY_API_KEY && `https://base-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`,
  () => process.env.RPC_URL,
  () => "https://sepolia.base.org",
  () => "https://base-sepolia-rpc.publicnode.com",
];

async function main() {
  const envPath = getEnvPath();
  const rpcUrl = RPC_URLS.map((f) => f()).find(Boolean) || "https://sepolia.base.org";

  const publicClient = createPublicClient({
    chain: baseSepolia,
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
