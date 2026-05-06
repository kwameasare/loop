/**
 * Migration Atelier (UX301) — typed model for entry, supported sources, the
 * import wizard, and the three-pane review.
 *
 * The canonical UX standard §18 demands that migration entry treats import as
 * first-class, labels every source `verified`/`planned`/`aspirational`, and
 * walks a builder through nine deliberate steps (§18.3) before the source/
 * middle/Loop review panes (§18.4) are useful. This module is the single
 * source of truth consumed by the React surface and its tests.
 */

import type { ObjectState } from "@/lib/design-tokens";

export type MigrationSourceStatus = "verified" | "planned" | "aspirational";

export const SOURCE_STATUS_TREATMENT: Record<
  MigrationSourceStatus,
  { label: string; tone: "success" | "info" | "warning"; description: string }
> = {
  verified: {
    label: "Verified",
    tone: "success",
    description:
      "Official export or API path implemented and tested. We can promise this in product copy.",
  },
  planned: {
    label: "Planned",
    tone: "info",
    description:
      "Feasible path identified. Importer is partial or behind a flag; do not promise feature parity yet.",
  },
  aspirational: {
    label: "Aspirational",
    tone: "warning",
    description:
      "Requires partnership, reverse mapping, or customer-supplied format. Engage support before quoting timelines.",
  },
};

export interface MigrationSource {
  id: string;
  name: string;
  status: MigrationSourceStatus;
  typicalInput: string;
  loopGoal: string;
  /**
   * External documentation URL referenced in canonical §40. Anchoring the UI
   * here prevents copy from drifting away from the actual upstream contract.
   */
  externalDocs?: string;
}

/**
 * Initial source list from canonical §18.2. Status reflects what is actually
 * implemented in the importer today; we deliberately bias toward `planned`
 * because UX301 ships the entry surface, not the importers themselves.
 */
export const MIGRATION_SOURCES: readonly MigrationSource[] = [
  {
    id: "botpress",
    name: "Botpress",
    status: "verified",
    typicalInput: ".bpz export or connected workspace",
    loopGoal:
      "Flows, KBs, actions, integrations, tables, variables, and transcripts.",
    externalDocs:
      "https://www.botpress.com/docs/learn/reference/import-export-bots",
  },
  {
    id: "voiceflow",
    name: "Voiceflow",
    status: "planned",
    typicalInput: ".vf, .vfr archive, or project API",
    loopGoal:
      "Intents, paths, variables, API blocks, knowledge, and transcripts.",
    externalDocs: "https://docs.voiceflow.com/reference/fetchproject",
  },
  {
    id: "dialogflow-cx",
    name: "Dialogflow CX",
    status: "planned",
    typicalInput: "Agent export archive or cloud export",
    loopGoal:
      "Intents, flows, routes, fulfillments, and training phrases.",
    externalDocs:
      "https://cloud.google.com/dialogflow/cx/docs/reference/rest/v3/projects.locations.agents/export",
  },
  {
    id: "dialogflow-es",
    name: "Dialogflow ES",
    status: "planned",
    typicalInput: "ZIP export from console",
    loopGoal:
      "Intents, training phrases, fulfillments, and entities.",
    externalDocs:
      "https://cloud.google.com/dialogflow/es/docs/reference/rest/v2/projects.agent/export",
  },
  {
    id: "rasa",
    name: "Rasa",
    status: "planned",
    typicalInput: "Git repo or project zip",
    loopGoal: "Domain, stories/rules, NLU data, actions, and endpoints.",
  },
  {
    id: "dify",
    name: "Dify",
    status: "planned",
    typicalInput: "YAML DSL export",
    loopGoal:
      "App config, workflow, tools, knowledge, and variables.",
    externalDocs: "https://docs.dify.ai/en/guides/management/app-management",
  },
  {
    id: "copilot-studio",
    name: "Microsoft Copilot Studio",
    status: "planned",
    typicalInput: "Solution export",
    loopGoal: "Topics, actions, entities, and channels.",
    externalDocs:
      "https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-export-import-bots",
  },
  {
    id: "langflow-flowise",
    name: "Langflow / Flowise",
    status: "planned",
    typicalInput: "JSON graph export",
    loopGoal: "Graph nodes, tools, routines, and eval fixtures.",
  },
  {
    id: "openai-assistants",
    name: "OpenAI Assistants / Custom GPTs",
    status: "planned",
    typicalInput: "Assistant config, manifest, and files",
    loopGoal: "Instructions, files, actions, and tools.",
  },
  {
    id: "n8n-zapier",
    name: "n8n / Zapier-style automations",
    status: "aspirational",
    typicalInput: "Workflow JSON",
    loopGoal: "LLM nodes, automations, and event handlers.",
  },
  {
    id: "chatbase-fin-sierra",
    name: "Chatbase / Intercom Fin / Sierra / ElevenLabs",
    status: "aspirational",
    typicalInput: "Token, export, or partnership path",
    loopGoal: "Prompts, KB, tools, escalation, and voice.",
  },
  {
    id: "custom-framework",
    name: "Custom framework",
    status: "planned",
    typicalInput: "Git repo, OpenAPI, transcripts",
    loopGoal: "Behavior draft, tools, evals, and migration gaps.",
  },
];

