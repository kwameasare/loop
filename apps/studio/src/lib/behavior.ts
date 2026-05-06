import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";
import { targetUxFixtures, type TargetUXFixture } from "@/lib/target-ux";

export type BehaviorMode = "plain" | "policy" | "config";

export type BehaviorRiskLevel = "low" | "medium" | "high" | "blocked";

export interface BehaviorRiskFlag {
  id: string;
  label: string;
  level: BehaviorRiskLevel;
  description: string;
  evidence: string;
}

export interface BehaviorSentenceTelemetry {
  citedOutputs7d: number;
  contradictedTraces: number;
  neverInvokedTurns: number;
  evalCases: number;
  evidence: string;
  confidence: ConfidenceLevel;
}

export interface BehaviorSentence {
  id: string;
  role:
    | "purpose"
    | "promise"
    | "style"
    | "refusal"
    | "escalation"
    | "tool"
    | "memory";
  text: string;
  tokenCount: number;
  telemetry: BehaviorSentenceTelemetry;
  riskIds: string[];
}

export interface BehaviorSection {
  id: string;
  label: string;
  description: string;
  diffFromProduction: string;
  coveragePercent: number;
  evidence: string;
  sentences: BehaviorSentence[];
  policyRules: string[];
  config: string;
}

export interface BehaviorSemanticDiff {
  id: string;
  summary: string;
  evidence: string;
  impact: string;
}

export interface BehaviorPreview {
  affectedEnvironments: string[];
  policyChecks: string[];
  costDelta: string;
  risk: BehaviorRiskLevel;
  rollback: string;
  evidence: string;
  canApply: boolean;
  blockedReason?: string | undefined;
}

export interface BehaviorEditorData {
  agentId: string;
  agentName: string;
  branch: string;
  objectState: ObjectState;
  trust: TrustState;
  sections: BehaviorSection[];
  riskFlags: BehaviorRiskFlag[];
  semanticDiffs: BehaviorSemanticDiff[];
  evalCoveragePercent: number;
  evalEvidence: string;
  evalConfidence: ConfidenceLevel;
  preview: BehaviorPreview;
  degradedReason?: string | undefined;
}

export const BEHAVIOR_MODE_LABEL: Record<BehaviorMode, string> = {
  plain: "Plain language",
  policy: "Structured policy",
  config: "Code/config",
};

export const BEHAVIOR_MODE_DESCRIPTION: Record<BehaviorMode, string> = {
  plain: "Purpose, promises, tone, and constraints as careful prose.",
  policy:
    "Goals, refusal, escalation, tools, memory, and compliance boundaries.",
  config: "Exact source representation with branch-ready config.",
};

const BEHAVIOR_RISKS: BehaviorRiskFlag[] = [
  {
    id: "risk_eval_gap",
    label: "Missing eval coverage",
    level: "high",
    description:
      "Spanish refund paraphrases have one regression and no approval replay yet.",
    evidence: "eval_refunds case refund_window_es_may",
  },
  {
    id: "risk_tool_grant",
    label: "Tool grant risk",
    level: "blocked",
    description:
      "`issue_refund` is staged and money-moving; production use needs approval.",
    evidence: "tool_call span_tool plus deploy_refund_canary approval gate",
  },
  {
    id: "risk_memory_boundary",
    label: "Memory boundary",
    level: "medium",
    description:
      "The durable memory rule is safe, but the new sentence must keep payment data out.",
    evidence: "control_pii memory policy check",
  },
];

