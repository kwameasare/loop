import type { AgentResponse, TurnEvent } from "./sdk-types";
import type { Operations } from "./openapi-types";
import { lastEventHeaders, parseSseText, type SseFrame, type SseReconnectState } from "./sse";

type FetchLike = typeof fetch;
type SleepFn = (ms: number) => Promise<void>;

export type LoopClientOptions = {
  baseUrl: string;
  token?: string;
  fetcher?: FetchLike;
  sleep?: SleepFn;
  maxRetries?: number;
};

export class LoopHttpError extends Error {
  readonly code: string;
  readonly requestId: string | undefined;
  constructor(
    message: string,
    readonly status: number,
    options: { code?: string; requestId?: string } = {},
  ) {
    super(message);
    this.code = options.code ?? `E_LOOP_${status}`;
    this.requestId = options.requestId;
  }
}

export class LoopClient {
  private readonly baseUrl: string;
  private readonly token: string | undefined;
  private readonly fetcher: FetchLike;
  private readonly sleep: SleepFn;
  private readonly maxRetries: number;

  constructor(options: LoopClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.token = options.token;
    this.fetcher = options.fetcher ?? fetch;
    this.sleep = options.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    this.maxRetries = options.maxRetries ?? 3;
  }

  async request<TResponse, TBody = unknown>(
    method: string,
    path: string,
    body?: TBody,
    init: RequestInit = {},
  ): Promise<TResponse> {
    let attempt = 0;
    while (true) {
      const headers = new Headers(init.headers);
      headers.set("accept", "application/json");
      if (body !== undefined) headers.set("content-type", "application/json");
      if (this.token) headers.set("authorization", `Bearer ${this.token}`);
      const response = await this.fetcher(`${this.baseUrl}${path}`, {
        ...init,
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (response.ok) {
        if (response.status === 204) return undefined as TResponse;
        return (await response.json()) as TResponse;
      }
      if (response.status >= 500 && attempt < this.maxRetries) {
        await this.sleep(this.retryDelayMs(response, attempt));
        attempt += 1;
        continue;
      }
      throw new LoopHttpError(
        `Loop API ${method} ${path} failed: ${response.status}`,
        response.status,
        { requestId: response.headers.get("x-request-id") ?? undefined },
      );
    }
  }

  operation<K extends keyof Operations>(
    operation: Operations[K],
    body?: Operations[K]["request"],
    init?: RequestInit,
  ): Promise<Operations[K]["response"]> {
    return this.request<Operations[K]["response"], Operations[K]["request"]>(
      operation.method,
      operation.path,
      body,
      init,
    );
  }

  async invokeTurn(
    agentId: string,
    body: Operations["PostAgentsByAgentIdInvoke"]["request"],
    state: SseReconnectState = { lastEventId: null, retryMs: 1000 },
  ): Promise<{ frames: SseFrame<TurnEvent>[]; reconnect: SseReconnectState }> {
    const response = await this.fetcher(`${this.baseUrl}/agents/${agentId}/invoke?stream=true`, {
      method: "POST",
      headers: {
        accept: "text/event-stream",
        "content-type": "application/json",
        ...(this.token ? { authorization: `Bearer ${this.token}` } : {}),
        ...lastEventHeaders(state),
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new LoopHttpError(
        `Loop API POST /turns stream failed: ${response.status}`,
        response.status,
        { requestId: response.headers.get("x-request-id") ?? undefined },
      );
    }
    const text = await response.text();
    const frames = parseSseText<TurnEvent>(text);
    const reconnect = frames.reduce(
      (acc, frame) => ({
        lastEventId: frame.id ?? acc.lastEventId,
        retryMs: frame.retry ?? acc.retryMs,
      }),
      state,
    );
    return { frames, reconnect };
  }

  async invokeTurnOnce(
    agentId: string,
    body: Operations["PostAgentsByAgentIdInvoke"]["request"],
  ): Promise<AgentResponse> {
    return this.request<AgentResponse, Operations["PostAgentsByAgentIdInvoke"]["request"]>(
      "POST",
      `/agents/${agentId}/invoke?stream=false`,
      body,
    );
  }

  private retryDelayMs(response: Response, attempt: number): number {
    const retryAfter = response.headers.get("Retry-After");
    if (retryAfter) {
      const seconds = Number.parseInt(retryAfter, 10);
      if (Number.isFinite(seconds) && seconds >= 0) return seconds * 1000;
    }
    return 100 * 2 ** attempt;
  }
}
