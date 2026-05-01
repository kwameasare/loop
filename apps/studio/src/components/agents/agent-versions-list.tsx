"use client";

import { useState } from "react";

import { type AgentVersionDetail, priorVersion } from "@/lib/agent-versions";
import { DiffViewerModal } from "./diff-viewer-modal";

export interface AgentVersionsListProps {
  /** All versions for this agent (used so the diff can find the prior one). */
  versions: AgentVersionDetail[];
  pageSize?: number;
}

const STATE_LABEL: Record<AgentVersionDetail["deploy_state"], string> = {
  inactive: "Inactive",
  canary: "Canary",
  active: "Active",
  rolled_back: "Rolled back",
};

/**
 * Paginated list of agent versions; clicking a row opens a diff modal
 * showing ``config_json`` against the previous version (by version
 * number). Pagination is local — the parent component fetches all
 * versions once; cp-api pagination kicks in as a follow-up when the
 * GET endpoint lands.
 */
export function AgentVersionsList({
  versions,
  pageSize = 5,
}: AgentVersionsListProps) {
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<AgentVersionDetail | null>(null);
  const totalPages = Math.max(1, Math.ceil(versions.length / pageSize));
  const start = page * pageSize;
  const slice = versions.slice(start, start + pageSize);
  const prior = selected ? priorVersion(versions, selected) : null;

  return (
    <div className="flex flex-col gap-3" data-testid="agent-versions">
      {versions.length === 0 ? (
        <p
          className="text-sm text-muted-foreground"
          data-testid="agent-versions-empty"
        >
          No versions deployed yet. Run <code>loop deploy</code> to create one.
        </p>
      ) : (
        <ul
          className="divide-y divide-border rounded-lg border"
          data-testid="agent-versions-list"
        >
          {slice.map((v) => (
            <li key={v.id}>
              <button
                type="button"
                onClick={() => setSelected(v)}
                data-testid={`agent-version-row-${v.version}`}
                className="flex w-full items-center justify-between gap-4 p-4 text-left hover:bg-accent"
              >
                <div className="flex flex-col">
                  <span className="text-sm font-medium">v{v.version}</span>
                  <span className="text-xs text-muted-foreground">
                    {v.deployed_at
                      ? new Date(v.deployed_at).toLocaleString()
                      : "Not deployed"}
                  </span>
                </div>
                <span
                  data-testid={`agent-version-state-${v.version}`}
                  className={
                    "rounded-full px-2 py-0.5 text-xs font-medium " +
                    (v.deploy_state === "active"
                      ? "bg-green-100 text-green-800"
                      : "bg-muted text-muted-foreground")
                  }
                >
                  {STATE_LABEL[v.deploy_state]}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {totalPages > 1 ? (
        <nav
          className="flex items-center justify-between text-sm"
          data-testid="agent-versions-pager"
        >
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            data-testid="agent-versions-prev"
            className="rounded-md border px-2 py-1 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-muted-foreground">
            Page {page + 1} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            data-testid="agent-versions-next"
            className="rounded-md border px-2 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </nav>
      ) : null}
      {selected ? (
        <DiffViewerModal
          version={selected}
          prior={prior}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </div>
  );
}
