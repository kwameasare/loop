import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentToolsPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("AgentToolsPage", () => {
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
    vi.unstubAllGlobals();
  });

  it("surfaces control-plane failures instead of pretending the catalog is simply empty", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(await AgentToolsPage({ params: { agent_id: "agent_support" } }));

    expect(screen.getByTestId("tools-room")).toBeInTheDocument();
    expect(screen.getByText("Tool catalog is empty")).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required for tools calls/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("tools-room-import")).toBeInTheDocument();
  });

  it("surfaces a missing tool-binding route instead of an empty catalog", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        new Response("missing", { status: 404 }),
      ),
    );

    render(await AgentToolsPage({ params: { agent_id: "agent_support" } }));

    expect(screen.getByTestId("tools-room")).toBeInTheDocument();
    expect(screen.getByText("Tool catalog is empty")).toBeInTheDocument();
    expect(screen.getByText(/tool-binding route/i)).toBeInTheDocument();
    expect(screen.queryByText("lookup_order")).not.toBeInTheDocument();
  });
});
