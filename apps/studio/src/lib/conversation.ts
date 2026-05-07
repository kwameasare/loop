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
