import { describe, expect, it, vi } from "vitest";

import {
  listToolContracts,
  localToolContracts,
  promoteToolContract,
  upsertToolContract,
} from "./tool-contracts";

describe("tool contracts client", () => {
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

    await upsertToolContract(
      "agt_1",
      "issue_refund",
      {
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
      },
      { baseUrl: "https://cp.test", fetcher },
    );
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
});
