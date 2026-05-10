import { describe, expect, it, vi } from "vitest";

import {
  formatScore,
  getKnowledgeAtelierModel,
  saveRetrievalEvalCase,
  sourceKindLabel,
} from "./knowledge";
import type { KbDocument } from "./kb";

const readyDoc: KbDocument = {
  id: "doc_ready",
  agentId: "agt_demo",
  name: "support_handbook.md",
  contentType: "text/markdown",
  bytes: 12_345,
  status: "ready",
  uploadedAt: "2026-04-01T12:00:00Z",
  lastRefreshedAt: "2026-05-01T08:00:00Z",
};

describe("knowledge atelier model", () => {
  it("builds source, chunk, retrieval, Why, and readiness views", () => {
    const model = getKnowledgeAtelierModel("agt_demo", [readyDoc]);

    expect(model.agentName).toBe("Agent agt_demo");
    expect(model.sources[0]).toMatchObject({
      documentId: "doc_ready",
      owner: "Support Ops",
      syncStatus: "ready",
      sensitivity: "internal",
    });
    expect(model.sources[0]?.freshness).toContain("days ago");
    expect(model.chunks.length).toBeGreaterThan(0);
    expect(model.chunks[0]?.metadata).toContain("kind:file");
    expect(model.retrievalLab.candidates[0]?.scores.hybrid).toBeGreaterThan(
      0.7,
    );
    expect(model.whyPanel?.sentQuery).toContain("refund");
    expect(model.readiness.generatedEvalCases).toContain(
      "retrieval.final_sale_refund.requires_exception",
    );
  });

  it("keeps empty knowledge unsupported instead of inventing candidates", () => {
    const model = getKnowledgeAtelierModel("agt_demo", []);

    expect(model.sources).toHaveLength(0);
    expect(model.chunks).toHaveLength(0);
    expect(model.retrievalLab.candidates).toHaveLength(0);
    expect(model.whyPanel).toBeNull();
    expect(model.readiness.evidence).toContain("Unsupported");
  });

  it("marks failed source syncs as low-confidence readiness blockers", () => {
    const model = getKnowledgeAtelierModel("agt_demo", [
      {
        ...readyDoc,
        id: "doc_error",
        status: "error",
        name: "legal_policy.pdf",
      },
    ]);

    expect(model.sources[0]?.syncStatus).toBe("error");
    expect(model.sources[0]?.errors[0]).toContain("Indexing failed");
    expect(model.sources[0]?.evalCoverage).toBeLessThan(50);
    expect(model.readiness.recommendation).toContain("Fix failed syncs");
    expect(model.readiness.sensitiveDataWarnings[0]).toContain("confidential");
  });
});

describe("knowledge formatting helpers", () => {
  it("formats source kinds and score percentages", () => {
    expect(sourceKindLabel("google_drive")).toBe("Google Drive");
    expect(formatScore(0.876)).toBe("88%");
  });
});

describe("knowledge eval persistence", () => {
  it("saves retrieval queries as eval cases with evidence", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_input, init) => {
      expect(JSON.parse(String(init?.body))).toMatchObject({
        query: "How do refunds work after final sale?",
        top_chunk_id: "chunk_refunds",
        candidate_chunk_ids: ["chunk_refunds", "chunk_legal"],
        metadata_filters: ["locale:any"],
        expected_citation: "refund_policy.pdf#p3",
        evidence_ref: "retrieval.final_sale_refund.requires_exception",
      });
      return Response.json(
        {
          ok: true,
          suite_id: "suite_retrieval",
          case_id: "case_retrieval",
          case: {
            id: "case_retrieval",
            name: "Retrieval: How do refunds work after final sale?",
            source: "knowledge-retrieval",
            source_ref: "retrieval.final_sale_refund.requires_exception",
          },
          next_url: "/agents/agt_demo/evals?case_id=case_retrieval",
        },
        { status: 201 },
      );
    });

    const result = await saveRetrievalEvalCase(
      "agt_demo",
      {
        query: "How do refunds work after final sale?",
        topChunkId: "chunk_refunds",
        candidateChunkIds: ["chunk_refunds", "chunk_legal"],
        metadataFilters: ["locale:any"],
        expectedCitation: "refund_policy.pdf#p3",
        evidenceRef: "retrieval.final_sale_refund.requires_exception",
        missedCandidateIds: ["chunk_exception"],
      },
      { baseUrl: "https://cp.test/v1", fetcher },
    );

    expect(result.case_id).toBe("case_retrieval");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_demo/kb/retrieval-eval-cases",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
