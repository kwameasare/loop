import { describe, expect, it, vi } from "vitest";

import {
  buildEmbeddingsExplorerModel,
  buildInverseRetrievalModel,
  fetchInverseRetrievalModel,
} from "@/lib/knowledge-diagnostics";
import { getKnowledgeAtelierModel } from "@/lib/knowledge";
import type { KbDocument } from "@/lib/kb";

const docs: KbDocument[] = [
  {
    id: "doc_refund",
    agentId: "agent_support",
    name: "support_handbook.md",
    contentType: "text/markdown",
    bytes: 12_345,
    status: "ready",
    uploadedAt: "2026-04-01T12:00:00Z",
    lastRefreshedAt: "2026-05-05T12:00:00Z",
  },
];

describe("knowledge diagnostics", () => {
  it("builds inverse retrieval misses with repair paths", () => {
    const atelier = getKnowledgeAtelierModel("agent_support", docs);
    const inverse = buildInverseRetrievalModel(atelier);

    expect(inverse.selectedChunkId).toContain("chunk");
    expect(inverse.misses).toHaveLength(3);
    expect(inverse.misses.map((miss) => miss.repair)).toContain("metadata");
  });

  it("loads inverse retrieval misses from cp-api", async () => {
    const atelier = getKnowledgeAtelierModel("agent_support", docs);
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        chunk_id: "chunk_refund",
        items: [
          {
            query: "Do renewal refunds work in California?",
            trace_id: "trace_1",
            rank: 4,
            miss_reason: "reranked_low",
            fix_path: "re-rank renewal policy chunk",
          },
        ],
      }),
    );

    const inverse = await fetchInverseRetrievalModel("agent_support", atelier, {
      baseUrl: "https://cp.test/v1",
      fetcher,
    });

    expect(inverse.misses[0]).toMatchObject({
      productionQuery: "Do renewal refunds work in California?",
      repair: "re-rank",
    });
  });

  it("requires cp-api before reporting inverse retrieval diagnostics", async () => {
    const atelier = getKnowledgeAtelierModel("agent_support", docs);

    await expect(
      fetchInverseRetrievalModel("agent_support", atelier, { baseUrl: "" }),
    ).rejects.toThrow(/LOOP_CP_API_BASE_URL is required/i);
  });

  it("builds an accessible embedding map and table fallback", () => {
    const atelier = getKnowledgeAtelierModel("agent_support", docs);
    const explorer = buildEmbeddingsExplorerModel(atelier);

    expect(explorer.clusters).toHaveLength(3);
    expect(explorer.tableFallback).toEqual(explorer.points);
  });
});
