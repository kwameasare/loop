import type { FlowEdge } from "./flow-edges";
import type { FlowNode } from "./flow-nodes";

export interface FlowDoc {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

/**
 * Render a {@link FlowDoc} to a small canonical YAML subset.
 *
 * The format is intentionally restricted: top-level keys ``nodes`` and
 * ``edges`` each hold a list of objects with primitive fields. We render
 * the YAML deterministically (sorted keys) so two flows that are equal
 * round-trip to byte-identical YAML, which is required by the cp-api
 * conflict-detection mechanism.
 */
export function flowToYaml(doc: FlowDoc): string {
  const lines: string[] = [];
  lines.push("nodes:");
  if (doc.nodes.length === 0) {
    lines.push("  []");
  } else {
    for (const n of doc.nodes) {
      lines.push(`  - id: ${quote(n.id)}`);
      lines.push(`    type: ${quote(n.type)}`);
      lines.push(`    x: ${n.x}`);
      lines.push(`    y: ${n.y}`);
    }
  }
  lines.push("edges:");
  if (doc.edges.length === 0) {
    lines.push("  []");
  } else {
    for (const e of doc.edges) {
      lines.push(`  - id: ${quote(e.id)}`);
      lines.push(`    source: ${quote(e.source)}`);
      lines.push(`    target: ${quote(e.target)}`);
    }
  }
  return lines.join("\n") + "\n";
}

export function flowFromYaml(text: string): FlowDoc {
  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];
  let section: "nodes" | "edges" | null = null;
  let current: Record<string, unknown> | null = null;
  const flush = () => {
    if (!current) return;
    if (section === "nodes") {
      nodes.push(current as unknown as FlowNode);
    } else if (section === "edges") {
      edges.push(current as unknown as FlowEdge);
    }
    current = null;
  };
  for (const raw of text.split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (!line) continue;
    if (line === "nodes:") {
      flush();
      section = "nodes";
      continue;
    }
    if (line === "edges:") {
      flush();
      section = "edges";
      continue;
    }
    if (line.trim() === "[]") continue;
    const itemMatch = /^ {2}- (\w+):\s*(.+)$/.exec(line);
    if (itemMatch) {
      flush();
      current = {};
      current[itemMatch[1]] = parseScalar(itemMatch[2]);
      continue;
    }
    const fieldMatch = /^ {4}(\w+):\s*(.+)$/.exec(line);
    if (fieldMatch && current) {
      current[fieldMatch[1]] = parseScalar(fieldMatch[2]);
    }
  }
  flush();
  return { nodes, edges };
}

function quote(value: string): string {
  return JSON.stringify(value);
}

function parseScalar(value: string): unknown {
  const trimmed = value.trim();
  if (trimmed.startsWith('"')) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return trimmed;
    }
  }
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return Number(trimmed);
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed === "null") return null;
  return trimmed;
}

export interface FlowVersion {
  /** Raw YAML body that was last persisted. */
  flowYaml: string;
  /** Opaque tag returned by the server (e.g. ETag/version hash). */
  versionTag: string;
}

export interface SaveFlowResult {
  ok: boolean;
  /** When ``ok=false`` and a stale tag was sent, the server's current tag. */
  serverVersionTag?: string;
  /** Tag minted for the saved revision when ``ok=true``. */
  versionTag?: string;
  error?: string;
}

export interface FlowApi {
  load(agentId: string): Promise<FlowVersion | null>;
  save(
    agentId: string,
    body: { flowYaml: string; baseVersionTag: string | null },
  ): Promise<SaveFlowResult>;
}

/**
 * In-memory test/demo backend that emulates cp-api's optimistic concurrency
 * semantics: ``save`` rejects when ``baseVersionTag`` does not match the
 * server's current tag and reports the server's tag back to the caller.
 */
export function makeMemoryFlowApi(seed?: {
  agentId: string;
  flowYaml: string;
  versionTag: string;
}): FlowApi & { _force(version: FlowVersion | null): void } {
  const store = new Map<string, FlowVersion>();
  if (seed) {
    store.set(seed.agentId, {
      flowYaml: seed.flowYaml,
      versionTag: seed.versionTag,
    });
  }
  let counter = 0;
  return {
    async load(agentId) {
      return store.get(agentId) ?? null;
    },
    async save(agentId, body) {
      const current = store.get(agentId) ?? null;
      const currentTag = current?.versionTag ?? null;
      if ((body.baseVersionTag ?? null) !== currentTag) {
        return {
          ok: false,
          error: "stale_version_tag",
          serverVersionTag: currentTag ?? undefined,
        };
      }
      counter += 1;
      const next: FlowVersion = {
        flowYaml: body.flowYaml,
        versionTag: `v-${counter}`,
      };
      store.set(agentId, next);
      return { ok: true, versionTag: next.versionTag };
    },
    _force(version) {
      if (version === null) {
        store.delete("__seed__");
      }
      // Force-set under any agentId not yet seen by callers.
      for (const k of [...store.keys()]) store.delete(k);
      if (version) store.set(seed?.agentId ?? "force", version);
    },
  };
}
