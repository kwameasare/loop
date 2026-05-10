import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DeployTimeline } from "./deploy-timeline";
import { buildLocalChangePackage } from "@/lib/change-package";
import type { Deployment, EvidencePack } from "@/lib/deploys";

function mkDep(overrides: Partial<Deployment>): Deployment {
  return {
    id: "dep_1",
    agentId: "a",
    versionId: "v1",
    stage: "canary",
    status: "canary",
    trafficPercent: 25,
    createdAt: "2025-02-21T12:00:00Z",
    promotedAt: null,
    pausedAt: null,
    rolledBackAt: null,
    notes: null,
    ...overrides,
  };
}

function mkEvidencePack(overrides: Partial<EvidencePack> = {}): EvidencePack {
  return {
    id: "ep_1",
    workspace_id: "ws_1",
    agent_id: "a",
    version_id: "v2",
    deployment_id: "dep_new",
    change_package_id: "cp_1",
    version_manifest: {
      commitment_document_id: "commit_1",
      release_candidate_id: "rc_1",
      content_hash: "hash_1",
    },
    behavior_diff_ref: "change_package.semantic_diff",
    tool_permission_diff_ref: "change_package.tool_changes",
    knowledge_diff_ref: "change_package.knowledge_changes",
    memory_policy_ref: "change_package.memory_changes",
    channel_deployment_plan_ref: "deployment.channel_scope",
    eval_results_ref: "eval/run",
    approval_records_ref: "change_package.required_approvals",
    canary_results_ref: "deployment/dep_new/canary",
    rollback_plan_ref: "v1",
    audit_log_ref: "audit/deployment/dep_new",
    created_at: "2026-05-09T00:00:00Z",
    export_formats: ["pdf", "json", "csv"],
    ...overrides,
  };
}

