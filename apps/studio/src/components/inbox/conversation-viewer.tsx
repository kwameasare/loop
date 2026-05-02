"use client";

import { useEffect, useRef, useState } from "react";

import {
  appendMessage,
  type ConversationMessage,
  type ConversationSubscriber,
} from "@/lib/conversation";

export type TakeoverFn = (args: {
  conversation_id: string;
}) => Promise<{ ok: boolean; error?: string }>;

export type PostMessageFn = (args: {
  conversation_id: string;
  body: string;
}) => Promise<{ ok: boolean; message?: ConversationMessage; error?: string }>;

export interface ConversationViewerProps {
  conversation_id: string;
  initialTranscript: ConversationMessage[];
  subscribe: ConversationSubscriber;
  operator_id?: string;
  takeover?: TakeoverFn;
  postMessage?: PostMessageFn;
  initialOwnership?: "agent" | "operator";
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
  const [ownership, setOwnership] = useState<"agent" | "operator">(
    props.initialOwnership ?? "agent",
  );
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
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

  async function handleTakeover() {
    if (!props.takeover || ownership === "operator" || busy) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      const res = await props.takeover({
        conversation_id: props.conversation_id,
      });
      if (res.ok) {
        setOwnership("operator");
      } else {
        setErrorMsg(res.error ?? "Takeover failed");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleSend() {
    if (!props.postMessage || ownership !== "operator" || busy) return;
    const body = draft.trim();
    if (body.length === 0) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      const res = await props.postMessage({
        conversation_id: props.conversation_id,
        body,
      });
      if (res.ok) {
        if (res.message) {
          setTranscript((prev) => appendMessage(prev, res.message!));
        }
        setDraft("");
      } else {
        setErrorMsg(res.error ?? "Post failed");
      }
    } finally {
      setBusy(false);
    }
  }

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
        className="flex items-center justify-between rounded border bg-zinc-50 px-3 py-2 text-xs"
        data-testid="conversation-ownership-bar"
      >
        <span data-testid="conversation-ownership">
          {ownership === "operator"
            ? "You have taken over this conversation. The agent is paused."
            : "Agent is handling this conversation."}
        </span>
        {ownership === "agent" ? (
          <button
            className="rounded bg-blue-600 px-3 py-1 text-white hover:bg-blue-700 disabled:opacity-50"
            data-testid="conversation-takeover"
            disabled={busy || !props.takeover}
            onClick={handleTakeover}
            type="button"
          >
            {busy ? "Taking over…" : "Takeover"}
          </button>
        ) : (
          <span
            className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-700"
            data-testid="conversation-owned-badge"
          >
            Operator
          </span>
        )}
      </div>

      {errorMsg ? (
        <p
          className="rounded border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700"
          data-testid="conversation-error"
          role="alert"
        >
          {errorMsg}
        </p>
      ) : null}

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

      <form
        className="flex flex-col gap-2"
        data-testid="conversation-composer"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSend();
        }}
      >
        <textarea
          aria-label="Compose a reply"
          className="rounded border px-3 py-2 text-sm disabled:bg-zinc-100"
          data-testid="conversation-composer-input"
          disabled={ownership !== "operator" || busy}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={
            ownership === "operator"
              ? "Type a reply… (Shift+Enter for newline)"
              : "Take over this conversation to reply."
          }
          rows={3}
          value={draft}
        />
        <div className="flex justify-end">
          <button
            className="rounded bg-emerald-600 px-3 py-1 text-sm text-white hover:bg-emerald-700 disabled:opacity-50"
            data-testid="conversation-composer-send"
            disabled={
              ownership !== "operator" ||
              busy ||
              draft.trim().length === 0 ||
              !props.postMessage
            }
            type="submit"
          >
            {busy ? "Sending…" : "Send as operator"}
          </button>
        </div>
      </form>
    </section>
  );
}
