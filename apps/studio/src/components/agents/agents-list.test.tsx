import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { AgentsList } from "./agents-list";
import type { AgentSummary } from "@/lib/cp-api";

const fixture: AgentSummary[] = [
  {
    id: "agt_support",
    name: "Support",
    model: "gpt-4o-mini",
    description: "Customer-support agent with KB grounding.",
    status: "active",
    updated_at: "2026-04-29T12:00:00Z",
  },
  {
    id: "agt_qa",
    name: "QA Bot",
    model: "claude-3-5-haiku",
    description: "Internal Q&A over the engineering handbook.",
    status: "draft",
    updated_at: "2026-04-28T09:30:00Z",
  },
];

describe("AgentsList", () => {
  it("renders one row per agent with status + model", () => {
    render(<AgentsList agents={fixture} />);
    const rows = screen.getAllByTestId("agents-item");
    expect(rows).toHaveLength(2);
    expect(screen.getByRole("heading", { name: "Support" })).toBeInTheDocument();
    expect(screen.getByText(/model: gpt-4o-mini/)).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("renders an empty-state when no agents exist", () => {
    render(<AgentsList agents={[]} />);
    expect(screen.getByTestId("agents-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("agents-list")).not.toBeInTheDocument();
  });
});
