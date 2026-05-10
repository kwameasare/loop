import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { AgentsList } from "./agents-list";
import type { AgentSummary } from "@/lib/cp-api";

const fixture: AgentSummary[] = [
  {
    id: "agt_support",
    name: "Support",
    slug: "support",
    description: "Customer-support agent with KB grounding.",
    active_version: 3,
    object_state: "production",
    state_reason: "Agent has an active production version.",
    state_evidence_ref: "deployment/dep_support",
    updated_at: "2026-04-29T12:00:00Z",
    workspace_id: "ws_1",
    owner_user_id: "maya@acme.test",
    backup_owner_user_id: "diego@acme.test",
    environment: "production",
    health_status: "watching",
    open_issue_count: 0,
    open_issue_sources: [],
    commitment_document_id: "commit_support",
    commitment_status: "accepted",
  },
  {
    id: "agt_qa",
    name: "QA Bot",
    slug: "qa-bot",
    description: "Internal Q&A over the engineering handbook.",
    active_version: null,
    object_state: "draft",
    state_reason: "Agent has no active production version.",
    state_evidence_ref: "agent.draft",
    updated_at: "2026-04-28T09:30:00Z",
    workspace_id: "ws_1",
    owner_user_id: null,
    backup_owner_user_id: null,
    environment: "draft",
    health_status: "needs_attention",
    open_issue_count: 3,
    open_issue_sources: [
      "commitment/commit_qa:missing:owner_user_id",
      "commitment/commit_qa:backup_owner_missing",
      "commitment/commit_qa:missing:worst_case_failure",
    ],
    commitment_document_id: "commit_qa",
    commitment_status: "draft",
  },
];

describe("AgentsList", () => {
  it("renders one row per agent with status + model", () => {
    render(<AgentsList agents={fixture} />);
    const rows = screen.getAllByTestId("agents-item");
    expect(rows).toHaveLength(2);
    expect(
      screen.getByRole("heading", { name: "Support" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/slug: support/)).toBeInTheDocument();
    expect(screen.getByText("v3")).toBeInTheDocument();
    expect(screen.getByTestId("agent-state-agt_support")).toHaveTextContent(
      "production",
    );
    expect(screen.getByTestId("agent-state-agt_qa")).toHaveTextContent("draft");
    expect(screen.getByText("deployment/dep_support")).toBeInTheDocument();
    expect(screen.getByText("agent.draft")).toBeInTheDocument();
    expect(screen.getByTestId("agent-ownership-agt_support")).toHaveTextContent(
      "maya@acme.test",
    );
    expect(screen.getByTestId("agent-ownership-agt_support")).toHaveTextContent(
      "diego@acme.test",
    );
    expect(screen.getByTestId("agent-health-agt_support")).toHaveTextContent(
      "watching",
    );
    expect(screen.getByTestId("agent-open-issues-agt_support")).toHaveTextContent(
      "No open issues",
    );
    expect(screen.getByTestId("agent-ownership-agt_qa")).toHaveTextContent(
      "Unassigned owner",
    );
    expect(screen.getByTestId("agent-open-issues-agt_qa")).toHaveTextContent(
      "3 open issues",
    );
  });

  it("renders an empty-state when no agents exist", () => {
    render(<AgentsList agents={[]} />);
    expect(screen.getByTestId("agents-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("agents-list")).not.toBeInTheDocument();
  });

  it("renders degraded registry state separately from an empty workspace", () => {
    render(
      <AgentsList
        agents={[]}
        degradedReason="LOOP_CP_API_BASE_URL is required to list agents"
      />,
    );

    expect(screen.getByTestId("agents-degraded")).toHaveTextContent(
      "Agent registry is unavailable",
    );
    expect(screen.queryByTestId("agents-empty")).not.toBeInTheDocument();
  });
});
