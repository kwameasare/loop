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
    updated_at: "2026-04-29T12:00:00Z",
    workspace_id: "ws_1",
  },
  {
    id: "agt_qa",
    name: "QA Bot",
    slug: "qa-bot",
    description: "Internal Q&A over the engineering handbook.",
    active_version: null,
    updated_at: "2026-04-28T09:30:00Z",
    workspace_id: "ws_1",
  },
];

describe("AgentsList", () => {
  it("renders one row per agent with status + model", () => {
    render(<AgentsList agents={fixture} />);
    const rows = screen.getAllByTestId("agents-item");
    expect(rows).toHaveLength(2);
    expect(screen.getByRole("heading", { name: "Support" })).toBeInTheDocument();
    expect(screen.getByText(/slug: support/)).toBeInTheDocument();
    expect(screen.getByText("v3")).toBeInTheDocument();
    expect(screen.getByText("vdraft")).toBeInTheDocument();
  });

  it("renders an empty-state when no agents exist", () => {
    render(<AgentsList agents={[]} />);
    expect(screen.getByTestId("agents-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("agents-list")).not.toBeInTheDocument();
  });
});
