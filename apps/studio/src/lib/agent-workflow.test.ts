import { describe, expect, it, vi } from "vitest";

import {
  approveReleaseCandidate,
  createAgentBranch,
  createAgentChangeSet,
  createReleaseCandidate,
  listAgentWorkflow,
  localAgentWorkflow,
  markChangeSetReadyForReview,
  markChangeSetReadyForTests,
} from "./agent-workflow";

describe("agent workflow client", () => {
  it("builds local branch, change set, and release candidate workflow", () => {
    const workflow = localAgentWorkflow("agent-1");

    expect(workflow.branches[0]).toMatchObject({
      status: "active",
      base_version_id: "production",
    });
    expect(workflow.change_sets[0]).toMatchObject({
      status: "ready_for_review",
      source_type: "failed_eval",
    });
    expect(workflow.release_candidates[0]).toMatchObject({
      status: "ready_for_approval",
      candidate_version_id: "ver_local_refund",
    });
  });

  it("calls workflow endpoints for the full release candidate path", async () => {
    const workflow = localAgentWorkflow("agent-1");
    const branch = workflow.branches[0]!;
    const changeSet = workflow.change_sets[0]!;
    const releaseCandidate = workflow.release_candidates[0]!;
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/workflow")) {
        return new Response(JSON.stringify(workflow), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/branches")) {
        return new Response(JSON.stringify(branch), {
          status: 201,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/change-sets")) {
        return new Response(JSON.stringify({ ...changeSet, status: "draft" }), {
          status: 201,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/ready-for-tests")) {
        return new Response(
          JSON.stringify({ ...changeSet, status: "ready_for_tests" }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      if (url.endsWith("/ready-for-review")) {
        return new Response(JSON.stringify(changeSet), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/release-candidates")) {
        return new Response(JSON.stringify(releaseCandidate), {
          status: 201,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/approve")) {
        return new Response(
          JSON.stringify({ ...releaseCandidate, status: "approved" }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      throw new Error(`unexpected ${init?.method} ${url}`);
    });

    const listed = await listAgentWorkflow("agent-1", {
      baseUrl: "https://cp.test",
      fetcher,
    });
    const createdBranch = await createAgentBranch(
      "agent-1",
      { name: "draft/refund" },
      { baseUrl: "https://cp.test", fetcher },
    );
    const createdChangeSet = await createAgentChangeSet(
      "agent-1",
      { branch_id: branch.id, name: "Fix refund policy" },
      { baseUrl: "https://cp.test", fetcher },
    );
    const readyTests = await markChangeSetReadyForTests(
      "agent-1",
      changeSet.id,
      {
        baseUrl: "https://cp.test",
        fetcher,
        fallbackChangeSet: changeSet,
      },
    );
    const readyReview = await markChangeSetReadyForReview(
      "agent-1",
      changeSet.id,
      { eval_results_ref: "eval/run/green", passed: true },
      { baseUrl: "https://cp.test", fetcher, fallbackChangeSet: changeSet },
    );
    const rc = await createReleaseCandidate(
      "agent-1",
      changeSet.id,
      { required_eval_suites: ["refund-core"] },
      { baseUrl: "https://cp.test", fetcher },
    );
    const approved = await approveReleaseCandidate(
      "agent-1",
      releaseCandidate.id,
      { approval_id: "owner" },
      {
        baseUrl: "https://cp.test",
        fetcher,
        fallbackReleaseCandidate: releaseCandidate,
      },
    );

    expect(listed.branches).toHaveLength(1);
    expect(createdBranch.id).toBe(branch.id);
    expect(createdChangeSet.status).toBe("draft");
    expect(readyTests.status).toBe("ready_for_tests");
    expect(readyReview.status).toBe("ready_for_review");
    expect(rc.candidate_version_id).toBe("ver_local_refund");
    expect(approved.status).toBe("approved");
    expect(fetcher.mock.calls.map(([url]) => String(url))).toEqual([
      "https://cp.test/v1/agents/agent-1/workflow",
      "https://cp.test/v1/agents/agent-1/branches",
      "https://cp.test/v1/agents/agent-1/change-sets",
      "https://cp.test/v1/agents/agent-1/change-sets/cs_local_refund/ready-for-tests",
      "https://cp.test/v1/agents/agent-1/change-sets/cs_local_refund/ready-for-review",
      "https://cp.test/v1/agents/agent-1/change-sets/cs_local_refund/release-candidates",
      "https://cp.test/v1/agents/agent-1/release-candidates/rc_local_refund/approve",
    ]);
  });
});
