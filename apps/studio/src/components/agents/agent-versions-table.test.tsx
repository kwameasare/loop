import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentVersionsTable } from "./agent-versions-table";
import { type AgentVersionSummary } from "@/lib/cp-api";

function version(
  versionNumber: number,
  config_json: Record<string, unknown>,
): AgentVersionSummary {
  return {
    id: `ver_${versionNumber}`,
    agent_id: "agt_42",
    version: versionNumber,
    deploy_state: versionNumber === 3 ? "active" : "inactive",
    eval_status: versionNumber === 1 ? "failed" : "passed",
    deployed_at: `2026-05-0${versionNumber}T10:00:00Z`,
    created_at: `2026-05-0${versionNumber}T09:00:00Z`,
    created_by: null,
    code_hash: `abcdef12345${versionNumber}`,
    config_json,
  };
}

describe("AgentVersionsTable", () => {
  it("renders version pagination and opens a config diff modal", () => {
    render(
      <AgentVersionsTable
        agentId="agt_42"
        nextCursor="cur_2"
        versions={[
          version(3, {
            model: "gpt-4.1-mini",
            tools: ["search"],
            rollout: { percent: 100 },
          }),
          version(2, {
            model: "gpt-4.1",
            tools: ["search"],
            rollout: { percent: 25 },
          }),
          version(1, { model: "gpt-4.1", tools: [] }),
        ]}
      />,
    );

    expect(screen.getAllByTestId("agent-version-row")).toHaveLength(3);
    expect(screen.getByTestId("agent-versions-next")).toHaveAttribute(
      "href",
      "/agents/agt_42/versions?cursor=cur_2",
    );

    fireEvent.click(screen.getByTestId("agent-version-diff-3"));

    const modal = screen.getByTestId("agent-version-diff-modal");
    expect(within(modal).getByText("v3 config diff")).toBeInTheDocument();
    expect(within(modal).getByText("Compared with v2")).toBeInTheDocument();
    expect(within(modal).getByText("model")).toBeInTheDocument();
    expect(within(modal).getByText("gpt-4.1")).toBeInTheDocument();
    expect(within(modal).getByText("gpt-4.1-mini")).toBeInTheDocument();
    expect(within(modal).getByText("rollout.percent")).toBeInTheDocument();
  });

  it("shows an empty state when no versions exist", () => {
    render(
      <AgentVersionsTable agentId="agt_42" nextCursor={null} versions={[]} />,
    );

    expect(screen.getByTestId("agent-versions-empty")).toHaveTextContent(
      "No versions yet",
    );
  });

  it("explains when a prior version is not loaded for the diff", () => {
    render(
      <AgentVersionsTable
        agentId="agt_42"
        nextCursor={null}
        versions={[version(1, { model: "gpt-4.1" })]}
      />,
    );

    fireEvent.click(screen.getByTestId("agent-version-diff-1"));

    expect(
      screen.getByTestId("agent-version-diff-missing-prior"),
    ).toHaveTextContent("previous version loaded");
  });
});
