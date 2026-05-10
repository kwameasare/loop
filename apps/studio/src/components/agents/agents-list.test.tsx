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
  });

  it("renders an empty-state when no agents exist", () => {
    render(<AgentsList agents={[]} />);
    expect(screen.getByTestId("agents-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("agents-list")).not.toBeInTheDocument();
  });
});
