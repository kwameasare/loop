import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { listAgents } from "./cp-api";

const ORIGINAL = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_TOKEN = process.env.LOOP_TOKEN;

describe("listAgents", () => {
  beforeEach(() => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.LOOP_TOKEN;
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIGINAL;
    process.env.LOOP_TOKEN = ORIGINAL_TOKEN;
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
          created_at: "2026-04-29T12:00:00Z",
          workspace_id: "ws_1",
        },
      ],
    });

    const result = await listAgents({ fetcher: fetchMock });

    expect(result.agents[0]).toMatchObject({
      id: "agt_support",
      name: "Support",
      slug: "support",
      active_version: 3,
      workspace_id: "ws_1",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://cp.test/v1/agents",
      expect.objectContaining({
        cache: "no-store",
        headers: expect.objectContaining({
          accept: "application/json",
          authorization: "Bearer test-token",
        }),
        method: "GET",
      }),
    );
  });

  it("throws when cp-api returns a non-2xx", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 503, json: async () => ({}) });

    await expect(listAgents({ fetcher: fetchMock })).rejects.toThrow(
      /503/,
    );
  });
});
