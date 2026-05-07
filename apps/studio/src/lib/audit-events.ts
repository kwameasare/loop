import type {
  AuditEventRow,
  AuditLogFilters,
} from "@/components/workspaces/audit-log-page";
import { createAuthedCpApiFetch } from "@/lib/cp-api-fetch";

interface CpAuditEvent {
  id: string;
  occurred_at: string;
  workspace_id: string;
  actor_sub: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  request_id?: string | null;
  payload_hash?: string | null;
  outcome: "success" | "denied" | "error";
}

export interface ListAuditEventsOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
  limit?: number;
}

export interface ListAuditEventsResult {
  events: AuditEventRow[];
  total: number;
}

function cpApiBaseUrl(override?: string): string | null {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function toAuditRow(event: CpAuditEvent): AuditEventRow {
  return {
    id: event.id,
    occurredAt: event.occurred_at,
    actorSub: event.actor_sub,
    action: event.action,
    resourceType: event.resource_type,
    resourceId: event.resource_id,
    ip: null,
    outcome: event.outcome,
  };
}

export function filterAuditRows(
  events: readonly AuditEventRow[],
  filters: AuditLogFilters,
): AuditEventRow[] {
  const from = filters.timeFrom ? Date.parse(filters.timeFrom) : null;
  const to = filters.timeTo ? Date.parse(filters.timeTo) : null;
  return events.filter((event) => {
    if (filters.actor && !event.actorSub.includes(filters.actor)) return false;
    if (filters.action && !event.action.includes(filters.action)) return false;
    if (
      filters.resource &&
      !`${event.resourceType} ${event.resourceId ?? ""}`.includes(filters.resource)
    ) {
      return false;
    }
    if (filters.ip && !(event.ip ?? "").includes(filters.ip)) return false;
    if (filters.outcome !== "any" && event.outcome !== filters.outcome) {
      return false;
    }
    const occurred = Date.parse(event.occurredAt);
    if (from !== null && occurred < from) return false;
    if (to !== null && occurred > to) return false;
    return true;
  });
}

export async function listAuditEvents(
  workspaceId: string,
  opts: ListAuditEventsOptions = {},
): Promise<ListAuditEventsResult> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) return { events: [], total: 0 };
  const inner = opts.fetcher ?? fetch;
  const fetcher = createAuthedCpApiFetch({
    fetcher: inner,
    refreshBaseUrl: base.replace(/\/v1$/, ""),
  });
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const params = new URLSearchParams({
    workspace_id: workspaceId,
    limit: String(opts.limit ?? 500),
  });
  const response = await fetcher(`${base}/audit/events?${params}`, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`cp-api GET audit events -> ${response.status}`);
  }
  const body = (await response.json()) as {
    items?: CpAuditEvent[];
    total?: number;
  };
  return {
    events: (body.items ?? []).map(toAuditRow).reverse(),
    total: body.total ?? body.items?.length ?? 0,
  };
}
