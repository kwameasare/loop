import { describe, expect, it, vi } from "vitest";

import {
  FIXTURE_THREADS,
  isThreadStale,
  resolveThreadAsEval,
  ThreadResolutionError,
} from "./comments";

import {
  ApprovalValidationError,
  clampPlayhead,
  eventAtPlayhead,
  fetchCollaborationWorkspace,
  FIXTURE_CHANGESET,
  FIXTURE_PAIR_DEBUG,
  isChangesetReadyToMerge,
  pendingAxes,
  PlayheadError,
  presenceSocketUrl,
  resolveCommentAsEvalCase,
  setPlayhead,
  validateChangesetApprovals,
} from "./collaboration";

describe("comment threads", () => {
  it("flags stale when observedAt differs from anchor authoredAt", () => {
    const [t1, t2] = FIXTURE_THREADS;
    expect(isThreadStale(t1)).toBe(false);
    expect(isThreadStale(t2)).toBe(true);
  });

  it("resolves a thread into an eval spec", () => {
    const [t1] = FIXTURE_THREADS;
    const resolved = resolveThreadAsEval(t1, {
      threadId: t1.id,
      evalSpecId: "eval_refund_callback_over_200",
      resolvedBy: "u_kojo",
      resolvedAt: "2025-02-21T11:00:00Z",
      evidenceRef: "audit/comments/cm_resolve_1",
    });
    expect(resolved.resolution?.kind).toBe("eval_spec");
    expect(resolved.resolution?.evalSpecId).toBe(
      "eval_refund_callback_over_200",
    );
  });

  it("refuses to double-resolve or to resolve with empty spec id", () => {
    const [t1] = FIXTURE_THREADS;
    const once = resolveThreadAsEval(t1, {
      threadId: t1.id,
      evalSpecId: "eval_a",
      resolvedBy: "u_kojo",
      resolvedAt: "2025-02-21T11:00:00Z",
      evidenceRef: "audit/comments/cm_resolve_a",
    });
    expect(() =>
      resolveThreadAsEval(once, {
        threadId: t1.id,
        evalSpecId: "eval_b",
        resolvedBy: "u_kojo",
        resolvedAt: "2025-02-21T11:01:00Z",
        evidenceRef: "audit/comments/cm_resolve_b",
      }),
    ).toThrow(ThreadResolutionError);
    expect(() =>
      resolveThreadAsEval(t1, {
        threadId: t1.id,
        evalSpecId: "   ",
        resolvedBy: "u_kojo",
        resolvedAt: "2025-02-21T11:00:00Z",
        evidenceRef: "audit/comments/cm_resolve_c",
      }),
    ).toThrow(ThreadResolutionError);
  });
});

describe("changeset approvals", () => {
  it("validates the fixture", () => {
    expect(() => validateChangesetApprovals(FIXTURE_CHANGESET)).not.toThrow();
  });

  it("requires every required axis", () => {
    const missing = {
      ...FIXTURE_CHANGESET,
      approvals: FIXTURE_CHANGESET.approvals.filter((a) => a.axis !== "latency"),
    };
    expect(() => validateChangesetApprovals(missing)).toThrow(
      ApprovalValidationError,
    );
  });

  it("requires rationale on rejected/changes_requested", () => {
    const noRationale = {
      ...FIXTURE_CHANGESET,
      approvals: FIXTURE_CHANGESET.approvals.map((a) =>
        a.axis === "cost" ? { ...a, rationale: "" } : a,
      ),
    };
    expect(() => validateChangesetApprovals(noRationale)).toThrow(
      ApprovalValidationError,
    );
  });

  it("isChangesetReadyToMerge only when all approved", () => {
    expect(isChangesetReadyToMerge(FIXTURE_CHANGESET)).toBe(false);
    const allGreen = {
      ...FIXTURE_CHANGESET,
      approvals: FIXTURE_CHANGESET.approvals.map((a) => {
        const { rationale: _rationale, ...rest } = a;
        return {
          ...rest,
          state: "approved" as const,
          reviewer: a.reviewer ?? "Latency Bot",
          decidedAt: a.decidedAt ?? "2025-02-21T11:36:00Z",
        };
      }),
    };
    expect(isChangesetReadyToMerge(allGreen)).toBe(true);
  });

  it("pendingAxes lists non-approved axes", () => {
    expect(pendingAxes(FIXTURE_CHANGESET)).toEqual(["cost", "latency"]);
  });
});

