"use client";

import { useState } from "react";

import type { EvidenceContext } from "@/lib/inbox-resolution";

type Pane = "trace" | "memory" | "tools" | "retrieval";

const PANES: readonly { id: Pane; label: string }[] = [
  { id: "trace", label: "Trace" },
  { id: "memory", label: "Memory" },
  { id: "tools", label: "Tools" },
  { id: "retrieval", label: "Retrieval" },
];

const STATUS_COLOR: Record<"ok" | "warn" | "error", string> = {
  ok: "border-success/30 bg-success/10 text-success",
  warn: "border-warning/30 bg-warning/10 text-warning",
  error: "border-destructive/30 bg-destructive/10 text-destructive",
};

export interface ConversationEvidenceProps {
  ctx: EvidenceContext;
  initialPane?: Pane;
}

/**
 * Trace / memory / tools / retrieval evidence panel. Backs §21.2
 * "Operator sees: ... trace, memory, tools used, retrieved chunks".
 */
export function ConversationEvidence({
  ctx,
  initialPane = "trace",
}: ConversationEvidenceProps) {
  const [pane, setPane] = useState<Pane>(initialPane);

  return (
    <section
      className="rounded-lg border bg-card"
      data-testid="conversation-evidence"
      aria-label="Conversation evidence"
    >
      <div
        className="flex gap-1 border-b bg-muted p-1 text-xs"
        role="tablist"
        data-testid="conversation-evidence-tablist"
      >
        {PANES.map((p) => {
          const active = pane === p.id;
          return (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={active}
              data-testid={`conversation-evidence-tab-${p.id}`}
              onClick={() => setPane(p.id)}
              className={
                active
                  ? "rounded bg-background px-3 py-1.5 font-medium shadow-sm"
                  : "rounded px-3 py-1.5 text-muted-foreground hover:bg-background"
              }
            >
              {p.label}
            </button>
          );
        })}
      </div>

      <div
        className="p-3"
        data-testid={`conversation-evidence-pane-${pane}`}
        role="tabpanel"
      >
        {pane === "trace" && (
          <ol className="space-y-2">
            {ctx.trace.map((s) => (
              <li
                key={s.id}
                data-testid={`evidence-trace-${s.id}`}
                className="flex items-start justify-between gap-3 rounded border bg-background px-3 py-2 text-sm"
              >
                <span className="flex-1">
                  <span className="font-medium">{s.step}</span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {s.detail}
                  </span>
                </span>
                <span
                  className={`rounded border px-2 py-0.5 text-[11px] ${STATUS_COLOR[s.status]}`}
                >
                  {s.status}
                </span>
              </li>
            ))}
          </ol>
        )}

        {pane === "memory" && (
          <ul className="space-y-2">
            {ctx.memory.map((m) => (
              <li
                key={m.id}
                data-testid={`evidence-memory-${m.id}`}
                className="rounded border bg-background px-3 py-2 text-sm"
              >
                <span className="mr-2 rounded bg-muted px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
                  {m.scope}
                </span>
                <span className="font-mono text-xs">{m.key}</span>
                <span className="mx-2 text-muted-foreground">→</span>
                <span className="font-mono text-xs">{m.value}</span>
              </li>
            ))}
          </ul>
        )}

        {pane === "tools" && (
          <ul className="space-y-2">
            {ctx.tools.map((t) => (
              <li
                key={t.id}
                data-testid={`evidence-tool-${t.id}`}
                className="flex items-start justify-between gap-3 rounded border bg-background px-3 py-2 text-sm"
              >
                <span className="flex-1">
                  <span className="font-medium">{t.name}</span>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {t.detail}
                  </p>
                </span>
                <span
                  className={`rounded border px-2 py-0.5 text-[11px] ${STATUS_COLOR[t.status]}`}
                >
                  {t.status}
                </span>
              </li>
            ))}
          </ul>
        )}

        {pane === "retrieval" && (
          <ul className="space-y-2">
            {ctx.retrieval.map((r) => (
              <li
                key={r.id}
                data-testid={`evidence-retrieval-${r.id}`}
                className="rounded border bg-background px-3 py-2 text-sm"
              >
                <header className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-mono">{r.source}</span>
                  <span className="tabular-nums">
                    score {r.score.toFixed(2)}
                  </span>
                </header>
                <p className="mt-1 text-sm">{r.excerpt}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
