"use client";

/**
 * S494 – KbRefreshPanel
 * Shows refresh status for a single KB document and lets the user:
 *   1. Change the scheduled cadence (manual / hourly / daily / weekly).
 *   2. Trigger an immediate on-demand refresh.
 */

import * as React from "react";
import {
  type DocRefreshStatus,
  type KbHelperOptions,
  type RefreshCadence,
  REFRESH_CADENCE_LABELS,
  getDocRefreshStatus,
  setDocRefreshCadence,
  triggerDocRefresh,
} from "@/lib/kb";

interface KbRefreshPanelProps {
  agentId: string;
  documentId: string;
  opts?: KbHelperOptions;
}

export function KbRefreshPanel({ agentId, documentId, opts = {} }: KbRefreshPanelProps) {
  const [refreshStatus, setRefreshStatus] = React.useState<DocRefreshStatus | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDocRefreshStatus(agentId, documentId, opts)
      .then((s) => { if (!cancelled) { setRefreshStatus(s); setLoading(false); } })
      .catch((e: unknown) => { if (!cancelled) { setError(String(e)); setLoading(false); } });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, documentId]);

  async function handleCadenceChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const cadence = e.target.value as RefreshCadence;
    try {
      const s = await setDocRefreshCadence(agentId, documentId, cadence, opts);
      setRefreshStatus(s);
    } catch (err: unknown) {
      setError(String(err));
    }
  }

  async function handleTrigger() {
    setError(null);
    try {
      const s = await triggerDocRefresh(agentId, documentId, opts);
      setRefreshStatus(s);
    } catch (err: unknown) {
      setError(String(err));
    }
  }

  if (loading) {
    return (
      <div data-testid="kb-refresh-loading" className="text-sm text-gray-500">
        Loading refresh status…
      </div>
    );
  }

  return (
    <div data-testid="kb-refresh-panel" className="rounded border p-3 space-y-2 text-sm">
      {/* Status row */}
      <div className="flex items-center gap-2">
        <span className="font-medium">Refresh status:</span>
        <span data-testid="kb-refresh-status-badge" className="capitalize">
          {refreshStatus?.status ?? "—"}
        </span>
      </div>

      {/* Run counts */}
      <div className="text-gray-500">
        <span>Runs: </span>
        <span data-testid="kb-refresh-run-count">{refreshStatus?.runCount ?? 0}</span>
        {refreshStatus?.lastRunAt && (
          <>
            <span className="ml-2">Last: </span>
            <span data-testid="kb-refresh-last-run">
              {new Date(refreshStatus.lastRunAt).toLocaleString()}
            </span>
          </>
        )}
        {refreshStatus?.nextRunAt && (
          <>
            <span className="ml-2">Next: </span>
            <span data-testid="kb-refresh-next-run">
              {new Date(refreshStatus.nextRunAt).toLocaleString()}
            </span>
          </>
        )}
      </div>

      {/* Error message */}
      {refreshStatus?.error && (
        <div data-testid="kb-refresh-error-msg" className="text-red-600">
          {refreshStatus.error}
        </div>
      )}

      {/* Cadence selector */}
      <div className="flex items-center gap-2">
        <label htmlFor="kb-refresh-cadence" className="font-medium">
          Schedule:
        </label>
        <select
          id="kb-refresh-cadence"
          data-testid="kb-refresh-cadence-select"
          value={refreshStatus?.cadence ?? "manual"}
          onChange={handleCadenceChange}
          className="border rounded px-1 py-0.5"
        >
          {(Object.entries(REFRESH_CADENCE_LABELS) as [RefreshCadence, string][]).map(
            ([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ),
          )}
        </select>
      </div>

      {/* On-demand trigger */}
      <button
        data-testid="kb-refresh-trigger-btn"
        onClick={handleTrigger}
        className="rounded bg-blue-600 px-3 py-1 text-white hover:bg-blue-700 disabled:opacity-50"
        disabled={refreshStatus?.status === "running"}
      >
        Refresh now
      </button>

      {/* API error */}
      {error && (
        <div data-testid="kb-refresh-api-error" className="text-red-600 text-xs">
          {error}
        </div>
      )}
    </div>
  );
}
