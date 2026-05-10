import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AgentWorkflowPage from "./page";

vi.mock("@/components/agents/release-candidate-panel", () => ({
  ReleaseCandidatePanel: ({ initialWorkflow }: { initialWorkflow: unknown }) => (
    <section data-testid="release-candidate-panel">
      {JSON.stringify(initialWorkflow)}
    </section>
  ),
}));

vi.mock("@/lib/agent-workflow", () => ({
  listAgentWorkflow: vi.fn(async () => ({
    branches: [
      {
        id: "br_replay",
        agent_id: "agent_replay",
        name: "fork/trace-frame",
        base_version_id: "production",
        created_by_user_id: "owner-1",
        status: "active",
        created_at: "2026-05-09T00:00:00Z",
        updated_at: "2026-05-09T00:00:00Z",
      },
    ],
    change_sets: [
      {
        id: "cs_replay",
        agent_id: "agent_replay",
        branch_id: "br_replay",
        name: "Replay fork from tool-plan",
        summary: "Trace replay fork.",
        source_type: "trace_replay_frame",
        source_refs: ["trace_1", "frame_1"],
        changed_objects: [],
        status: "draft",
        created_by_user_id: "owner-1",
        created_at: "2026-05-09T00:00:00Z",
        updated_at: "2026-05-09T00:00:00Z",
        eval_results_ref: null,
        required_eval_suites: [],
      },
    ],
    release_candidates: [],
  })),
}));

describe("AgentWorkflowPage", () => {
  it("renders replay fork branch context instead of sending next_url to a missing route", async () => {
    render(
      await AgentWorkflowPage({
        params: { agent_id: "agent_replay" },
        searchParams: { branch_id: "br_replay" },
      }),
    );

    expect(screen.getByTestId("agent-workflow-tab")).toBeInTheDocument();
    expect(screen.getByTestId("workflow-deep-link-context")).toHaveTextContent(
      "fork/trace-frame",
    );
    expect(screen.getByTestId("workflow-deep-link-context")).toHaveTextContent(
      "cs_replay",
    );
    expect(screen.getByTestId("release-candidate-panel")).toHaveTextContent(
      "br_replay",
    );
  });
});
