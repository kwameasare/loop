import { describe, expect, it } from "vitest";

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
  FIXTURE_CHANGESET,
  FIXTURE_PAIR_DEBUG,
  isChangesetReadyToMerge,
  pendingAxes,
  PlayheadError,
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
      approvals: FIXTURE_CHANGESET.approvals.map((a) => ({
        ...a,
        state: "approved" as const,
        rationale: undefined,
        reviewer: a.reviewer ?? "Latency Bot",
        decidedAt: a.decidedAt ?? "2025-02-21T11:36:00Z",
      })),
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
