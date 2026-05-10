import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentGovernancePage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentGovernancePage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("shows degraded governance evidence instead of the old placeholder when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(
      await AgentGovernancePage({ params: { agent_id: "agent_govern" } }),
    );

    expect(screen.getByTestId("agent-governance-page")).toBeInTheDocument();
    expect(screen.getByTestId("target-state")).toHaveTextContent(
      /Agent governance/i,
    );
    expect(screen.getByTestId("target-state")).toHaveTextContent(
      /will not claim approvals, secrets, auditability, or residency posture/i,
    );
    expect(screen.queryByTestId("agent-section-placeholder")).toBeNull();
    expect(screen.getByText("unconfigured")).toBeInTheDocument();
  });

  it("renders commitment, secret references, and audit events from live agent evidence", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_govern")) {
        return Response.json({
          id: "agent_govern",
          name: "Governed Agent",
          description: "Enterprise support agent.",
          slug: "governed-agent",
          active_version: 6,
          created_at: "2026-05-09T10:00:00Z",
          workspace_id: "ws_govern",
          object_state: "staged",
          state_reason: "Awaiting approval.",
          state_evidence_ref: "approval.req_123",
        });
      }
      if (url.endsWith("/agents/agent_govern/commitment/current")) {
        return Response.json({
          id: "commitment_govern_1",
          agent_id: "agent_govern",
          workspace_id: "ws_govern",
          version: 3,
          body: {
            business_responsibility: "Resolve enterprise renewals.",
            target_users: "Enterprise customers",
            owner_user_id: "owner@example.com",
            backup_owner_user_id: "backup@example.com",
            worst_case_failure: "Wrong cancellation guidance.",
            channels: ["web", "whatsapp", "voice"],
            systems_touched: ["crm", "billing"],
            regions: ["us-east-1"],
            languages: ["en"],
            success_metric: "Eval pass rate >= 95%",
            compliance_domain: "SOC2",
            expected_volume: "10k turns/month",
            launch_date: "2026-05-15",
            budget_target: "$0.08/turn",
            out_of_scope: "Medical advice",
            escalation_policy: "Escalate legal threats.",
          },
          structured_summary: {
            responsibility: "Resolve enterprise renewals.",
            audience: "Enterprise customers",
            owner: "owner@example.com",
            backup_owner: "backup@example.com",
            risk: "Wrong cancellation guidance.",
            channels: ["web", "whatsapp", "voice"],
            systems_touched: ["crm", "billing"],
            regions: ["us-east-1"],
            languages: ["en"],
            readiness: "complete",
            missing_required_fields: [],
          },
          owner_user_id: "owner@example.com",
          status: "accepted",
          content_hash: "sha256:0123456789abcdef0123456789abcdef",
          created_from: "studio:intake",
          created_at: "2026-05-08T10:00:00Z",
          updated_at: "2026-05-09T10:00:00Z",
          accepted_at: "2026-05-09T10:30:00Z",
          superseded_at: null,
        });
      }
      if (url.endsWith("/agents/agent_govern/secrets")) {
        return Response.json({
          items: [
            {
              id: "sec_govern_1",
              agent_id: "agent_govern",
              name: "BILLING_API_TOKEN",
              ref: "kms://prod/billing-api-token",
              value: "super-secret-token",
              created_at: "2026-05-01T09:00:00Z",
              rotated_at: "2026-05-09T09:00:00Z",
            },
          ],
        });
      }
      if (url.endsWith("/agents/agent_govern/pre-approved-classes")) {
        return Response.json({
          items: [
            {
              id: "pac_govern_copy",
              workspace_id: "ws_govern",
              agent_id: "agent_govern",
              granted_by_user_id: "security@example.com",
              granted_to_user_id: "builder@example.com",
              team_id: "",
              allowed_change_types: ["instruction"],
              excluded_change_types: ["tool", "memory", "channel", "budget"],
              risk_ceiling: "low",
              expires_at: "2026-05-16T00:00:00Z",
              status: "active",
              reason: "Instruction-only copy fixes.",
              created_at: "2026-05-09T00:00:00Z",
              updated_at: "2026-05-09T00:00:00Z",
              revoked_at: null,
              invalidated_at: null,
              used_by_change_packages: ["cp_govern_1"],
            },
          ],
        });
      }
      if (url.startsWith("https://cp.test/v1/audit/events?")) {
        return Response.json({
          items: [
            {
              id: "audit_govern_1",
              occurred_at: "2026-05-09T11:00:00Z",
              workspace_id: "ws_govern",
              actor_sub: "security@example.com",
              action: "agent.approval.requested",
              resource_type: "agent",
              resource_id: "agent_govern",
              outcome: "success",
            },
          ],
          total: 1,
        });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      await AgentGovernancePage({ params: { agent_id: "agent_govern" } }),
    );

    expect(
      screen.getByText(/Governance evidence for Governed Agent/i),
    ).toBeInTheDocument();
    expect(screen.getByText("accepted")).toBeInTheDocument();
    expect(screen.getByText("sha256:012...abcdef")).toBeInTheDocument();
    expect(screen.getByText("BILLING_API_TOKEN")).toBeInTheDocument();
    expect(
      screen.getByText(/kms:\/\/prod\/billing-api-token/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("super-secret-token")).toBeNull();
    expect(screen.getByText("agent.approval.requested")).toBeInTheDocument();
    expect(screen.getByText("pac_govern_copy - active")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-section-placeholder")).toBeNull();
    expect(screen.queryByTestId("target-state")).toBeNull();
  });
});
