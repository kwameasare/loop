"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  formatRelativeMs,
  listInboxQueue,
  type InboxChannel,
  type InboxItem,
  type InboxSortKey,
  type InboxStatus,
} from "@/lib/inbox";

export interface InboxQueueProps {
  items: InboxItem[];
  workspace_id: string;
  now_ms: number;
  teams: { id: string; name: string }[];
  agents: { id: string; name: string }[];
  initialPageSize?: number;
}

const CHANNELS: (InboxChannel | "all")[] = [
  "all",
  "web",
  "voice",
  "sms",
  "whatsapp",
  "slack",
];

const STATUSES: (InboxStatus | "all")[] = ["all", "pending", "claimed", "resolved"];

const SORTABLE: { key: InboxSortKey; label: string }[] = [
  { key: "created_at", label: "Created" },
  { key: "user_id", label: "User" },
  { key: "channel", label: "Channel" },
  { key: "status", label: "Status" },
];

/**
 * Cross-team inbox queue: filter by team / agent / channel / status,
 * sort by any column, paginate, and click into the detail page (the
 * existing operator workbench under /inbox).
 */
export function InboxQueue(props: InboxQueueProps) {
  const [teamId, setTeamId] = useState("");
  const [agentId, setAgentId] = useState("");
  const [channel, setChannel] = useState<InboxChannel | "all">("all");
  const [status, setStatus] = useState<InboxStatus | "all">("all");
  const [sortBy, setSortBy] = useState<InboxSortKey>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const pageSize = props.initialPageSize ?? 15;

  const result = useMemo(
    () =>
      listInboxQueue(props.items, {
        workspace_id: props.workspace_id,
        team_id: teamId || undefined,
        agent_id: agentId || undefined,
        channel,
        status,
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        page_size: pageSize,
      }),
    [
      props.items,
      props.workspace_id,
      teamId,
      agentId,
      channel,
      status,
      sortBy,
      sortDir,
      page,
      pageSize,
    ],
  );

  const agentName = useMemo(
    () => new Map(props.agents.map((a) => [a.id, a.name])),
    [props.agents],
  );
  const teamName = useMemo(
    () => new Map(props.teams.map((t) => [t.id, t.name])),
    [props.teams],
  );

  function toggleSort(key: InboxSortKey) {
    if (sortBy === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
    setPage(1);
  }

  return (
    <section className="flex flex-col gap-3" data-testid="inbox-queue">
      <header className="flex flex-wrap items-center gap-2 text-sm">
        <select
          aria-label="Filter by team"
          className="rounded border px-2 py-1"
          data-testid="queue-filter-team"
          onChange={(e) => {
            setTeamId(e.target.value);
            setPage(1);
          }}
          value={teamId}
        >
          <option value="">All teams</option>
          {props.teams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by agent"
          className="rounded border px-2 py-1"
          data-testid="queue-filter-agent"
          onChange={(e) => {
            setAgentId(e.target.value);
            setPage(1);
          }}
          value={agentId}
        >
          <option value="">All agents</option>
          {props.agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by channel"
          className="rounded border px-2 py-1"
          data-testid="queue-filter-channel"
          onChange={(e) => {
            setChannel(e.target.value as InboxChannel | "all");
            setPage(1);
          }}
          value={channel}
        >
          {CHANNELS.map((c) => (
            <option key={c} value={c}>
              {c === "all" ? "All channels" : c}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by status"
          className="rounded border px-2 py-1"
          data-testid="queue-filter-status"
          onChange={(e) => {
            setStatus(e.target.value as InboxStatus | "all");
            setPage(1);
          }}
          value={status}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === "all" ? "All statuses" : s}
            </option>
          ))}
        </select>
        <span
          className="text-muted-foreground ml-auto text-xs"
          data-testid="queue-count"
        >
          {result.total} item{result.total === 1 ? "" : "s"}
        </span>
      </header>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm" data-testid="queue-table">
          <thead className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
            <tr>
              {SORTABLE.map((col) => {
                const isActive = sortBy === col.key;
                const arrow = isActive ? (sortDir === "asc" ? "▲" : "▼") : "";
                return (
                  <th className="px-3 py-2" key={col.key}>
                    <button
                      className="flex items-center gap-1 text-xs font-semibold uppercase text-zinc-500 hover:text-zinc-900"
                      data-testid={`queue-sort-${col.key}`}
                      onClick={() => toggleSort(col.key)}
                      type="button"
                    >
                      {col.label} {arrow}
                    </button>
                  </th>
                );
              })}
              <th className="px-3 py-2">Team</th>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Last message</th>
            </tr>
          </thead>
          <tbody>
            {result.items.length === 0 ? (
              <tr data-testid="queue-empty">
                <td className="px-3 py-6 text-center text-zinc-500" colSpan={7}>
                  No items match the current filters.
                </td>
              </tr>
            ) : (
              result.items.map((item) => (
                <tr
                  className="border-t hover:bg-zinc-50"
                  data-testid={`queue-row-${item.id}`}
                  key={item.id}
                >
                  <td className="px-3 py-2 whitespace-nowrap">
                    {formatRelativeMs(props.now_ms, item.created_at_ms)}
                  </td>
                  <td className="px-3 py-2 font-medium">
                    <Link
                      className="text-blue-600 hover:underline"
                      data-testid={`queue-link-${item.id}`}
                      href="/inbox"
                    >
                      {item.user_id}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{item.channel}</td>
                  <td className="px-3 py-2">
                    <span
                      className={
                        item.status === "pending"
                          ? "rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700"
                          : item.status === "claimed"
                            ? "rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700"
                            : "rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700"
                      }
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {teamName.get(item.team_id) ?? item.team_id}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {agentName.get(item.agent_id) ?? item.agent_id}
                  </td>
                  <td
                    className="px-3 py-2 text-xs text-zinc-600"
                    data-testid={`queue-preview-${item.id}`}
                  >
                    <span className="line-clamp-1">
                      {item.last_message_excerpt}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between text-xs">
        <span data-testid="queue-page-indicator">
          Page {result.page} of {result.page_count}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded border px-2 py-1 disabled:opacity-50"
            data-testid="queue-prev"
            disabled={result.page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            type="button"
          >
            Prev
          </button>
          <button
            className="rounded border px-2 py-1 disabled:opacity-50"
            data-testid="queue-next"
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
