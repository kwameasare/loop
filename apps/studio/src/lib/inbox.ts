/**
 * Operator inbox: types + reducers + fixtures.
 *
 * Wire shape mirrors `loop_control_plane.inbox` /
 * `loop_control_plane.inbox_api`. Reducers are pure so the screen
 * can drive optimistic updates and tests can exercise the state
 * machine without an HTTP layer.
 */

export type InboxStatus = "pending" | "claimed" | "resolved";

export type InboxItem = {
  id: string;
  workspace_id: string;
  agent_id: string;
  conversation_id: string;
  user_id: string;
  status: InboxStatus;
  reason: string;
  operator_id: string | null;
  created_at_ms: number;
  claimed_at_ms: number | null;
  resolved_at_ms: number | null;
  last_message_excerpt: string;
};

export class InboxStateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InboxStateError";
  }
}

export function claimItem(
  item: InboxItem,
  args: { operator_id: string; now_ms: number },
): InboxItem {
  if (item.status !== "pending") {
    throw new InboxStateError(
      `cannot claim from status ${item.status}`,
    );
  }
  return {
    ...item,
    status: "claimed",
    operator_id: args.operator_id,
    claimed_at_ms: args.now_ms,
  };
}

export function releaseItem(item: InboxItem): InboxItem {
  if (item.status !== "claimed") {
    throw new InboxStateError(
      `cannot release from status ${item.status}`,
    );
  }
  return {
    ...item,
    status: "pending",
    operator_id: null,
    claimed_at_ms: null,
  };
}

export function resolveItem(
  item: InboxItem,
  args: { now_ms: number },
): InboxItem {
  if (item.status !== "claimed") {
    throw new InboxStateError(
      `cannot resolve from status ${item.status}`,
    );
  }
  return {
    ...item,
    status: "resolved",
    resolved_at_ms: args.now_ms,
  };
}

/** Pending items for a workspace, oldest first. */
export function listPending(
  items: InboxItem[],
  workspace_id: string,
): InboxItem[] {
  return items
    .filter((i) => i.workspace_id === workspace_id && i.status === "pending")
    .sort((a, b) => a.created_at_ms - b.created_at_ms);
}

/** Items currently CLAIMED by an operator, oldest claim first. */
export function listClaimedBy(
  items: InboxItem[],
  operator_id: string,
): InboxItem[] {
  return items
    .filter(
      (i) => i.status === "claimed" && i.operator_id === operator_id,
    )
    .sort(
      (a, b) =>
        (a.claimed_at_ms ?? 0) - (b.claimed_at_ms ?? 0),
    );
}

export function formatRelativeMs(now_ms: number, then_ms: number): string {
  const delta = Math.max(0, now_ms - then_ms);
  const sec = Math.floor(delta / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

// ---------------------------------------------------------------- fixtures

export const FIXTURE_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001";
export const FIXTURE_OPERATOR_ID = "op-alice";
export const FIXTURE_NOW_MS = Date.UTC(2026, 4, 1, 12, 0, 0);

export const FIXTURE_INBOX: InboxItem[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    workspace_id: FIXTURE_WORKSPACE_ID,
    agent_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    conversation_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
    user_id: "user-7281",
    status: "pending",
    reason: "user requested human",
    operator_id: null,
    created_at_ms: FIXTURE_NOW_MS - 4 * 60 * 1000,
    claimed_at_ms: null,
    resolved_at_ms: null,
    last_message_excerpt:
      "I'd like to talk to a real person about my refund please.",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    workspace_id: FIXTURE_WORKSPACE_ID,
    agent_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    conversation_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
    user_id: "user-9914",
    status: "pending",
    reason: "low confidence: refund policy",
    operator_id: null,
    created_at_ms: FIXTURE_NOW_MS - 12 * 60 * 1000,
    claimed_at_ms: null,
    resolved_at_ms: null,
    last_message_excerpt:
      "The bot keeps repeating itself, this isn't useful.",
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    workspace_id: FIXTURE_WORKSPACE_ID,
    agent_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    conversation_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
    user_id: "user-1024",
    status: "claimed",
    reason: "PII detected in user input",
    operator_id: FIXTURE_OPERATOR_ID,
    created_at_ms: FIXTURE_NOW_MS - 25 * 60 * 1000,
    claimed_at_ms: FIXTURE_NOW_MS - 60 * 1000,
    resolved_at_ms: null,
    last_message_excerpt:
      "My account is 4111-1111-1111-1111 and I need to update it.",
  },
];
