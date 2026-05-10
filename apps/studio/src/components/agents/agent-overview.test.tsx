import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { waitFor } from "@testing-library/react";

import {
  AgentOverview,
  type AgentOverviewProps,
} from "@/components/agents/agent-overview";
import {
  EMPTY_COMMITMENT_BODY,
  buildLocalCommitmentDocument,
} from "@/lib/agent-commitment";
import { buildLocalChangePackage } from "@/lib/change-package";
import { buildLocalChannelBindings } from "@/lib/channel-bindings";
import type { EvalSuite } from "@/lib/evals";
import type { AgentIntakeRecord } from "@/lib/agent-intake";
import { localAgentHandoff } from "@/lib/agent-handoff";
import { localAgentWorkflow } from "@/lib/agent-workflow";
import type { KbDocument } from "@/lib/kb";
import { localMemoryPolicies } from "@/lib/memory-policies";
import { localToolContracts } from "@/lib/tool-contracts";
import type { TraceSummary } from "@/lib/traces";

const BASE_PROPS: AgentOverviewProps = {
  id: "ag_1",
  name: "Support Bot",
  description: "Handles tier-1 tickets.",
  model: "gpt-4o-mini",
  activeVersion: 3,
  updatedAt: "2025-01-15T10:00:00Z",
  lastDeploy: {
    deployed_at: "2025-01-15T10:00:00Z",
    version: 3,
    status: "active",
  },
};

const EVAL_SUITES: EvalSuite[] = [
  {
    id: "suite_refund",
    name: "Refund regression",
    agentId: "ag_1",
    cases: 24,
    lastRunAt: "2026-05-09T12:00:00Z",
    passRate: 0.96,
  },
  {
    id: "suite_voice",
    name: "Voice handoff",
    agentId: "ag_1",
    cases: 12,
    lastRunAt: "2026-05-08T12:00:00Z",
    passRate: 0.9,
  },
];

const KNOWLEDGE_DOCUMENTS: KbDocument[] = [
  {
    id: "doc_ready",
    agentId: "ag_1",
    name: "support_handbook.md",
    contentType: "text/markdown",
    bytes: 12_288,
    status: "ready",
    uploadedAt: "2026-05-01T00:00:00Z",
    lastRefreshedAt: "2026-05-09T00:00:00Z",
  },
];

const TRACE_SUMMARIES: TraceSummary[] = [
  {
    id: "trc_old_ok",
    agent_id: "ag_1",
    agent_name: "Support Bot",
    root_name: "turn old_ok",
    status: "ok",
    duration_ns: 620_000_000,
    started_at_ms: Date.UTC(2026, 4, 9, 10, 0, 0),
    span_count: 5,
  },
  {
    id: "trc_latest_error",
    agent_id: "ag_1",
    agent_name: "Support Bot",
    root_name: "turn latest_error",
    status: "error",
    duration_ns: 940_000_000,
    started_at_ms: Date.UTC(2026, 4, 9, 13, 0, 0),
    span_count: 7,
  },
];

function intakeRecord(): AgentIntakeRecord {
  return {
    id: "intake_1",
    workspace_id: "ws_1",
    agent_id: "ag_1",
    state: "draft_ready",
    creation_path: "legacy_import",
    jobs: [
      { name: "parse_artifacts", state: "completed", count: 2 },
      { name: "extract_intents", state: "completed", count: 4 },
    ],
    artifact_reports: [
      {
        name: "botpress-export.json",
        kind: "botpress_export",
        status: "parsed",
      },
    ],
    intent_map: [
      { id: "intent_refund", label: "Refund request", confidence: "high" },
    ],
    contradictions: [],
    sensitive_data_findings: [],
    candidate_tools: [{ name: "lookup_order" }],
    candidate_knowledge_sources: [{ name: "refund-policy.pdf" }],
    candidate_channels: [{ channel: "whatsapp", status: "draft" }],
    candidate_memory_policy: { scope: "conversation" },
    candidate_eval_cases: [
      { name: "Refund handoff", source: "intake:contract" },
      { name: "Channel format", source: "intake:channel" },
    ],
    risk_notes: [],
    missing_information: [],
    readiness: {
      score: 78,
      ready: ["Commitment Document drafted"],
      needs_attention: ["Run first simulation suite before preflight."],
      landing: "/agents/ag_1",
    },
    created_object_refs: {},
    created_by: "maya@example.com",
    created_at: "2026-05-09T10:00:00Z",
    updated_at: "2026-05-09T10:05:00Z",
  };
}

