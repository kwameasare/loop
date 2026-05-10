import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EstateOverview } from "@/components/estate/estate-overview";
import type { EstateHealth } from "@/lib/estate-health";

const HEALTH: EstateHealth = {
  workspace_id: "ws_1",
  generated_at: "2026-05-08T12:00:00Z",
  data_source: "live",
  provenance: ["agents.list_for_workspace", "trace_search.run"],
  summary: {
    agents_total: 12,
    agents_production: 9,
    agents_draft: 3,
    pending_handoffs: 2,
    pending_approvals: 1,
    active_rollouts: 1,
    trace_errors: 4,
    trace_count: 88,
    eval_suites: 6,
    audit_events: 50,
    open_incidents: 0,
    blocked_deploys: 1,
    owner_risks: 1,
    open_catches: 2,
  },
  attention: [
    {
      id: "pending-approvals",
      severity: "critical",
      title: "1 change set needs approval",
      detail: "Release candidate cannot promote.",
      href: "/deploys",
      source: "approval_changesets",
    },
  ],
  shared_dependencies: [
    {
      id: "tool:refund_payment",
      type: "tool",
      name: "refund_payment",
      risk: "high",
      detail: "2 agents depend on this money-moving tool.",
      evidence_ref: "tool-contract/tc_refund",
      agents: [
        {
          agent_id: "agt_1",
          agent_name: "Refund Agent",
          contract_id: "tc_refund",
          live_status: "review_required",
          side_effect_level: "money_movement",
          pii_access: true,
          money_movement: true,
          evidence_ref: "tool-contract/tc_refund",
        },
      ],
    },
  ],
  rollout_health: [
    {
      id: "dep_canary",
      agent_id: "agt_1",
      agent_name: "Refund Agent",
      version_id: "v24",
      stage: "canary",
      status: "canary",
      traffic_percent: 10,
      channel_scope: ["web_chat", "whatsapp"],
      region_scope: ["eu-west-2"],
      segment_scope: ["enterprise"],
      hold_time_minutes: 45,
      auto_rollback_thresholds: { error_rate_percent: 2 },
      evidence_pack_id: "ep_1",
      evidence_ref: "deployment/dep_canary",
    },
  ],
  channel_health: [
    {
      id: "cb_whatsapp",
      agent_id: "agt_1",
      agent_name: "Refund Agent",
      channel_type: "whatsapp",
      status: "draft",
      blocking_checks: 2,
      last_failure_at: null,
      evidence_ref: "channel-binding/cb_whatsapp",
    },
  ],
  failure_clusters: [
    {
      id: "incident:inc_1",
      kind: "incident",
      severity: "high",
      title: "Refund quote regressed in canary",
      affected: 4,
      href: "/observe?incident=inc_1",
      evidence_ref: "incident/inc_1",
    },
  ],
  owner_risks: [
    {
      id: "ownerless-agent-agt_1",
      agent_id: "agt_1",
      agent_name: "Refund Agent",
      severity: "critical",
      owner_user_id: "",
      backup_owner_user_id: "",
      detail: "No owner is set on the current Commitment Document.",
      href: "/agents/agt_1/history",
      evidence_ref: "commitment/commit_1",
    },
  ],
  background_jobs: [
    {
      id: "cluster_failures",
      status: "completed",
      output_count: 1,
      evidence_ref: "estate/jobs/cluster_failures",
    },
  ],
  next_actions: [
    {
      id: "pending-approvals",
      severity: "critical",
      title: "1 change set needs approval",
      detail: "Release candidate cannot promote.",
      href: "/deploys",
      source: "approval_changesets",
    },
  ],
};

describe("EstateOverview", () => {
  it("renders estate metrics and source-backed attention", () => {
    render(<EstateOverview health={HEALTH} />);

    expect(screen.getByTestId("estate-data-source")).toHaveTextContent(
      "Live cp-api",
    );
    expect(screen.getByTestId("estate-overview")).toHaveTextContent("12");
    expect(screen.getByTestId("estate-overview")).toHaveTextContent("Catches");
    expect(screen.getByTestId("estate-overview")).toHaveTextContent("2");
    expect(screen.getByTestId("estate-attention")).toHaveTextContent(
      "1 change set needs approval",
    );
    expect(screen.getByTestId("estate-attention")).toHaveTextContent(
      "source: approval_changesets",
    );
    expect(screen.getByTestId("estate-shared-dependencies")).toHaveTextContent(
      "refund_payment",
    );
    expect(screen.getByTestId("estate-rollouts")).toHaveTextContent(
      "Refund Agent",
    );
    expect(screen.getByTestId("estate-rollouts")).toHaveTextContent(
      "web_chat, whatsapp",
    );
    expect(screen.getByTestId("estate-failure-clusters")).toHaveTextContent(
      "Refund quote regressed",
    );
    expect(screen.getByTestId("estate-channels")).toHaveTextContent("whatsapp");
    expect(screen.getByTestId("estate-continuity")).toHaveTextContent(
      "No owner is set",
    );
    expect(screen.getByTestId("estate-jobs")).toHaveTextContent(
      "cluster failures",
    );
  });

  it("shows degraded provenance instead of pretending data is live", () => {
    render(
      <EstateOverview
        health={{
          ...HEALTH,
          data_source: "unavailable",
          degraded_reason: "cp-api estate health returned 503.",
        }}
      />,
    );

    expect(screen.getByTestId("estate-data-source")).toHaveTextContent(
      "cp-api unavailable",
    );
    expect(screen.getByTestId("estate-degraded-reason")).toHaveTextContent(
      "503",
    );
  });
});
