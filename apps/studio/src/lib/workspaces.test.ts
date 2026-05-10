import { describe, expect, it } from "vitest";

import {
  createWorkspace,
  listFixtureWorkspaces,
  listWorkspaces,
} from "./workspaces";

describe("listWorkspaces", () => {
  it("does not create fixture workspace context by default", async () => {
    const out = await listWorkspaces({ baseUrl: "" });
    expect(out.workspaces).toEqual([]);
    expect(out.degraded_reason).toMatch(/workspace endpoint/i);
  });

  it("keeps fixture workspaces only for explicit fixture mode", async () => {
    const out = await listFixtureWorkspaces();
    expect(out.workspaces.map((workspace) => workspace.slug)).toEqual([
      "local",
    ]);

    const explicit = await listWorkspaces({ baseUrl: "", allowFixture: true });
    expect(explicit.workspaces.map((workspace) => workspace.slug)).toEqual([
      "local",
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

  it("requires cp-api for workspace creation", async () => {
    await expect(
      createWorkspace({ name: "Acme", slug: "acme", region: "na-east" }, {
        baseUrl: "",
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required to create a workspace");
  });

  it("creates workspaces through cp-api and returns the persisted object", async () => {
    const fetcher = async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe("https://cp.example/v1/workspaces");
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        name: "Acme Live",
        slug: "acme-live",
        region: "eu-west",
      });
      return new Response(
        JSON.stringify({
          id: "22222222-2222-2222-2222-222222222222",
          name: "Acme Live",
          slug: "acme-live",
          role: "owner",
          region: "eu-west",
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      );
    };

    const out = await createWorkspace(
      { name: "Acme Live", slug: "acme-live", region: "eu-west" },
      {
        baseUrl: "https://cp.example",
        fetcher: fetcher as typeof fetch,
      },
    );

    expect(out).toEqual({
      id: "22222222-2222-2222-2222-222222222222",
      name: "Acme Live",
      slug: "acme-live",
      role: "owner",
    });
  });
});
