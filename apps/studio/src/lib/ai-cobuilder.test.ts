import { describe, expect, it } from "vitest";

import {
  CoBuilderConsentError,
  FIXTURE_ACTION_DRIVE,
  FIXTURE_ACTION_SUGGEST,
  FIXTURE_OPERATOR,
  FIXTURE_REVIEW,
  ReviewShapeError,
  applyAction,
  blockingBullets,
  createFixtureCoBuilderWorkspace,
  evaluateConsent,
  fetchCoBuilderWorkspace,
  validateAdversarialReview,
} from "./ai-cobuilder";

describe("evaluateConsent", () => {
  it("accepts an action within mode, scope, and budget", () => {
    const out = evaluateConsent(FIXTURE_ACTION_SUGGEST, FIXTURE_OPERATOR);
    expect(out.ok).toBe(true);
    expect(out.reasons).toEqual([]);
  });

  it("rejects when action mode exceeds operator's max mode", () => {
    const out = evaluateConsent(FIXTURE_ACTION_DRIVE, FIXTURE_OPERATOR);
    expect(out.ok).toBe(false);
    expect(out.reasons.find((r) => r.code === "mode")).toBeDefined();
  });

  it("rejects when scopes are missing", () => {
    const out = evaluateConsent(FIXTURE_ACTION_DRIVE, {
      ...FIXTURE_OPERATOR,
      maxMode: "drive",
    });
    expect(out.ok).toBe(false);
    expect(out.reasons.find((r) => r.code === "scope")?.message).toContain(
      "kb:rebuild",
    );
  });

  it("rejects when budget is exceeded", () => {
    const out = evaluateConsent(FIXTURE_ACTION_SUGGEST, {
      ...FIXTURE_OPERATOR,
      budgetRemainingUsd: 0.01,
    });
    expect(out.ok).toBe(false);
    expect(out.reasons.find((r) => r.code === "budget")).toBeDefined();
  });
});

describe("applyAction", () => {
  it("returns appliedAt and evidenceRef on success", () => {
    const out = applyAction(
      FIXTURE_ACTION_SUGGEST,
      FIXTURE_OPERATOR,
      () => "2026-01-01T00:00:00Z",
    );
    expect(out.appliedAt).toBe("2026-01-01T00:00:00Z");
    expect(out.evidenceRef).toBe(
      "audit/cobuilder/act_offer_callback/applied",
    );
  });

  it("throws CoBuilderConsentError when consent fails", () => {
    expect(() => applyAction(FIXTURE_ACTION_DRIVE, FIXTURE_OPERATOR)).toThrow(
      CoBuilderConsentError,
    );
  });
});

describe("validateAdversarialReview", () => {
  it("accepts the canonical 5-bullet review with evidence", () => {
    expect(() => validateAdversarialReview(FIXTURE_REVIEW)).not.toThrow();
  });

  it("rejects reviews that are not exactly five bullets", () => {
    expect(() =>
      validateAdversarialReview({
        ...FIXTURE_REVIEW,
        bullets: FIXTURE_REVIEW.bullets.slice(0, 4),
      }),
    ).toThrow(ReviewShapeError);
  });

  it("rejects bullets missing evidenceRef", () => {
    expect(() =>
      validateAdversarialReview({
        ...FIXTURE_REVIEW,
        bullets: FIXTURE_REVIEW.bullets.map((b, i) =>
          i === 0 ? { ...b, evidenceRef: "  " } : b,
        ),
      }),
    ).toThrow(/missing evidenceRef/);
  });
});

describe("blockingBullets", () => {
  it("returns only block-severity bullets", () => {
    const blockers = blockingBullets(FIXTURE_REVIEW);
    expect(blockers).toHaveLength(1);
    expect(blockers[0].id).toBe("rb_3");
  });
});

describe("fetchCoBuilderWorkspace", () => {
  it("loads the workspace-scoped Co-Builder contract from cp-api", async () => {
    const fetcher = async (input: RequestInfo | URL) => {
      expect(String(input)).toBe(
        "https://cp.example/v1/workspaces/ws-1/cobuilder?agent_id=agent-1",
      );
      return new Response(
        JSON.stringify(createFixtureCoBuilderWorkspace("ws-1")),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    };

    const workspace = await fetchCoBuilderWorkspace("ws-1", {
      baseUrl: "https://cp.example",
      agentId: "agent-1",
      fetcher: fetcher as typeof fetch,
    });

    expect(workspace.workspaceId).toBe("ws-1");
    expect(workspace.actions).toHaveLength(2);
  });
});
