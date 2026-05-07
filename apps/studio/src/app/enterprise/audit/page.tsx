"use client";

import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import {
  AuditLogPage,
  EMPTY_FILTERS,
  type AuditEventRow,
  type AuditLogFilters,
} from "@/components/workspaces/audit-log-page";
import { filterAuditRows, listAuditEvents } from "@/lib/audit-events";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

const PAGE_SIZE = 25;

export default function EnterpriseAuditPage(): JSX.Element {
  return (
    <RequireAuth>
      <EnterpriseAuditPageBody />
    </RequireAuth>
  );
}

function EnterpriseAuditPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [events, setEvents] = useState<AuditEventRow[]>([]);
  const [filters, setFilters] = useState<AuditLogFilters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setLoading(true);
    setError(undefined);
    void listAuditEvents(active.id)
      .then((result) => {
        if (cancelled) return;
        setEvents(result.events);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load audit log");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  const filtered = useMemo(
    () => filterAuditRows(events, filters),
    [events, filters],
  );
  const pageEvents = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function updateFilters(next: AuditLogFilters) {
    setFilters(next);
    setPage(1);
  }

  if (wsLoading || !active) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading audit log...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <header className="max-w-3xl">
        <p className="text-xs font-semibold uppercase text-muted-foreground">
          Govern / Audit Explorer
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">
          Workspace evidence trail
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Every write is append-only, searchable, and tied to the workspace so
          operators can prove who changed what without spelunking logs.
        </p>
      </header>
      <AuditLogPage
        events={pageEvents}
        filters={filters}
        onFiltersChange={updateFilters}
        page={page}
        pageSize={PAGE_SIZE}
        totalCount={filtered.length}
        onPageChange={setPage}
        loading={loading}
        {...(error ? { errorMessage: error } : {})}
      />
    </main>
  );
}
