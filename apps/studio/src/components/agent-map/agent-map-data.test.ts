import { describe, expect, it } from "vitest";

import { fetchAgentMapData } from "./agent-map-data";

describe("fetchAgentMapData", () => {
  it("preserves the versions backend degraded reason when no map can be built", async () => {
    const data = await fetchAgentMapData("agent_1", { baseUrl: "" });

    expect(data.nodes).toEqual([]);
    expect(data.degradedReason).toMatch(/control-plane versions endpoint/i);
    expect(data.agentName).toBe("Agent agent_1");
  });
});