describe("pair-debug shared playhead", () => {
  it("clamps below min and above max", () => {
    expect(clampPlayhead(FIXTURE_PAIR_DEBUG, -100)).toBe(0);
    expect(clampPlayhead(FIXTURE_PAIR_DEBUG, 999_999)).toBe(2600);
  });

  it("rejects NaN offsets", () => {
    expect(() => clampPlayhead(FIXTURE_PAIR_DEBUG, Number.NaN)).toThrow(
      PlayheadError,
    );
  });

  it("eventAtPlayhead returns the latest event <= playhead", () => {
    const ev = eventAtPlayhead(FIXTURE_PAIR_DEBUG);
    expect(ev?.id).toBe("ev_3"); // playhead 1200ms; ev_3 @ 1180ms
    const advanced = setPlayhead(FIXTURE_PAIR_DEBUG, 2200);
    expect(eventAtPlayhead(advanced)?.id).toBe("ev_4");
  });

  it("setPlayhead clamps and returns a new session", () => {
    const back = setPlayhead(FIXTURE_PAIR_DEBUG, -50);
    expect(back.playheadMs).toBe(0);
    expect(back).not.toBe(FIXTURE_PAIR_DEBUG);
  });
});

describe("fetchCollaborationWorkspace", () => {
  it("derives review presence and pair-debug state from live traces", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.includes("/workspaces/ws-1/traces")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                workspace_id: "ws-1",
                trace_id: "b".repeat(32),
                turn_id: "11111111-1111-4111-8111-111111111111",
                conversation_id: "22222222-2222-4222-8222-222222222222",
                agent_id: "33333333-3333-4333-8333-333333333333",
                started_at: "2026-05-07T12:00:00Z",
                duration_ms: 100,
                span_count: 1,
                error: false,
              },
            ],
            next_cursor: null,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      if (url.includes("/audit/events")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "ev-1",
                occurred_at: "2026-05-07T12:00:00Z",
                workspace_id: "ws-1",
                actor_sub: "sam@example.com",
                action: "agent.version.promoted",
                resource_type: "agent_version",
                resource_id: "v1",
                outcome: "success",
              },
            ],
            total: 1,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          trace_id: "b".repeat(32),
          turn_id: "11111111-1111-4111-8111-111111111111",
          conversation_id: "22222222-2222-4222-8222-222222222222",
          agent_id: "33333333-3333-4333-8333-333333333333",
          started_at: "2026-05-07T12:00:00Z",
          duration_ms: 100,
          span_count: 1,
          error: false,
          spans: [
            {
              span_id: "span-1",
              parent_span_id: null,
              kind: "channel",
              name: "runtime turn",
              started_at: "2026-05-07T12:00:00Z",
              latency_ms: 100,
              cost_usd: 0,
              status: "ok",
              attrs: {},
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const workspace = await fetchCollaborationWorkspace("ws-1", {
      baseUrl: "https://cp.example.test/v1",
      fetcher,
    });

    expect(workspace.presence[0].focus).toContain("trace/");
    expect(workspace.changeset.title).toContain("agent.version.promoted");
    expect(workspace.pairDebug.trace[0].evidenceRef).toContain("span-1");
  });
});

describe("collaboration wireup", () => {
  it("builds presence sockets against the canonical cp-api websocket path", () => {
    expect(
      presenceSocketUrl("ws-1", {
        baseUrl: "https://cp.example.test/v1",
        callerSub: "sam@example.com",
      }),
    ).toBe(
      "wss://cp.example.test/v1/workspaces/ws-1/presence?caller_sub=sam%40example.com",
    );
  });

  it("resolves comments into eval cases through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          comment_id: "cmt_1",
          resolved_by: "sam@example.com",
          eval_case_created: true,
          case_id: "eval_comment_cmt_1",
          expected_behavior: "Refund the order.",
          failure_reason: "The agent escalated.",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const result = await resolveCommentAsEvalCase(
      "agt_1",
      "cmt_1",
      {
        expected_behavior: "Refund the order.",
        failure_reason: "The agent escalated.",
      },
      {
        baseUrl: "https://cp.example.test/v1",
        fetcher,
      },
    );

    expect(result.case_id).toBe("eval_comment_cmt_1");
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.example.test/v1/agents/agt_1/comments/cmt_1/resolve");
    expect(JSON.parse(String(init?.body))).toMatchObject({
      also_create_eval_case: true,
    });
  });
});
