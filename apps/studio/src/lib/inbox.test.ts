import { describe, expect, it } from "vitest";

import {
  FIXTURE_INBOX,
  FIXTURE_OPERATOR_ID,
  FIXTURE_WORKSPACE_ID,
  InboxStateError,
  claimItem,
  formatRelativeMs,
  listClaimedBy,
  listPending,
  releaseItem,
  resolveItem,
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
