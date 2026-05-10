import { describe, expect, it, vi } from "vitest";

import {
  approveMemoryPolicy,
  listMemoryPolicies,
  localMemoryPolicies,
  upsertMemoryPolicy,
} from "./memory-policies";

describe("memory-policies client", () => {
  const userPolicyInput = {
    scope: "user" as const,
    allowed_memory_types: ["preference"],
    retention: "Keep confirmed preferences for 90 days.",
    consent_requirement: "Explicit consent required.",
    pii_policy: "No secrets or payment data.",
    delete_behavior: "Delete on request.",
    privacy_implications: ["Affects future user conversations."],
    source_trace_required: true,
  };

  it("builds local policy fallbacks with privacy implications", () => {
    const policies = localMemoryPolicies("agent-1");

    expect(policies.map((policy) => policy.scope)).toEqual([
      "session",
      "user",
      "account",
      "organization",
      "task",
      "agent",
      "workspace",
    ]);
    expect(policies.find((policy) => policy.scope === "user")).toMatchObject({
      approval_status: "review_required",
      source_trace_required: true,
    });
    expect(
      policies.every((policy) => policy.privacy_implications.length > 0),
    ).toBe(true);
    expect(policies.find((policy) => policy.scope === "account")).toMatchObject(
      {
        approval_status: "review_required",
        source_trace_required: true,
      },
    );
    expect(policies.find((policy) => policy.scope === "task")).toMatchObject({
      approval_status: "draft",
      source_trace_required: true,
    });
  });

  it("lists, upserts, and approves through cp-api", async () => {
    const base = localMemoryPolicies("agent-1")[1]!;
    const fetcher = vi.fn<typeof fetch>(async (_input, init) => {
      if (init?.method === "PUT") {
        return new Response(
          JSON.stringify({
            ...base,
            retention: "Keep confirmed preferences for 90 days.",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      if (init?.method === "POST") {
        return new Response(
          JSON.stringify({ ...base, approval_status: "approved" }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(JSON.stringify({ items: [base] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });

    const listed = await listMemoryPolicies("agent-1", {
      baseUrl: "https://cp.test",
      fetcher,
    });
    const updated = await upsertMemoryPolicy(
      "agent-1",
      userPolicyInput,
      { baseUrl: "https://cp.test", fetcher },
    );
    const approved = await approveMemoryPolicy("agent-1", "user", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(listed.items).toHaveLength(1);
    expect(updated.retention).toContain("90 days");
    expect(approved.approval_status).toBe("approved");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent-1/memory-policies/user",
      expect.objectContaining({ method: "PUT" }),
    );
  });

  it("does not fabricate memory policy state without cp-api", async () => {
    await expect(
      listMemoryPolicies("agent-1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      upsertMemoryPolicy("agent-1", userPolicyInput, { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      approveMemoryPolicy("agent-1", "user", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic memory policy behavior explicitly opt-in", async () => {
    await expect(
      listMemoryPolicies("agent-1", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      items: expect.arrayContaining([
        expect.objectContaining({ scope: "user" }),
      ]),
    });

    await expect(
      upsertMemoryPolicy("agent-1", userPolicyInput, {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      scope: "user",
      approval_status: "review_required",
      retention: "Keep confirmed preferences for 90 days.",
    });

    await expect(
      approveMemoryPolicy("agent-1", "user", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      scope: "user",
      approval_status: "approved",
    });
  });
});
