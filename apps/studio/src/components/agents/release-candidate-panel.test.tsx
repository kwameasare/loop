import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  localAgentWorkflow,
  type AgentBranch,
  type AgentChangeSet,
  type AgentReleaseCandidate,
  type AgentWorkflow,
} from "@/lib/agent-workflow";

import { ReleaseCandidatePanel } from "./release-candidate-panel";

function emptyWorkflow(): AgentWorkflow {
  return { branches: [], change_sets: [], release_candidates: [] };
}

describe("ReleaseCandidatePanel", () => {
  it("renders branch, change set, readiness, candidate version, and approvals", () => {
    render(
      <ReleaseCandidatePanel
        agentId="agent-1"
        initialWorkflow={localAgentWorkflow("agent-1")}
      />,
    );

    expect(screen.getByTestId("release-candidate-panel")).toHaveTextContent(
      "Branch to release candidate",
    );
    expect(screen.getByTestId("workflow-branch")).toHaveTextContent(
      "draft/refund-policy-fix",
    );
    expect(screen.getByTestId("workflow-change-set")).toHaveTextContent(
      "ready for review",
    );
    expect(screen.getByTestId("workflow-release-candidate")).toHaveTextContent(
      "candidate version ver_local_refund",
    );
    expect(screen.getByTestId("workflow-approve-owner")).toBeEnabled();
  });

  it("shows degraded workflow state without enabling release actions", () => {
    render(
      <ReleaseCandidatePanel
        agentId="agent-1"
        initialWorkflow={{
          ...emptyWorkflow(),
          degraded_reason: "LOOP_CP_API_BASE_URL is required",
        }}
      />,
    );

    expect(screen.getByTestId("workflow-degraded")).toHaveTextContent(
      "Release workflow is unavailable",
    );
    expect(screen.getByTestId("workflow-create-branch")).toBeDisabled();
    expect(screen.getByTestId("workflow-create-change-set")).toBeDisabled();
    expect(screen.getByTestId("workflow-create-release-candidate")).toBeDisabled();
  });

  it("walks an empty agent through branch, change set, tests, and release candidate", async () => {
    const branch: AgentBranch = {
      ...localAgentWorkflow("agent-1").branches[0]!,
      id: "br_created",
      name: "draft/current-agent-work",
    };
    const draftChangeSet: AgentChangeSet = {
      ...localAgentWorkflow("agent-1").change_sets[0]!,
      id: "cs_created",
      branch_id: branch.id,
      status: "draft",
      eval_results_ref: null,
      required_eval_suites: [],
    };
    const readyTests: AgentChangeSet = {
      ...draftChangeSet,
      status: "ready_for_tests",
    };
    const readyReview: AgentChangeSet = {
      ...draftChangeSet,
      status: "ready_for_review",
      eval_results_ref: "eval/run/current-agent-work/green",
      required_eval_suites: ["core-regression"],
    };
    const rc: AgentReleaseCandidate = {
      ...localAgentWorkflow("agent-1").release_candidates[0]!,
      id: "rc_created",
      branch_id: branch.id,
      change_set_id: draftChangeSet.id,
      candidate_version_id: "ver_created",
      status: "ready_for_approval",
    };
    const createBranch = vi.fn(async () => branch);
    const createChangeSet = vi.fn(async () => draftChangeSet);
    const markReadyForTests = vi.fn(async () => readyTests);
    const markReadyForReview = vi.fn(async () => readyReview);
    const createReleaseCandidate = vi.fn(async () => rc);

    render(
      <ReleaseCandidatePanel
        agentId="agent-1"
        initialWorkflow={emptyWorkflow()}
        createBranch={createBranch}
        createChangeSet={createChangeSet}
        markReadyForTests={markReadyForTests}
        markReadyForReview={markReadyForReview}
        createReleaseCandidate={createReleaseCandidate}
      />,
    );

    expect(screen.getByTestId("workflow-create-change-set")).toBeDisabled();
    fireEvent.click(screen.getByTestId("workflow-create-branch"));
    await waitFor(() => expect(createBranch).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("workflow-create-change-set"));
    await waitFor(() => expect(createChangeSet).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("workflow-ready-tests"));
    await waitFor(() => expect(markReadyForTests).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("workflow-ready-review"));
    await waitFor(() => expect(markReadyForReview).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("workflow-create-release-candidate"));
    await waitFor(() => expect(createReleaseCandidate).toHaveBeenCalled());

    expect(screen.getByTestId("workflow-release-candidate")).toHaveTextContent(
      "candidate version ver_created",
    );
    expect(screen.getByTestId("workflow-change-set")).toHaveTextContent(
      "converted to release candidate",
    );
  });
});
