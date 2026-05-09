import type { AgentSummary } from "@/lib/cp-api";
import {
  cpApiBaseUrl,
  cpApiHeaders,
  type UxWireupClientOptions,
} from "@/lib/ux-wireup";

export type EstateHealthDataSource =
  | "live"
  | "derived"
  | "unconfigured"
  | "unavailable";

export type EstateAttentionSeverity = "critical" | "watch" | "ready";

export interface EstateAttentionItem {
  id: string;
  severity: EstateAttentionSeverity;
  title: string;
  detail: string;
  href: string;
  source: string;
}

export interface EstateHealthSummary {
  agents_total: number;
  agents_production: number;
  agents_draft: number;
  pending_handoffs: number;
  pending_approvals: number;
  trace_errors: number;
  trace_count: number;
  eval_suites: number;
  audit_events: number;
  open_incidents: number;
  blocked_deploys: number;
}

export interface EstateHealth {
  workspace_id: string | null;
  generated_at: string;
  data_source: EstateHealthDataSource;
  provenance: string[];
  summary: EstateHealthSummary;
  attention: EstateAttentionItem[];
  degraded_reason?: string | undefined;
}

export interface FetchEstateHealthOptions extends UxWireupClientOptions {
  fallbackAgents?: AgentSummary[];
}

const EMPTY_SUMMARY: EstateHealthSummary = {
  agents_total: 0,
  agents_production: 0,
  agents_draft: 0,
  pending_handoffs: 0,
  pending_approvals: 0,
  trace_errors: 0,
  trace_count: 0,
  eval_suites: 0,
  audit_events: 0,
  open_incidents: 0,
  blocked_deploys: 0,
};

function nowIso(): string {
  return new Date().toISOString();
}

export function deriveEstateHealthFromAgents(
  agents: AgentSummary[],
  options: {
    workspaceId?: string | null | undefined;
    dataSource?: EstateHealthDataSource | undefined;
    degradedReason?: string | undefined;
  } = {},
): EstateHealth {
  const draftAgents = agents.filter((agent) => agent.active_version === null);
  const productionAgents = agents.filter(
    (agent) => agent.active_version !== null,
  );
  const attention: EstateAttentionItem[] = draftAgents
    .slice(0, 5)
    .map((agent) => ({
      id: `draft-agent-${agent.id}`,
      severity: "watch",
      title: `${agent.name} has no production version`,
      detail:
        agent.description ||
        "Finish behavior, eval gates, approvals, and deployment.",
      href: `/agents/${agent.id}`,
      source: `agents/${agent.id}.active_version`,
    }));

  if (agents.length === 0) {
    attention.push({
      id: "no-agents",
      severity: "ready",
      title: "No agents registered",
      detail: "Create or import the first governed agent for this workspace.",
      href: "/agents",
      source: "agents.list",
    });
  }

  return {
    workspace_id: options.workspaceId ?? agents[0]?.workspace_id ?? null,
    generated_at: nowIso(),
    data_source: options.dataSource ?? "derived",
    provenance: ["studio.listAgents"],
    summary: {
      ...EMPTY_SUMMARY,
      agents_total: agents.length,
      agents_production: productionAgents.length,
      agents_draft: draftAgents.length,
    },
    attention,
    degraded_reason: options.degradedReason,
  };
}

export async function fetchEstateHealth(
  workspaceId: string | null | undefined,
  opts: FetchEstateHealthOptions = {},
): Promise<EstateHealth> {
  const fallbackAgents = opts.fallbackAgents ?? [];
  if (!workspaceId) {
    return deriveEstateHealthFromAgents(fallbackAgents, {
      workspaceId: null,
      dataSource: "unconfigured",
      degradedReason: "No active workspace id is available yet.",
    });
  }

  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    return deriveEstateHealthFromAgents(fallbackAgents, {
      workspaceId,
      dataSource: "unconfigured",
      degradedReason: "LOOP_CP_API_BASE_URL is not configured.",
    });
  }

  const fetcher = opts.fetcher ?? fetch;
  const response = await fetcher(
    `${base}/workspaces/${encodeURIComponent(workspaceId)}/estate-health`,
    {
      method: "GET",
      headers: cpApiHeaders(opts),
      cache: "no-store",
    },
  ).catch((error: unknown) => {
    if (error instanceof TypeError) return null;
    throw error;
  });

  if (response === null) {
    return deriveEstateHealthFromAgents(fallbackAgents, {
      workspaceId,
      dataSource: "unavailable",
      degradedReason: "cp-api estate health could not be reached.",
    });
  }
  if (!response.ok) {
    return deriveEstateHealthFromAgents(fallbackAgents, {
      workspaceId,
      dataSource: "unavailable",
      degradedReason: `cp-api estate health returned ${response.status}.`,
    });
  }

  return (await response.json()) as EstateHealth;
}
