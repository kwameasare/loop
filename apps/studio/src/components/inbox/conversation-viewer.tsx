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

export type HandbackFn = (args: {
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
  handback?: HandbackFn;
  initialOwnership?: "agent" | "operator";
  degradedReason?: string | undefined;
}

const ROLE_LABEL: Record<ConversationMessage["role"], string> = {
  user: "User",
  assistant: "Assistant",
  operator: "Operator",
  system: "System",
};

const ROLE_CLASS: Record<ConversationMessage["role"], string> = {
  user: "bg-muted text-foreground",
  assistant: "border border-info/30 bg-info/10 text-foreground",
  operator: "border border-success/30 bg-success/10 text-foreground",
  system: "border border-warning/30 bg-warning/10 text-foreground",
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
  const [status, setStatus] = useState<
    "connecting" | "live" | "error" | "degraded"
  >(props.degradedReason ? "degraded" : "connecting");
  const [tail, setTail] = useState(true);
  const [ownership, setOwnership] = useState<"agent" | "operator">(
    props.initialOwnership ?? "agent",
  );
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [confirmHandback, setConfirmHandback] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const isDegraded = Boolean(props.degradedReason);

  useEffect(() => {
    if (props.degradedReason) {
      setStatus("degraded");
      return;
    }
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
    if (isDegraded || !props.takeover || ownership === "operator" || busy)
      return;
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
    if (isDegraded || !props.postMessage || ownership !== "operator" || busy) {
      return;
    }
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

  async function handleHandback() {
    if (isDegraded || !props.handback || ownership !== "operator" || busy) {
      return;
    }
    setBusy(true);
    setErrorMsg(null);
    try {
      const res = await props.handback({
        conversation_id: props.conversation_id,
      });
      if (res.ok) {
        setOwnership("agent");
        setConfirmHandback(false);
        setToast("Handed back to agent.");
      } else {
        setErrorMsg(res.error ?? "Handback failed");
      }
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (toast === null) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  return (
    <section className="flex flex-col gap-3" data-testid="conversation-viewer">
      <header className="flex items-center justify-between text-xs">
        <span data-testid="conversation-status">
          <span
            aria-hidden
            className={
              status === "live"
                ? "mr-1 inline-block size-2 rounded-full bg-success"
                : status === "degraded"
                  ? "mr-1 inline-block size-2 rounded-full bg-warning"
                  : status === "error"
                    ? "mr-1 inline-block size-2 rounded-full bg-destructive"
                    : "mr-1 inline-block size-2 rounded-full bg-muted-foreground"
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
        className="flex items-center justify-between rounded border bg-muted/45 px-3 py-2 text-xs"
        data-testid="conversation-ownership-bar"
      >
        <span data-testid="conversation-ownership">
          {props.degradedReason
            ? "Conversation state unavailable. Studio has paused takeover controls until backend evidence is available."
            : ownership === "operator"
              ? "You have taken over this conversation. The agent is paused."
              : "Agent is handling this conversation."}
        </span>
        {isDegraded ? null : ownership === "agent" ? (
          <button
            className="rounded bg-primary px-3 py-1 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            data-testid="conversation-takeover"
            disabled={busy || !props.takeover}
            onClick={handleTakeover}
            type="button"
          >
            {busy ? "Taking over…" : "Takeover"}
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <span
              className="rounded border border-success/30 bg-success/10 px-2 py-0.5 text-success"
              data-testid="conversation-owned-badge"
            >
              Operator
            </span>
            {props.handback ? (
              <button
                className="rounded border bg-background px-3 py-1 text-foreground hover:bg-muted disabled:opacity-50"
                data-testid="conversation-handback"
                disabled={busy}
                onClick={() => setConfirmHandback(true)}
                type="button"
              >
                Hand back to agent
              </button>
            ) : null}
          </div>
        )}
      </div>

      {errorMsg ? (
        <p
          className="rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          data-testid="conversation-error"
          role="alert"
        >
          {errorMsg}
        </p>
      ) : null}

      {props.degradedReason ? (
        <p
          className="rounded border border-warning/40 bg-warning/10 px-3 py-2 text-xs text-warning"
          data-testid="conversation-degraded"
          role="status"
        >
          {props.degradedReason}
        </p>
      ) : null}

      <div
        className="flex h-[480px] flex-col gap-2 overflow-y-auto rounded-lg border bg-card p-3"
        data-testid="conversation-scroll"
        ref={scrollRef}
      >
        {transcript.length === 0 ? (
          <p
            className="text-center text-sm text-muted-foreground"
            data-testid="conversation-empty"
          >
            {props.degradedReason
              ? "Conversation transcript unavailable."
              : "No messages yet."}
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
          className="rounded border bg-background px-3 py-2 text-sm disabled:bg-muted"
          data-testid="conversation-composer-input"
          disabled={isDegraded || ownership !== "operator" || busy}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={
            props.degradedReason
              ? "Conversation evidence is unavailable."
              : ownership === "operator"
                ? "Type a reply… (Shift+Enter for newline)"
                : "Take over this conversation to reply."
          }
          rows={3}
          value={draft}
        />
        <div className="flex justify-end">
          <button
            className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            data-testid="conversation-composer-send"
            disabled={
              ownership !== "operator" ||
              isDegraded ||
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

      {confirmHandback ? (
        <div
          aria-modal
          className="fixed inset-0 z-40 flex items-center justify-center bg-foreground/40 p-4"
          data-testid="conversation-handback-modal"
          role="dialog"
        >
          <div className="w-full max-w-sm rounded-lg border bg-card p-4 shadow-lg">
            <h2 className="text-base font-semibold">Hand back to agent?</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              The agent will resume control of this conversation. Any pending
              operator drafts will be discarded.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="rounded border bg-background px-3 py-1 text-sm hover:bg-muted"
                data-testid="conversation-handback-cancel"
                disabled={busy}
                onClick={() => setConfirmHandback(false)}
                type="button"
              >
                Cancel
              </button>
              <button
                className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                data-testid="conversation-handback-confirm"
                disabled={busy}
                onClick={handleHandback}
                type="button"
              >
                {busy ? "Handing back…" : "Hand back"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div
          aria-live="polite"
          className="fixed bottom-4 right-4 z-50 rounded-lg bg-foreground px-3 py-2 text-sm text-background shadow-lg"
          data-testid="conversation-toast"
          role="status"
        >
          {toast}
        </div>
      ) : null}
    </section>
  );
}
