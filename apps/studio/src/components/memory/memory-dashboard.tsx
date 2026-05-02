"use client";

import type { MemoryEntry } from "./memory-table";
import { MemoryTable } from "./memory-table";

interface MemoryDashboardProps {
  /** All entries for this agent, redacted by the server */
  entries: MemoryEntry[];
  /** The agent whose memory is being displayed */
  agentId: string;
  onDelete: (id: string) => void;
  isDeleting?: string | null;
}

/**
 * Memory dashboard panel for a single agent.
 *
 * Displays total entry count, total size, and a sortable list of entries.
 * Each entry has a GDPR Art-17 "right to erasure" delete button.
 */
export function MemoryDashboard({
  entries,
  agentId,
  onDelete,
  isDeleting = null,
}: MemoryDashboardProps) {
  const totalBytes = entries.reduce((acc, e) => acc + e.size_bytes, 0);
  const uniqueUsers = new Set(entries.map((e) => e.user_id)).size;

  return (
    <section aria-labelledby="memory-dashboard-title" data-testid="memory-dashboard">
      <div className="mb-4 flex items-center justify-between">
        <h2
          id="memory-dashboard-title"
          className="text-lg font-semibold"
          data-testid="memory-dashboard-heading"
        >
          Memory — {agentId}
        </h2>
        <span className="text-xs text-muted-foreground">
          GDPR Art-17: users may request erasure via the Delete button
        </span>
      </div>

      {/* KPI bar */}
      <div
        className="mb-6 grid grid-cols-3 gap-4 rounded-lg border border-border p-4 text-center"
        data-testid="memory-kpi-bar"
      >
        <div>
          <p className="text-2xl font-bold tabular-nums" data-testid="memory-kpi-entries">
            {entries.length}
          </p>
          <p className="text-xs text-muted-foreground mt-1">Entries</p>
        </div>
        <div>
          <p className="text-2xl font-bold tabular-nums" data-testid="memory-kpi-users">
            {uniqueUsers}
          </p>
          <p className="text-xs text-muted-foreground mt-1">Users</p>
        </div>
        <div>
          <p className="text-2xl font-bold tabular-nums" data-testid="memory-kpi-size">
            {formatBytes(totalBytes)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">Total size</p>
        </div>
      </div>

      <MemoryTable entries={entries} onDelete={onDelete} isDeleting={isDeleting} />
    </section>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
