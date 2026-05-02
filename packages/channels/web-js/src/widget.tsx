import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
} from "react";

import {
  WebChannelClient,
  type WebChannelClientOptions,
  type WebChannelEvent,
} from "./index";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  /** "streaming" while tokens are flowing, "complete" after final, "error" on failure. */
  status: "streaming" | "complete" | "error";
}

export type StreamFn = (
  prompt: string,
  signal: AbortSignal,
) => AsyncIterable<WebChannelEvent>;

export interface ChatWidgetProps {
  /** Pre-built client. Omit to use ``connect`` instead. */
  client?: WebChannelClient;
  /** Convenience: build a client from these options. */
  connect?: WebChannelClientOptions;
  /** Override the stream source (used by tests/stories). */
  stream?: StreamFn;
  /** Initial messages to display (e.g., a greeting). */
  initialMessages?: ChatMessage[];
  /** Visual title rendered above the message list. */
  title?: string;
  /** Placeholder for the prompt input. */
  placeholder?: string;
  /**
   * S178: sessionStorage key used to persist the last 30 messages.
   * Omit to disable persistence. Must be unique per agent/widget instance.
   */
  historyKey?: string;
}

let counter = 0;
function nextId(): string {
  counter += 1;
  return `m_${counter}`;
}

// ---------------------------------------------------------------------------
// S178: History persistence helpers
// ---------------------------------------------------------------------------
const HISTORY_MAX = 30;

function loadHistory(key: string): ChatMessage[] {
  if (typeof sessionStorage === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Only restore completed messages -- drop any streaming/error state
    return (parsed as ChatMessage[]).filter((m) => m.status === "complete");
  } catch {
    return [];
  }
}

function saveHistory(key: string, messages: ChatMessage[]): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    const toSave = messages
      .filter((m) => m.status === "complete")
      .slice(-HISTORY_MAX);
    sessionStorage.setItem(key, JSON.stringify(toSave));
  } catch {
    // Silently ignore quota errors
  }
}

// ---------------------------------------------------------------------------
// S178: Typing indicator
// ---------------------------------------------------------------------------

