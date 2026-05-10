import { describe, expect, it, vi } from "vitest";

import {
  findCurrentCanary,
  findLiveDeployment,
  listDeployments,
  listEvidencePacks,
  pauseDeployment,
  promoteDeployment,
  rampDeployment,
  rollbackDeployment,
  startCanaryDeployment,
  type Deployment,
} from "./deploys";

describe("listDeployments fixture mode", () => {
  it("returns degraded state when no baseUrl is configured", async () => {
    const { items, degraded_reason } = await listDeployments("agt_fix_a");
    expect(items).toEqual([]);
    expect(degraded_reason).toMatch(/LOOP_CP_API_BASE_URL is required/);
  });

  it("returns canary + live deployments seeded for the agent", async () => {
    const { items } = await listDeployments("agt_fix_a", {
      allowFixture: true,
    });
    expect(items.find((d) => d.status === "canary")).toBeDefined();
    expect(items.find((d) => d.status === "live")).toBeDefined();
  });

  it("promote moves canary to live and supersedes prior live", async () => {
    const fixtureOpts = { allowFixture: true };
    const { items: before } = await listDeployments("agt_fix_b", fixtureOpts);
    const canary = findCurrentCanary(before)!;
    const promoted = await promoteDeployment(
      "agt_fix_b",
      canary.id,
      fixtureOpts,
    );
    expect(promoted.status).toBe("live");
    expect(promoted.trafficPercent).toBe(100);
    const { items: after } = await listDeployments("agt_fix_b", fixtureOpts);
    const lives = after.filter((d) => d.status === "live");
    expect(lives).toHaveLength(1);
    expect(after.some((d) => d.status === "superseded")).toBe(true);
  });

  it("pause freezes the deployment without changing traffic", async () => {
    const fixtureOpts = { allowFixture: true };
    const { items } = await listDeployments("agt_fix_c", fixtureOpts);
    const canary = findCurrentCanary(items)!;
    const paused = await pauseDeployment("agt_fix_c", canary.id, fixtureOpts);
    expect(paused.status).toBe("paused");
    expect(paused.pausedAt).not.toBeNull();
  });

  it("ramp increases an active rollout before production", async () => {
    const fixtureOpts = { allowFixture: true };
    const { items } = await listDeployments("agt_fix_ramp", fixtureOpts);
    const canary = findCurrentCanary(items)!;
    const ramped = await rampDeployment(
      "agt_fix_ramp",
      canary.id,
      50,
      fixtureOpts,
    );
    expect(ramped.status).toBe("ramp");
    expect(ramped.stage).toBe("ramp");
    expect(ramped.trafficPercent).toBe(50);
  });

  it("rollback flips a live deployment to rolled_back and restores prior", async () => {
    const fixtureOpts = { allowFixture: true };
    const { items } = await listDeployments("agt_fix_d", fixtureOpts);
    const live = findLiveDeployment(items)!;
    const result = await rollbackDeployment("agt_fix_d", live.id, fixtureOpts);
    expect(result.status).toBe("rolled_back");
    expect(result.trafficPercent).toBe(0);
  });

  it("requires cp-api before mutating deployments", async () => {
    await expect(promoteDeployment("agt_fix", "dep_001")).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required to promote deployments",
    );
    await expect(rampDeployment("agt_fix", "dep_001", 50)).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required to ramp deployments",
    );
  });

  it("returns degraded evidence pack state when no baseUrl is configured", async () => {
    const { items, degraded_reason } = await listEvidencePacks("agt_fix_a");
    expect(items).toEqual([]);
    expect(degraded_reason).toMatch(/evidence packs/);
  });
});

