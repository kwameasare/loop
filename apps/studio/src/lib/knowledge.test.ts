import { describe, expect, it } from "vitest";

import {
  formatScore,
  getKnowledgeAtelierModel,
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
