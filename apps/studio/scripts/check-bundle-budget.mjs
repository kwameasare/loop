import { promises as fs } from "node:fs";
import path from "node:path";

async function listJsonFiles(dir) {
  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      return [];
    }
    throw error;
  }
  const results = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...(await listJsonFiles(full)));
    } else if (entry.isFile() && entry.name.endsWith(".json")) {
      results.push(full);
    }
  }
  return results;
}

function bytesFromStats(stats) {
  if (!stats || typeof stats !== "object") return null;
  const assets = stats.assets;
  if (!Array.isArray(assets)) return null;

  const totalJsBytes = assets
    .filter(
      (asset) =>
        asset &&
        typeof asset === "object" &&
        typeof asset.name === "string" &&
        asset.name.endsWith(".js") &&
        typeof asset.size === "number",
    )
    .reduce((sum, asset) => sum + asset.size, 0);

  return totalJsBytes > 0 ? totalJsBytes : null;
}

function addJsEntries(value, out) {
  if (!Array.isArray(value)) return;
  for (const item of value) {
    if (typeof item === "string" && item.endsWith(".js")) {
      out.add(item);
    }
  }
}

async function bytesFromBuildManifests(studioRoot) {
  const nextDir = path.join(studioRoot, ".next");
  const buildManifestPath = path.join(nextDir, "build-manifest.json");
  const appBuildManifestPath = path.join(nextDir, "app-build-manifest.json");

  const referencedJs = new Set();

  try {
    const buildManifest = JSON.parse(
      await fs.readFile(buildManifestPath, "utf8"),
    );
    addJsEntries(buildManifest.polyfillFiles, referencedJs);
    addJsEntries(buildManifest.rootMainFiles, referencedJs);
    addJsEntries(buildManifest.lowPriorityFiles, referencedJs);
    if (buildManifest.pages && typeof buildManifest.pages === "object") {
      for (const files of Object.values(buildManifest.pages)) {
        addJsEntries(files, referencedJs);
      }
    }
  } catch {
    return null;
  }

  try {
    const appBuildManifest = JSON.parse(
      await fs.readFile(appBuildManifestPath, "utf8"),
    );
    if (appBuildManifest.pages && typeof appBuildManifest.pages === "object") {
      for (const files of Object.values(appBuildManifest.pages)) {
        addJsEntries(files, referencedJs);
      }
    }
  } catch {
    // App manifest is optional for some Next setups.
  }

  if (referencedJs.size === 0) {
    return null;
  }

  let totalBytes = 0;
  for (const assetPath of referencedJs) {
    const diskPath = path.join(nextDir, assetPath);
    try {
      const stat = await fs.stat(diskPath);
      totalBytes += stat.size;
    } catch {
      // Ignore missing chunks; manifests can reference optional assets.
    }
  }

  if (totalBytes <= 0) {
    return null;
  }

  return {
    file: "build-manifest.json + app-build-manifest.json",
    bytes: totalBytes,
  };
}

async function main() {
  const studioRoot = process.cwd();
  const budgetPath = path.join(studioRoot, "bundle-budget.json");
  const analyzeDir = path.join(studioRoot, ".next", "analyze");

  const budget = JSON.parse(await fs.readFile(budgetPath, "utf8"));
  const baseline = Number(budget.baselineClientJsBytes);
  const growth = Number(budget.maxGrowthPercent);
  if (!Number.isFinite(baseline) || !Number.isFinite(growth)) {
    throw new Error("bundle-budget.json must define baselineClientJsBytes and maxGrowthPercent numbers");
  }

  const jsonFiles = await listJsonFiles(analyzeDir);
  const candidates = [];
  if (jsonFiles.length > 0) {
    for (const file of jsonFiles) {
      try {
        const parsed = JSON.parse(await fs.readFile(file, "utf8"));
        const bytes = bytesFromStats(parsed);
        if (bytes !== null) {
          candidates.push({ file, bytes });
        }
      } catch {
        // Ignore malformed analyzer files.
      }
    }
  }

  if (candidates.length === 0) {
    const fallback = await bytesFromBuildManifests(studioRoot);
    if (fallback) {
      candidates.push(fallback);
    }
  }

  if (candidates.length === 0) {
    throw new Error(
      "No usable analyzer stats or build-manifest JS assets were found. Run `pnpm build:analyze` first.",
    );
  }

  const preferred =
    candidates.find((c) => c.file.toLowerCase().includes("client")) ||
    candidates.sort((a, b) => b.bytes - a.bytes)[0];

  const maxAllowed = Math.floor(baseline * (1 + growth / 100));
  const current = preferred.bytes;

  console.log(`bundle budget source: ${path.relative(studioRoot, preferred.file)}`);
  console.log(`bundle baseline: ${baseline} bytes`);
  console.log(`bundle current:  ${current} bytes`);
  console.log(`bundle max:      ${maxAllowed} bytes (${growth}% growth cap)`);

  if (current > maxAllowed) {
    throw new Error(
      `Bundle budget exceeded: ${current} > ${maxAllowed} bytes. ` +
        "If intentional, update bundle-budget.json with justification in PR notes.",
    );
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
