/**
 * Conversation viewer types + helpers.
 *
 * Real messages will arrive via the data plane SSE stream
 * ``/v1/conversations/{id}/events``. The page subscribes when it
 * mounts and unsubscribes on unmount; the helper here keeps the
 * append/dedupe rules pure so they're easy to unit test.
 */

export type ConversationRole = "user" | "assistant" | "operator" | "system";

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: ConversationRole;
  body: string;
  created_at_ms: number;
}

export interface ConversationClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

interface CpConversationMessage {
  id: string;
  conversation_id: string;
  role: ConversationRole;
  body: string;
  created_at: string;
}

interface CpConversationDetail {
  summary: {
    id: string;
    state: "open" | "closed" | "in-takeover";
    operator_taken_over: boolean;
  };
  last_user_message?: string;
  last_assistant_message?: string;
  messages?: CpConversationMessage[];
}

function cpApiBaseUrl(override?: string): string | null {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function headers(opts: ConversationClientOptions): Record<string, string> {
  const out: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) out.authorization = `Bearer ${token}`;
  return out;
}

function mapMessage(message: CpConversationMessage): ConversationMessage {
  return {
    id: message.id,
    conversation_id: message.conversation_id,
    role: message.role,
    body: message.body,
    created_at_ms: Date.parse(message.created_at),
  };
}

function messagesFromDetail(detail: CpConversationDetail): ConversationMessage[] {
  if (detail.messages && detail.messages.length > 0) {
    return detail.messages.map(mapMessage);
  }
  const now = Date.now();
  const fallback: ConversationMessage[] = [];
  if (detail.last_user_message) {
    fallback.push({
      id: `${detail.summary.id}:last-user`,
      conversation_id: detail.summary.id,
      role: "user",
      body: detail.last_user_message,
      created_at_ms: now - 60_000,
    });
  }
  if (detail.last_assistant_message) {
    fallback.push({
      id: `${detail.summary.id}:last-assistant`,
      conversation_id: detail.summary.id,
      role: "assistant",
      body: detail.last_assistant_message,
      created_at_ms: now,
    });
  }
  return fallback;
}

export interface ConversationDetailView {
  messages: ConversationMessage[];
  ownership: "agent" | "operator";
}

export async function fetchConversationDetail(
  conversation_id: string,
  opts: ConversationClientOptions = {},
): Promise<ConversationDetailView> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    return { messages: FIXTURE_TRANSCRIPT, ownership: "agent" };
  }
  const fetcher = opts.fetcher ?? fetch;
  const response = await fetcher(
    `${base}/conversations/${encodeURIComponent(conversation_id)}`,
    {
      method: "GET",
      headers: headers(opts),
      cache: "no-store",
    },
  );
  if (response.status === 404) return { messages: [], ownership: "agent" };
  if (!response.ok) {
    throw new Error(`cp-api GET conversation -> ${response.status}`);
  }
  const detail = (await response.json()) as CpConversationDetail;
  return {
    messages: messagesFromDetail(detail),
    ownership: detail.summary.operator_taken_over ? "operator" : "agent",
  };
}

