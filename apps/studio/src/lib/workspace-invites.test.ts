import { describe, expect, it, vi } from "vitest";

import { createWorkspaceInvite, listWorkspaceInvites } from "./workspace-invites";

describe("workspace invite client", () => {
  it("lists workspace invites from cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        items: [
          {
            id: "inv_1",
            workspace_id: "ws_1",
            email: "builder@example.com",
            role: "member",
            status: "pending",
            created_at: "2026-05-12T00:00:00Z",
            expires_at: "2026-05-26T00:00:00Z",
            created_by: "owner",
            invite_url: "/signup?invite=inv_1",
          },
        ],
      }),
    );

    const result = await listWorkspaceInvites("ws_1", {
      baseUrl: "https://cp.test",
      token: "token",
      fetcher,
    });

    expect(result.items[0]?.email).toBe("builder@example.com");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws_1/invites",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("creates audit-backed workspace invites", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_url, init) => {
      expect(JSON.parse(String(init?.body))).toEqual({
        email: "operator@example.com",
        role: "admin",
      });
      return Response.json(
        {
          id: "inv_2",
          workspace_id: "ws_1",
          email: "operator@example.com",
          role: "admin",
          status: "pending",
          created_at: "2026-05-12T00:00:00Z",
          expires_at: "2026-05-26T00:00:00Z",
          created_by: "owner",
          invite_url: "/signup?invite=inv_2",
        },
        { status: 201 },
      );
    });

    const result = await createWorkspaceInvite(
      "ws_1",
      { email: "operator@example.com", role: "admin" },
      { baseUrl: "https://cp.test/v1", token: "token", fetcher },
    );

    expect(result.role).toBe("admin");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws_1/invites",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
