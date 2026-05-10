import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentEvidenceRail } from "./agent-evidence-rail";

describe("AgentEvidenceRail", () => {
  it("shows behavior-specific evidence beside behavior editing", () => {
    render(
      <AgentEvidenceRail
        agentId="agent_1"
        pathname="/agents/agent_1/behavior"
      />,
    );

    expect(screen.getByTestId("agent-evidence-context")).toHaveTextContent(
      "Behavior evidence",
    );
    expect(
      screen.getByTestId("agent-evidence-link-failed-traces"),
    ).toHaveAttribute("href", "/agents/agent_1/traces?filter=failed");
    expect(
      screen.getByTestId("agent-evidence-link-approval-requirements"),
    ).toHaveAttribute("href", "/agents/agent_1/governance");
  });

  it("switches evidence context for tool and deployment routes", () => {
    const { rerender } = render(
      <AgentEvidenceRail agentId="agent_1" pathname="/agents/agent_1/tools" />,
    );

    expect(screen.getByTestId("agent-evidence-context")).toHaveTextContent(
      "Tool evidence",
    );
    expect(screen.getByTestId("agent-evidence-link-secrets")).toHaveAttribute(
      "href",
      "/agents/agent_1/secrets",
    );

    rerender(
      <AgentEvidenceRail
        agentId="agent_1"
        pathname="/agents/agent_1/deploys"
      />,
    );
    expect(screen.getByTestId("agent-evidence-context")).toHaveTextContent(
      "Deployment evidence",
    );
    expect(
      screen.getByTestId("agent-evidence-link-release-candidate"),
    ).toHaveAttribute(
      "href",
      "/agents/agent_1/deploys?panel=release-candidate",
    );
  });

  it("falls back to general workbench evidence for the overview", () => {
    render(<AgentEvidenceRail agentId="agent_1" pathname="/agents/agent_1" />);

    expect(screen.getByTestId("agent-evidence-context")).toHaveTextContent(
      "Workbench evidence",
    );
    expect(screen.getByTestId("agent-evidence-link-traces")).toHaveAttribute(
      "href",
      "/agents/agent_1/traces",
    );
  });
});
