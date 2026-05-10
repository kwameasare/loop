import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentKbPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("AgentKbPage", () => {
  afterEach(() => {
    if (ORIGINAL_BASE === undefined) delete process.env.LOOP_CP_API_BASE_URL;
    else process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
    vi.unstubAllGlobals();
  });

  it("fails closed when the knowledge service errors", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () => new Response("boom", { status: 500 })),
    );

    render(await AgentKbPage({ params: { agent_id: "agent_kb" } }));

    expect(screen.getByTestId("kb-degraded")).toHaveTextContent(
      "Knowledge service error: cp-api GET /agents/agent_kb/kb/documents -> 500",
    );
    expect(
      screen.queryByText("No knowledge sources indexed"),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByText("Inverse retrieval unavailable"),
    ).toBeInTheDocument();
  });

  it("passes evidence query state into Knowledge Atelier", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json({
          items: [
            {
              id: "doc_error",
              agentId: "agent_kb",
              name: "policy.pdf",
              contentType: "application/pdf",
              bytes: 1000,
              status: "error",
              uploadedAt: "2026-05-09T10:00:00Z",
              lastRefreshedAt: null,
            },
          ],
        }),
      ),
    );

    render(
      await AgentKbPage({
        params: { agent_id: "agent_kb" },
        searchParams: { filter: "stale", view: "retrieval" },
      }),
    );

    expect(screen.getByTestId("knowledge-focused-query")).toHaveTextContent(
      "Stale-source filter is active",
    );
    expect(screen.getByTestId("retrieval-lab")).toHaveAttribute(
      "data-focused",
      "true",
    );
  });
});
