import { describe, expect, it, vi } from "vitest";

import { approveEnterpriseSignup, fetchSystemAdminOverview } from "./system-admin";

describe("system admin client", () => {
  it("fetches installation-level admin overview", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        access: { mode: "configured", actor_sub: "system-admin" },
        metrics: {
          workspaces: 2,
          members: 7,
          agents: 5,
          pending_signups: 1,
          pending_invites: 3,
        },
        enterprise_signups: [],
        recent_invites: [],
        degraded_reasons: [],
      }),
    );

    const overview = await fetchSystemAdminOverview({
      baseUrl: "https://cp.test",
      token: "token",
      fetcher,
    });

    expect(overview.metrics.workspaces).toBe(2);
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/system/admin/overview",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("approves a signup through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_url, init) => {
      expect(JSON.parse(String(init?.body))).toEqual({ note: "approved" });
      return Response.json({
        workspace_id: "ws_1",
        signup: {
          id: "ens_1",
          organization_name: "Acme",
          workspace_slug: "acme",
          admin_name: "Maya",
          admin_email: "maya@example.com",
          company_size: "100-500",
          region: "na-east",
          primary_use_case: "Operate agents.",
          channel_priorities: [],
          compliance_needs: [],
          sso_required: true,
          status: "approved",
          created_at: "2026-05-12T00:00:00Z",
          updated_at: "2026-05-12T00:00:00Z",
        },
        admin_invite: null,
      });
    });

    const result = await approveEnterpriseSignup("ens_1", "approved", {
      baseUrl: "https://cp.test/v1",
      token: "token",
      fetcher,
    });

    expect(result.signup.status).toBe("approved");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/system/admin/signups/ens_1/approve",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