function behaviorSections(): BehaviorSection[] {
  return [
    {
      id: "purpose",
      label: "Purpose",
      description: "Fast prose that defines what this agent may help with.",
      diffFromProduction:
        "Purpose now names refund disputes and cancellation policy explicitly.",
      coveragePercent: 94,
      evidence: "snap_refund_may plus eval_refunds coverage map",
      policyRules: [
        "Answer order, refund, and escalation questions for active customers.",
        "Keep cancellation answers grounded in the current refund policy.",
        "Name uncertainty before asking for an order lookup.",
      ],
      config: [
        "purpose:",
        "  domains: [orders, refunds, cancellations]",
        "  current_policy: refund_policy_2026",
        "  uncertainty_rule: ask_for_order_lookup_before_refund_window",
      ].join("\n"),
      sentences: [
        {
          id: "sentence_purpose_refunds",
          role: "purpose",
          text: "Resolve order, refund, and escalation questions across chat and voice.",
          tokenCount: 12,
          riskIds: [],
          telemetry: {
            citedOutputs7d: 47,
            contradictedTraces: 0,
            neverInvokedTurns: 38,
            evalCases: 9,
            evidence: "trace_refund_742 and eval_refunds",
            confidence: "high",
          },
        },
        {
          id: "sentence_purpose_cancel",
          role: "promise",
          text: "When a customer asks to cancel, cite the May 2026 refund policy before quoting a refund window.",
          tokenCount: 19,
          riskIds: ["risk_eval_gap"],
          telemetry: {
            citedOutputs7d: 31,
            contradictedTraces: 3,
            neverInvokedTurns: 412,
            evalCases: 4,
            evidence: "eval_refunds refund_window_es_may",
            confidence: "medium",
          },
        },
      ],
    },
    {
      id: "escalation",
      label: "Escalation policy",
      description:
        "Boundaries for legal threats, high-value refunds, and policy conflicts.",
      diffFromProduction:
        "Escalation now routes legal threats and refund disputes over USD $200.",
      coveragePercent: 88,
      evidence: "scene_escalation_legal_threat and trace_refund_742",
      policyRules: [
        "Escalate legal threats to the retention policy owner.",
        "Escalate refund disputes above USD $200 before promising a refund.",
        "Escalate when policy documents disagree.",
      ],
      config: [
        "escalation:",
        "  legal_threat: operator_handoff",
        "  refund_dispute_usd_gt: 200",
        "  policy_conflict: retention_policy_owner",
      ].join("\n"),
      sentences: [
        {
          id: "sentence_escalate_legal",
          role: "escalation",
          text: "Escalate legal threats, refund disputes over USD $200, and policy conflicts.",
          tokenCount: 14,
          riskIds: [],
          telemetry: {
            citedOutputs7d: 18,
            contradictedTraces: 0,
            neverInvokedTurns: 144,
            evalCases: 5,
            evidence: "scene_escalation_legal_threat",
            confidence: "high",
          },
        },
      ],
    },
    {
      id: "tools-memory",
      label: "Tools and memory",
      description:
        "Tool grants and memory boundaries that keep side effects controlled.",
      diffFromProduction:
        "`lookup_order` stays read-only; `issue_refund` remains staged until approval.",
      coveragePercent: 82,
      evidence: "span_tool, tool_issue_refund, and control_pii",
      policyRules: [
        "Use `lookup_order` before quoting account-specific refund windows.",
        "Do not call `issue_refund` in production until Release Manager approval lands.",
        "Keep payment data and secrets out of durable memory.",
      ],
      config: [
        "tools:",
        "  lookup_order: read_only",
        "  issue_refund: staged_until_release_manager_approval",
        "memory:",
        "  durable_allow: [preferred_language]",
        "  durable_deny: [payment_data, secrets]",
      ].join("\n"),
      sentences: [
        {
          id: "sentence_tool_lookup",
          role: "tool",
          text: "Look up the order before quoting an exact refund window.",
          tokenCount: 11,
          riskIds: ["risk_tool_grant"],
          telemetry: {
            citedOutputs7d: 64,
            contradictedTraces: 1,
            neverInvokedTurns: 72,
            evalCases: 7,
            evidence: "span_tool lookup_order",
            confidence: "medium",
          },
        },
        {
          id: "sentence_memory_payment",
          role: "memory",
          text: "Remember durable preferences only; never retain payment data or secrets.",
          tokenCount: 12,
          riskIds: ["risk_memory_boundary"],
          telemetry: {
            citedOutputs7d: 8,
            contradictedTraces: 0,
            neverInvokedTurns: 211,
            evalCases: 3,
            evidence: "control_pii memory write audit",
            confidence: "medium",
          },
        },
      ],
    },
  ];
}

