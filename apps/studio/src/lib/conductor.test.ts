import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchConductorData } from "./conductor";

describe("conductor cp-api client", () => {
  const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("fetches live conductor topology", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        agentId: "agent-1",
        agentName: "Support Bot",
        branch: "v1",
        objectState: "saved",
        trust: "healthy",
        subAgents: [],
        contracts: [],
        delegations: [],
        topology: [],
        orchestrationEvidence: "agent agent-1; version 1",
      }),
    });

    const data = await fetchConductorData("agent-1", { fetcher });

    expect(data.agentName).toBe("Support Bot");
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/agents/agent-1/conductor");
  });
});
