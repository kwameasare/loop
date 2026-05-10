import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentTestDrawer } from "./agent-test-drawer";

describe("AgentTestDrawer", () => {
  it("keeps test and replay actions adjacent to the agent workbench", () => {
    render(<AgentTestDrawer agentId="agent_1" />);

    expect(screen.getByTestId("agent-test-drawer")).toHaveTextContent(
      "Test drawer",
    );
    expect(screen.getByTestId("agent-test-action-simulation")).toHaveAttribute(
      "href",
      "/agents/agent_1/simulator",
    );
    expect(
      screen.getByTestId("agent-test-action-channel-preview"),
    ).toHaveTextContent("WhatsApp");
    expect(
      screen.getByTestId("agent-test-action-replay-production"),
    ).toHaveAttribute("href", "/agents/agent_1/traces?mode=replay");
    expect(screen.getByTestId("agent-test-action-preflight")).toHaveAttribute(
      "href",
      "/agents/agent_1/deploys",
    );
  });
});
