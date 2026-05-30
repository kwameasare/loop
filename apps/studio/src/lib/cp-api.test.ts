import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createAgent, listAgents } from "./cp-api";

const ORIGINAL = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_TOKEN = process.env.LOOP_TOKEN;
const ORIGINAL_WORKSPACE = process.env.LOOP_DEFAULT_WORKSPACE_ID;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = value;
  }
}

describe("listAgents", () => {
  beforeEach(() => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.LOOP_TOKEN;
    delete process.env.LOOP_DEFAULT_WORKSPACE_ID;
  });

  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL);
    restoreEnv("LOOP_TOKEN", ORIGINAL_TOKEN);
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
    vi.restoreAllMocks();
  });

  it("requires a real cp-api base URL", async () => {
    await expect(listAgents()).rejects.toThrow(/LOOP_CP_API_BASE_URL/);
  });

  it("calls cp-api when LOOP_CP_API_BASE_URL is set", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    process.env.LOOP_TOKEN = "test-token";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [
        {
          id: "agt_support",
          name: "Support",
          slug: "support",
          active_version: 3,
          object_state: "canary",
          state_reason: "Deployment dep_1 is in canary rollout.",
          state_evidence_ref: "deployment/dep_1",
          created_at: "2026-04-29T12:00:00Z",
          workspace_id: "ws_1",
        },
      ],
    });

    const result = await listAgents({
      fetcher: fetchMock,
      workspaceId: "ws_1",
    });

    expect(result.agents[0]).toMatchObject({
      id: "agt_support",
      name: "Support",
      slug: "support",
      active_version: 3,
      object_state: "canary",
      state_evidence_ref: "deployment/dep_1",
      workspace_id: "ws_1",
    });
    const [url, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(url).toBe("https://cp.test/v1/agents");
    expect(init).toMatchObject({ cache: "no-store", method: "GET" });
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.get("authorization")).toBe("Bearer test-token");
    expect(headers.get("x-loop-workspace-id")).toBe("ws_1");
  });

  it("throws when cp-api returns a non-2xx", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 503, json: async () => ({}) });

    await expect(listAgents({ fetcher: fetchMock })).rejects.toThrow(/503/);
  });

  it("does not invent workspace scope from LOOP_DEFAULT_WORKSPACE_ID", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    process.env.LOOP_TOKEN = "test-token";
    process.env.LOOP_DEFAULT_WORKSPACE_ID = "stale-workspace";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });

    await listAgents({ fetcher: fetchMock });

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(headers.get("x-loop-workspace-id")).toBeNull();
  });
});

describe("createAgent", () => {
  beforeEach(() => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.LOOP_TOKEN;
    delete process.env.LOOP_DEFAULT_WORKSPACE_ID;
  });

  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL);
    restoreEnv("LOOP_TOKEN", ORIGINAL_TOKEN);
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
    vi.restoreAllMocks();
  });

  it("posts the form payload to /v1/agents and returns the canonical summary", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        id: "agt_42",
        name: "Sales",
        slug: "sales",
        description: "Outbound sales",
        active_version: null,
        created_at: "2026-05-01T00:00:00Z",
        workspace_id: "ws_1",
      }),
    });

    const summary = await createAgent(
      { name: "Sales", slug: "sales", description: "Outbound sales" },
      { fetcher: fetchMock, token: "tkn", workspaceId: "ws_1" },
    );

    expect(summary).toMatchObject({
      id: "agt_42",
      name: "Sales",
      slug: "sales",
      object_state: "draft",
      workspace_id: "ws_1",
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/agents");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      name: "Sales",
      slug: "sales",
      description: "Outbound sales",
    });
    const headers = new Headers(init.headers);
    expect(headers.get("authorization")).toBe("Bearer tkn");
    expect(headers.get("x-loop-workspace-id")).toBe("ws_1");
  });

  it("propagates non-2xx responses as errors", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 409, json: async () => ({}) });

    await expect(
      createAgent({ name: "Dup", slug: "dup" }, { fetcher: fetchMock }),
    ).rejects.toThrow(/409/);
  });
});
