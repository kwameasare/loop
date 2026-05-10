import { describe, expect, it, vi } from "vitest";

import {
  listToolContractMetrics,
  listToolContracts,
  localToolContracts,
  promoteToolContract,
  type ToolContractInput,
  upsertToolContract,
} from "./tool-contracts";

describe("tool contracts client", () => {
  const refundContractInput: ToolContractInput = {
    name: "issue_refund",
    description: "Refund safely.",
    side_effect_level: "money_movement",
    pii_access: false,
    money_movement: true,
    rate_limits: { per_minute: 20 },
    budget_limits: { max_per_call_cents: 50_000 },
    sandbox_status: "sandbox",
    owner_user_id: "owner",
    approval_policy_id: "policy",
    failure_behavior: "Escalate.",
    compensation_behavior: "Void pending refund.",
  };

  it("builds local contracts with sandbox defaults and money caps", () => {
    const contracts = localToolContracts("agt_1", [
      "lookup_order",
      "issue_refund",
    ]);

    expect(contracts[0]?.sandbox_status).toBe("sandbox");
    expect(contracts[0]?.live_status).toBe("approved");
    expect(contracts[1]?.money_movement).toBe(true);
    expect(contracts[1]?.budget_limits).toMatchObject({
      max_per_call_cents: 50_000,
    });
  });

  it("loads contracts from the agent route", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({ items: [] }),
    );

    await listToolContracts("agt_1", {
      baseUrl: "https://cp.test",
      fetcher,
      token: "tok",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/tool-contracts",
      expect.objectContaining({
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
  });

  it("loads tool contract metrics from the agent route", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        items: [
          {
            tool_id: "lookup_order",
            production_usage_7d: 2,
            success_rate_percent: 50,
            p95_latency_ms: 520,
            retry_rate_percent: 50,
            failed_calls_7d: 1,
            pii_sent_7d: 3,
            last_schema_change_at: "2026-05-10T00:00:00Z",
            measurement_status: "measured",
            evidence_ref: "tool-telemetry/lookup_order/2-calls",
          },
        ],
      }),
    );

    const result = await listToolContractMetrics("agt_1", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(result.items[0]?.measurement_status).toBe("measured");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/tool-contracts/metrics",
      expect.any(Object),
    );
  });

  it("upserts and promotes contracts through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) =>
      Response.json({
        id: "tc_1",
        tool_id: String(input).includes("promote") ? "issue_refund" : "draft",
        live_status: String(input).includes("promote")
          ? "approved"
          : "disabled",
      }),
    );

    await upsertToolContract("agt_1", "issue_refund", refundContractInput, {
      baseUrl: "https://cp.test",
      fetcher,
    });
    const promoted = await promoteToolContract("agt_1", "issue_refund", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(promoted.live_status).toBe("approved");
    expect(fetcher.mock.calls[0]?.[0]).toBe(
      "https://cp.test/v1/agents/agt_1/tool-contracts/issue_refund",
    );
    expect(fetcher.mock.calls[1]?.[0]).toBe(
      "https://cp.test/v1/agents/agt_1/tool-contracts/issue_refund/promote",
    );
  });

  it("does not fabricate tool contract mutations without cp-api", async () => {
    await expect(
      upsertToolContract("agt_1", "issue_refund", refundContractInput, {
        baseUrl: "",
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      promoteToolContract("agt_1", "issue_refund", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic tool contract mutations explicitly opt-in", async () => {
    await expect(
      upsertToolContract("agt_1", "issue_refund", refundContractInput, {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      tool_id: "issue_refund",
      live_status: "review_required",
      sandbox_status: "sandbox",
    });

    await expect(
      promoteToolContract("agt_1", "issue_refund", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      tool_id: "issue_refund",
      live_status: "approved",
    });
  });
});
