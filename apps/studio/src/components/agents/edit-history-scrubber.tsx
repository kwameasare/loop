"use client";

import { useEffect, useState } from "react";

import { cpJson } from "@/lib/ux-wireup";

interface EditHistoryItem {
  id: string;
  at: string;
  actor: string;
  label: string;
  object_state: string;
  content_hash: string;
  summary: string;
}

export function EditHistoryScrubber({ agentId }: { agentId: string }): JSX.Element {
  const [items, setItems] = useState<EditHistoryItem[]>([]);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void cpJson<{ items: EditHistoryItem[] }>(
      `/agents/${encodeURIComponent(agentId)}/edit-history`,
      {
        fallback: { items: [] },
      },
    ).then((next) => {
      if (!cancelled) setItems(next.items);
    });
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  if (items.length === 0) {
    return (
      <section className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
        No edit history has been recorded for this agent yet.
      </section>
    );
  }

  const current = items[Math.min(index, items.length - 1)]!;
  return (
    <section className="rounded-md border bg-card p-4" data-testid="edit-history-scrubber">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">Edit-history scrubber</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Drag across saved changes to inspect who changed what and which
            hash approvals should bind to.
          </p>
        </div>
        <span className="rounded-md border bg-background px-2 py-1 font-mono text-xs">
          {current.object_state}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={Math.max(0, items.length - 1)}
        step={1}
        value={index}
        onChange={(event) => setIndex(Number(event.target.value))}
        className="mt-4 w-full"
        aria-label="Agent edit history"
        data-testid="edit-history-range"
      />
      <article className="mt-3 rounded-md border bg-background p-3 text-sm">
        <p className="font-medium">{current.label}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {current.actor} · {current.at}
        </p>
        <p className="mt-2">{current.summary}</p>
        <p className="mt-2 break-all font-mono text-xs text-muted-foreground">
          {current.content_hash}
        </p>
      </article>
    </section>
  );
}
