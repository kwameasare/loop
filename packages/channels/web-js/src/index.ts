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
