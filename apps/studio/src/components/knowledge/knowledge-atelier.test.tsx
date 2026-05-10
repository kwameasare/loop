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
