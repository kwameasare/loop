"use client";

import { useEffect, useRef, useState } from "react";

import {
  appendMessage,
  type ConversationMessage,
  type ConversationSubscriber,
} from "@/lib/conversation";

export interface ConversationViewerProps {
  conversation_id: string;
  initialTranscript: ConversationMessage[];
  subscribe: ConversationSubscriber;
}

const ROLE_LABEL: Record<ConversationMessage["role"], string> = {
  user: "User",
  assistant: "Assistant",
  operator: "Operator",
  system: "System",
};

const ROLE_CLASS: Record<ConversationMessage["role"], string> = {
  user: "bg-zinc-100 text-zinc-900",
  assistant: "bg-blue-50 text-blue-900",
  operator: "bg-emerald-50 text-emerald-900",
  system: "bg-amber-50 text-amber-900",
};

function formatHHMM(ms: number): string {
  const d = new Date(ms);
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${hh}:${mm} UTC`;
}

/**
 * Live conversation viewer. Subscribes on mount, appends each
 * incoming message to the transcript, and shows a connection
 * indicator. Supports auto-scroll to the latest message and a
 * "live tail" toggle that pauses auto-scroll when the operator
 * is reading older messages.
 */
export function ConversationViewer(props: ConversationViewerProps) {
  const [transcript, setTranscript] = useState<ConversationMessage[]>(
    props.initialTranscript,
  );
  const [status, setStatus] = useState<"connecting" | "live" | "error">(
    "connecting",
  );
  const [tail, setTail] = useState(true);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sub = props.subscribe({
      conversation_id: props.conversation_id,
      onMessage: (m) => {
        setStatus("live");
        setTranscript((prev) => appendMessage(prev, m));
      },
      onError: () => setStatus("error"),
    });
    setStatus((s) => (s === "error" ? s : "live"));
    return () => sub.unsubscribe();
  }, [props]);

  useEffect(() => {
    if (!tail) return;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [transcript, tail]);

  return (
    <section
      className="flex flex-col gap-3"
      data-testid="conversation-viewer"
    >
      <header className="flex items-center justify-between text-xs">
        <span data-testid="conversation-status">
          <span
            aria-hidden
            className={
              status === "live"
                ? "mr-1 inline-block size-2 rounded-full bg-emerald-500"
                : status === "error"
                  ? "mr-1 inline-block size-2 rounded-full bg-red-500"
                  : "mr-1 inline-block size-2 rounded-full bg-zinc-400"
            }
          />
          {status}
        </span>
        <label className="flex items-center gap-2">
          <input
            checked={tail}
            data-testid="conversation-tail-toggle"
            onChange={(e) => setTail(e.target.checked)}
            type="checkbox"
          />
          Live tail
        </label>
      </header>

      <div
        className="flex h-[480px] flex-col gap-2 overflow-y-auto rounded-lg border bg-white p-3"
        data-testid="conversation-scroll"
        ref={scrollRef}
      >
        {transcript.length === 0 ? (
          <p
            className="text-center text-sm text-zinc-500"
            data-testid="conversation-empty"
          >
            No messages yet.
          </p>
        ) : (
          transcript.map((m) => (
            <article
              className={`rounded-lg px-3 py-2 text-sm ${ROLE_CLASS[m.role]}`}
              data-testid={`conversation-message-${m.id}`}
              key={m.id}
            >
              <header className="mb-1 flex items-center justify-between text-xs opacity-70">
                <span>{ROLE_LABEL[m.role]}</span>
                <time>{formatHHMM(m.created_at_ms)}</time>
              </header>
              <p className="whitespace-pre-wrap">{m.body}</p>
            </article>
          ))
        )}
      </div>

      <footer
        className="text-muted-foreground text-xs"
        data-testid="conversation-count"
      >
        {transcript.length} message{transcript.length === 1 ? "" : "s"}
      </footer>
    </section>
  );
}
