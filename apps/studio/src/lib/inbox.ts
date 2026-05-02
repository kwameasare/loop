/**
 * Operator inbox: types + reducers + fixtures.
 *
 * Wire shape mirrors `loop_control_plane.inbox` /
 * `loop_control_plane.inbox_api`. Reducers are pure so the screen
 * can drive optimistic updates and tests can exercise the state
 * machine without an HTTP layer.
 */

export type InboxStatus = "pending" | "claimed" | "resolved";

export type InboxChannel = "web" | "voice" | "sms" | "whatsapp" | "slack";

export type InboxItem = {
  id: string;
  workspace_id: string;
  team_id: string;
  agent_id: string;
  channel: InboxChannel;
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
    team_id: "team-care",
    agent_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    channel: "web",
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
    team_id: "team-care",
    agent_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    channel: "whatsapp",
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
    team_id: "team-trust",
    agent_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    channel: "voice",
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

export const FIXTURE_TEAMS: { id: string; name: string }[] = [
  { id: "team-care", name: "Customer Care" },
  { id: "team-trust", name: "Trust & Safety" },
  { id: "team-billing", name: "Billing" },
];

export const FIXTURE_AGENTS: { id: string; name: string }[] = [
  { id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", name: "Support Bot" },
  { id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", name: "Voice Concierge" },
  { id: "cccccccc-cccc-cccc-cccc-cccccccccccc", name: "Billing Helper" },
];

export const FIXTURE_QUEUE: InboxItem[] = (() => {
  const teams = ["team-care", "team-trust", "team-billing"];
  const agents = [
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "cccccccc-cccc-cccc-cccc-cccccccccccc",
  ];
  const channels: InboxChannel[] = ["web", "voice", "sms", "whatsapp", "slack"];
  const statuses: InboxStatus[] = ["pending", "claimed", "resolved"];
  const items: InboxItem[] = [...FIXTURE_INBOX];
  for (let i = 0; i < 60; i += 1) {
    const status = statuses[i % statuses.length];
    items.push({
      id: `q-${String(i).padStart(3, "0")}`,
      workspace_id: FIXTURE_WORKSPACE_ID,
      team_id: teams[i % teams.length],
      agent_id: agents[i % agents.length],
      channel: channels[i % channels.length],
      conversation_id: `conv-${i}`,
      user_id: `user-${1000 + i}`,
      status,
      reason: i % 3 === 0 ? "low confidence" : "user requested human",
      operator_id: status === "pending" ? null : FIXTURE_OPERATOR_ID,
      created_at_ms: FIXTURE_NOW_MS - (i + 1) * 5 * 60 * 1000,
      claimed_at_ms:
        status === "pending"
          ? null
          : FIXTURE_NOW_MS - (i + 1) * 4 * 60 * 1000,
      resolved_at_ms:
        status === "resolved"
          ? FIXTURE_NOW_MS - (i + 1) * 3 * 60 * 1000
          : null,
      last_message_excerpt: `Sample ${i} — could you help me with my ticket?`,
    });
  }
  return items;
})();

export type InboxSortKey = "created_at" | "user_id" | "channel" | "status";

export interface InboxQueueOptions {
  workspace_id: string;
  team_id?: string;
  agent_id?: string;
  channel?: InboxChannel | "all";
  status?: InboxStatus | "all";
  sort_by?: InboxSortKey;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface InboxQueueResult {
  items: InboxItem[];
  total: number;
  page: number;
  page_size: number;
  page_count: number;
}

/**
 * Filter, sort and paginate a flat inbox dataset. Pure so the page
 * can render entirely from server state and the same function backs
 * unit tests for the query semantics.
 */
export function listInboxQueue(
  items: readonly InboxItem[],
  opts: InboxQueueOptions,
): InboxQueueResult {
  const page = Math.max(1, opts.page ?? 1);
  const page_size = Math.max(1, opts.page_size ?? 20);
  const sort_by = opts.sort_by ?? "created_at";
  const sort_dir = opts.sort_dir ?? "desc";

  const filtered = items.filter((it) => {
    if (it.workspace_id !== opts.workspace_id) return false;
    if (opts.team_id && it.team_id !== opts.team_id) return false;
    if (opts.agent_id && it.agent_id !== opts.agent_id) return false;
    if (opts.channel && opts.channel !== "all" && it.channel !== opts.channel) {
      return false;
    }
    if (opts.status && opts.status !== "all" && it.status !== opts.status) {
      return false;
    }
    return true;
  });

  filtered.sort((a, b) => {
    let cmp = 0;
    if (sort_by === "created_at") cmp = a.created_at_ms - b.created_at_ms;
    else if (sort_by === "user_id") cmp = a.user_id.localeCompare(b.user_id);
    else if (sort_by === "channel") cmp = a.channel.localeCompare(b.channel);
    else if (sort_by === "status") cmp = a.status.localeCompare(b.status);
    return sort_dir === "asc" ? cmp : -cmp;
  });

  const total = filtered.length;
  const page_count = Math.max(1, Math.ceil(total / page_size));
  const safePage = Math.min(page, page_count);
  const start = (safePage - 1) * page_size;
  return {
    items: filtered.slice(start, start + page_size),
    total,
    page: safePage,
    page_size,
    page_count,
  };
}
