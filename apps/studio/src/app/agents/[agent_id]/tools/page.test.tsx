import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import AgentToolsPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("AgentToolsPage", () => {
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
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
});
