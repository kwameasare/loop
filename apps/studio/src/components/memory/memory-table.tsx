"use client";

import { useState } from "react";

/** A single memory entry as returned by the control-plane API. */
export interface MemoryEntry {
  id: string;
  agent_id: string;
  user_id: string;
  /** Redacted content — raw value replaced with "[REDACTED]" for display */
  content: string;
  created_at: string;
  /** Size in bytes of the raw stored value */
  size_bytes: number;
}

interface MemoryTableProps {
  entries: MemoryEntry[];
  onDelete: (id: string) => void;
  isDeleting?: string | null;
}

/**
 * Pure presentational table for a list of memory entries.
 * Shows redacted content, size, agent/user attribution, and a
 * per-row GDPR Art-17 delete action.
 */
export function MemoryTable({ entries, onDelete, isDeleting = null }: MemoryTableProps) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="memory-empty">
        No memory entries found.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border" data-testid="memory-table">
      <table className="min-w-full text-sm">
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th className="px-4 py-2 text-left font-medium">ID</th>
            <th className="px-4 py-2 text-left font-medium">Agent</th>
            <th className="px-4 py-2 text-left font-medium">User</th>
            <th className="px-4 py-2 text-left font-medium">Content</th>
            <th className="px-4 py-2 text-right font-medium">Size</th>
            <th className="px-4 py-2 text-left font-medium">Created</th>
            <th className="px-4 py-2 text-right font-medium">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map((entry) => (
            <tr key={entry.id} data-testid="memory-row">
              <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                {entry.id.slice(0, 8)}…
              </td>
              <td className="px-4 py-2 font-mono text-xs">{entry.agent_id}</td>
              <td className="px-4 py-2 font-mono text-xs">{entry.user_id}</td>
              <td className="px-4 py-2 max-w-xs truncate text-muted-foreground italic">
                {entry.content}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">
                {formatBytes(entry.size_bytes)}
              </td>
              <td className="px-4 py-2 text-xs text-muted-foreground whitespace-nowrap">
                {new Date(entry.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-2 text-right">
                <button
                  aria-label={`Delete memory entry ${entry.id}`}
                  disabled={isDeleting === entry.id}
                  onClick={() => onDelete(entry.id)}
                  className="rounded px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
                  data-testid="memory-delete-btn"
                >
                  {isDeleting === entry.id ? "Deleting…" : "Delete"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
