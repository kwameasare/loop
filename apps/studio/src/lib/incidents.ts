import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus =
  | "open"
  | "contained"
  | "investigating"
  | "fix_staged"
  | "resolved"
  | "archived";

export interface IncidentRecord {
  id: string;
  workspace_id: string;
  agent_id: string;
  deployment_id: string;
  severity: IncidentSeverity;
  trigger: string;
  status: IncidentStatus;
  affected_trace_ids: string[];
  affected_conversation_count: number;
  root_cause_hypothesis: string;
  rollback_action_ref: string;
  proposed_fix: string;
  candidate_eval_suite_id: string | null;
  channel_scope: string[];
  notifications: Array<{
    recipient: string;
    channel: string;
    status: string;
    sent_at: string;
    summary: string;
  }>;
  timeline: Array<{ kind: string; at: string; summary: string }>;
  report: Record<string, unknown>;
  created_at: string;
  created_by: string;
  resolved_at: string | null;
}

export interface IncidentListResponse {
  items: IncidentRecord[];
}

export interface IncidentEvalSeedResponse {
  ok: boolean;
  suite_id: string;
  case_ids: string[];
  incident: IncidentRecord;
}

const LOCAL_INCIDENTS: IncidentRecord[] = [
  {
    id: "inc_local_rollback",
    workspace_id: "local",
    agent_id: "agent_support",
    deployment_id: "dep_local",
    severity: "high",
    trigger: "error_rate breached 4% for web_chat canary",
    status: "contained",
    affected_trace_ids: ["trace_refund_742"],
    affected_conversation_count: 17,
    root_cause_hypothesis: "Tool schema changed upstream during canary.",
    rollback_action_ref: "deployment/dep_local/rollback",
    proposed_fix:
      "Replay affected traces, pin the tool schema, and create a Change Package with regression coverage.",
    candidate_eval_suite_id: null,
    channel_scope: ["web_chat"],
    notifications: [
      {
        recipient: "maya@acme.test",
        channel: "in_app",
        status: "queued",
        sent_at: "2026-05-09T03:12:00.000Z",
        summary: "high incident: error_rate breached 4% for web_chat canary",
      },
      {
        recipient: "diego@acme.test",
        channel: "in_app",
        status: "queued",
        sent_at: "2026-05-09T03:12:00.000Z",
        summary: "high incident: error_rate breached 4% for web_chat canary",
      },
    ],
    timeline: [
      {
        kind: "incident_created",
        at: "2026-05-09T03:12:00.000Z",
        summary: "Incident created from auto_rollback.",
      },
      {
        kind: "containment",
        at: "2026-05-09T03:12:38.000Z",
        summary: "Auto-rollback moved traffic away from v24.",
      },
    ],
    report: {
      rollback_status: "executed",
      suspected_cause: "Tool schema changed upstream during canary.",
      proposed_fix:
        "Replay affected traces, pin the tool schema, and create a Change Package with regression coverage.",
    },
    created_at: "2026-05-09T03:12:00.000Z",
    created_by: "loop-system",
    resolved_at: null,
  },
];

export async function listWorkspaceIncidents(
  workspaceId: string,
  opts: UxWireupClientOptions = {},
): Promise<IncidentListResponse> {
  return cpJson<IncidentListResponse>(
    `/workspaces/${encodeURIComponent(workspaceId)}/incidents`,
    {
      ...opts,
      fallback: { items: LOCAL_INCIDENTS },
    },
  );
}

export async function listAgentIncidents(
  agentId: string,
  opts: UxWireupClientOptions = {},
): Promise<IncidentListResponse> {
  return cpJson<IncidentListResponse>(
    `/agents/${encodeURIComponent(agentId)}/incidents`,
    {
      ...opts,
      fallback: {
        items: LOCAL_INCIDENTS.filter(
          (incident) => incident.agent_id === agentId,
        ),
      },
    },
  );
}

export async function seedIncidentEvalCases(
  agentId: string,
  incidentId: string,
  opts: UxWireupClientOptions = {},
): Promise<IncidentEvalSeedResponse> {
  const localIncident =
    LOCAL_INCIDENTS.find((incident) => incident.id === incidentId) ??
    LOCAL_INCIDENTS[0]!;
  return cpJson<IncidentEvalSeedResponse>(
    `/agents/${encodeURIComponent(agentId)}/incidents/${encodeURIComponent(
      incidentId,
    )}/eval-cases`,
    {
      ...opts,
      method: "POST",
      fallback: {
        ok: true,
        suite_id: "suite_incident_regressions_local",
        case_ids: [`case_${incidentId}`],
        incident: {
          ...localIncident,
          candidate_eval_suite_id: "suite_incident_regressions_local",
        },
      },
    },
  );
}
