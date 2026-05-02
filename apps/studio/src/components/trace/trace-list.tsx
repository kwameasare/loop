"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  formatDurationNs,
  formatTraceTimestamp,
  listTraces,
  type TraceSummary,
} from "@/lib/traces";

export interface TraceListProps {
  traces: TraceSummary[];
  initialPageSize?: number;
}

/**
 * Paginated trace list with free-text search and status/agent filters.
 * Filtering and pagination run client-side against the supplied
 * fixture set; when wired to the data plane the same component will
 * accept server-prepared rows page-by-page.
 */
export function TraceList(props: TraceListProps) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<"all" | "ok" | "error">("all");
  const [agentId, setAgentId] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = props.initialPageSize ?? 10;

  const agents = useMemo(() => {
    const seen = new Map<string, string>();
    for (const t of props.traces) seen.set(t.agent_id, t.agent_name);
    return [...seen.entries()]
      .map(([agent_id, agent_name]) => ({ agent_id, agent_name }))
      .sort((a, b) => a.agent_name.localeCompare(b.agent_name));
  }, [props.traces]);

  const result = useMemo(
    () =>
      listTraces(props.traces, {
        q,
        status,
        agent_id: agentId || undefined,
        page,
        page_size: pageSize,
      }),
    [props.traces, q, status, agentId, page, pageSize],
  );

  return (
    <section className="flex flex-col gap-3" data-testid="trace-list">
      <header className="flex flex-wrap items-center gap-2">
        <input
          aria-label="Search traces"
          className="rounded border px-2 py-1 text-sm"
          data-testid="trace-search"
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          placeholder="Search id, agent, or endpoint"
          value={q}
        />
        <select
          aria-label="Filter by status"
          className="rounded border px-2 py-1 text-sm"
          data-testid="trace-filter-status"
          onChange={(e) => {
            setStatus(e.target.value as "all" | "ok" | "error");
            setPage(1);
          }}
          value={status}
        >
          <option value="all">All statuses</option>
          <option value="ok">OK</option>
          <option value="error">Error</option>
        </select>
        <select
          aria-label="Filter by agent"
          className="rounded border px-2 py-1 text-sm"
          data-testid="trace-filter-agent"
          onChange={(e) => {
            setAgentId(e.target.value);
            setPage(1);
          }}
          value={agentId}
        >
          <option value="">All agents</option>
          {agents.map((a) => (
            <option key={a.agent_id} value={a.agent_id}>
              {a.agent_name}
            </option>
          ))}
        </select>
        <span className="text-muted-foreground text-xs" data-testid="trace-count">
          {result.total} trace{result.total === 1 ? "" : "s"}
        </span>
      </header>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm" data-testid="trace-table">
          <thead className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
            <tr>
              <th className="px-3 py-2">Trace</th>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Endpoint</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Duration</th>
              <th className="px-3 py-2">Started</th>
              <th className="px-3 py-2">Spans</th>
            </tr>
          </thead>
          <tbody>
            {result.traces.length === 0 ? (
              <tr data-testid="trace-empty">
                <td className="px-3 py-6 text-center text-zinc-500" colSpan={7}>
                  No traces match the current filters.
                </td>
              </tr>
            ) : (
              result.traces.map((t) => (
                <tr
                  className="border-t hover:bg-zinc-50"
                  data-testid={`trace-row-${t.id}`}
                  key={t.id}
                >
                  <td className="px-3 py-2 font-mono">
                    <Link
                      className="text-blue-600 hover:underline"
                      data-testid={`trace-link-${t.id}`}
                      href={`/traces/${t.id}`}
                    >
                      {t.id}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{t.agent_name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{t.root_name}</td>
                  <td
                    className="px-3 py-2"
                    data-testid={`trace-status-${t.id}`}
                  >
                    <span
                      className={
                        t.status === "error"
                          ? "rounded bg-red-100 px-2 py-0.5 text-xs text-red-700"
                          : "rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700"
                      }
                    >
                      {t.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">{formatDurationNs(t.duration_ns)}</td>
                  <td className="px-3 py-2">
                    {formatTraceTimestamp(t.started_at_ms)}
                  </td>
                  <td className="px-3 py-2">{t.span_count}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between text-xs">
        <span data-testid="trace-page-indicator">
          Page {result.page} of {result.page_count}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded border px-2 py-1 disabled:opacity-50"
            data-testid="trace-prev"
            disabled={result.page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            type="button"
          >
            Prev
          </button>
          <button
            className="rounded border px-2 py-1 disabled:opacity-50"
            data-testid="trace-next"
            disabled={result.page >= result.page_count}
            onClick={() => setPage((p) => p + 1)}
            type="button"
          >
            Next
          </button>
        </div>
      </footer>
    </section>
  );
}
