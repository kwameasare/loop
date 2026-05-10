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
});
