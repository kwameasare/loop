"use client";

import { useState } from "react";
import { formatDurationNs, type Span } from "@/lib/traces";

type Tab = "attributes" | "events" | "raw";

const TABS: { id: Tab; label: string }[] = [
  { id: "attributes", label: "Attributes" },
  { id: "events", label: "Events" },
  { id: "raw", label: "Raw" },
];

export function SpanDetail({ span }: { span: Span }) {
  const [tab, setTab] = useState<Tab>("attributes");

  return (
    <section
      className="rounded-lg border bg-white p-4"
      data-testid="span-detail"
      aria-label="span detail"
    >
      <header className="mb-3">
        <h2 className="text-base font-medium">{span.name}</h2>
        <p className="text-muted-foreground text-xs">
          {span.service} · {span.kind} · {formatDurationNs(span.end_ns - span.start_ns)} ·{" "}
          <span
            className={
              span.status === "error" ? "text-red-600" : "text-emerald-700"
            }
          >
            {span.status}
          </span>
        </p>
      </header>
      <div role="tablist" className="mb-3 flex gap-1 border-b">
        {TABS.map((t) => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              role="tab"
              type="button"
              aria-selected={isActive}
              data-testid={`span-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 text-sm transition-colors ${
                isActive
                  ? "border-b-2 border-zinc-900 font-medium"
                  : "text-muted-foreground hover:text-zinc-900"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" data-testid={`span-panel-${tab}`}>
        {tab === "attributes" && (
          <dl className="grid grid-cols-1 gap-2 text-sm">
            {Object.entries(span.attributes).length === 0 ? (
              <p className="text-muted-foreground">No attributes.</p>
            ) : (
              Object.entries(span.attributes).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3">
                  <dt className="text-muted-foreground font-mono text-xs">{k}</dt>
                  <dd className="font-mono text-xs">{String(v)}</dd>
                </div>
              ))
            )}
          </dl>
        )}
        {tab === "events" && (
          <ul className="space-y-2 text-sm">
            {span.events.length === 0 ? (
              <p className="text-muted-foreground">No events.</p>
            ) : (
              span.events.map((e, i) => (
                <li key={`${e.name}-${i}`} className="rounded border p-2">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium">{e.name}</span>
                    <span className="text-muted-foreground">
                      {formatDurationNs(e.timestamp_ns - span.start_ns)} in
                    </span>
                  </div>
                </li>
              ))
            )}
          </ul>
        )}
        {tab === "raw" && (
          <pre className="bg-muted overflow-auto rounded p-2 text-xs">
            {JSON.stringify(span, null, 2)}
          </pre>
        )}
      </div>
    </section>
  );
}
