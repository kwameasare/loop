/**
 * @loop/web-channel-js — browser-side client for the Loop Web channel.
 *
 * The package exposes a tiny, dependency-free surface so apps can embed
 * a chat conversation backed by Loop's `/v1/agents/{id}/invoke?stream=true`
 * SSE endpoint without bundling the rest of the Studio.
 */

export interface WebChannelClientOptions {
  /** Loop API base URL, e.g. ``https://api.loop.dev/v1``. */
  baseUrl: string;
  /** Agent id to chat against. */
  agentId: string;
  /** Conversation id (stable across turns). Defaults to a random id. */
  conversationId?: string;
  /** Bearer token, if your gateway requires auth. */
  token?: string;
  /** Override fetch (handy for tests / SSR). */
  fetch?: typeof fetch;
}

export interface SendOptions {
  /** Optional user id passthrough. */
  userId?: string;
  /** Abort the in-flight request. */
  signal?: AbortSignal;
}

/**
 * Backoff parameters for {@link WebChannelClient.connect}.
 *
 * The delay between attempt ``n`` and ``n + 1`` is computed as
 * ``min(initialMs * factor^n, maxMs)`` and then perturbed by a uniform
 * jitter in ``[1 - jitter, 1 + jitter]``.
 */
export interface RetryPolicy {
  initialMs?: number;
  maxMs?: number;
  factor?: number;
  /** Jitter ratio in [0, 1]. Defaults to 0.3. */
  jitter?: number;
  /** Number of reconnects allowed (in addition to the initial attempt). */
  maxAttempts?: number;
}

export interface ConnectOptions extends SendOptions {
  retry?: RetryPolicy;
  /** Resume from this SSE event id (sent as Last-Event-Id header). */
  lastEventId?: string;
  /** Notified when a reconnect is scheduled. */
  onRetry?: (info: { attempt: number; delayMs: number; lastEventId?: string }) => void;
  /**
   * Override the random source for jitter. Defaults to ``Math.random``.
   * Exposed for deterministic tests.
   */
  random?: () => number;
}

export type WebChannelEvent =
  | { type: "token"; text: string }
  | { type: "tool_call"; name: string; args?: unknown }
  | { type: "tool_result"; name: string; result?: unknown; error?: unknown }
  | { type: "complete"; text: string }
  | { type: "error"; message: string; status?: number; requestId?: string };

const DEFAULT_RETRY_MS = 1000;

function genConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `conv_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export class WebChannelClient {
  private readonly baseUrl: string;
  private readonly agentId: string;
  private readonly conversationId: string;
  private readonly token: string | undefined;
  private readonly fetcher: typeof fetch;

  constructor(options: WebChannelClientOptions) {
    if (!options.baseUrl) throw new Error("baseUrl is required");
    if (!options.agentId) throw new Error("agentId is required");
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.agentId = options.agentId;
    this.conversationId = options.conversationId ?? genConversationId();
    this.token = options.token;
    this.fetcher = options.fetch ?? fetch;
  }

  /** The conversation id this client is bound to. */
  get conversation(): string {
    return this.conversationId;
  }

  /**
   * Send a text turn and yield each parsed ``WebChannelEvent``.
   *
   * The implementation reads the SSE body and yields events as JSON
   * frames are decoded. Callers can ``for await`` the result.
   */
  async *send(
    text: string,
    options: SendOptions = {},
  ): AsyncGenerator<WebChannelEvent> {
    const headers: Record<string, string> = {
      accept: "text/event-stream",
      "content-type": "application/json",
    };
    if (this.token) headers.authorization = `Bearer ${this.token}`;
    const response = await this.fetcher(
      `${this.baseUrl}/agents/${this.agentId}/invoke?stream=true`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          conversation_id: this.conversationId,
          user_id: options.userId ?? "web-channel",
          channel: "web",
          content: [{ type: "text", text }],
        }),
        signal: options.signal,
      },
    );
    if (!response.ok) {
      yield {
        type: "error",
        message: `Loop returned ${response.status}`,
        status: response.status,
        requestId: response.headers.get("x-request-id") ?? undefined,
      };
      return;
    }
    const body = await response.text();
    for (const event of parseSseEvents(body)) {
      yield event;
    }
  }

  /**
   * Stream a turn with auto-reconnect. The generator transparently
   * reconnects with exponential backoff (and jitter) when the underlying
   * SSE stream drops mid-conversation. On reconnect it sends the most
   * recently observed ``id:`` line via the ``Last-Event-Id`` header so
   * the gateway can resume from where it left off.
   *
   * The generator terminates when:
   *   - a ``complete`` event is yielded;
   *   - the supplied ``signal`` is aborted;
   *   - ``retry.maxAttempts`` reconnects have been exhausted; or
   *   - the server returns a non-2xx response (yielded as ``error``).
   */
  async *connect(
    text: string,
    options: ConnectOptions = {},
  ): AsyncGenerator<WebChannelEvent> {
    const retry: Required<RetryPolicy> = {
      initialMs: options.retry?.initialMs ?? 250,
      maxMs: options.retry?.maxMs ?? 8000,
      factor: options.retry?.factor ?? 2,
      jitter: options.retry?.jitter ?? 0.3,
      maxAttempts: options.retry?.maxAttempts ?? 5,
    };
    const random = options.random ?? Math.random;
    const parser = new SseParser();
    if (options.lastEventId) parser.lastEventId = options.lastEventId;
    let attempt = 0;
    while (true) {
      let response: Response;
      try {
        response = await this.openStream(text, options, parser.lastEventId);
      } catch (err) {
        if (options.signal?.aborted) return;
        if (attempt >= retry.maxAttempts) {
          yield {
            type: "error",
            message: (err as Error)?.message ?? "stream error",
          };
          return;
        }
        attempt += 1;
        const delay = computeBackoff(attempt - 1, retry, random);
        options.onRetry?.({
          attempt,
          delayMs: delay,
          lastEventId: parser.lastEventId,
        });
        await sleep(delay, options.signal);
        continue;
      }
      if (!response.ok) {
        yield {
          type: "error",
          message: `Loop returned ${response.status}`,
          status: response.status,
          requestId: response.headers.get("x-request-id") ?? undefined,
        };
        return;
      }
      const reader = response.body?.getReader();
      let endedNormally = false;
      let yielded = false;
      if (!reader) {
        const body = await response.text();
        for (const ev of parser.feed(body)) {
          yield ev;
          yielded = true;
          if (ev.type === "complete") endedNormally = true;
        }
        for (const ev of parser.flush()) {
          yield ev;
          yielded = true;
          if (ev.type === "complete") endedNormally = true;
        }
      } else {
        const decoder = new TextDecoder();
        try {
          for (;;) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            for (const ev of parser.feed(chunk)) {
              yield ev;
              yielded = true;
              if (ev.type === "complete") {
                endedNormally = true;
                break;
              }
            }
            if (endedNormally) break;
          }
        } catch (err) {
          if (options.signal?.aborted) return;
          // fall through to retry path below
          void err;
        } finally {
          try {
            reader.releaseLock();
          } catch {
            /* ignore */
          }
        }
        if (!endedNormally) {
          for (const ev of parser.flush()) {
            yield ev;
            yielded = true;
            if (ev.type === "complete") endedNormally = true;
          }
        }
      }
      if (endedNormally) return;
      if (options.signal?.aborted) return;
      if (attempt >= retry.maxAttempts) {
        yield {
          type: "error",
          message: "Loop stream ended without completion after max retries",
        };
        return;
      }
      attempt += 1;
      const delay = computeBackoff(attempt - 1, retry, random);
      options.onRetry?.({
        attempt,
        delayMs: delay,
        lastEventId: parser.lastEventId,
      });
      await sleep(delay, options.signal);
      // partial progress is fine — parser keeps lastEventId across retries
      void yielded;
    }
  }

  private async openStream(
    text: string,
    options: SendOptions,
    lastEventId?: string,
  ): Promise<Response> {
    const headers: Record<string, string> = {
      accept: "text/event-stream",
      "content-type": "application/json",
    };
    if (this.token) headers.authorization = `Bearer ${this.token}`;
    if (lastEventId) headers["last-event-id"] = lastEventId;
    return this.fetcher(
      `${this.baseUrl}/agents/${this.agentId}/invoke?stream=true`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          conversation_id: this.conversationId,
          user_id: options.userId ?? "web-channel",
          channel: "web",
          content: [{ type: "text", text }],
        }),
        signal: options.signal,
      },
    );
  }
}

/**
 * Incremental SSE parser. Feed it raw chunks via {@link feed}; it yields
 * any complete events and remembers the most recent ``id:`` line so a
 * caller can resume on reconnect.
 */
export class SseParser {
  private buf = "";
  /** Last ``id:`` value observed, or ``undefined`` if none yet. */
  lastEventId: string | undefined;

  /** Append a raw chunk and return any events that became complete. */
  feed(chunk: string): WebChannelEvent[] {
    this.buf += chunk;
    const out: WebChannelEvent[] = [];
    while (true) {
      const match = this.buf.match(/\r?\n\r?\n/);
      if (!match || match.index === undefined) break;
      const end = match.index;
      const block = this.buf.slice(0, end);
      this.buf = this.buf.slice(end + match[0].length);
      const ev = this.parseBlock(block);
      if (ev) out.push(ev);
    }
    return out;
  }

  /** Drain any pending block (e.g. server closed without trailing newline). */
  flush(): WebChannelEvent[] {
    if (!this.buf.trim()) {
      this.buf = "";
      return [];
    }
    const block = this.buf;
    this.buf = "";
    const ev = this.parseBlock(block);
    return ev ? [ev] : [];
  }

  private parseBlock(block: string): WebChannelEvent | null {
    const dataLines: string[] = [];
    for (const raw of block.replace(/\r\n/g, "\n").split("\n")) {
      if (raw.startsWith("data:")) {
        dataLines.push(raw.slice(5).replace(/^ /, ""));
      } else if (raw.startsWith("id:")) {
        this.lastEventId = raw.slice(3).trim() || undefined;
      }
      // event:/retry: lines are tolerated but currently unused.
    }
    if (dataLines.length === 0) return null;
    try {
      const obj = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
      return mapServerEvent(obj);
    } catch {
      return null;
    }
  }
}

/** Compute the delay before reconnect attempt ``n`` (0-indexed). */
export function computeBackoff(
  attemptIndex: number,
  policy: Required<RetryPolicy>,
  random: () => number = Math.random,
): number {
  const base = Math.min(
    policy.initialMs * Math.pow(policy.factor, attemptIndex),
    policy.maxMs,
  );
  const jitter = policy.jitter;
  if (jitter <= 0) return base;
  const factor = 1 - jitter + random() * 2 * jitter;
  return Math.max(0, Math.round(base * factor));
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal?.aborted) {
      resolve();
      return;
    }
    const handle = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(handle);
      resolve();
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

/** Parse a full SSE body into typed events. Exported for tests. */
export function parseSseEvents(text: string): WebChannelEvent[] {
  const out: WebChannelEvent[] = [];
  for (const block of text.replace(/\r\n/g, "\n").split(/\n\n+/)) {
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
    }
    if (dataLines.length === 0) continue;
    try {
      const obj = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
      const ev = mapServerEvent(obj);
      if (ev) out.push(ev);
    } catch {
      // Drop unparseable frames; the channel intentionally tolerates noise.
    }
  }
  return out;
}

function mapServerEvent(obj: Record<string, unknown>): WebChannelEvent | null {
  const type = obj.type;
  if (type === "token") {
    return { type: "token", text: String(obj.text ?? "") };
  }
  if (type === "tool_call" || type === "tool_call_start") {
    return {
      type: "tool_call",
      name: String(obj.name ?? "tool"),
      args: obj.args,
    };
  }
  if (type === "tool_result" || type === "tool_call_end") {
    return {
      type: "tool_result",
      name: String(obj.name ?? "tool"),
      result: obj.result,
      error: obj.error,
    };
  }
  if (type === "complete") {
    const response = obj.response as
      | { content?: { type?: string; text?: string | null }[] }
      | undefined;
    const text = (response?.content ?? [])
      .filter((p) => p.type === "text")
      .map((p) => p.text ?? "")
      .join("");
    return { type: "complete", text };
  }
  return null;
}

/** Re-export so callers can opt into manual reconnect handling later. */
export const RETRY_MS = DEFAULT_RETRY_MS;

export { ChatWidget } from "./widget";
export type {
  ChatMessage,
  ChatWidgetProps,
  StreamFn,
} from "./widget";
