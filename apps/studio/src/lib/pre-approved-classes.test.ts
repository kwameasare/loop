import { describe, expect, it, vi } from "vitest";

import {
  createPreApprovedClass,
  listPreApprovedClasses,
  revokePreApprovedClass,
} from "./pre-approved-classes";

const RECORD = {
  id: "pac_123",
  workspace_id: "workspace_1",
  agent_id: "agent_1",
  granted_by_user_id: "security@example.com",
  granted_to_user_id: "builder@example.com",
  team_id: "",
  allowed_change_types: ["instruction"],
  excluded_change_types: ["tool", "memory"],
  risk_ceiling: "low",
  expires_at: "2026-05-16T00:00:00Z",
  status: "active",
  reason: "Instruction-only copy fixes.",
  created_at: "2026-05-09T00:00:00Z",
  updated_at: "2026-05-09T00:00:00Z",
  revoked_at: null,
  expired_at: null,
  invalidated_at: null,
  used_by_change_packages: [],
} as const;

describe("pre-approved classes client", () => {
  it("lists, creates, and revokes through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST" && url.endsWith("/revoke")) {
        return Response.json({ ...RECORD, status: "revoked" });
      }
      if (init?.method === "POST") {
        expect(JSON.parse(String(init.body))).toMatchObject({
          granted_to_user_id: "builder@example.com",
          allowed_change_types: ["instruction"],
          excluded_change_types: ["tool"],
          risk_ceiling: "low",
        });
        return Response.json(RECORD, { status: 201 });
      }
      return Response.json({ items: [RECORD] });
    });

    const listed = await listPreApprovedClasses("agent_1", {
      baseUrl: "https://cp.test",
      fetcher,
    });
    const created = await createPreApprovedClass(
      "agent_1",
      {
        granted_to_user_id: "builder@example.com",
        allowed_change_types: ["instruction"],
        excluded_change_types: ["tool"],
        risk_ceiling: "low",
        expires_at: "2026-05-16T00:00:00Z",
      },
      { baseUrl: "https://cp.test", fetcher },
    );
    const revoked = await revokePreApprovedClass("agent_1", "pac_123", {
      baseUrl: "https://cp.test/v1",
      fetcher,
    });

    expect(listed.items[0]?.id).toBe("pac_123");
    expect(created.id).toBe("pac_123");
    expect(revoked.status).toBe("revoked");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/pre-approved-classes",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/pre-approved-classes/pac_123/revoke",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not fabricate pre-approved class state without cp-api", async () => {
    await expect(
      listPreApprovedClasses("agent_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      createPreApprovedClass(
        "agent_1",
        {
          granted_to_user_id: "builder@example.com",
          allowed_change_types: ["instruction"],
          risk_ceiling: "low",
          expires_at: "2026-05-16T00:00:00Z",
        },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      revokePreApprovedClass("agent_1", "pac_123", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });
});
