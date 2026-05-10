import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KnowledgeAtelier } from "./knowledge-atelier";
import type { KbDocument } from "@/lib/kb";

const readyDocs: KbDocument[] = [
  {
    id: "doc_ready",
    agentId: "agt_demo",
    name: "support_handbook.md",
    contentType: "text/markdown",
    bytes: 12_345,
    status: "ready",
    uploadedAt: "2026-04-01T12:00:00Z",
    lastRefreshedAt: "2026-05-01T08:00:00Z",
  },
];

describe("KnowledgeAtelier", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "";
  });

  afterEach(() => {
    if (previousBaseUrl === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    }
    vi.unstubAllGlobals();
  });

  async function waitForDiagnosticsToSettle() {
    await screen.findAllByText(/LOOP_CP_API_BASE_URL is required/i);
  }

  it("renders source health, chunks, retrieval lab, Why panel, and readiness", async () => {
    render(
      <KnowledgeAtelier agentId="agt_demo" initialDocuments={readyDocs} />,
    );

    expect(screen.getByTestId("knowledge-atelier")).toBeInTheDocument();
    expect(screen.getByTestId("knowledge-source-doc_ready")).toHaveTextContent(
      "Support Ops",
    );
    expect(screen.getByTestId("knowledge-source-doc_ready")).toHaveTextContent(
      "Eval coverage",
    );
    expect(screen.getAllByTestId(/knowledge-chunk-/).length).toBeGreaterThan(0);
    expect(screen.getByTestId("retrieval-lab")).toHaveTextContent("Hybrid");
    expect(screen.getByTestId("retrieval-why-panel")).toHaveTextContent("Why");
    expect(screen.getByTestId("knowledge-readiness")).toHaveTextContent(
      "Generated eval cases",
    );
    expect(screen.getByTestId("knowledge-readiness")).toHaveTextContent(
      "Capability coverage",
    );
    expect(screen.getByTestId("knowledge-chunk-ks_doc_ready_chunk_1")).toHaveTextContent(
      "Affected policies",
    );
    await waitForDiagnosticsToSettle();
  });

  it("marks a chunk superseded through the backend-bound review action", async () => {
    const supersedeChunk = vi.fn(async () => ({
      chunk_id: "ks_doc_ready_chunk_1",
      lifecycle: "superseded" as const,
      superseded_at: "2026-05-06T12:00:00Z",
      reason: "Outdated policy source.",
      evidence_ref: "knowledge/superseded/1",
    }));
    render(
      <KnowledgeAtelier
        agentId="agt_demo"
        initialDocuments={readyDocs}
        supersedeChunk={supersedeChunk}
      />,
    );

    fireEvent.click(screen.getByTestId("knowledge-supersede-ks_doc_ready_chunk_1"));

    expect(supersedeChunk).toHaveBeenCalledWith(
      "agt_demo",
      "ks_doc_ready_chunk_1",
      expect.objectContaining({
        reason: expect.stringContaining("Builder marked this chunk"),
      }),
    );
    expect(
      await screen.findByTestId(
        "knowledge-chunk-lifecycle-ks_doc_ready_chunk_1",
      ),
    ).toHaveTextContent("superseded");
    await waitForDiagnosticsToSettle();
  });

  it("maps knowledge contradictions to affected behavior policies and evals", async () => {
    render(
      <KnowledgeAtelier
        agentId="agt_demo"
        initialDocuments={[
          ...readyDocs,
          {
            id: "doc_policy",
            agentId: "agt_demo",
            name: "legal_refund_policy.pdf",
            contentType: "application/pdf",
            bytes: 8_192,
            status: "ready",
            uploadedAt: "2026-04-15T12:00:00Z",
            lastRefreshedAt: "2026-05-02T08:00:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByTestId("knowledge-readiness")).toHaveTextContent(
      "Contradiction impact",
    );
    expect(screen.getByTestId("knowledge-readiness")).toHaveTextContent(
      "behavior.refund_policy",
    );
    expect(screen.getByTestId("knowledge-readiness")).toHaveTextContent(
      "eval.refund_exception_escalates",
    );
    await waitForDiagnosticsToSettle();
  });

  it("saves a retrieval query as an eval seed with evidence", async () => {
    render(
      <KnowledgeAtelier agentId="agt_demo" initialDocuments={readyDocs} />,
    );

    fireEvent.change(screen.getByLabelText("Query"), {
      target: { value: "How do refunds work after final sale?" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Save as retrieval eval" }),
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Saved retrieval eval seed",
    );
    expect(screen.getByRole("status")).toHaveTextContent("retrieval eval");
    await waitForDiagnosticsToSettle();
  });

  it("shows unsupported empty states without retrieval candidates", async () => {
    render(<KnowledgeAtelier agentId="agt_demo" initialDocuments={[]} />);

    expect(
      screen.getByText("No knowledge sources indexed"),
    ).toBeInTheDocument();
    expect(screen.getByText("No chunks available")).toBeInTheDocument();
    expect(
      screen.getByText("No scored retrieval candidates"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Save as retrieval eval" }),
    ).toBeDisabled();
    expect(screen.getByTestId("retrieval-why-panel")).toHaveTextContent(
      "No retrieval to explain",
    );
    await waitForDiagnosticsToSettle();
  });

  it("separates backend-unavailable state from a true empty knowledge base", async () => {
    render(
      <KnowledgeAtelier
        agentId="agt_demo"
        degradedReason="Knowledge documents require cp-api."
        initialDocuments={[]}
      />,
    );

    expect(screen.getByText("Knowledge service unavailable")).toBeInTheDocument();
    expect(screen.queryByText("No knowledge sources indexed")).not.toBeInTheDocument();
    expect(screen.getByTestId("kb-degraded")).toHaveTextContent(
      /knowledge service unavailable/i,
    );
    await waitForDiagnosticsToSettle();
  });

  it("does not show fixture inverse-retrieval misses when cp-api is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(
      <KnowledgeAtelier agentId="agt_demo" initialDocuments={readyDocs} />,
    );

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Can I cancel my annual plan if I am in California/i),
    ).not.toBeInTheDocument();
  });

  it("surfaces degraded source errors and readiness blockers", async () => {
    render(
      <KnowledgeAtelier
        agentId="agt_demo"
        initialDocuments={[
          {
            ...readyDocs[0]!,
            id: "doc_error",
            name: "legal_policy.pdf",
            status: "error",
          },
        ]}
      />,
    );

    expect(screen.getByTestId("knowledge-source-doc_error")).toHaveTextContent(
      "Source needs attention",
    );
    expect(screen.getByTestId("knowledge-readiness")).toHaveTextContent(
      "Fix failed syncs",
    );
    await waitForDiagnosticsToSettle();
  });
});
