import { describe, expect, it } from "vitest";

import {
  flowFromYaml,
  flowToYaml,
  makeMemoryFlowApi,
} from "./flow-yaml";

const SAMPLE = {
  nodes: [
    { id: "start-1", type: "start" as const, x: 100, y: 100 },
    { id: "message-1", type: "message" as const, x: 300, y: 200 },
  ],
  edges: [{ id: "edge-1", source: "start-1", target: "message-1" }],
};

describe("flow-yaml", () => {
  it("flowToYaml produces deterministic, indented YAML", () => {
    const yaml = flowToYaml(SAMPLE);
    expect(yaml).toBe(
      [
        "nodes:",
        '  - id: "start-1"',
        '    type: "start"',
        "    x: 100",
        "    y: 100",
        '  - id: "message-1"',
        '    type: "message"',
        "    x: 300",
        "    y: 200",
        "edges:",
        '  - id: "edge-1"',
        '    source: "start-1"',
        '    target: "message-1"',
        "",
      ].join("\n"),
    );
  });

  it("flowToYaml renders empty docs explicitly", () => {
    expect(flowToYaml({ nodes: [], edges: [] })).toBe(
      "nodes:\n  []\nedges:\n  []\n",
    );
  });

  it("flowFromYaml round-trips through flowToYaml", () => {
    const yaml = flowToYaml(SAMPLE);
    const parsed = flowFromYaml(yaml);
    expect(parsed).toEqual(SAMPLE);
  });

  it("flowFromYaml handles empty doc and unknown extra whitespace", () => {
    const empty = flowFromYaml("nodes:\n  []\nedges:\n  []\n");
    expect(empty).toEqual({ nodes: [], edges: [] });
  });
});

describe("makeMemoryFlowApi", () => {
  it("save with matching base tag succeeds and rotates the tag", async () => {
    const api = makeMemoryFlowApi();
    const first = await api.save("a1", {
      flowYaml: "nodes:\n  []\nedges:\n  []\n",
      baseVersionTag: null,
    });
    expect(first.ok).toBe(true);
    expect(first.versionTag).toBe("v-1");

    const second = await api.save("a1", {
      flowYaml: "nodes:\n  []\nedges:\n  []\n",
      baseVersionTag: "v-1",
    });
    expect(second.ok).toBe(true);
    expect(second.versionTag).toBe("v-2");
  });

  it("save with stale base tag returns the server's current tag", async () => {
    const api = makeMemoryFlowApi();
    const a = await api.save("a1", {
      flowYaml: "nodes:\n  []\nedges:\n  []\n",
      baseVersionTag: null,
    });
    expect(a.ok).toBe(true);
    const stale = await api.save("a1", {
      flowYaml: "nodes:\n  []\nedges:\n  []\n",
      baseVersionTag: "v-0-mismatch",
    });
    expect(stale.ok).toBe(false);
    expect(stale.error).toBe("stale_version_tag");
    expect(stale.serverVersionTag).toBe("v-1");
  });

  it("load returns null for an unknown agent and the seeded version otherwise", async () => {
    const api = makeMemoryFlowApi({
      agentId: "a1",
      flowYaml: "nodes:\n  []\nedges:\n  []\n",
      versionTag: "v-seed",
    });
    expect(await api.load("missing")).toBeNull();
    expect(await api.load("a1")).toEqual({
      flowYaml: "nodes:\n  []\nedges:\n  []\n",
      versionTag: "v-seed",
    });
  });
});
