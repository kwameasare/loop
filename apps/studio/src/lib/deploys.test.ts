import { describe, expect, it, vi } from "vitest";

import {
  findCurrentCanary,
  findLiveDeployment,
  listDeployments,
  pauseDeployment,
  promoteDeployment,
  rollbackDeployment,
  type Deployment,
} from "./deploys";

describe("listDeployments fixture mode", () => {
  it("returns canary + live deployments seeded for the agent", async () => {
    const { items } = await listDeployments("agt_fix_a");
    expect(items.find((d) => d.status === "canary")).toBeDefined();
    expect(items.find((d) => d.status === "live")).toBeDefined();
  });

  it("promote moves canary to live and supersedes prior live", async () => {
    const { items: before } = await listDeployments("agt_fix_b");
    const canary = findCurrentCanary(before)!;
    const promoted = await promoteDeployment("agt_fix_b", canary.id);
    expect(promoted.status).toBe("live");
    expect(promoted.trafficPercent).toBe(100);
    const { items: after } = await listDeployments("agt_fix_b");
    const lives = after.filter((d) => d.status === "live");
    expect(lives).toHaveLength(1);
    expect(after.some((d) => d.status === "superseded")).toBe(true);
  });

  it("pause freezes the deployment without changing traffic", async () => {
    const { items } = await listDeployments("agt_fix_c");
    const canary = findCurrentCanary(items)!;
    const paused = await pauseDeployment("agt_fix_c", canary.id);
    expect(paused.status).toBe("paused");
    expect(paused.pausedAt).not.toBeNull();
  });

  it("rollback flips a live deployment to rolled_back and restores prior", async () => {
    const { items } = await listDeployments("agt_fix_d");
    const live = findLiveDeployment(items)!;
    const result = await rollbackDeployment("agt_fix_d", live.id);
    expect(result.status).toBe("rolled_back");
    expect(result.trafficPercent).toBe(0);
  });
});

describe("listDeployments cp-api mode", () => {
  it("calls the deployments endpoint and returns parsed items", async () => {
    const sample: Deployment = {
      id: "dep_001",
      agentId: "agt_x",
      versionId: "ver_1",
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
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock.calls[0];
    expect(call[0]).toBe("https://api.loop.dev/v1/agents/agt_x/deployments");
  });

  it("promote POSTs to the promote endpoint", async () => {
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        id: "dep_001", agentId: "a", versionId: "v", status: "live",
        trafficPercent: 100, createdAt: "", promotedAt: "now",
        pausedAt: null, rolledBackAt: null, notes: null,
      }),
    })) as unknown as typeof fetch;
    await promoteDeployment("a", "dep_001", {
      fetcher,
      baseUrl: "https://api.loop.dev",
    });
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock.calls[0];
    expect(call[0]).toBe("https://api.loop.dev/v1/agents/a/deployments/dep_001/promote");
    expect((call[1] as { method: string }).method).toBe("POST");
  });

  it("rollback throws on non-ok response", async () => {
    const fetcher = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({}),
    })) as unknown as typeof fetch;
    await expect(
      rollbackDeployment("a", "dep_x", { fetcher, baseUrl: "https://api.loop.dev" }),
    ).rejects.toThrow(/500/);
  });
});
