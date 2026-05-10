import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentWorkbenchControls } from "./agent-workbench-controls";

describe("AgentWorkbenchControls", () => {
  it("routes each topbar control to an agent-scoped durable surface", () => {
    render(<AgentWorkbenchControls agentId="agent_1" />);

    expect(
      screen.getByTestId("agent-workbench-control-versions"),
    ).toHaveAttribute("href", "/agents/agent_1/versions");
    expect(
      screen.getByTestId("agent-workbench-control-environment"),
    ).toHaveAttribute("href", "/agents/agent_1/deploys?panel=environments");
    expect(screen.getByTestId("agent-workbench-control-tests")).toHaveAttribute(
      "href",
      "/agents/agent_1/simulator",
    );
    expect(
      screen.getByTestId("agent-workbench-control-change-set"),
    ).toHaveTextContent("Open Change Set");
    expect(
      screen.getByTestId("agent-workbench-control-change-set"),
    ).toHaveAttribute("href", "/agents/agent_1/workflow");
    expect(
      screen.getByTestId("agent-workbench-control-promote"),
    ).toHaveAttribute("href", "/agents/agent_1/deploys?panel=promotion");
    expect(
      screen.getByTestId("agent-workbench-control-governance"),
    ).toHaveAttribute("href", "/agents/agent_1/governance");
  });
});
