import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  FIXTURE_INBOX,
  FIXTURE_OPERATOR_ID,
  FIXTURE_WORKSPACE_ID,
  InboxStateError,
  claimInboxItem,
  claimItem,
  formatRelativeMs,
  listClaimedBy,
  listInbox,
  listPending,
  releaseInboxItem,
  releaseItem,
  resolveInboxItem,
  resolveItem,
  takeoverConversation,
  type InboxItem,
} from "./inbox";

const pending = FIXTURE_INBOX[0];

describe("inbox reducers", () => {
  it("claimItem moves pending -> claimed and stamps operator/time", () => {
    const claimed = claimItem(pending, {
      operator_id: "alice",
      now_ms: 1_700_000_000_000,
    });
    expect(claimed.status).toBe("claimed");
    expect(claimed.operator_id).toBe("alice");
    expect(claimed.claimed_at_ms).toBe(1_700_000_000_000);
  });

  it("claimItem refuses non-pending input", () => {
    const claimed = claimItem(pending, {
      operator_id: "alice",
      now_ms: 1,
    });
    expect(() =>
      claimItem(claimed, { operator_id: "bob", now_ms: 2 }),
    ).toThrow(InboxStateError);
  });

  it("releaseItem returns claimed -> pending and clears operator", () => {
    const claimed = claimItem(pending, { operator_id: "alice", now_ms: 1 });
    const released = releaseItem(claimed);
    expect(released.status).toBe("pending");
    expect(released.operator_id).toBeNull();
    expect(released.claimed_at_ms).toBeNull();
  });

  it("releaseItem refuses non-claimed input", () => {
    expect(() => releaseItem(pending)).toThrow(InboxStateError);
  });

  it("resolveItem terminates a claimed item", () => {
    const claimed = claimItem(pending, { operator_id: "alice", now_ms: 1 });
    const resolved = resolveItem(claimed, { now_ms: 99 });
    expect(resolved.status).toBe("resolved");
    expect(resolved.resolved_at_ms).toBe(99);
  });

  it("resolveItem refuses non-claimed input", () => {
    expect(() => resolveItem(pending, { now_ms: 1 })).toThrow(
      InboxStateError,
    );
  });
});

describe("inbox listings", () => {
  it("listPending returns workspace pending oldest-first", () => {
    const out = listPending(FIXTURE_INBOX, FIXTURE_WORKSPACE_ID);
    expect(out.map((i) => i.id)).toEqual([
      "22222222-2222-2222-2222-222222222222",
      "11111111-1111-1111-1111-111111111111",
    ]);
  });

  it("listPending excludes other workspaces", () => {
    const other: InboxItem = {
      ...FIXTURE_INBOX[0],
      id: "aa",
      workspace_id: "other",
    };
    expect(
      listPending([...FIXTURE_INBOX, other], FIXTURE_WORKSPACE_ID).find(
        (i) => i.id === "aa",
      ),
    ).toBeUndefined();
  });

  it("listClaimedBy filters by operator", () => {
    const out = listClaimedBy(FIXTURE_INBOX, FIXTURE_OPERATOR_ID);
    expect(out).toHaveLength(1);
    expect(out[0].id).toBe("33333333-3333-3333-3333-333333333333");
  });
});

describe("formatRelativeMs", () => {
  it("formats seconds, minutes, hours, days", () => {
    const now = 1_000_000_000_000;
    expect(formatRelativeMs(now, now - 5_000)).toBe("5s ago");
    expect(formatRelativeMs(now, now - 90_000)).toBe("1m ago");
    expect(formatRelativeMs(now, now - 3_600_000 * 2)).toBe("2h ago");
    expect(formatRelativeMs(now, now - 86_400_000 * 3)).toBe("3d ago");
    expect(formatRelativeMs(now, now + 1_000)).toBe("0s ago");
  });
});

import { listInboxQueue, FIXTURE_QUEUE, type InboxQueueOptions } from "./inbox";

describe("listInboxQueue", () => {
  const baseOpts: InboxQueueOptions = { workspace_id: FIXTURE_WORKSPACE_ID };

  it("paginates by created_at desc by default", () => {
    const result = listInboxQueue(FIXTURE_QUEUE, { ...baseOpts, page: 1, page_size: 10 });
    expect(result.total).toBeGreaterThanOrEqual(60);
    expect(result.items).toHaveLength(10);
    for (let i = 1; i < result.items.length; i += 1) {
      expect(result.items[i - 1].created_at_ms).toBeGreaterThanOrEqual(
        result.items[i].created_at_ms,
      );
    }
  });

  it("filters by team, agent, and channel", () => {
    const careOnly = listInboxQueue(FIXTURE_QUEUE, {
      ...baseOpts,
      team_id: "team-care",
      page_size: 999,
    });
    expect(careOnly.items.every((i) => i.team_id === "team-care")).toBe(true);

    const voice = listInboxQueue(FIXTURE_QUEUE, {
      ...baseOpts,
      channel: "voice",
      page_size: 999,
    });
    expect(voice.items.every((i) => i.channel === "voice")).toBe(true);
  });

  it("sorts ascending by user_id when requested", () => {
    const result = listInboxQueue(FIXTURE_QUEUE, {
      ...baseOpts,
      sort_by: "user_id",
      sort_dir: "asc",
      page_size: 5,
    });
    const ids = result.items.map((i) => i.user_id);
    const sorted = [...ids].sort();
    expect(ids).toEqual(sorted);
  });

  it("ignores items from other workspaces", () => {
    const cross = listInboxQueue(
      [
        ...FIXTURE_QUEUE,
        { ...FIXTURE_QUEUE[0], id: "x", workspace_id: "other-ws" },
      ],
      { ...baseOpts, page_size: 999 },
    );
    expect(cross.items.find((i) => i.id === "x")).toBeUndefined();
  });

  it("clamps page beyond available pages", () => {
    const result = listInboxQueue(FIXTURE_QUEUE, {
      ...baseOpts,
      page: 99,
      page_size: 10,
    });
    expect(result.page).toBeLessThanOrEqual(result.page_count);
  });
});

describe("inbox cp-api client", () => {
  const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("listInbox GETs /v1/workspaces/{id}/inbox and returns items", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [{ id: "1", workspace_id: "ws1", status: "pending" }],
      }),
    });
    const res = await listInbox("ws1", { fetcher });
    expect(res.items).toHaveLength(1);
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/workspaces/ws1/inbox");
  });

  it("listInbox returns empty list on 404 (route not yet shipped)", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await listInbox("ws1", { fetcher });
    expect(res.items).toEqual([]);
  });

  it("listInbox propagates non-404 errors", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    await expect(listInbox("ws1", { fetcher })).rejects.toThrow(/500/);
  });

  it("claimInboxItem POSTs operator_id", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "i1", status: "claimed" }),
    });
    await claimInboxItem("i1", "op-1", { fetcher });
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/inbox/i1/claim");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ operator_id: "op-1" });
  });

  it("releaseInboxItem POSTs without a body", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "i1", status: "pending" }),
    });
    await releaseInboxItem("i1", { fetcher });
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/inbox/i1/release");
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
  });

  it("resolveInboxItem POSTs to /resolve", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "i1", status: "resolved" }),
    });
    await resolveInboxItem("i1", { fetcher });
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/inbox/i1/resolve");
  });

  it("takeoverConversation POSTs to /v1/conversations/{id}/takeover with reason", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    await takeoverConversation("c1", "user requested human", { fetcher });
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/conversations/c1/takeover");
    expect(JSON.parse(init.body)).toEqual({ reason: "user requested human" });
  });
});