/** Animated three-dot indicator shown while the assistant is typing. */
function TypingIndicator() {
  return (
    <li
      data-testid="chat-typing-indicator"
      aria-label="Assistant is typing"
      style={{
        alignSelf: "flex-start",
        display: "flex",
        gap: 4,
        padding: "8px 10px",
        borderRadius: 12,
        background: "#f3f4f6",
      }}
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#9ca3af",
            display: "inline-block",
            animation: `loop-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </li>
  );
}

function resolveStream(
  props: Pick<ChatWidgetProps, "stream" | "client" | "connect">,
): StreamFn {
  if (props.stream) return props.stream;
  const client =
    props.client ??
    (props.connect ? new WebChannelClient(props.connect) : null);
  if (!client) {
    throw new Error(
      "ChatWidget requires one of: stream, client, or connect props.",
    );
  }
  return (prompt, signal) => client.send(prompt, { signal });
}

/**
 * Drop-in chat surface for the Loop Web channel. Renders the message
 * list, a prompt input, and pipes streamed tokens straight into the
 * latest assistant message bubble.
 */
export function ChatWidget(props: ChatWidgetProps) {
  const {
    initialMessages = [],
    title = "Loop chat",
    placeholder = "Send a message…",
    historyKey,
  } = props;

  // S178: seed from sessionStorage when a historyKey is provided
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (historyKey) {
      const persisted = loadHistory(historyKey);
      if (persisted.length > 0) return persisted;
    }
    return initialMessages;
  });
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const inputId = useId();
  const abortRef = useRef<AbortController | null>(null);

  // S178: persist whenever messages change
  useEffect(() => {
    if (historyKey) saveHistory(historyKey, messages);
  }, [historyKey, messages]);

  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  const send = useCallback(
    async (text: string) => {
      const stream = resolveStream(props);
      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        text,
        status: "complete",
      };
      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: "assistant",
        text: "",
        status: "streaming",
      };
      setErrorBanner(null);
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        for await (const event of stream(text, controller.signal)) {
          if (event.type === "token") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, text: m.text + event.text }
                  : m,
              ),
            );
          } else if (event.type === "complete") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      status: "complete",
                      text: event.text || m.text,
                    }
                  : m,
              ),
            );
          } else if (event.type === "error") {
            setErrorBanner(
              `${event.message}${event.requestId ? ` (request_id=${event.requestId})` : ""}`,
            );
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, status: "error" }
                  : m,
              ),
            );
          }
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id && m.status === "streaming"
              ? { ...m, status: "complete" }
              : m,
          ),
        );
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Stream failed.";
        setErrorBanner(msg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, status: "error" }
              : m,
          ),
        );
      } finally {
        setStreaming(false);
        abortRef.current = null;
      }
    },
    [props],
  );

  const handleSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const trimmed = input.trim();
      if (!trimmed || streaming) return;
      setInput("");
      void send(trimmed);
    },
    [input, send, streaming],
  );

  const isEmpty = messages.length === 0 && errorBanner === null;

  return (
    <section
      data-testid="chat-widget"
      className="loop-chat-widget"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 320,
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        background: "#fff",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <header
        style={{
          padding: "10px 12px",
          borderBottom: "1px solid #e5e7eb",
          fontSize: 14,
          fontWeight: 600,
        }}
      >
        {title}
      </header>
      <ol
        data-testid="chat-messages"
        style={{
          listStyle: "none",
          margin: 0,
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          overflowY: "auto",
          flex: 1,
        }}
      >
        {isEmpty ? (
          <li
            data-testid="chat-empty"
            style={{ color: "#6b7280", fontSize: 13 }}
          >
            Say hi to get started.
          </li>
        ) : null}
        {messages.map((m) => (
          <li
            key={m.id}
            data-testid={`chat-message-${m.role}`}
            data-status={m.status}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "80%",
              padding: "6px 10px",
              borderRadius: 12,
              fontSize: 14,
              background:
                m.role === "user"
                  ? "#2563eb"
                  : m.status === "error"
                    ? "#fee2e2"
                    : "#f3f4f6",
              color: m.role === "user" ? "#fff" : "#111827",
              whiteSpace: "pre-wrap",
            }}
          >
            {m.text || (m.status === "streaming" ? "…" : "")}
          </li>
        ))}
        {/* S178: typing indicator while server is streaming and no text yet */}
        {streaming && messages.at(-1)?.role === "assistant" && messages.at(-1)?.text === "" ? (
          <TypingIndicator />
        ) : null}
      </ol>
      {errorBanner ? (
        <p
          data-testid="chat-error"
          style={{
            margin: 0,
            padding: "6px 12px",
            background: "#fee2e2",
            color: "#991b1b",
            fontSize: 12,
          }}
        >
          {errorBanner}
        </p>
      ) : null}
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          gap: 6,
          padding: 8,
          borderTop: "1px solid #e5e7eb",
        }}
      >
        <label htmlFor={inputId} style={{ position: "absolute", left: -9999 }}>
          Message
        </label>
        <input
          id={inputId}
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={streaming}
          style={{
            flex: 1,
            padding: "6px 8px",
            border: "1px solid #d1d5db",
            borderRadius: 6,
            fontSize: 14,
          }}
        />
        <button
          type="submit"
          data-testid="chat-send"
          disabled={!input.trim() || streaming}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "none",
            background: "#111827",
            color: "#fff",
            fontSize: 14,
            cursor: streaming ? "not-allowed" : "pointer",
            opacity: !input.trim() || streaming ? 0.5 : 1,
          }}
        >
          {streaming ? "…" : "Send"}
        </button>
      </form>
    </section>
  );
}
