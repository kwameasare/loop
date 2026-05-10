import { describe, expect, it } from "vitest";

import {
  CoBuilderConsentError,
  FIXTURE_ACTION_DRIVE,
  FIXTURE_ACTION_SUGGEST,
  FIXTURE_OPERATOR,
  FIXTURE_REVIEW,
  ReviewShapeError,
  applyCoBuilderAction,
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
  it("requires cp-api configuration instead of returning fixture workspace data", async () => {
    await expect(fetchCoBuilderWorkspace("ws-1")).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required for Co-Builder calls",
    );
  });

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

describe("applyCoBuilderAction", () => {
  it("posts consented apply requests to cp-api and returns workflow evidence", async () => {
    const fetcher = async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe(
        "https://cp.example/v1/workspaces/ws-1/cobuilder/actions/act_offer_callback/apply",
      );
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        agent_id: "agent-1",
        selection_context: "agents/refunds-bot/flow/escalate.ts",
      });
      return new Response(
        JSON.stringify({
          appliedAt: "2026-01-01T00:00:00Z",
          evidenceRef: "audit/cobuilder/act_offer_callback/applied",
          branch: {
            id: "br_1",
            name: "cobuilder/act-offer-callback",
            base_version_id: "v1",
            status: "active",
          },
          changeSet: {
            id: "cs_1",
            branch_id: "br_1",
            name: "Offer callback",
            status: "draft",
            source_type: "ai_cobuilder",
          },
          nextUrl: "/agents/agent-1/deploys?change_set=cs_1",
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      );
    };

    const out = await applyCoBuilderAction("ws-1", "act_offer_callback", {
      baseUrl: "https://cp.example",
      agentId: "agent-1",
      selectionContext: "agents/refunds-bot/flow/escalate.ts",
      fetcher: fetcher as typeof fetch,
    });

    expect(out.changeSet?.id).toBe("cs_1");
    expect(out.nextUrl).toContain("change_set=cs_1");
  });
});
