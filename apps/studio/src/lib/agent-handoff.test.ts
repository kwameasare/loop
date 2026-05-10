import { describe, expect, it, vi } from "vitest";

import {
  fetchAgentHandoff,
  localAgentHandoff,
  transferAgentOwner,
} from "./agent-handoff";

describe("agent handoff client", () => {
  it("falls back to a local walkthrough when cp-api is not configured", async () => {
    const model = await fetchAgentHandoff("agent_1");
    expect(model.agent.id).toBe("agent_1");
    expect(model.open_risks[0]?.id).toBe("commitment_missing_fields");
    expect(model.walkthrough_sections.map((section) => section.id)).toContain(
      "important-comments",
    );
  });

  it("posts ownership transfer to the durable handoff endpoint", async () => {
    const model = localAgentHandoff("agent_1");
    let capturedUrl = "";
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      capturedUrl = String(input);
      return Response.json({
        ...model,
        owner_user_id: "new-owner@acme.test",
      });
    });

    await expect(
      transferAgentOwner(
        "agent_1",
        {
          new_owner_user_id: "new-owner@acme.test",
          backup_owner_user_id: "backup@acme.test",
          acknowledged_risk_ids: ["commitment_missing_fields"],
        },
        {
          baseUrl: "https://cp.example.test",
          fetcher,
          fallbackModel: model,
        },
      ),
    ).resolves.toMatchObject({ owner_user_id: "new-owner@acme.test" });
    expect(capturedUrl).toContain("/agents/agent_1/handoff/transfer");
  });

  it("keeps handoff risk and walkthrough receipts in local fallback mode", async () => {
    const transferred = await transferAgentOwner("agent_1", {
      new_owner_user_id: "new-owner@acme.test",
      backup_owner_user_id: "backup@acme.test",
      acknowledged_risk_ids: ["commitment_missing_fields"],
    });

    expect(transferred.transfers[0]?.open_risk_ids).toContain(
      "commitment_missing_fields",
    );
    expect(transferred.transfers[0]?.walkthrough_section_ids).toContain(
      "important-comments",
    );
    expect(transferred.transfers[0]?.notification.recipient).toBe(
      "new-owner@acme.test",
    );
  });
});
