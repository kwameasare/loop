import { describe, expect, it } from "vitest";

import { listAgentVersions, priorVersion } from "./agent-versions";

describe("listAgentVersions", () => {
  it("paginates the fixture with the requested page size", async () => {
    const first = await listAgentVersions("agt_1", { pageSize: 5 });
    expect(first.items).toHaveLength(5);
    expect(first.next_cursor).toBe("5");

    const second = await listAgentVersions("agt_1", {
      pageSize: 5,
      cursor: first.next_cursor!,
    });
    expect(second.items).toHaveLength(5);
    expect(second.next_cursor).toBe("10");

    const tail = await listAgentVersions("agt_1", {
      pageSize: 5,
      cursor: second.next_cursor!,
    });
    expect(tail.items).toHaveLength(2);
    expect(tail.next_cursor).toBeNull();
  });

  it("orders versions newest-first", async () => {
    const { items } = await listAgentVersions("agt_1", { pageSize: 100 });
    const numbers = items.map((v) => v.version);
    expect(numbers).toEqual([...numbers].sort((a, b) => b - a));
  });
});

describe("priorVersion", () => {
  it("returns the version with version-1 against the target", async () => {
    const { items } = await listAgentVersions("agt_1", { pageSize: 100 });
    const v5 = items.find((v) => v.version === 5)!;
    const prior = priorVersion(items, v5);
    expect(prior?.version).toBe(4);
  });

  it("returns null for the first-ever version", async () => {
    const { items } = await listAgentVersions("agt_1", { pageSize: 100 });
    const v1 = items.find((v) => v.version === 1)!;
    expect(priorVersion(items, v1)).toBeNull();
  });
});
