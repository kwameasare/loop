import { describe, expect, it } from "vitest";

import {
  FIXTURE_EVIDENCE_CONTEXT,
  ResolutionDraftError,
  buildEvalCaseFromResolution,
  createEvidenceContextFromConversation,
  saveResolutionEvalCase,
  suggestOperatorDraftFromConversation,
} from "./inbox-resolution";

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("buildEvalCaseFromResolution", () => {
  it("links the trace, copies operator inputs, and attaches tool + retrieval evidence", () => {
    const c = buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
      outcome: "resolved",
      saveAsEval: true,
      expectedOutcome: "  Refund and email receipt  ",
      failureReason: "Tool flakiness",
    });
    expect(c.id).toBe("eval_thr_8823");
    expect(c.linkedTrace).toBe("trace/thr_8823");
    expect(c.expectedOutcome).toBe("Refund and email receipt");
    expect(c.failureReason).toBe("Tool flakiness");
    expect(c.source).toBe("operator-resolution");
    expect(c.attachments).toEqual([
      "tool/shopify-orders#thr_8823",
      "tool/refund-policy#thr_8823",
      "kb/refund-policy.md#section-2",
      "kb/escalation.md#tool-failure",
    ]);
  });

  it("throws when saveAsEval is false", () => {
    expect(() =>
      buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
        outcome: "resolved",
        saveAsEval: false,
        expectedOutcome: "x",
        failureReason: "y",
      }),
    ).toThrow(ResolutionDraftError);
  });

  it("throws when expectedOutcome is blank", () => {
    expect(() =>
      buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
        outcome: "resolved",
        saveAsEval: true,
        expectedOutcome: "   ",
        failureReason: "y",
      }),
    ).toThrow(/expectedOutcome/);
  });

  it("throws when failureReason is blank", () => {
    expect(() =>
      buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
        outcome: "resolved",
        saveAsEval: true,
        expectedOutcome: "x",
        failureReason: "",
      }),
    ).toThrow(/failureReason/);
  });
});

describe("saveResolutionEvalCase", () => {
  it("posts operator resolution cases to the workspace eval endpoint", async () => {
    const draft = buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
      outcome: "resolved",
      saveAsEval: true,
      expectedOutcome: "Refund and email receipt",
      failureReason: "Tool flakiness",
    });
    const fetcher = async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe(
        "https://cp.test/v1/workspaces/ws1/eval-cases/from-resolution",
      );
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toMatchObject({
        id: "eval_thr_8823",
        linkedTrace: "trace/thr_8823",
      });
      return response({
        ok: true,
        suite_id: "suite-1",
        case_id: "case-1",
      });
    };

    await expect(
      saveResolutionEvalCase("ws1", draft, {
        baseUrl: "https://cp.test/v1",
        fetcher: fetcher as unknown as typeof fetch,
      }),
    ).resolves.toEqual({ ok: true, suite_id: "suite-1", case_id: "case-1" });
  });
});

describe("conversation evidence derivation", () => {
  const messages = [
    {
      id: "m1",
      role: "user" as const,
      body: "I need a refund for order 4421 and may ask my lawyer.",
      created_at_ms: 1,
    },
    {
      id: "m2",
      role: "assistant" as const,
      body: "I can help with the refund policy.",
      created_at_ms: 2,
    },
  ];

  it("builds trace, tool, retrieval, and linked-trace evidence from messages", () => {
    const ctx = createEvidenceContextFromConversation({
      conversation_id: "conv-1",
      messages,
    });

    expect(ctx.resolutionEvidenceRef).toBe("trace/conv-1");
    expect(ctx.trace).toHaveLength(2);
    expect(ctx.tools.map((tool) => tool.name)).toContain("OrderLookup.read");
    expect(ctx.tools.map((tool) => tool.name)).toContain(
      "HandoffPolicy.evaluate",
    );
    expect(ctx.retrieval.map((item) => item.source)).toContain(
      "kb/refund-and-cancellation-policy",
    );
  });

  it("suggests a legal escalation draft when the latest user turn says lawyer", () => {
    expect(suggestOperatorDraftFromConversation(messages)).toMatch(/escalating/i);
  });
});