export type MigrationEntryKind = "import" | "template" | "git" | "blank";

export interface MigrationEntryChoice {
  id: MigrationEntryKind;
  label: string;
  summary: string;
  /**
   * `firstClass` raises the entry visually so import never feels secondary,
   * per canonical §18.1.
   */
  firstClass: boolean;
  href: string;
}

export const MIGRATION_ENTRY_CHOICES: readonly MigrationEntryChoice[] = [
  {
    id: "import",
    label: "Import from existing platform",
    summary:
      "Bring a Botpress, Voiceflow, Dialogflow, Rasa, Dify, or custom agent in with parity proof and rollback.",
    firstClass: true,
    href: "/migrate#sources",
  },
  {
    id: "template",
    label: "Start from template",
    summary: "Begin with a curated agent skeleton and customize the behavior.",
    firstClass: false,
    href: "/agents?surface=templates",
  },
  {
    id: "git",
    label: "Connect Git repository",
    summary: "Treat your repo as the source of truth for behavior and tools.",
    firstClass: false,
    href: "/agents?surface=git",
  },
  {
    id: "blank",
    label: "Start blank",
    summary:
      "Create an empty agent. Recommended only for exploratory builds without legacy context.",
    firstClass: false,
    href: "/agents?surface=blank",
  },
];

export type ImportWizardStepId =
  | "choose-source"
  | "upload-or-connect"
  | "analyze"
  | "inventory"
  | "map"
  | "resolve-gaps"
  | "generate"
  | "prove-parity"
  | "stage-cutover";

export interface ImportWizardStep {
  id: ImportWizardStepId;
  /** Numeric step displayed in the stepper (1-indexed). */
  index: number;
  label: string;
  description: string;
  /**
   * State expressed in the canonical object-state grammar so the stepper
   * can paint the same shapes the rest of the studio uses.
   */
  state: ObjectState;
}

/**
 * Canonical wizard from §18.3. The `state` values are the defaults used when
 * the user has not yet engaged the step; the component clamps later steps to
 * `draft` once the cursor moves past them so we never falsely imply progress.
 */
export const IMPORT_WIZARD_STEPS: readonly ImportWizardStep[] = [
  {
    id: "choose-source",
    index: 1,
    label: "Choose source",
    description:
      "Pick the platform you are leaving. Verified sources have an implemented importer; planned and aspirational sources require extra steps.",
    state: "draft",
  },
  {
    id: "upload-or-connect",
    index: 2,
    label: "Upload or connect",
    description:
      "Upload an export archive or authorize a connector. Secrets stay in vault and never touch the studio.",
    state: "draft",
  },
  {
    id: "analyze",
    index: 3,
    label: "Analyze project",
    description:
      "Loop parses flows, KBs, actions, integrations, tables, variables, transcripts, and preserves source IDs for lineage.",
    state: "draft",
  },
  {
    id: "inventory",
    index: 4,
    label: "Review inventory",
    description:
      "Confirm what was found. Anything unmapped is surfaced before behavior is generated.",
    state: "draft",
  },
  {
    id: "map",
    index: 5,
    label: "Map to Loop",
    description:
      "Apply the canonical mapping (flows → routines, actions → tools, KBs → knowledge sources). Override anything you disagree with.",
    state: "draft",
  },
  {
    id: "resolve-gaps",
    index: 6,
    label: "Resolve gaps",
    description:
      "Reconnect secrets, replace unsupported nodes, and accept or reject assisted-repair suggestions.",
    state: "draft",
  },
  {
    id: "generate",
    index: 7,
    label: "Generate agent",
    description:
      "Produce a draft Loop agent with prompts, tools, knowledge, memory rules, and eval seeds.",
    state: "draft",
  },
  {
    id: "prove-parity",
    index: 8,
    label: "Prove parity",
    description:
      "Replay historical conversations against source and Loop. Behavior, cost, and risk diffs must clear thresholds.",
    state: "draft",
  },
  {
    id: "stage-cutover",
    index: 9,
    label: "Stage cutover",
    description:
      "Connect production channel, enable shadow traffic, set canary percentage, and arm the rollback route.",
    state: "draft",
  },
];