async function postConversationAction<T>(
  conversation_id: string,
  path: string,
  body: unknown,
  opts: ConversationClientOptions,
): Promise<T> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) throw new Error("LOOP_CP_API_BASE_URL is required for conversation calls");
  const fetcher = opts.fetcher ?? fetch;
  const response = await fetcher(
    `${base}/conversations/${encodeURIComponent(conversation_id)}${path}`,
    {
      method: "POST",
      headers: { ...headers(opts), "content-type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`cp-api POST conversation ${path} -> ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function takeoverConversation(
  conversation_id: string,
  opts: ConversationClientOptions = {},
): Promise<{ ok: boolean; error?: string }> {
  try {
    await postConversationAction(conversation_id, "/takeover", { note: "" }, opts);
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Takeover failed" };
  }
}

export async function handbackConversation(
  conversation_id: string,
  opts: ConversationClientOptions = {},
): Promise<{ ok: boolean; error?: string }> {
  try {
    await postConversationAction(conversation_id, "/handback", { note: "" }, opts);
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Handback failed" };
  }
}

export async function postOperatorMessage(
  args: { conversation_id: string; body: string },
  opts: ConversationClientOptions = {},
): Promise<{ ok: boolean; message?: ConversationMessage; error?: string }> {
  try {
    const message = await postConversationAction<CpConversationMessage>(
      args.conversation_id,
      "/operator-messages",
      { body: args.body },
      opts,
    );
    return { ok: true, message: mapMessage(message) };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Post failed" };
  }
}

/**
 * Append a message to a transcript, ignoring duplicates by id and
 * keeping the result sorted by created_at_ms ascending.
 */
export function appendMessage(
  transcript: readonly ConversationMessage[],
  next: ConversationMessage,
): ConversationMessage[] {
  if (transcript.some((m) => m.id === next.id)) return [...transcript];
  const merged = [...transcript, next];
  merged.sort((a, b) => a.created_at_ms - b.created_at_ms);
  return merged;
}

export interface ConversationSubscription {
  unsubscribe: () => void;
}

export type ConversationSubscriber = (args: {
  conversation_id: string;
  onMessage: (m: ConversationMessage) => void;
  onError?: (err: Error) => void;
}) => ConversationSubscription;

export function createPollingSubscriber(
  opts: ConversationClientOptions & { intervalMs?: number } = {},
): ConversationSubscriber {
  return ({ conversation_id, onMessage, onError }) => {
    const base = cpApiBaseUrl(opts.baseUrl);
    if (!base) {
      return fixtureSubscriber({
        conversation_id,
        onMessage,
        ...(onError ? { onError } : {}),
      });
    }
    let cancelled = false;
    let seen = new Set<string>();
    const intervalMs = opts.intervalMs ?? 3000;

    async function poll() {
      try {
        const detail = await fetchConversationDetail(conversation_id, opts);
        for (const message of detail.messages) {
          if (seen.has(message.id)) continue;
          seen.add(message.id);
          onMessage(message);
        }
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error("Conversation poll failed"));
      }
    }

    void poll();
    const id = window.setInterval(() => {
      if (!cancelled) void poll();
    }, intervalMs);
    return {
      unsubscribe: () => {
        cancelled = true;
        window.clearInterval(id);
      },
    };
  };
}

export const FIXTURE_CONVERSATION_ID =
  "cccccccc-cccc-cccc-cccc-cccccccccccc";

export const FIXTURE_TRANSCRIPT: ConversationMessage[] = [
  {
    id: "m1",
    conversation_id: FIXTURE_CONVERSATION_ID,
    role: "user",
    body: "Hi, I need help with a refund.",
    created_at_ms: Date.UTC(2026, 4, 1, 11, 55),
  },
  {
    id: "m2",
    conversation_id: FIXTURE_CONVERSATION_ID,
    role: "assistant",
    body: "Happy to help. Could you share your order number?",
    created_at_ms: Date.UTC(2026, 4, 1, 11, 55, 30),
  },
  {
    id: "m3",
    conversation_id: FIXTURE_CONVERSATION_ID,
    role: "user",
    body: "Order 4421. I'd like to talk to a real person please.",
    created_at_ms: Date.UTC(2026, 4, 1, 11, 56),
  },
];

/**
 * Stub subscriber used by the page in fixture mode. It pushes a
 * couple of synthetic messages on a short timer so the live tail
 * is visible during ``pnpm dev`` without the data plane.
 */
export const fixtureSubscriber: ConversationSubscriber = ({
  conversation_id,
  onMessage,
}) => {
  let cancelled = false;
  const t1 = setTimeout(() => {
    if (cancelled) return;
    onMessage({
      id: `live-${Date.now()}-1`,
      conversation_id,
      role: "user",
      body: "Are you still there?",
      created_at_ms: Date.now(),
    });
  }, 1500);
  const t2 = setTimeout(() => {
    if (cancelled) return;
    onMessage({
      id: `live-${Date.now()}-2`,
      conversation_id,
      role: "assistant",
      body: "Connecting you to a human agent now…",
      created_at_ms: Date.now(),
    });
  }, 3000);
  return {
    unsubscribe: () => {
      cancelled = true;
      clearTimeout(t1);
      clearTimeout(t2);
    },
  };
};
