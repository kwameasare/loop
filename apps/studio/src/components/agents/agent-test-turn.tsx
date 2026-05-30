"use client";

/**
 * First-agent moment: send a real prompt through cp → dp → gateway →
 * model and show the reply.
 *
 * Wire: POST /v1/agents/{agent_id}/test-turn  (cp proxy → dp /v1/turns)
 *
 * The widget is intentionally small. Real "Test in workbench" UI with
 * conversation history, channel preview, etc. lives in the simulator
 * once this round-trip is proven.
 */

import { Send, Sparkles } from "lucide-react";
import { useCallback, useState, type FormEvent } from "react";

import { readSessionToken } from "@/lib/cp-auth-exchange";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface TurnReply {
  text: string;
  turnId: string;
}

interface AgentTestTurnProps {
  agentId: string;
  /** Optional pinned version. When omitted, dp resolves the agent's
   *  active version (404s cleanly if the agent is still draft). */
  version?: number;
}

// Route through the studio same-origin proxy; see the channels form
// for the same pattern.
function apiBaseUrl(): string {
  return "/api/cp";
}

export function AgentTestTurn({
  agentId,
  version,
}: AgentTestTurnProps): JSX.Element {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<
    | { kind: "idle" }
    | { kind: "sending" }
    | { kind: "reply"; reply: TurnReply }
    | { kind: "error"; message: string }
  >({ kind: "idle" });

  const send = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = input.trim();
      if (!trimmed) return;
      setStatus({ kind: "sending" });

      const session = readSessionToken();
      if (!session?.access_token) {
        setStatus({
          kind: "error",
          message: "You need to sign in before sending a test turn.",
        });
        return;
      }

      try {
        const response = await fetch(
          `${apiBaseUrl()}/v1/agents/${encodeURIComponent(
            agentId,
          )}/test-turn`,
          {
            method: "POST",
            headers: {
              "content-type": "application/json",
              authorization: `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              input: trimmed,
              ...(version !== undefined ? { version } : {}),
            }),
          },
        );
        const text = await response.text();
        if (!response.ok) {
          let message = `test-turn failed: HTTP ${response.status}`;
          try {
            const parsed = JSON.parse(text) as { detail?: unknown };
            if (typeof parsed.detail === "string") {
              message = parsed.detail;
            } else if (parsed.detail) {
              message = JSON.stringify(parsed.detail);
            }
          } catch {
            /* keep generic message */
          }
          setStatus({ kind: "error", message });
          return;
        }
        const payload = JSON.parse(text) as {
          turn_id: string;
          reply?: { text?: string };
        };
        setStatus({
          kind: "reply",
          reply: {
            turnId: payload.turn_id,
            text: payload.reply?.text ?? "",
          },
        });
      } catch (err) {
        setStatus({
          kind: "error",
          message:
            err instanceof Error
              ? err.message
              : "Network error sending test turn.",
        });
      }
    },
    [agentId, input, version],
  );

  return (
    <section
      className="instrument-panel rounded-2xl p-5"
      aria-label="Send a test turn to this agent"
      data-testid="agent-test-turn"
    >
      <div className="flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" aria-hidden />
        </span>
        <div>
          <p className="text-sm font-semibold">Test turn</p>
          <p className="text-xs text-muted-foreground">
            Send a prompt through the full runtime — cp resolves the
            spec, dp executes, you see the reply.
          </p>
        </div>
      </div>
      <form className="mt-4 flex flex-col gap-3" onSubmit={send}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          rows={3}
          placeholder="Hi, can you help me with a billing question?"
          className="w-full resize-none rounded-xl border border-border bg-background/70 p-3 text-sm leading-6 placeholder:text-muted-foreground/60 focus:border-primary/60 focus:outline-none focus:ring-2 focus:ring-focus/50"
          data-testid="agent-test-turn-input"
        />
        <div className="flex items-center justify-between gap-2">
          <p className="text-[0.7rem] text-muted-foreground">
            {version !== undefined
              ? `Pinned to v${version}`
              : "Using the active version."}
          </p>
          <button
            type="submit"
            disabled={status.kind === "sending" || !input.trim()}
            data-testid="agent-test-turn-send"
            className={cn(
              buttonVariants({ size: "sm" }),
              "shadow-[0_18px_42px_-18px_hsl(var(--primary)/0.6)]",
            )}
          >
            <Send className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            {status.kind === "sending" ? "Sending…" : "Send"}
          </button>
        </div>
      </form>

      {status.kind === "reply" ? (
        <div
          className="mt-4 rounded-xl border border-border/50 bg-muted/40 p-3"
          data-testid="agent-test-turn-reply"
        >
          <p className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Agent reply
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6">
            {status.reply.text || "(empty reply)"}
          </p>
          <p className="mt-2 font-mono text-[0.65rem] text-muted-foreground/70">
            turn {status.reply.turnId}
          </p>
        </div>
      ) : null}

      {status.kind === "error" ? (
        <div
          className="notice notice--warning mt-4"
          role="alert"
          data-testid="agent-test-turn-error"
        >
          <div className="notice__body">{status.message}</div>
        </div>
      ) : null}
    </section>
  );
}
