"use client";

import { useRef, useState } from "react";

import {
  type EmulatorTransport,
  extractTokenText,
} from "@/lib/emulator-transport";
import type { TurnEvent } from "@/lib/sdk-types";

export interface EmulatorMessage {
  role: "user" | "assistant";
  text: string;
  /** True while assistant tokens are still streaming in. */
  streaming?: boolean;
  /** Set when the turn ended in an error. */
  error?: string;
}

export interface FlowEmulatorPanelProps {
  agentId: string;
  transport: EmulatorTransport;
  /**
   * Optional callback that receives every {@link TurnEvent} as it arrives;
   * the flow editor wires this up to record variable inspector frames.
   */
  onTurnEvent?: (event: TurnEvent) => void;
}

export function FlowEmulatorPanel(props: FlowEmulatorPanelProps) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<EmulatorMessage[]>([]);
  const [running, setRunning] = useState(false);
  const cancelRef = useRef<{ cancel: () => void } | null>(null);

  async function play() {
    const text = draft.trim();
    if (!text || running) return;
    setDraft("");
    setRunning(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", text },
      { role: "assistant", text: "", streaming: true },
    ]);

    const stream = props.transport.start({ agentId: props.agentId, text });
    const iterator = stream[Symbol.asyncIterator]();
    let cancelled = false;
    cancelRef.current = {
      cancel() {
        cancelled = true;
        void iterator.return?.();
      },
    };

    try {
      while (true) {
        const result = await iterator.next();
        if (cancelled) break;
        if (result.done) break;
        const evt = result.value as TurnEvent;
        props.onTurnEvent?.(evt);
        if (evt.type === "token") {
          const chunk = extractTokenText(evt);
          if (chunk) {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.role === "assistant") {
                next[next.length - 1] = {
                  ...last,
                  text: last.text + chunk,
                };
              }
              return next;
            });
          }
        } else if (evt.type === "complete") {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = { ...last, streaming: false };
            }
            return next;
          });
          break;
        } else if (evt.type === "degrade") {
          const reason =
            (evt.payload as { reason?: string }).reason ?? "degraded";
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = {
                ...last,
                streaming: false,
                error: reason,
              };
            }
            return next;
          });
          break;
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "stream failed";
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === "assistant") {
          next[next.length - 1] = {
            ...last,
            streaming: false,
            error: message,
          };
        }
        return next;
      });
    } finally {
      setRunning(false);
      cancelRef.current = null;
    }
  }

  function stop() {
    cancelRef.current?.cancel();
  }

  return (
    <section
      aria-label="Flow emulator"
      className="flex w-96 flex-col border-l bg-white"
      data-testid="flow-emulator"
    >
      <header className="flex items-center justify-between border-b px-4 py-2">
        <h2 className="text-sm font-semibold">Emulator</h2>
        <span
          className={`rounded px-2 py-0.5 text-xs ${running ? "bg-emerald-100 text-emerald-700" : "bg-zinc-100 text-zinc-600"}`}
          data-testid="emulator-status"
        >
          {running ? "streaming" : "idle"}
        </span>
      </header>
      <ol
        className="flex flex-1 flex-col gap-2 overflow-auto p-4"
        data-testid="emulator-messages"
      >
        {messages.length === 0 ? (
          <li
            className="rounded border border-dashed border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-500"
            data-testid="emulator-empty"
          >
            Send a message to start a turn.
          </li>
        ) : null}
        {messages.map((m, idx) => (
          <li
            className={`rounded border px-3 py-2 text-sm ${m.role === "user" ? "bg-blue-50" : "bg-white"}`}
            data-testid={`emulator-msg-${idx}`}
            data-role={m.role}
            key={idx}
          >
            <p className="text-xs uppercase text-zinc-500">{m.role}</p>
            <p className="whitespace-pre-wrap" data-testid={`emulator-text-${idx}`}>
              {m.text}
              {m.streaming ? (
                <span className="ml-1 animate-pulse text-zinc-400">▍</span>
              ) : null}
            </p>
            {m.error ? (
              <p
                className="mt-1 text-xs text-red-600"
                data-testid={`emulator-error-${idx}`}
                role="alert"
              >
                {m.error}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
      <footer className="flex items-center gap-2 border-t p-3">
        <input
          aria-label="Emulator message"
          className="flex-1 rounded border px-2 py-1 text-sm"
          data-testid="emulator-input"
          disabled={running}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void play();
            }
          }}
          placeholder="Send a turn"
          type="text"
          value={draft}
        />
        {running ? (
          <button
            className="rounded border border-rose-300 bg-rose-50 px-3 py-1 text-sm text-rose-800 hover:bg-rose-100"
            data-testid="emulator-stop"
            onClick={stop}
            type="button"
          >
            Stop
          </button>
        ) : (
          <button
            className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-zinc-300"
            data-testid="emulator-play"
            disabled={!draft.trim()}
            onClick={() => void play()}
            type="button"
          >
            Play
          </button>
        )}
      </footer>
    </section>
  );
}
