"use client";

/**
 * S631 — Studio audit log page.
 *
 * Filterable, paginated view of the cp-api ``/v1/workspaces/:id/audit_events``
 * endpoint. Seven filters per the AC: actor, action, resource, time-from,
 * time-to, ip, outcome.
 *
 * The component is pure UI: the parent owns the cp-api fetcher and passes
 * in the current filter+page state and a list of events. Filter changes
 * call ``onFiltersChange`` (debounced upstream by the parent if desired);
 * pagination calls ``onPageChange``.
 */

import { useMemo, useState } from "react";

export type AuditOutcome = "any" | "success" | "denied" | "error";

export interface AuditEventRow {
  id: string;
  occurredAt: string; // ISO-8601
  actorSub: string;
  action: string;
  resourceType: string;
  resourceId: string | null;
  ip: string | null;
  outcome: "success" | "denied" | "error";
}

export interface AuditLogFilters {
  actor: string;
  action: string;
  resource: string;
  timeFrom: string; // ISO datetime-local string ("" = unset)
  timeTo: string;
  ip: string;
  outcome: AuditOutcome;
}

export const EMPTY_FILTERS: AuditLogFilters = {
  actor: "",
  action: "",
  resource: "",
  timeFrom: "",
  timeTo: "",
  ip: "",
  outcome: "any",
};

export interface AuditLogPageProps {
  events: readonly AuditEventRow[];
  filters: AuditLogFilters;
  onFiltersChange: (filters: AuditLogFilters) => void;
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  loading?: boolean;
  errorMessage?: string;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toISOString().replace("T", " ").replace(/\.\d{3}Z$/, "Z");
  } catch {
    return iso;
  }
}

export function AuditLogPage({
  events,
  filters,
  onFiltersChange,
  page,
  pageSize,
  totalCount,
  onPageChange,
  loading,
  errorMessage,
}: AuditLogPageProps) {
  const [localFilters, setLocalFilters] = useState<AuditLogFilters>(filters);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(totalCount / Math.max(1, pageSize))),
    [totalCount, pageSize],
  );

  function update<K extends keyof AuditLogFilters>(
    key: K,
    value: AuditLogFilters[K],
  ): void {
    const next = { ...localFilters, [key]: value };
    setLocalFilters(next);
  }

  function applyFilters(): void {
    onFiltersChange(localFilters);
  }

  function resetFilters(): void {
    setLocalFilters(EMPTY_FILTERS);
    onFiltersChange(EMPTY_FILTERS);
  }

  return (
    <section
      data-testid="audit-log-page"
      className="flex flex-col gap-4 rounded-md border p-4"
    >
      <header>
        <h1 className="text-lg font-semibold">Audit log</h1>
        <p className="text-xs text-muted-foreground">
          Append-only record of every workspace write. Filter by actor,
          action, resource, time window, IP, or outcome.
        </p>
      </header>

      <form
        data-testid="audit-log-filters"
        className="grid grid-cols-2 gap-2 sm:grid-cols-4"
        onSubmit={(e) => {
          e.preventDefault();
          applyFilters();
        }}
      >
        <label className="flex flex-col gap-1 text-xs">
          <span>Actor</span>
          <input
            data-testid="audit-filter-actor"
            value={localFilters.actor}
            onChange={(e) => update("actor", e.target.value)}
            placeholder="auth0|alice"
            className="rounded-md border bg-background px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span>Action</span>
          <input
            data-testid="audit-filter-action"
            value={localFilters.action}
            onChange={(e) => update("action", e.target.value)}
            placeholder="workspace.create"
            className="rounded-md border bg-background px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span>Resource</span>
          <input
            data-testid="audit-filter-resource"
            value={localFilters.resource}
            onChange={(e) => update("resource", e.target.value)}
            placeholder="workspace"
            className="rounded-md border bg-background px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span>IP address</span>
          <input
            data-testid="audit-filter-ip"
            value={localFilters.ip}
            onChange={(e) => update("ip", e.target.value)}
            placeholder="10.0.0.0/8"
            className="rounded-md border bg-background px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span>Time from</span>
          <input
            data-testid="audit-filter-time-from"
            type="datetime-local"
            value={localFilters.timeFrom}
            onChange={(e) => update("timeFrom", e.target.value)}
            className="rounded-md border bg-background px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span>Time to</span>
          <input
            data-testid="audit-filter-time-to"
            type="datetime-local"
            value={localFilters.timeTo}
            onChange={(e) => update("timeTo", e.target.value)}
            className="rounded-md border bg-background px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span>Outcome</span>
          <select
            data-testid="audit-filter-outcome"
            value={localFilters.outcome}
            onChange={(e) =>
              update("outcome", e.target.value as AuditOutcome)
            }
            className="rounded-md border bg-background px-2 py-1 text-sm"
          >
            <option value="any">Any</option>
            <option value="success">Success</option>
            <option value="denied">Denied</option>
            <option value="error">Error</option>
          </select>
        </label>
        <div className="flex items-end gap-2">
          <button
            type="submit"
            data-testid="audit-filters-apply"
            className="rounded-md border bg-primary px-3 py-1 text-sm text-primary-foreground"
          >
            Apply
          </button>
          <button
            type="button"
            data-testid="audit-filters-reset"
            onClick={resetFilters}
            className="rounded-md border px-3 py-1 text-sm"
          >
            Reset
          </button>
        </div>
      </form>

      {errorMessage && (
        <p
          data-testid="audit-log-error"
          className="text-sm text-red-600"
          role="alert"
        >
          {errorMessage}
        </p>
      )}

      <div className="overflow-x-auto">
        <table data-testid="audit-log-table" className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-muted-foreground">
              <th className="px-2 py-1">When</th>
              <th className="px-2 py-1">Actor</th>
              <th className="px-2 py-1">Action</th>
              <th className="px-2 py-1">Resource</th>
              <th className="px-2 py-1">IP</th>
              <th className="px-2 py-1">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr data-testid="audit-log-loading">
                <td colSpan={6} className="px-2 py-3 text-xs text-muted-foreground">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && events.length === 0 && (
              <tr data-testid="audit-log-empty">
                <td colSpan={6} className="px-2 py-3 text-xs text-muted-foreground">
                  No audit events match the current filters.
                </td>
              </tr>
            )}
            {!loading &&
              events.map((row) => (
                <tr key={row.id} data-testid={`audit-row-${row.id}`}>
                  <td className="px-2 py-1 font-mono text-xs">
                    {formatDate(row.occurredAt)}
                  </td>
                  <td className="px-2 py-1 font-mono text-xs">{row.actorSub}</td>
                  <td className="px-2 py-1">{row.action}</td>
                  <td className="px-2 py-1">
                    {row.resourceType}
                    {row.resourceId ? ` · ${row.resourceId}` : ""}
                  </td>
                  <td className="px-2 py-1 font-mono text-xs">
                    {row.ip ?? "—"}
                  </td>
                  <td
                    className="px-2 py-1 capitalize"
                    data-testid={`audit-row-outcome-${row.id}`}
                  >
                    {row.outcome}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <footer
        data-testid="audit-log-pagination"
        className="flex items-center justify-between text-xs"
      >
        <span>
          Page {page} / {totalPages} · {totalCount} events total
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            data-testid="audit-page-prev"
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="rounded-md border px-2 py-1 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            type="button"
            data-testid="audit-page-next"
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="rounded-md border px-2 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </footer>
    </section>
  );
}
