import { describe, expect, it } from "vitest";

import {
  buildEmbeddingsExplorerModel,
  buildInverseRetrievalModel,
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

  it("builds an accessible embedding map and table fallback", () => {
    const atelier = getKnowledgeAtelierModel("agent_support", docs);
    const explorer = buildEmbeddingsExplorerModel(atelier);

    expect(explorer.clusters).toHaveLength(3);
    expect(explorer.tableFallback).toEqual(explorer.points);
  });
});