describe("DeployTimeline", () => {
  it("renders rows + current canary/live banners", () => {
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[
          mkDep({ id: "d1", status: "canary", trafficPercent: 25 }),
          mkDep({
            id: "d2",
            status: "live",
            trafficPercent: 75,
            versionId: "v0",
          }),
        ]}
      />,
    );
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute(
      "data-status",
      "canary",
    );
    expect(screen.getByTestId("deploy-current-canary")).toHaveTextContent(
      "25%",
    );
    expect(screen.getByTestId("deploy-current-live")).toHaveTextContent("v0");
  });

  it("focuses a deployment opened from an evidence link", () => {
    render(
      <DeployTimeline
        agentId="a"
        focusedDeploymentId="d1"
        initialDeployments={[mkDep({ id: "d1", status: "canary" })]}
      />,
    );

    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute(
      "data-focused",
      "true",
    );
    expect(screen.getByTestId("deploy-focused-d1")).toHaveTextContent(
      "deployment d1 is focused",
    );
  });

  it("focuses rollout and rollback panels opened from evidence links", () => {
    const view = render(
      <DeployTimeline
        agentId="a"
        focusedPanel="rollout"
        initialDeployments={[mkDep({ id: "d1", status: "canary" })]}
      />,
    );

    expect(screen.getByTestId("deploy-focused-panel")).toHaveTextContent(
      "rollout controls are highlighted",
    );
    expect(screen.getByTestId("rollout-plan-controls")).toHaveAttribute(
      "data-focused",
      "true",
    );

    view.unmount();
    render(
      <DeployTimeline
        agentId="a"
        focusedPanel="rollback"
        initialDeployments={[
          mkDep({
            id: "d_live",
            status: "live",
            trafficPercent: 100,
            versionId: "v0",
          }),
        ]}
      />,
    );

    expect(screen.getByTestId("deploy-focused-panel")).toHaveTextContent(
      "rollback candidates are highlighted",
    );
    expect(screen.getByTestId("deploy-row-d_live")).toHaveAttribute(
      "data-focused",
      "true",
    );
  });

  it("focuses promotion controls from the Workbench deploy button", () => {
    render(
      <DeployTimeline
        agentId="a"
        focusedPanel="promotion"
        initialDeployments={[mkDep({ id: "d1", status: "canary" })]}
      />,
    );

    expect(screen.getByTestId("deploy-focused-panel")).toHaveTextContent(
      "promotion controls are highlighted",
    );
    expect(screen.getByTestId("rollout-plan-controls")).toHaveAttribute(
      "data-focused",
      "true",
    );
  });

  it("focuses environment context from the Workbench environment control", () => {
    render(
      <DeployTimeline
        agentId="a"
        focusedPanel="environments"
        initialDeployments={[
          mkDep({
            id: "d_shadow",
            status: "shadow",
            stage: "shadow",
            trafficPercent: 0,
            versionId: "v2",
            evidencePackId: "ep_shadow",
          }),
          mkDep({
            id: "d_canary",
            status: "canary",
            stage: "canary",
            trafficPercent: 25,
            versionId: "v3",
          }),
          mkDep({
            id: "d_live",
            status: "live",
            stage: "production",
            trafficPercent: 100,
            versionId: "v1",
          }),
        ]}
      />,
    );

    expect(screen.getByTestId("deploy-focused-panel")).toHaveTextContent(
      "environment selector is highlighted",
    );
    expect(screen.getByTestId("deploy-environment-selector")).toHaveAttribute(
      "data-focused",
      "true",
    );
    expect(screen.getByTestId("deploy-environment-shadow")).toHaveTextContent(
      "v2",
    );
    expect(screen.getByTestId("deploy-environment-shadow")).toHaveTextContent(
      "ep_shadow",
    );
    expect(
      screen.getByTestId("deploy-environment-production"),
    ).toHaveTextContent("100% traffic");
  });

  it("disables promote/pause for non-canary rows and rollback for non-live rows", () => {
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[mkDep({ id: "d1", status: "rolled_back" })]}
      />,
    );
    expect(screen.getByTestId("deploy-ramp-d1")).toBeDisabled();
    expect(screen.getByTestId("deploy-promote-d1")).toBeDisabled();
    expect(screen.getByTestId("deploy-pause-d1")).toBeDisabled();
    expect(screen.getByTestId("deploy-rollback-d1")).toBeDisabled();
  });

  it("shows degraded deployment history separately from an empty timeline", () => {
    render(
      <DeployTimeline
        agentId="a"
        degradedReason="LOOP_CP_API_BASE_URL is required to load deployment history."
        initialDeployments={[]}
      />,
    );

    expect(screen.getByTestId("deploy-degraded")).toHaveTextContent(
      "Deployment history is unavailable",
    );
    expect(screen.getByTestId("deploy-empty")).toHaveTextContent(
      "Deployment state cannot be confirmed",
    );
  });

  it("ramps an active rollout to the selected traffic percentage", async () => {
    const ramp = vi.fn(async () =>
      mkDep({
        id: "d1",
        stage: "ramp",
        status: "ramp",
        trafficPercent: 50,
      }),
    );
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[mkDep({ id: "d1", status: "canary" })]}
        ramp={ramp}
      />,
    );

    await act(async () => {
      fireEvent.change(screen.getByTestId("deploy-ramp-slider-d1"), {
        target: { value: "50" },
      });
      fireEvent.click(screen.getByTestId("deploy-ramp-d1"));
    });

    expect(ramp).toHaveBeenCalledWith("a", "d1", 50);
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute(
      "data-status",
      "ramp",
    );
    expect(screen.getByTestId("deploy-current-canary")).toHaveTextContent(
      "Ramp at 50%",
    );
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent(
      "Ramped d1 to 50%",
    );
  });

  it("promote replaces the canary row with the live deployment and supersedes prior live", async () => {
    const promote = vi.fn(async () =>
      mkDep({
        id: "d1",
        status: "live",
        trafficPercent: 100,
        promotedAt: "now",
      }),
    );
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[
          mkDep({ id: "d1", status: "canary", trafficPercent: 25 }),
          mkDep({
            id: "d2",
            status: "live",
            trafficPercent: 75,
            versionId: "v0",
          }),
        ]}
        promote={promote}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-promote-d1"));
    });
    expect(promote).toHaveBeenCalledWith("a", "d1");
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute(
      "data-status",
      "live",
    );
    expect(screen.getByTestId("deploy-row-d2")).toHaveAttribute(
      "data-status",
      "superseded",
    );
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent(
      "Promoted",
    );
  });

  it("rollback flips a live deployment and surfaces a toast", async () => {
    const rollback = vi.fn(async () =>
      mkDep({
        id: "d1",
        status: "rolled_back",
        trafficPercent: 0,
        rolledBackAt: "now",
      }),
    );
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[
          mkDep({ id: "d1", status: "live", trafficPercent: 100 }),
        ]}
        rollback={rollback}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-rollback-d1"));
    });
    expect(rollback).toHaveBeenCalledWith("a", "d1");
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute(
      "data-status",
      "rolled_back",
    );
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent(
      "Rolled back",
    );
  });

  it("surfaces an error toast if the action throws", async () => {
    const pause = vi.fn(async () => {
      throw new Error("boom");
    });
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[mkDep({ id: "d1", status: "canary" })]}
        pause={pause}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-pause-d1"));
    });
    expect(screen.getByTestId("deploy-toast-error")).toHaveTextContent("boom");
  });

  it("evaluates active rollout thresholds and updates deployment state", async () => {
    const evaluateThreshold = vi.fn(async () => ({
      decision: "paused" as const,
      breached: true,
      metric: "error_rate_percent",
      observed: 3,
      threshold: 2,
      policy: "pause" as const,
      deployment: mkDep({
        id: "d1",
        status: "paused",
        stage: "paused",
        trafficPercent: 25,
      }),
    }));
    render(
      <DeployTimeline
        agentId="a"
        evaluateThreshold={evaluateThreshold}
        initialDeployments={[
          mkDep({
            id: "d1",
            status: "canary",
            autoRollbackThresholds: { error_rate_percent: 2 },
          }),
        ]}
      />,
    );

    fireEvent.change(screen.getByTestId("deploy-threshold-observed-d1"), {
      target: { value: "3" },
    });
    fireEvent.change(screen.getByTestId("deploy-threshold-policy-d1"), {
      target: { value: "pause" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-threshold-evaluate-d1"));
    });

    expect(evaluateThreshold).toHaveBeenCalledWith("a", "d1", {
      metric: "error_rate_percent",
      observed: 3,
      policy: "pause",
      window: "5m",
      reason: "Manual Workbench rollout threshold check.",
    });
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute(
      "data-status",
      "paused",
    );
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent(
      "deployment paused",
    );
  });

  it("starts canary from an approved Change Package and shows the evidence pack", async () => {
    const changePackage = {
      ...buildLocalChangePackage("a"),
      id: "cp_1",
      status: "approved" as const,
      to_version_id: "v2",
      evidence_pack_id: "ep_cp_1",
    };
    const startCanary = vi.fn(async () => ({
      deployment: mkDep({
        id: "dep_new",
        stage: "canary",
        status: "canary",
        versionId: "v2",
        trafficPercent: 10,
        channelScope: ["web_chat", "whatsapp"],
        regionScope: ["eu-west-2"],
        segmentScope: ["enterprise"],
        holdTimeMinutes: 45,
        autoRollbackThresholds: {
          error_rate_percent: 1,
          p95_latency_ms: 1800,
          cost_delta_percent: 12,
          tool_failure_rate_percent: 3,
        },
        evidencePackId: "ep_1",
      }),
      evidence_pack: mkEvidencePack(),
    }));
    render(
      <DeployTimeline
        agentId="a"
        approvedChangePackage={changePackage}
        initialDeployments={[]}
        startCanary={startCanary}
      />,
    );

    fireEvent.change(screen.getByTestId("rollout-traffic-percent"), {
      target: { value: "10" },
    });
    fireEvent.change(screen.getByTestId("rollout-channel-scope"), {
      target: { value: "web_chat, whatsapp" },
    });
    fireEvent.change(screen.getByTestId("rollout-region-scope"), {
      target: { value: "eu-west-2" },
    });
    fireEvent.change(screen.getByTestId("rollout-segment-scope"), {
      target: { value: "enterprise" },
    });
    fireEvent.change(screen.getByTestId("rollout-hold-time"), {
      target: { value: "45" },
    });
    fireEvent.change(screen.getByTestId("rollout-error-rate"), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByTestId("rollout-p95-latency"), {
      target: { value: "1800" },
    });
    fireEvent.change(screen.getByTestId("rollout-cost-delta"), {
      target: { value: "12" },
    });
    fireEvent.change(screen.getByTestId("rollout-tool-failure"), {
      target: { value: "3" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-start-canary"));
    });

    expect(startCanary).toHaveBeenCalledWith(
      "a",
      expect.objectContaining({
        change_package_id: "cp_1",
        version_id: "v2",
        stage: "canary",
        traffic_percent: 10,
        channel_scope: ["web_chat", "whatsapp"],
        region_scope: ["eu-west-2"],
        segment_scope: ["enterprise"],
        hold_time_minutes: 45,
        auto_rollback_thresholds: {
          error_rate_percent: 1,
          p95_latency_ms: 1800,
          cost_delta_percent: 12,
          tool_failure_rate_percent: 3,
        },
      }),
    );
    expect(screen.getByTestId("deploy-row-dep_new")).toHaveTextContent(
      "Evidence pack",
    );
    expect(screen.getByTestId("deploy-scope-dep_new")).toHaveTextContent(
      "web_chat, whatsapp",
    );
    expect(screen.getByTestId("deploy-scope-dep_new")).toHaveTextContent(
      "eu-west-2",
    );
    expect(screen.getByTestId("deploy-scope-dep_new")).toHaveTextContent(
      "enterprise",
    );
    expect(screen.getByTestId("deploy-scope-dep_new")).toHaveTextContent(
      "hold 45 min",
    );
    expect(screen.getByTestId("deploy-thresholds-dep_new")).toHaveTextContent(
      "error rate <= 1%",
    );
    expect(screen.getByTestId("deploy-thresholds-dep_new")).toHaveTextContent(
      "p95 latency <= 1800 ms",
    );
    expect(
      screen.getByTestId("evidence-pack-manifest-ep_1"),
    ).toHaveTextContent("Exportable proof bundle");
    expect(
      screen.getByTestId("evidence-pack-manifest-ep_1"),
    ).toHaveTextContent("rc_1");
    expect(
      screen.getByTestId("evidence-pack-manifest-ep_1"),
    ).toHaveTextContent("change_package.semantic_diff");
    expect(
      screen.getByTestId("evidence-pack-manifest-ep_1"),
    ).toHaveTextContent("audit/deployment/dep_new");
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent(
      "Started canary",
    );
  });

  it("renders existing evidence pack manifests with exact deployment evidence", () => {
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[
          mkDep({
            id: "dep_new",
            status: "live",
            versionId: "v2",
            evidencePackId: "ep_1",
          }),
        ]}
        initialEvidencePacks={[mkEvidencePack()]}
      />,
    );

    const manifest = screen.getByTestId("evidence-pack-manifest-ep_1");
    expect(manifest).toHaveTextContent("Change Package");
    expect(manifest).toHaveTextContent("cp_1");
    expect(manifest).toHaveTextContent("Content hash");
    expect(manifest).toHaveTextContent("hash_1");
    expect(manifest).toHaveTextContent("Rollback plan");
    expect(manifest).toHaveTextContent("v1");
    expect(manifest).toHaveTextContent("pdf, json, csv");
  });

  it("exports evidence pack manifests with redaction proof", async () => {
    const exportPack = vi.fn(async () => ({
      id: "epex_1",
      status: "ready" as const,
      format: "json" as const,
      purpose: "deployment evidence review",
      workspace_id: "ws_1",
      agent_id: "a",
      evidence_pack_id: "ep_1",
      deployment_id: "dep_new",
      change_package_id: "cp_1",
      sections: ["change_package", "eval_results", "audit_log"],
      artifact_refs: ["evidence-pack/ep_1", "change-package/cp_1"],
      redactions: ["credentials", "pii", "raw_tool_credentials", "secrets"],
      download_url: "/v1/agents/a/evidence-packs/ep_1/exports/epex_1",
      created_at: "2026-05-09T00:00:00Z",
      expires_at: "2026-05-16T00:00:00Z",
    }));
    render(
      <DeployTimeline
        agentId="a"
        exportPack={exportPack}
        initialDeployments={[
          mkDep({
            id: "dep_new",
            status: "live",
            versionId: "v2",
            evidencePackId: "ep_1",
          }),
        ]}
        initialEvidencePacks={[mkEvidencePack()]}
      />,
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("evidence-pack-export-ep_1-json"));
    });

    expect(exportPack).toHaveBeenCalledWith("a", "ep_1", {
      format: "json",
      purpose: "deployment evidence review",
      redactions: ["secrets", "pii", "credentials", "pricing"],
    });
    expect(
      screen.getByTestId("evidence-pack-export-result-ep_1"),
    ).toHaveTextContent("epex_1");
    expect(
      screen.getByTestId("evidence-pack-export-result-ep_1"),
    ).toHaveTextContent("raw_tool_credentials");
  });

  it("starts shadow from an approved Change Package without routing traffic", async () => {
    const changePackage = {
      ...buildLocalChangePackage("a"),
      id: "cp_1",
      status: "approved" as const,
      to_version_id: "v2",
      evidence_pack_id: "ep_cp_1",
    };
    const startCanary = vi.fn(async () => ({
      deployment: mkDep({
        id: "dep_shadow",
        stage: "shadow",
        status: "shadow",
        versionId: "v2",
        trafficPercent: 0,
        evidencePackId: "ep_1",
      }),
    }));
    render(
      <DeployTimeline
        agentId="a"
        approvedChangePackage={changePackage}
        initialDeployments={[]}
        startCanary={startCanary}
      />,
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-start-shadow"));
    });

    expect(startCanary).toHaveBeenCalledWith(
      "a",
      expect.objectContaining({
        change_package_id: "cp_1",
        version_id: "v2",
        stage: "shadow",
        traffic_percent: 0,
      }),
    );
    expect(screen.getByTestId("deploy-row-dep_shadow")).toHaveAttribute(
      "data-status",
      "shadow",
    );
    expect(screen.getByTestId("deploy-row-dep_shadow")).toHaveTextContent(
      "shadow · 0%",
    );
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent(
      "Started shadow",
    );
  });
});