export function createBehaviorEditorData(
  agentId: string,
  fixture: TargetUXFixture = targetUxFixtures,
): BehaviorEditorData {
  const agent =
    fixture.agents.find((candidate) => candidate.id === agentId) ??
    fixture.agents[0]!;
  const evalSuite = fixture.evals[0]!;
  const deploy = fixture.deploys[0]!;
  return {
    agentId,
    agentName: agent.name,
    branch: fixture.workspace.branch,
    objectState: fixture.workspace.objectState,
    trust: fixture.workspace.trust,
    sections: behaviorSections(),
    riskFlags: BEHAVIOR_RISKS,
    semanticDiffs: [
      {
        id: "diff_refund_policy",
        summary:
          "You made cancellation answers cite the May 2026 refund policy before quoting a refund window.",
        evidence: "diff prompt_refund_policy -> snap_refund_may",
        impact:
          "Expected to reduce archived-policy answers; Spanish refund coverage still blocks apply.",
      },
      {
        id: "diff_tool_scope",
        summary:
          "You kept `lookup_order` read-only and left `issue_refund` staged until approval.",
        evidence: "tool_issue_refund safety contract",
        impact:
          "Production side effects remain locked while replay checks run against the draft.",
      },
      {
        id: "diff_memory_boundary",
        summary:
          "You narrowed durable memory to preferences and excluded payment data and secrets.",
        evidence: "control_pii memory policy",
        impact:
          "Enterprise memory policy remains compliant with zero recent violations.",
      },
    ],
    evalCoveragePercent: evalSuite.passRate,
    evalEvidence: `${evalSuite.id}: ${evalSuite.coverage}; ${evalSuite.regressionCount} regression`,
    evalConfidence: evalSuite.confidence,
    preview: {
      affectedEnvironments: ["dev", "staging"],
      policyChecks: [
        "Release Manager approval required for money-moving tool grant.",
        "Spanish refund paraphrase must pass before production promotion.",
        "Memory policy `control_pii` remains healthy.",
      ],
      costDelta: "+24 tokens per refund turn; +USD $0.003 projected p50.",
      risk: deploy.approvals < deploy.requiredApprovals ? "blocked" : "medium",
      rollback: `Keep ${deploy.rollbackTarget} live and restore snap_refund_may.`,
      evidence: `${deploy.id}; trace_refund_742; ${evalSuite.id}`,
      canApply: deploy.approvals >= deploy.requiredApprovals,
      blockedReason:
        deploy.approvals >= deploy.requiredApprovals
          ? undefined
          : "Preview is ready, but apply is blocked until Release Manager approval and the Spanish refund eval pass.",
    },
  };
}

export function createEmptyBehaviorEditorData(
  agentId = "agent_empty",
): BehaviorEditorData {
  const base = createBehaviorEditorData(agentId);
  return {
    ...base,
    sections: [],
    semanticDiffs: [],
    riskFlags: [],
    evalCoveragePercent: 0,
    evalEvidence:
      "No behavior sections exist yet. Import a prompt or create the first policy section.",
    evalConfidence: "unsupported",
    preview: {
      affectedEnvironments: ["dev"],
      policyChecks: ["No policy checks can run until behavior exists."],
      costDelta: "No token delta yet.",
      risk: "low",
      rollback: "No draft behavior has been saved.",
      evidence: "empty_behavior_fixture",
      canApply: false,
      blockedReason: "Create a behavior section before preview can apply.",
    },
  };
}