describe("AgentOverview", () => {
  it("renders description text", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "Handles tier-1 tickets.",
    );
  });

  it("shows placeholder when description is empty", () => {
    render(<AgentOverview {...BASE_PROPS} description="" />);
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "No description yet.",
    );
  });

  it("renders model identifier", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-model")).toHaveTextContent(
      "gpt-4o-mini",
    );
  });

  it("shows canonical aliases when the direct model is empty", () => {
    render(<AgentOverview {...BASE_PROPS} model="" />);
    expect(screen.getByTestId("overview-model")).toHaveTextContent(
      "No model configured",
    );
  });

  it("renders last-deploy version", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-deploy-version")).toHaveTextContent(
      "v3",
    );
  });

  it("renders last-deploy status", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-deploy-status")).toHaveTextContent(
      "active",
    );
  });

  it("renders the creation intake landing panel when deep-linked after agent creation", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        focusedIntakeId="intake_1"
        intakeRecord={intakeRecord()}
      />,
    );

    expect(screen.getByTestId("agent-intake-landing")).toHaveTextContent(
      "Created from governed intake",
    );
    expect(screen.getByTestId("intake-readiness-score")).toHaveTextContent(
      "78%",
    );
    expect(screen.getByTestId("intake-jobs")).toHaveTextContent(
      "parse_artifacts: completed (2)",
    );
    expect(screen.getByTestId("intake-created")).toHaveTextContent(
      "1 channel candidate",
    );
    expect(screen.getByTestId("intake-created")).toHaveTextContent(
      "1 knowledge source candidate",
    );
    expect(screen.getByTestId("intake-artifacts")).toHaveTextContent(
      "botpress-export.json - parsed",
    );
    expect(screen.getByTestId("intake-intents")).toHaveTextContent(
      "Refund request - high",
    );
    expect(screen.getByText("Review Commitment Document")).toHaveAttribute(
      "href",
      "/agents/ag_1/contract",
    );
    expect(screen.getByTestId("agent-intake-landing")).toHaveTextContent(
      "Draft readiness checklist",
    );
    expect(screen.getByTestId("intake-readiness-commitment")).toHaveTextContent(
      "Commitment accepted",
    );
    expect(screen.getByTestId("intake-readiness-commitment")).toHaveTextContent(
      "blocked",
    );
    expect(
      screen
        .getByTestId("intake-readiness-commitment")
        .querySelector("a"),
    ).toHaveAttribute("href", "/agents/ag_1/contract");
    expect(screen.getByTestId("intake-readiness-channels")).toHaveTextContent(
      "1 draft channel binding created",
    );
    expect(
      screen.getByTestId("intake-readiness-channels").querySelector("a"),
    ).toHaveAttribute("href", "/agents/ag_1/channels");
    expect(screen.getByTestId("intake-readiness-tools")).toHaveTextContent(
      "1 mock tool contract created",
    );
    expect(screen.getByTestId("intake-readiness-knowledge")).toHaveTextContent(
      "1 knowledge source candidate captured",
    );
    expect(screen.getByTestId("intake-readiness-risk")).toHaveTextContent(
      "No unresolved intake risk",
    );
    expect(screen.getByTestId("intake-readiness-preflight")).toHaveTextContent(
      "Generate a Change Package",
    );
  });

  it("renders intake job progress and recoverable artifact parse failures", () => {
    const record = intakeRecord();
    record.jobs = [
      {
        name: "parse_artifacts",
        state: "needs_recovery",
        count: 2,
        progress_percent: 100,
        partial_results_ref: "artifact_reports",
        partial_result_count: 2,
        recoverable: true,
        error: "OpenAPI artifact must include an openapi version and paths.",
      },
    ];
    record.artifact_reports = [
      {
        name: "broken-openapi.yaml",
        kind: "openapi",
        status: "failed",
        recoverable: true,
        recovery_action: "replace_openapi_or_continue_without_source",
        error: "OpenAPI artifact must include an openapi version and paths.",
      },
    ];

    render(
      <AgentOverview
        {...BASE_PROPS}
        focusedIntakeId="intake_1"
        intakeRecord={record}
      />,
    );

    expect(screen.getByTestId("intake-jobs")).toHaveTextContent(
      "parse_artifacts: needs_recovery (2)",
    );
    expect(screen.getByTestId("intake-jobs")).toHaveTextContent(
      "2 partial results in artifact_reports",
    );
    expect(
      screen.getByRole("progressbar", { name: /parse_artifacts/i }),
    ).toHaveAttribute("aria-valuenow", "100");
    expect(screen.getByTestId("intake-artifacts")).toHaveTextContent(
      "broken-openapi.yaml - failed",
    );
    expect(screen.getByTestId("intake-artifacts")).toHaveTextContent(
      "OpenAPI artifact must include an openapi version and paths.",
    );
  });

  it("does not fake intake details when the focused intake cannot load", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        focusedIntakeId="intake_missing"
        intakeDegradedReason="cp-api GET /agent-intakes -> 404"
      />,
    );

    expect(screen.getByTestId("agent-intake-landing")).toHaveTextContent(
      "Creation intake unavailable",
    );
    expect(screen.getByTestId("agent-intake-landing")).toHaveTextContent(
      "intake_missing",
    );
  });

  it("renders the workbench profile, state sentence, outline, evidence panel, and safe actions without fixture claims", () => {
    render(<AgentOverview {...BASE_PROPS} />);

    expect(screen.getByTestId("agent-workbench-profile")).toHaveTextContent(
      "Support Bot",
    );
    expect(screen.getByTestId("agent-state-sentence")).toHaveTextContent(
      "Production is currently v3",
    );
    expect(screen.getByTestId("agent-state-evidence")).toHaveTextContent(
      "agent.active_version",
    );
    expect(screen.getByTestId("overview-environment")).toHaveTextContent(
      "unconfigured",
    );
    expect(screen.getByTestId("overview-branch")).toHaveTextContent(
      "No branch loaded",
    );
    expect(screen.getByTestId("overview-production-version")).toHaveTextContent(
      "v3",
    );
    expect(screen.getByTestId("agent-outline-purpose")).toHaveTextContent(
      "Purpose",
    );
    expect(screen.getByTestId("agent-outline-commitment")).toHaveTextContent(
      "No versioned Commitment Document loaded",
    );
    expect(screen.getByTestId("agent-outline-channels")).toHaveTextContent(
      "No channel binding records loaded",
    );
    expect(screen.getByTestId("agent-outline-link-channels")).toHaveAttribute(
      "href",
      "/agents/ag_1/channels",
    );
    expect(screen.getByTestId("agent-outline-tools")).toHaveTextContent(
      "No tool contracts loaded",
    );
    expect(screen.getByTestId("agent-outline-link-tools")).toHaveAttribute(
      "href",
      "/agents/ag_1/tools",
    );
    expect(screen.getByTestId("agent-live-preview")).toHaveTextContent(
      "No preview run loaded",
    );
    expect(screen.getAllByTestId("diff-ribbon")[0]).toHaveTextContent(
      "No draft diff loaded",
    );
    expect(screen.getByTestId("safe-next-actions")).toHaveTextContent(
      "Run first simulator turn",
    );
    expect(screen.getByTestId("safe-action-replay")).toHaveAttribute(
      "href",
      "/agents/ag_1/simulator",
    );
    expect(screen.getByTestId("safe-action-eval")).toHaveAttribute(
      "href",
      "/agents/ag_1/evals",
    );
    expect(screen.queryByText("trace_refund_742")).not.toBeInTheDocument();
    expect(screen.queryByText("I need to cancel my annual renewal")).toBeNull();
  });

  it("uses an accepted Commitment Document as the workbench purpose and commitment evidence", () => {
    const body = {
      ...EMPTY_COMMITMENT_BODY,
      business_responsibility: "Resolve support billing escalations.",
      target_users: "Enterprise admins.",
      owner_user_id: "maya@acme.test",
      worst_case_failure: "Refunds an ineligible account.",
      channels: ["web", "telegram"],
      systems_touched: ["billing"],
      regions: ["eu-west-2"],
      languages: ["en"],
      budget_target: "$0.08 per resolved turn",
      escalation_policy: "Escalate legal threats and refunds over $200.",
    };
    const commitment = {
      ...buildLocalCommitmentDocument("ag_1", body),
      id: "commit_accepted",
      version: 3,
      status: "accepted" as const,
      accepted_at: "2026-05-09T12:00:00Z",
    };

    render(<AgentOverview {...BASE_PROPS} commitment={commitment} />);

    expect(screen.getByTestId("agent-outline-purpose")).toHaveTextContent(
      "Resolve support billing escalations",
    );
    expect(screen.getByTestId("agent-outline-commitment")).toHaveTextContent(
      "accepted v3",
    );
    expect(screen.getByTestId("agent-workbench-profile")).toHaveTextContent(
      "maya@acme.test",
    );
    expect(screen.getByText("Budget cap").parentElement).toHaveTextContent(
      "$0.08 per resolved turn",
    );
    expect(screen.getByText("Escalation").parentElement).toHaveTextContent(
      "Escalate legal threats and refunds over $200.",
    );
  });

  it("surfaces channel readiness from real channel bindings", () => {
    const channelBindings = buildLocalChannelBindings("ag_1").map((binding) =>
      binding.channel_type === "whatsapp"
        ? {
            ...binding,
            status: "ready" as const,
            display_name: "WhatsApp",
            readiness: binding.readiness.map((check) => ({
              ...check,
              status: "passed" as const,
              evidence_ref: `channel/${binding.id}/${check.id}`,
            })),
          }
        : binding,
    );

    render(
      <AgentOverview {...BASE_PROPS} channelBindings={channelBindings} />,
    );

    expect(screen.getByTestId("agent-outline-channels")).toHaveTextContent(
      "1/9 channel binding ready: WhatsApp",
    );
    expect(screen.getByTestId("agent-outline-channels")).toHaveTextContent(
      "1 ready channel can proceed",
    );
    expect(screen.getByTestId("overview-channels")).toHaveTextContent(
      "WhatsApp",
    );
  });

  it("surfaces tool contract risk from real tool contracts", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        toolContracts={localToolContracts("ag_1", [
          "lookup_order",
          "refund_payment",
        ])}
      />,
    );

    expect(screen.getByTestId("agent-outline-tools")).toHaveTextContent(
      "2 tool contracts loaded; 1 money-moving; 1 review-required.",
    );
    expect(screen.getByTestId("agent-outline-tools")).toHaveTextContent(
      "Request approval before live use of refund_payment",
    );
    expect(screen.getByTestId("agent-outline-tools-count")).toHaveTextContent(
      "2 tools",
    );
  });

  it("surfaces memory policy review from real memory policies", () => {
    const memoryPolicies = localMemoryPolicies("ag_1").map((policy) =>
      policy.scope === "workspace"
        ? { ...policy, approval_status: "approved" as const }
        : policy,
    );

    render(
      <AgentOverview
        {...BASE_PROPS}
        memoryPolicies={memoryPolicies}
      />,
    );

    expect(screen.getByTestId("agent-outline-memory")).toHaveTextContent(
      "3 memory policies loaded; 2 durable; 1 review-required.",
    );
    expect(screen.getByTestId("agent-outline-memory")).toHaveTextContent(
      "Review user memory policy before promotion",
    );
    expect(screen.getByTestId("agent-outline-memory-count")).toHaveTextContent(
      "3 memory rules",
    );
  });

  it("surfaces weakest eval coverage from agent eval suites", () => {
    render(<AgentOverview {...BASE_PROPS} evalSuites={EVAL_SUITES} />);

    expect(screen.getByTestId("agent-outline-evals")).toHaveTextContent(
      "2 eval suites: 36 cases; weakest gate Voice handoff at 90%",
    );
    expect(screen.getByTestId("agent-outline-evals")).toHaveTextContent(
      "90% pass rate",
    );
    expect(screen.getByTestId("agent-live-preview")).toHaveTextContent(
      "last run May",
    );
  });

  it("surfaces knowledge source readiness from KB documents", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        knowledgeDocuments={KNOWLEDGE_DOCUMENTS}
      />,
    );

    expect(screen.getByTestId("agent-outline-knowledge")).toHaveTextContent(
      "1 knowledge source ready; 12.0 KB indexed.",
    );
    expect(screen.getByTestId("agent-outline-knowledge")).toHaveTextContent(
      "run retrieval evals before deploy",
    );
    expect(screen.getByTestId("agent-outline-sources-count")).toHaveTextContent(
      "1 sources",
    );
  });

  it("surfaces persisted trace evidence and links the latest trace", () => {
    render(
      <AgentOverview {...BASE_PROPS} traceSummaries={TRACE_SUMMARIES} />,
    );

    expect(screen.getByTestId("agent-outline-traces")).toHaveTextContent(
      "2 persisted traces loaded; 1 failed; latest trc_latest_error",
    );
    expect(screen.getByTestId("agent-outline-traces")).toHaveTextContent(
      "Investigate 1 failed trace before promotion",
    );
    expect(screen.getByTestId("agent-live-preview")).toHaveTextContent(
      "Latest persisted trace: trc_latest_error",
    );
    expect(screen.getByTestId("safe-action-trace")).toHaveAttribute(
      "href",
      "/traces/trc_latest_error",
    );
    expect(screen.getByTestId("safe-action-trace")).toHaveTextContent(
      "Open latest trace",
    );
  });

  it("surfaces Change Package approval and content-hash evidence", () => {
    const changePackage = {
      ...buildLocalChangePackage("ag_1"),
      id: "cp_refund_42",
      status: "submitted" as const,
      summary: "Refund behavior tightens escalation and replay gates.",
      content_hash: "hash_refund_package_123456789",
      rollback_target_version_id: "ver_3",
      updated_at: "2026-05-09T14:00:00Z",
      required_approvals: [
        {
          id: "owner",
          role: "Agent owner",
          required: true,
          satisfied: true,
          reason: "Owner approved.",
          state: "approved",
          content_hash: "hash_refund_package_123456789",
        },
        {
          id: "risk",
          role: "Risk reviewer",
          required: true,
          satisfied: false,
          reason: "Money movement approval required.",
          state: "pending",
        },
      ],
    };

    render(<AgentOverview {...BASE_PROPS} changePackage={changePackage} />);

    expect(screen.getByTestId("agent-outline-governance")).toHaveTextContent(
      "submitted Change Package cp_refund_42; approvals 1/2",
    );
    expect(screen.getByTestId("agent-outline-governance")).toHaveTextContent(
      "1 required approval still pending",
    );
    expect(screen.getByTestId("agent-outline-deployments")).toHaveTextContent(
      "Refund behavior tightens escalation and replay gates",
    );
    expect(screen.getByTestId("safe-action-approval")).toBeDisabled();
    expect(screen.getByTestId("safe-action-approval")).toHaveTextContent(
      "1 required approval pending",
    );
  });

  it("surfaces handoff walkthrough ownership and open-risk evidence", () => {
    const handoffModel = {
      ...localAgentHandoff("ag_1"),
      owner_user_id: "maya@acme.test",
      backup_owner_user_id: "sam@acme.test",
      generated_at: "2026-05-09T15:00:00Z",
      open_risks: [
        {
          id: "risk_open_escalation",
          severity: "blocking" as const,
          title: "Escalation owner missing",
          detail: "Assign a fallback owner before PTO handoff.",
          evidence_ref: "commitment/commit_1",
        },
      ],
      walkthrough_sections: [
        {
          id: "change-packages",
          title: "Change Packages",
          summary: "Two recent packages need review.",
          count: 2,
          evidence_refs: ["change-package/cp_1", "change-package/cp_2"],
        },
        {
          id: "incidents",
          title: "Incidents",
          summary: "One incident produced eval coverage.",
          count: 1,
          evidence_refs: ["incident/inc_1"],
        },
      ],
      transfers: [
        {
          id: "transfer_1",
          workspace_id: "ws_1",
          agent_id: "ag_1",
          previous_owner_user_id: "old@acme.test",
          new_owner_user_id: "maya@acme.test",
          backup_owner_user_id: "sam@acme.test",
          reason: "Planned support rotation.",
          acknowledged_risk_ids: [],
          open_risk_ids: ["risk_open_escalation"],
          walkthrough_section_ids: ["change-packages", "incidents"],
          notification: {
            recipient: "maya@acme.test",
            channel: "in_app",
            status: "sent",
            sent_at: "2026-05-09T15:05:00Z",
            summary: "Review the walkthrough.",
          },
          history_walkthrough_id: "walk_1",
          created_by_user_id: "lead@acme.test",
          created_at: "2026-05-09T15:00:00Z",
        },
      ],
    };

    render(<AgentOverview {...BASE_PROPS} handoffModel={handoffModel} />);

    expect(screen.getByTestId("agent-outline-history")).toHaveTextContent(
      "2 walkthrough sections; 1 open risk; owner maya@acme.test",
    );
    expect(screen.getByTestId("agent-outline-history")).toHaveTextContent(
      "Resolve 1 blocking handoff risk before ownership transfer",
    );
    expect(screen.getByTestId("safe-action-rollback")).toHaveTextContent(
      "walk_1",
    );
  });

  it("surfaces workflow branch, Change Set, and release candidate evidence", () => {
    const workflow = localAgentWorkflow("ag_1");

    render(<AgentOverview {...BASE_PROPS} workflow={workflow} />);

    expect(screen.getByTestId("overview-branch")).toHaveTextContent(
      "draft/refund-policy-fix",
    );
    expect(screen.getByText(/Change Set cs_local_refund/)).toBeInTheDocument();
    expect(screen.getAllByTestId("diff-ribbon")[0]).toHaveTextContent(
      "ver_local_refund",
    );
    expect(screen.getAllByTestId("diff-ribbon")[0]).toHaveTextContent(
      "2 release approvals pending",
    );
  });

  it("uses the durable agent object state when provided by cp-api", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        objectState="canary"
        stateReason="Deployment dep_1 is in ramp rollout."
        stateEvidenceRef="deployment/dep_1"
      />,
    );

    expect(screen.getByTestId("agent-state-sentence")).toHaveTextContent(
      "Deployment dep_1 is in ramp rollout",
    );
    expect(screen.getByTestId("agent-state-evidence")).toHaveTextContent(
      "deployment/dep_1",
    );
    expect(screen.getByTestId("agent-workbench-profile")).toHaveTextContent(
      "Canary",
    );
  });

  it("surfaces degraded cached-data evidence when live agent data is unavailable", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        dataState="degraded"
        degradedReason="cp-api GET /agents/agt_1 returned 503."
      />,
    );

    expect(screen.getByTestId("agent-workbench-degraded")).toHaveTextContent(
      "cp-api GET /agents/agt_1 returned 503",
    );
  });

  it("does not proxy last deploy from agent summary when deployment history is unavailable", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        lastDeploy={{
          deployed_at: null,
          version: null,
          status: null,
          unavailableReason:
            "LOOP_CP_API_BASE_URL is required to load deployment history.",
        }}
      />,
    );

    expect(screen.getByTestId("overview-deploy-time")).toHaveTextContent(
      "Unavailable",
    );
    expect(
      screen.getByTestId("overview-deploy-unavailable"),
    ).toHaveTextContent("deployment history");
    expect(screen.queryByTestId("overview-deploy-version")).toBeNull();
  });

  it("keeps production promotion visible but blocked when approval is missing", () => {
    render(<AgentOverview {...BASE_PROPS} activeVersion={null} />);

    expect(screen.getByTestId("agent-workbench-permission")).toHaveTextContent(
      "Production promote is locked",
    );
    expect(screen.getByTestId("safe-action-approval")).toBeDisabled();
    expect(screen.getByTestId("safe-action-approval")).toHaveTextContent(
      "No Change Package or approval is loaded",
    );
  });

  it("renders 'Never' when deployed_at is null", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        lastDeploy={{ deployed_at: null, version: null, status: null }}
      />,
    );
    expect(screen.getByTestId("overview-deploy-time")).toHaveTextContent(
      "Never",
    );
  });

  it("omits version row when version is null", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        lastDeploy={{ deployed_at: null, version: null, status: null }}
      />,
    );
    expect(screen.queryByTestId("overview-deploy-version")).toBeNull();
  });

  // Edit-description modal
  it("opens edit modal when Edit button is clicked", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    expect(screen.getByTestId("edit-desc-modal")).toBeInTheDocument();
  });

  it("modal textarea is pre-filled with current description", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    const textarea = screen.getByTestId(
      "edit-desc-textarea",
    ) as HTMLTextAreaElement;
    expect(textarea.value).toBe("Handles tier-1 tickets.");
  });

  it("saves updated description and closes modal", () => {
    const onSave = vi.fn();
    render(<AgentOverview {...BASE_PROPS} onDescriptionSave={onSave} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    fireEvent.change(screen.getByTestId("edit-desc-textarea"), {
      target: { value: "Updated copy." },
    });
    fireEvent.click(screen.getByTestId("edit-desc-save"));
    // Modal closed
    expect(screen.queryByTestId("edit-desc-modal")).toBeNull();
    // Callback called
    expect(onSave).toHaveBeenCalledWith("Updated copy.");
    // Description text updated in DOM
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "Updated copy.",
    );
  });

  it("cancel closes modal without updating description", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    fireEvent.change(screen.getByTestId("edit-desc-textarea"), {
      target: { value: "Discarded text" },
    });
    fireEvent.click(screen.getByTestId("edit-desc-cancel"));
    expect(screen.queryByTestId("edit-desc-modal")).toBeNull();
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "Handles tier-1 tickets.",
    );
  });

  it("autofocuses textarea and closes on Escape, restoring trigger focus", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    const trigger = screen.getByTestId("overview-edit-desc-button");
    trigger.focus();
    fireEvent.click(trigger);
    expect(screen.getByTestId("edit-desc-textarea")).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByTestId("edit-desc-modal")).toBeNull();
    return waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });
});
