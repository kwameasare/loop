import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";
import type { ChangePackage } from "@/lib/change-package";

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
  fix_change_package_id: string | null;
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

export interface IncidentFixPackageResponse {
  ok: boolean;
  change_package: ChangePackage;
  incident: IncidentRecord;
}

export type IncidentTransitionAction =
  | "contain"
  | "investigate"
  | "resolve"
  | "archive";

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
    fix_change_package_id: null,
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

function getLocalIncident(agentId: string, incidentId: string): IncidentRecord {
  const incident =
    LOCAL_INCIDENTS.find((item) => item.id === incidentId) ??
    LOCAL_INCIDENTS[0]!;
  return {
    ...incident,
    id: incidentId,
    agent_id: agentId,
  };
}

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
  const localIncident = getLocalIncident(agentId, incidentId);
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

export async function createIncidentFixChangePackage(
  agentId: string,
  incidentId: string,
  opts: UxWireupClientOptions = {},
): Promise<IncidentFixPackageResponse> {
  const localIncident = getLocalIncident(agentId, incidentId);
  const now = new Date().toISOString();
  return cpJson<IncidentFixPackageResponse>(
    `/agents/${encodeURIComponent(agentId)}/incidents/${encodeURIComponent(
      incidentId,
    )}/change-package`,
    {
      ...opts,
      method: "POST",
      body: {},
      fallback: {
        ok: true,
        change_package: {
          id: `cp_${incidentId}`,
          workspace_id: localIncident.workspace_id,
          agent_id: agentId,
          branch_id: "incident/fix",
          change_set_id: `cs_${incidentId}`,
          release_candidate_id: `rc_${incidentId}`,
          from_version_id: "production",
          to_version_id: "draft-incident-fix",
          commitment_document_id: "commitment_local",
          commitment_document_version: 1,
          summary: `Fix incident ${localIncident.id}: ${localIncident.trigger}`,
          semantic_diff: [
            {
              dimension: "incident",
              summary: localIncident.proposed_fix,
              evidence_ref: `incident/${localIncident.id}`,
            },
          ],
          eval_results_ref:
            localIncident.candidate_eval_suite_id ??
            `incident/${localIncident.id}/candidate-evals`,
          replay_results_ref: `incident/${localIncident.id}/affected-traces`,
          risk_summary: `${localIncident.severity} incident fix.`,
          cost_summary: "Replay required before cost claims.",
          latency_summary: "Replay required before latency claims.",
          channel_readiness_summary: `Incident channel scope: ${localIncident.channel_scope.join(
            ", ",
          )}`,
          tool_changes: [],
          memory_changes: [],
          knowledge_changes: [],
          required_approvals: [],
          pre_approved_classes: [],
          approval_status: "blocked",
          rollback_target_version_id:
            localIncident.rollback_action_ref || "last-known-safe",
          evidence_pack_id: `ep_${incidentId}`,
          evidence: {
            incident: localIncident.id,
            replay_results: `incident/${localIncident.id}/affected-traces`,
          },
          content_hash: `local-${incidentId}`,
          status: "generated",
          created_at: now,
          updated_at: now,
          submitted_at: null,
          stale_at: null,
        },
        incident: {
          ...localIncident,
          status: "fix_staged",
          fix_change_package_id: `cp_${incidentId}`,
          report: {
            ...localIncident.report,
            fix_change_package_id: `cp_${incidentId}`,
          },
        },
      },
    },
  );
}

export async function transitionIncident(
  agentId: string,
  incidentId: string,
  action: IncidentTransitionAction,
  note: string,
  opts: UxWireupClientOptions = {},
): Promise<IncidentRecord> {
  const localIncident = getLocalIncident(agentId, incidentId);
  const statusByAction: Record<IncidentTransitionAction, IncidentStatus> = {
    contain: "contained",
    investigate: "investigating",
    resolve: "resolved",
    archive: "archived",
  };
  const nextStatus = statusByAction[action];
  const now = new Date().toISOString();
  return cpJson<IncidentRecord>(
    `/agents/${encodeURIComponent(agentId)}/incidents/${encodeURIComponent(
      incidentId,
    )}/${action}`,
    {
      ...opts,
      method: "POST",
      body: { note },
      fallback: {
        ...localIncident,
        status: nextStatus,
        resolved_at:
          nextStatus === "resolved" ? now : localIncident.resolved_at,
        timeline: [
          ...localIncident.timeline,
          {
            at: now,
            kind: `incident_${nextStatus}`,
            summary: note || `Incident moved to ${nextStatus}.`,
          },
        ],
      },
    },
  );
}
