import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getAgent } from "@/lib/cp-api";
import { listAgentWorkflow, localAgentWorkflow } from "@/lib/agent-workflow";

import AgentDetailLayout from "./layout";

vi.mock("@/components/agents/agent-evidence-rail", () => ({
  AgentEvidenceRail: ({ agentId }: { agentId: string }) => (
    <aside data-testid="agent-evidence-rail">Evidence {agentId}</aside>
  ),
}));

vi.mock("@/components/agents/agent-test-drawer", () => ({
  AgentTestDrawer: ({ agentId }: { agentId: string }) => (
    <div data-testid="agent-test-drawer">Test {agentId}</div>
  ),
}));

vi.mock("@/components/agents/agent-tabs", () => ({
  AgentTabs: ({ agentId }: { agentId: string }) => (
    <nav data-testid="agent-tabs">Tabs {agentId}</nav>
  ),
}));

vi.mock("@/lib/cp-api", () => ({
  getAgent: vi.fn(),
}));

vi.mock("@/lib/agent-workflow", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/agent-workflow")>();
  return {
    ...actual,
    listAgentWorkflow: vi.fn(),
  };
});

describe("AgentDetailLayout", () => {
  it("renders persistent workbench facts from agent and workflow state", async () => {
    vi.mocked(getAgent).mockResolvedValue({
      id: "agent_1",
      workspace_id: "workspace_1",
      name: "Refund Concierge",
      slug: "refund-concierge",
      description: "Handles refunds.",
      active_version: 24,
      object_state: "canary",
      state_reason: "Canary held for eval review.",
      state_evidence_ref: "deployment/dep_1",
      updated_at: "2026-05-10T00:00:00Z",
    });
    vi.mocked(listAgentWorkflow).mockResolvedValue({
      ...localAgentWorkflow("agent_1"),
      change_sets: [
        {
          ...localAgentWorkflow("agent_1").change_sets[0]!,
          name: "Refund copy fix",
          status: "ready_for_tests",
          updated_at: "2026-05-10T10:00:00Z",
        },
      ],
    });

    render(
      await AgentDetailLayout({
        params: { agent_id: "agent_1" },
        children: <div data-testid="child">Child</div>,
      }),
    );

    expect(screen.getByTestId("agent-local-topbar-facts")).toBeInTheDocument();
    expect(screen.getByTestId("agent-topbar-fact-branch")).toHaveTextContent(
      "draft/refund-policy-fix",
    );
    expect(screen.getByTestId("agent-topbar-fact-draft")).toHaveTextContent(
      "Refund copy fix",
    );
    expect(
      screen.getByTestId("agent-topbar-fact-production"),
    ).toHaveTextContent("v24");
    expect(screen.getByTestId("agent-topbar-fact-health")).toHaveTextContent(
      "Needs attention",
    );
    expect(screen.getByTestId("agent-topbar-fact-openIssues")).toHaveTextContent(
      "1",
    );
    expect(screen.getByTestId("child")).toHaveTextContent("Child");
  });
});
