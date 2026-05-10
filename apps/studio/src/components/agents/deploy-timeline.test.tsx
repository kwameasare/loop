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
        trafficPercent: 5,
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

    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-start-canary"));
    });

    expect(startCanary).toHaveBeenCalledWith(
      "a",
      expect.objectContaining({
        change_package_id: "cp_1",
        version_id: "v2",
        stage: "canary",
      }),
    );
    expect(screen.getByTestId("deploy-row-dep_new")).toHaveTextContent(
      "Evidence pack",
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
