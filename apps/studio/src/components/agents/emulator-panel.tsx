"use client";

import { useId, useState, type FormEvent } from "react";

import { LoopClient } from "@/lib/loop-client";
import type { TurnEvent } from "@/lib/sdk-types";

export interface EmulatorPanelProps {
  agentId: string;
  /** Override for tests. Receives a prompt string + onFrame callback. */
  invoke?: (
    agentId: string,
    prompt: string,
    onFrame: (event: TurnEvent) => void,
  ) => Promise<void>;
  /** Override the default LoopClient (used in production). */
  client?: LoopClient;
}

interface ToolCallTile {
  key: string;
  name: string;
  status: "running" | "ok" | "error";
  argsPreview?: string;
  resultPreview?: string;
}

interface PanelState {
  tokens: string;
  toolCalls: ToolCallTile[];
  finalAnswer: string | null;
  degradeReason: string | null;
  done: boolean;
  error: string | null;
}

const INITIAL_STATE: PanelState = {
  tokens: "",
  toolCalls: [],
  finalAnswer: null,
  degradeReason: null,
  done: false,
  error: null,
};

function summarize(value: unknown, max = 80): string {
  if (value === undefined || value === null) return "";
  const text =
    typeof value === "string" ? value : JSON.stringify(value);
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

function defaultInvoke(client: LoopClient) {
  return async (
    agentId: string,
    prompt: string,
    onFrame: (event: TurnEvent) => void,
  ) => {
    const conversationId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `conv_${Date.now()}`;
    const result = await client.invokeTurn(agentId, {
      conversation_id: conversationId,
      user_id: "studio-emulator",
      channel: "web",
      content: [{ type: "text", text: prompt }],
    });
    for (const frame of result.frames) onFrame(frame.data);
  };
}

/**
 * Right-rail emulator. Lets editors send a quick text turn at the
 * agent and watch tokens, tool calls, and the final answer stream
 * back. Backed by ``LoopClient.invokeTurn`` (SSE under the hood).
 */
export function EmulatorPanel({
  agentId,
  invoke,
  client,
}: EmulatorPanelProps) {
  const [prompt, setPrompt] = useState("");
  const [state, setState] = useState<PanelState>(INITIAL_STATE);
  const [running, setRunning] = useState(false);
  const inputId = useId();

  const submit = invoke
    ? invoke
    : defaultInvoke(
        client ??
          new LoopClient({
            baseUrl:
              process.env.NEXT_PUBLIC_LOOP_API_URL ??
              "http://localhost:8080/v1",
          }),
      );

  function handleFrame(event: TurnEvent) {
    setState((prev) => applyEvent(prev, event));
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!prompt.trim() || running) return;
    setRunning(true);
    setState(INITIAL_STATE);
    try {
      await submit(agentId, prompt.trim(), handleFrame);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Emulator request failed.",
        done: true,
      }));
    } finally {
      setRunning(false);
    }
  }

  return (
    <aside
      className="flex h-full flex-col gap-3 rounded-lg border bg-muted/20 p-4"
      data-testid="emulator-panel"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Emulator</h2>
        <span className="text-xs text-muted-foreground">{agentId}</span>
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label htmlFor={inputId} className="sr-only">
          Prompt
        </label>
        <textarea
          id={inputId}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          disabled={running}
          data-testid="emulator-input"
          placeholder="Ask the agent something…"
          className="rounded-md border px-2 py-1 text-sm"
        />
        <button
          type="submit"
          disabled={!prompt.trim() || running}
          data-testid="emulator-send"
          className="self-end rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
        >
          {running ? "Streaming…" : "Send"}
        </button>
      </form>
      <section
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto"
        data-testid="emulator-stream"
      >
        {state.error ? (
          <p
            className="rounded-md border border-red-300 bg-red-50 p-2 text-xs text-red-800"
            data-testid="emulator-error"
          >
            {state.error}
          </p>
        ) : null}
        {state.tokens ? (
          <div data-testid="emulator-tokens" className="whitespace-pre-wrap text-sm">
            {state.tokens}
          </div>
        ) : null}
        {state.toolCalls.length > 0 ? (
          <ul
            className="flex flex-col gap-2"
            data-testid="emulator-tool-calls"
          >
            {state.toolCalls.map((call) => (
              <li
                key={call.key}
                data-testid={`emulator-tool-call-${call.name}`}
                className={
                  "rounded-md border p-2 text-xs " +
                  (call.status === "ok"
                    ? "border-green-300 bg-green-50"
                    : call.status === "error"
                      ? "border-red-300 bg-red-50"
                      : "border-amber-300 bg-amber-50")
                }
              >
                <div className="flex items-center justify-between">
                  <code className="font-medium">{call.name}</code>
                  <span className="text-muted-foreground">{call.status}</span>
                </div>
                {call.argsPreview ? (
                  <code className="block text-muted-foreground">
                    args: {call.argsPreview}
                  </code>
                ) : null}
                {call.resultPreview ? (
                  <code className="block text-muted-foreground">
                    → {call.resultPreview}
                  </code>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        {state.degradeReason ? (
          <p
            className="rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900"
            data-testid="emulator-degrade"
          >
            Degraded: {state.degradeReason}
          </p>
        ) : null}
        {state.finalAnswer ? (
          <div
            className="rounded-md border bg-background p-2 text-sm"
            data-testid="emulator-final"
          >
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Final answer
            </p>
            <p className="whitespace-pre-wrap">{state.finalAnswer}</p>
          </div>
        ) : null}
      </section>
    </aside>
  );
}

function applyEvent(state: PanelState, event: TurnEvent): PanelState {
  const e = event as TurnEvent & {
    text?: string;
    name?: string;
    args?: unknown;
    result?: unknown;
    error?: unknown;
    response?: { content?: { type?: string; text?: string | null }[] };
    degrade_reason?: string;
    reason?: string;
  };
  switch (event.type) {
    case "token": {
      return { ...state, tokens: state.tokens + (e.text ?? "") };
    }
    case "tool_call":
    case "tool_call_start": {
      const name = e.name ?? "tool";
      return {
        ...state,
        toolCalls: [
          ...state.toolCalls,
          {
            key: `${name}-${state.toolCalls.length}`,
            name,
            status: "running",
            argsPreview: summarize(e.args),
          },
        ],
      };
    }
    case "tool_call_end":
    case "tool_result": {
      const name = e.name ?? "tool";
      const idx = [...state.toolCalls]
        .reverse()
        .findIndex((c) => c.name === name && c.status === "running");
      if (idx === -1) return state;
      const realIdx = state.toolCalls.length - 1 - idx;
      const updated = state.toolCalls.slice();
      const failed = e.error !== undefined && e.error !== null;
      const current = updated[realIdx];
      if (!current) return state;
      updated[realIdx] = {
        ...current,
        status: failed ? "error" : "ok",
        resultPreview: failed
          ? summarize(e.error)
          : summarize(e.result),
      };
      return { ...state, toolCalls: updated };
    }
    case "degrade": {
      return {
        ...state,
        degradeReason: e.degrade_reason ?? e.reason ?? "unknown",
      };
    }
    case "complete": {
      const parts = e.response?.content ?? [];
      const text = parts
        .filter((p) => p.type === "text")
        .map((p) => p.text ?? "")
        .join("");
      return {
        ...state,
        finalAnswer: text || state.tokens,
        done: true,
      };
    }
    default:
      return state;
  }
}
