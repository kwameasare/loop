"use client";

import { useEffect, useState } from "react";

import {
  type AgentVersionDetail,
  type PromoteAgentVersionInput,
  type PromoteAgentVersionResult,
  priorVersion,
  promoteAgentVersion as defaultPromote,
} from "@/lib/agent-versions";
import { DiffViewerModal } from "./diff-viewer-modal";

export interface AgentVersionsListProps {
  /** All versions for this agent (used so the diff can find the prior one). */
  versions: AgentVersionDetail[];
  pageSize?: number;
  /** Override for tests. */
  promote?: (
    input: PromoteAgentVersionInput,
  ) => Promise<PromoteAgentVersionResult>;
  /** Override the confirm dialog (default: window.confirm). */
  confirmFn?: (message: string) => boolean;
}

const STATE_LABEL: Record<AgentVersionDetail["deploy_state"], string> = {
  inactive: "Inactive",
  canary: "Canary",
  active: "Active",
  rolled_back: "Rolled back",
};

type Toast = { kind: "success" | "error"; message: string } | null;

/**
 * Paginated list of agent versions. Each row supports two actions:
 *  - clicking the row opens the diff modal (config_json vs prior).
 *  - clicking "Promote" confirms and POSTs to cp-api /promote, then
 *    updates the row inline with the new ``promoted_to`` value and
 *    surfaces a toast.
 */
export function AgentVersionsList({
  versions,
  pageSize = 5,
  promote = defaultPromote,
  confirmFn,
}: AgentVersionsListProps) {
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<AgentVersionDetail | null>(null);
  const [rows, setRows] = useState(versions);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);

  useEffect(() => setRows(versions), [versions]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const start = page * pageSize;
  const slice = rows.slice(start, start + pageSize);
  const prior = selected ? priorVersion(rows, selected) : null;
  const confirm = confirmFn ?? ((m: string) => window.confirm(m));

  async function handlePromote(v: AgentVersionDetail) {
    if (!confirm(`Promote v${v.version} to production?`)) return;
    setPendingId(v.id);
    try {
      const result = await promote({
        agentId: v.agent_id,
        versionId: v.id,
        stage: "production",
      });
      setRows((prev) =>
        prev.map((r) =>
          r.id === v.id ? { ...r, promoted_to: result.promoted_to } : r,
        ),
      );
      setToast({
        kind: "success",
        message: `v${v.version} promoted to ${result.promoted_to}.`,
      });
    } catch (err) {
      setToast({
        kind: "error",
        message:
          err instanceof Error
            ? `Promote failed: ${err.message}`
            : "Promote failed.",
      });
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-3" data-testid="agent-versions">
      {rows.length === 0 ? (
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
            <li
              key={v.id}
              className="flex items-center justify-between gap-4 p-4"
            >
              <button
                type="button"
                onClick={() => setSelected(v)}
                data-testid={`agent-version-row-${v.version}`}
                className="flex flex-1 items-center justify-between gap-4 text-left"
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
              <div className="flex items-center gap-3">
                <span
                  data-testid={`agent-version-promoted-${v.version}`}
                  className="text-xs text-muted-foreground"
                >
                  {v.promoted_to ? `→ ${v.promoted_to}` : "—"}
                </span>
                <button
                  type="button"
                  onClick={() => handlePromote(v)}
                  disabled={pendingId === v.id}
                  data-testid={`agent-version-promote-${v.version}`}
                  className="rounded-md border px-2 py-1 text-xs font-medium disabled:opacity-50"
                >
                  {pendingId === v.id ? "Promoting…" : "Promote"}
                </button>
              </div>
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
      {toast ? (
        <div
          role="status"
          aria-live="polite"
          data-testid={`promote-toast-${toast.kind}`}
          className={
            "fixed bottom-4 right-4 z-50 rounded-md px-3 py-2 text-sm shadow " +
            (toast.kind === "success"
              ? "bg-green-600 text-white"
              : "bg-red-600 text-white")
          }
        >
          {toast.message}
        </div>
      ) : null}
    </div>
  );
}