export function findWizardStep(id: ImportWizardStepId): ImportWizardStep {
  const step = IMPORT_WIZARD_STEPS.find((s) => s.id === id);
  if (!step) {
    throw new Error(`Unknown import wizard step: ${id}`);
  }
  return step;
}

/**
 * Compute the per-step `ObjectState` given the current cursor. Earlier steps
 * are marked `production` (complete), the active step is `canary`, and later
 * steps stay `draft` so the stepper never lies about completed work.
 */
export function wizardStepStates(
  currentId: ImportWizardStepId,
): { id: ImportWizardStepId; state: ObjectState; label: string }[] {
  const cursor = findWizardStep(currentId).index;
  return IMPORT_WIZARD_STEPS.map((step) => {
    const state: ObjectState =
      step.index < cursor
        ? "production"
        : step.index === cursor
          ? "canary"
          : "draft";
    return { id: step.id, state, label: step.label };
  });
}

export type ReviewPane = "source" | "needs-eyes" | "loop";

export type ReviewDecisionSeverity = "blocking" | "advisory" | "fyi";

export interface ReviewItem {
  id: string;
  /** Stable origin identifier from the source platform — preserved for lineage. */
  sourceId: string;
  /** What the user is being asked to decide. */
  question: string;
  /** Concrete next action the middle pane offers. */
  action: string;
  severity: ReviewDecisionSeverity;
  /** Source-pane summary (legacy structure, read-only). */
  sourceSummary: string;
  /** Loop-pane summary (generated agent view, editable). */
  loopSummary: string;
  /** Migration confidence 0-100. */
  confidence: number;
  /**
   * Optional advisory copy displayed beneath the action. Used to keep the
   * middle pane from celebrating risk: degraded states must be explicit.
   */
  evidence?: string;
}

export const REVIEW_ITEMS: readonly ReviewItem[] = [
  {
    id: "review_refund_routine",
    sourceId: "botpress.workflow.refunds",
    question: "Does the refund routine match the legacy refund flow?",
    action: "Open routine and replay 12 production refund transcripts.",
    severity: "blocking",
    sourceSummary:
      "Botpress workflow `refunds` with nodes refund_start → lookup_order → refund_decision → escalation.",
    loopSummary:
      "Loop routine `refund-policy` with grounded answer step, `lookup_order` tool grant, and policy citation.",
    confidence: 78,
    evidence: "Custom JavaScript action `refund_decision` references an external secret.",
  },
  {
    id: "review_kb_policy",
    sourceId: "botpress.kb.policies",
    question: "Map legacy policy KB to Loop knowledge source?",
    action: "Approve mapping or split into per-policy sources.",
    severity: "advisory",
    sourceSummary: "Botpress KB `policies` with 32 documents tagged refund/cancellation/legal.",
    loopSummary: "Loop knowledge source `policies-2026` ingested with same tags and grounded ranking.",
    confidence: 91,
  },
  {
    id: "review_handoff",
    sourceId: "botpress.action.handoff_human",
    question: "Replace human handoff action with escalation policy?",
    action: "Convert to escalation policy with inbox route.",
    severity: "blocking",
    sourceSummary:
      "Botpress action `handoff_human` invoked from refund_decision when amount > $500.",
    loopSummary:
      "Loop escalation policy `refund-over-500` routes to inbox queue `retention` with full trace.",
    confidence: 64,
    evidence: "No mapping yet for the legacy `priority_tag` payload.",
  },
  {
    id: "review_unsupported_voice",
    sourceId: "botpress.integration.legacy_ivr",
    question: "Source uses an integration with no Loop equivalent.",
    action: "Mark intentionally unsupported or open a partner request.",
    severity: "fyi",
    sourceSummary: "Legacy IVR integration `legacy_ivr` configured with 4 handler webhooks.",
    loopSummary: "No Loop destination. Cutover plan must call this out explicitly.",
    confidence: 22,
    evidence: "This is an aspirational target. Do not block parity on it.",
  },
];

export interface MigrationReadiness {
  /** Aggregate readiness 0-100 used by the headline confidence meter. */
  overallScore: number;
  cleanlyImported: number;
  needsReview: number;
  secretsToReconnect: number;
  unsupported: number;
  parityPassing: number;
  parityTotal: number;
}

export const MIGRATION_READINESS: MigrationReadiness = {
  overallScore: 82,
  cleanlyImported: 147,
  needsReview: 23,
  secretsToReconnect: 8,
  unsupported: 4,
  parityPassing: 91,
  parityTotal: 100,
};

export function countReviewItemsBySeverity(
  items: readonly ReviewItem[],
): Record<ReviewDecisionSeverity, number> {
  return items.reduce<Record<ReviewDecisionSeverity, number>>(
    (acc, item) => {
      acc[item.severity] += 1;
      return acc;
    },
    { blocking: 0, advisory: 0, fyi: 0 },
  );
}
