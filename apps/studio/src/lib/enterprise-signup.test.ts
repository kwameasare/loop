import { describe, expect, it, vi } from "vitest";

import { createEnterpriseSignup } from "./enterprise-signup";

describe("enterprise signup client", () => {
  it("posts public tenant requests to cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_url, init) => {
      expect(JSON.parse(String(init?.body))).toMatchObject({
        organization_name: "Acme Bank",
        admin_email: "maya@example.com",
      });
      return Response.json(
        {
          signup: {
            id: "ens_1",
            organization_name: "Acme Bank",
            workspace_slug: "acme-bank",
            admin_name: "Maya",
            admin_email: "maya@example.com",
            company_size: "100-500",
            region: "na-east",
            primary_use_case: "Operate agents.",
            channel_priorities: ["web"],
            compliance_needs: ["SSO"],
            sso_required: true,
            status: "pending_review",
            created_at: "2026-05-12T00:00:00Z",
            updated_at: "2026-05-12T00:00:00Z",
          },
          next_step: {
            label: "Review queued",
            detail: "System admin review.",
            href: "/login?returnTo=/system/admin",
          },
        },
        { status: 201 },
      );
    });

    const result = await createEnterpriseSignup(
      {
        organization_name: "Acme Bank",
        workspace_slug: "acme-bank",
        admin_name: "Maya",
        admin_email: "maya@example.com",
        company_size: "100-500",
        region: "na-east",
        primary_use_case: "Operate agents.",
        channel_priorities: ["web"],
        compliance_needs: ["SSO"],
        sso_required: true,
      },
      { baseUrl: "https://cp.test", fetcher },
    );

    expect(result.signup.status).toBe("pending_review");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/enterprise/signups",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not fabricate signup success without cp-api", async () => {
    await expect(
      createEnterpriseSignup(
        {
          organization_name: "Acme",
          admin_name: "Maya",
          admin_email: "maya@example.com",
          company_size: "100-500",
          region: "na-east",
          primary_use_case: "Operate agents.",
          channel_priorities: [],
          compliance_needs: [],
          sso_required: false,
        },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("NEXT_PUBLIC_LOOP_API_URL is required");
  });
});
