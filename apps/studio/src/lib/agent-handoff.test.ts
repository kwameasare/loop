import { describe, expect, it, vi } from "vitest";

import {
  evidenceLinksForAgent,
  fetchAgentHandoff,
  localAgentHandoff,
  transferAgentOwner,
} from "./agent-handoff";

describe("agent handoff client", () => {
  it("keeps local walkthroughs explicitly opt-in", async () => {
    const model = await fetchAgentHandoff("agent_1", {
      baseUrl: "",
      allowFixture: true,
    });
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

  it("does not fabricate handoff reads or ownership transfers without cp-api", async () => {
    await expect(fetchAgentHandoff("agent_1", { baseUrl: "" })).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required",
    );
    await expect(
      transferAgentOwner(
        "agent_1",
        {
          new_owner_user_id: "new-owner@acme.test",
          backup_owner_user_id: "backup@acme.test",
          acknowledged_risk_ids: ["commitment_missing_fields"],
        },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps handoff risk and walkthrough receipts in explicit fixture mode", async () => {
    const transferred = await transferAgentOwner(
      "agent_1",
      {
        new_owner_user_id: "new-owner@acme.test",
        backup_owner_user_id: "backup@acme.test",
        acknowledged_risk_ids: ["commitment_missing_fields"],
      },
      {
        baseUrl: "",
        allowFixture: true,
      },
    );

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

  it("maps walkthrough evidence refs to source artifact links", () => {
    expect(
      evidenceLinksForAgent(
        "agent_1",
        "comment/cmt_handoff -> eval/eval_comment_cmt_handoff",
      ),
    ).toEqual([
      {
        ref: "comment/cmt_handoff",
        href: "/agents/agent_1/history?comment_id=cmt_handoff",
      },
      {
        ref: "eval/eval_comment_cmt_handoff",
        href: "/agents/agent_1/evals?case_id=eval_comment_cmt_handoff",
      },
    ]);
    expect(evidenceLinksForAgent("agent 1", "trace/trace 1")[0]?.href).toBe(
      "/traces/trace%201",
    );
  });
});