describe("listDeployments cp-api mode", () => {
  it("calls the deployments endpoint and returns parsed items", async () => {
    const sample: Deployment = {
      id: "dep_001",
      agentId: "agt_x",
      versionId: "ver_1",
      stage: "production",
      status: "live",
      trafficPercent: 100,
      createdAt: "2025-01-01T00:00:00Z",
      promotedAt: "2025-01-01T00:00:01Z",
      pausedAt: null,
      rolledBackAt: null,
      notes: null,
    };
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ items: [sample] }),
    })) as unknown as typeof fetch;
    const { items } = await listDeployments("agt_x", {
      fetcher,
      baseUrl: "https://api.loop.dev/v1",
      token: "tok",
    });
    expect(items).toHaveLength(1);
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock
      .calls[0];
    expect(call[0]).toBe("https://api.loop.dev/v1/agents/agt_x/deployments");
  });

  it("calls the evidence packs endpoint and returns proof bundles", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            items: [
              {
                id: "ep_1",
                workspace_id: "ws_1",
                agent_id: "agt_x",
                version_id: "v2",
                deployment_id: "dep_new",
                change_package_id: "cp_1",
                version_manifest: {
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
                export_formats: ["pdf", "json"],
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );

    const { items } = await listEvidencePacks("agt_x", {
      fetcher: fetcher as unknown as typeof fetch,
      baseUrl: "https://api.loop.dev/v1",
      token: "tok",
    });

    expect(items[0]?.change_package_id).toBe("cp_1");
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock
      .calls[0];
    expect(call[0]).toBe(
      "https://api.loop.dev/v1/agents/agt_x/evidence-packs",
    );
  });

  it("promote POSTs to the promote endpoint", async () => {
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        id: "dep_001",
        agentId: "a",
        versionId: "v",
        status: "live",
        trafficPercent: 100,
        createdAt: "",
        promotedAt: "now",
        pausedAt: null,
        rolledBackAt: null,
        notes: null,
      }),
    })) as unknown as typeof fetch;
    await promoteDeployment("a", "dep_001", {
      fetcher,
      baseUrl: "https://api.loop.dev",
    });
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock
      .calls[0];
    expect(call[0]).toBe(
      "https://api.loop.dev/v1/agents/a/deployments/dep_001/promote",
    );
    expect((call[1] as { method: string }).method).toBe("POST");
  });

  it("ramp POSTs the target traffic percentage", async () => {
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        id: "dep_001",
        agentId: "a",
        versionId: "v",
        stage: "ramp",
        status: "ramp",
        trafficPercent: 50,
        createdAt: "",
        promotedAt: null,
        pausedAt: null,
        rolledBackAt: null,
        notes: null,
      }),
    })) as unknown as typeof fetch;
    const result = await rampDeployment("a", "dep_001", 50, {
      fetcher,
      baseUrl: "https://api.loop.dev",
    });
    expect(result.status).toBe("ramp");
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock
      .calls[0];
    expect(call[0]).toBe(
      "https://api.loop.dev/v1/agents/a/deployments/dep_001/ramp",
    );
    expect(JSON.parse(String((call[1] as RequestInit).body))).toEqual({
      traffic_percent: 50,
    });
  });

  it("starts a canary deployment from an approved change package", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            deployment: {
              id: "dep_new",
              agentId: "agt_x",
              versionId: "v2",
              changePackageId: "cp_1",
              evidencePackId: "ep_1",
              stage: "canary",
              status: "canary",
              trafficPercent: 10,
              createdAt: "2026-05-09T00:00:00Z",
              promotedAt: null,
              pausedAt: null,
              rolledBackAt: null,
              notes: null,
            },
            evidence_pack: {
              id: "ep_1",
              workspace_id: "ws_1",
              agent_id: "agt_x",
              version_id: "v2",
              deployment_id: "dep_new",
              change_package_id: "cp_1",
              version_manifest: {},
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
              export_formats: ["pdf", "json"],
            },
          }),
          { status: 201, headers: { "content-type": "application/json" } },
        ),
    );

    const result = await startCanaryDeployment(
      "agt_x",
      {
        change_package_id: "cp_1",
        version_id: "v2",
        traffic_percent: 10,
        channel_scope: ["web_chat", "whatsapp"],
      },
      {
        fetcher: fetcher as unknown as typeof fetch,
        baseUrl: "https://api.loop.dev",
      },
    );

    expect(result.deployment.evidencePackId).toBe("ep_1");
    expect(result.deployment.stage).toBe("canary");
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock
      .calls[0]!;
    expect(call[0]).toBe(
      "https://api.loop.dev/v1/agents/agt_x/deployments/start",
    );
    expect(
      JSON.parse(String((call[1] as RequestInit | undefined)?.body)),
    ).toMatchObject({
      change_package_id: "cp_1",
      channel_scope: ["web_chat", "whatsapp"],
    });
  });

  it("requires cp-api before starting a deployment", async () => {
    await expect(
      startCanaryDeployment("agt_shadow", {
        change_package_id: "cp_shadow",
        version_id: "v2",
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required to start deployments");
  });

  it("starts a shadow deployment with zero routed traffic only in explicit fixture mode", async () => {
    const result = await startCanaryDeployment(
      "agt_shadow",
      {
        change_package_id: "cp_shadow",
        version_id: "v2",
        stage: "shadow",
        traffic_percent: 40,
        channel_scope: ["web_chat"],
      },
      { allowFixture: true },
    );

    expect(result.deployment.stage).toBe("shadow");
    expect(result.deployment.status).toBe("shadow");
    expect(result.deployment.trafficPercent).toBe(0);
    expect(result.evidence_pack.canary_results_ref).toContain("/shadow");
  });

  it("rollback throws on non-ok response", async () => {
    const fetcher = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({}),
    })) as unknown as typeof fetch;
    await expect(
      rollbackDeployment("a", "dep_x", {
        fetcher,
        baseUrl: "https://api.loop.dev",
      }),
    ).rejects.toThrow(/500/);
  });
});
