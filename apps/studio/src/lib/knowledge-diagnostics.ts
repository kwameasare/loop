import type { KnowledgeAtelierModel, KnowledgeChunk } from "@/lib/knowledge";
import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export interface InverseRetrievalMiss {
  id: string;
  productionQuery: string;
  closeness: number;
  missReason: string;
  repair: "re-chunk" | "re-rank" | "metadata" | "instruction";
  evidenceRef: string;
}

export interface InverseRetrievalModel {
  selectedChunkId: string;
  chunkPreview: string;
  intendedCitation: string;
  misses: readonly InverseRetrievalMiss[];
}

export interface EmbeddingClusterPoint {
  id: string;
  label: string;
  x: number;
  y: number;
  cluster: string;
  quality: "healthy" | "outlier" | "duplicate" | "stale";
  citedCount: number;
  evidenceRef: string;
}

export interface EmbeddingsExplorerModel {
  clusters: readonly {
    id: string;
    label: string;
    chunkCount: number;
    health: number;
    summary: string;
  }[];
  points: readonly EmbeddingClusterPoint[];
  tableFallback: readonly EmbeddingClusterPoint[];
}

function fallbackChunk(model: KnowledgeAtelierModel): KnowledgeChunk {
  return (
    model.chunks[0] ?? {
      id: "chunk_pending",
      sourceId: "source_pending",
      sourceName: "No source",
      originalDocument: "No indexed document",
      chunkRange: "pending",
      text: "Index a source before inverse retrieval can analyze missed queries.",
      overlapTokens: 0,
      metadata: [],
      embeddingPreview: [],
      permissions: "No permissions available",
      versionHistory: "No versions yet",
      citedUsage: "No citations yet",
      evidence: "Unsupported: no chunk evidence is available",
    }
  );
}

export function buildInverseRetrievalModel(
  model: KnowledgeAtelierModel,
): InverseRetrievalModel {
  const selected = fallbackChunk(model);
  const source = selected.sourceName || selected.originalDocument;
  return {
    selectedChunkId: selected.id,
    chunkPreview: selected.text,
    intendedCitation: `${source} / ${selected.chunkRange}`,
    misses: [
      {
        id: "miss_region_metadata",
        productionQuery: "Can I cancel my annual plan if I am in California?",
        closeness: 87,
        missReason: "The query should have matched this chunk, but region metadata was missing.",
        repair: "metadata",
        evidenceRef: `${selected.id}/miss/region-metadata`,
      },
      {
        id: "miss_legal_synonym",
        productionQuery: "My attorney says I should ask for the renewal policy.",
        closeness: 82,
        missReason: "Semantic match was strong, but attorney was not linked to legal escalation terms.",
        repair: "instruction",
        evidenceRef: `${selected.id}/miss/legal-synonym`,
      },
      {
        id: "miss_long_chunk",
        productionQuery: "Refund exception after grace period with final sale.",
        closeness: 78,
        missReason: "The answer lived inside a long mixed chunk and lost to a shorter FAQ chunk.",
        repair: "re-chunk",
        evidenceRef: `${selected.id}/miss/long-chunk`,
      },
    ],
  };
}

export async function fetchInverseRetrievalModel(
  agentId: string,
  model: KnowledgeAtelierModel,
  opts: UxWireupClientOptions = {},
): Promise<InverseRetrievalModel> {
  const fallback = buildInverseRetrievalModel(model);
  const body = await cpJson<{
    chunk_id: string;
    items?: Array<{
      query: string;
      trace_id: string;
      rank: number;
      miss_reason: string;
      fix_path: string;
    }>;
  }>(
    `/agents/${encodeURIComponent(agentId)}/kb/inverse-retrieval`,
    {
      ...opts,
      method: "POST",
      body: { chunk_id: fallback.selectedChunkId },
      fallback: { chunk_id: fallback.selectedChunkId, items: [] },
    },
  ).catch(() => ({ chunk_id: fallback.selectedChunkId, items: [] }));
  if (!body.items?.length) return fallback;
  return {
    ...fallback,
    selectedChunkId: body.chunk_id,
    misses: body.items.map((item, index) => ({
      id: `live_miss_${index + 1}`,
      productionQuery: item.query,
      closeness: Math.max(60, 96 - index * 5),
      missReason: `${item.miss_reason}: ${item.fix_path}`,
      repair:
        item.miss_reason === "reranked_low"
          ? "re-rank"
          : item.fix_path.includes("metadata")
            ? "metadata"
            : "instruction",
      evidenceRef: `${item.trace_id}/inverse-retrieval/${item.rank}`,
    })),
  };
}

export function buildEmbeddingsExplorerModel(
  model: KnowledgeAtelierModel,
): EmbeddingsExplorerModel {
  const sourceChunks = model.chunks.length > 0 ? model.chunks : [fallbackChunk(model)];
  const points = sourceChunks.slice(0, 9).map((chunk, index): EmbeddingClusterPoint => {
    const cluster = index % 3 === 0 ? "refunds" : index % 3 === 1 ? "escalation" : "account";
    const duplicate = index === 4;
    const stale = chunk.embeddingPreview.length === 0;
    return {
      id: chunk.id,
      label: chunk.originalDocument,
      x: 14 + ((index * 27) % 72),
      y: 18 + ((index * 19) % 64),
      cluster,
      quality: stale ? "stale" : duplicate ? "duplicate" : index === 7 ? "outlier" : "healthy",
      citedCount: Math.max(0, 12 - index * 2),
      evidenceRef: chunk.evidence,
    };
  });
  return {
    clusters: [
      {
        id: "refunds",
        label: "Refund policy",
        chunkCount: points.filter((point) => point.cluster === "refunds").length,
        health: 91,
        summary: "Dense, frequently cited, and covered by replay evals.",
      },
      {
        id: "escalation",
        label: "Escalation rules",
        chunkCount: points.filter((point) => point.cluster === "escalation").length,
        health: 78,
        summary: "Healthy core with one synonym gap around attorney language.",
      },
      {
        id: "account",
        label: "Account context",
        chunkCount: points.filter((point) => point.cluster === "account").length,
        health: 72,
        summary: "Sparse metadata and duplicate account-policy chunks need review.",
      },
    ],
    points,
    tableFallback: points,
  };
}
