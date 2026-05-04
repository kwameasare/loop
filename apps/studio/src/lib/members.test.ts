import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  addMember,
  listMembers,
  removeMember,
  updateMemberRole,
} from "./members";

const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIG_TOKEN = process.env.LOOP_TOKEN;

describe("members client", () => {
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    process.env.LOOP_TOKEN = "tkn";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    process.env.LOOP_TOKEN = ORIG_TOKEN;
    vi.restoreAllMocks();
  });

  it("listMembers issues GET and returns the items envelope", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            workspace_id: "ws1",
            user_sub: "user-a",
            role: "owner",
          },
        ],
      }),
    });
    const res = await listMembers("ws1", { fetcher });
    expect(res.items[0].role).toBe("owner");
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/workspaces/ws1/members");
    expect(init.method).toBe("GET");
    expect(init.headers.authorization).toBe("Bearer tkn");
  });

  it("addMember POSTs user_sub+role and returns the membership", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        workspace_id: "ws1",
        user_sub: "user-b",
        role: "admin",
      }),
    });
    const res = await addMember(
      "ws1",
      { user_sub: "user-b", role: "admin" },
      { fetcher },
    );
    expect(res.user_sub).toBe("user-b");
    const [, init] = fetcher.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      user_sub: "user-b",
      role: "admin",
    });
  });

  it("removeMember issues DELETE and tolerates 204", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => ({}),
    });
    await removeMember("ws1", "user-c", { fetcher });
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/workspaces/ws1/members/user-c");
    expect(init.method).toBe("DELETE");
  });

  it("updateMemberRole PATCHes the new role", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        workspace_id: "ws1",
        user_sub: "user-d",
        role: "viewer",
      }),
    });
    const res = await updateMemberRole("ws1", "user-d", "viewer", { fetcher });
    expect(res.role).toBe("viewer");
    const [, init] = fetcher.mock.calls[0];
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ role: "viewer" });
  });

  it("propagates non-2xx as an error", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 403, json: async () => ({}) });
    await expect(listMembers("ws1", { fetcher })).rejects.toThrow(/403/);
  });

  it("requires LOOP_CP_API_BASE_URL", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    await expect(listMembers("ws1", { fetcher: vi.fn() })).rejects.toThrow(
      /LOOP_CP_API_BASE_URL/,
    );
  });
});
