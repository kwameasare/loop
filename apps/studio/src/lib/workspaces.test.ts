import { describe, expect, it } from "vitest";

import { listFixtureWorkspaces, listWorkspaces } from "./workspaces";

describe("listWorkspaces", () => {
  it("keeps fixture workspaces for no-backend local mode", async () => {
    const out = await listFixtureWorkspaces();
    expect(out.workspaces.map((workspace) => workspace.slug)).toEqual([
      "acme",
      "globex",
    ]);
  });

  it("loads real workspace ids and roles from cp-api when configured", async () => {
    const fetcher = async (input: RequestInfo | URL) => {
      expect(String(input)).toBe("https://cp.example/v1/workspaces");
      return new Response(
        JSON.stringify({
          items: [
            {
              id: "11111111-1111-1111-1111-111111111111",
              name: "Acme Live",
              slug: "acme-live",
              role: "owner",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    };

    const out = await listWorkspaces({
      baseUrl: "https://cp.example",
      fetcher: fetcher as typeof fetch,
    });

    expect(out.workspaces).toEqual([
      {
        id: "11111111-1111-1111-1111-111111111111",
        name: "Acme Live",
        slug: "acme-live",
        role: "owner",
      },
    ]);
  });
});
