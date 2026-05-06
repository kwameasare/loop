/**
 * UX402 — Studio onboarding library.
 *
 * Implements §33 (Onboarding) and §4.8–§4.10 (First 60 seconds / 30 minutes /
 * Enterprise first day) of the canonical target UX standard.
 *
 * Three doors only: Import, Template, Blank. No fourth door, no forced video,
 * no team survey before value (§33.1).
 *
 * Templates are working agents — they ship with a sample KB, mock tools, eval
 * suite, seeded conversations, trace examples, and a cost estimate (§33.2).
 *
 * Spotlight has exactly three first-run hints (§33.3). Concierge from real
 * data is permissioned, reversible, and explicit about what is read (§33.7).
 */

export const ONBOARDING_DOORS = ["import", "template", "blank"] as const;
export type OnboardingDoor = (typeof ONBOARDING_DOORS)[number];

export interface OnboardingDoorMeta {
  id: OnboardingDoor;
  title: string;
  summary: string;
  cta: string;
  estimatedSeconds: number;
}

export const ONBOARDING_DOOR_META: Record<OnboardingDoor, OnboardingDoorMeta> = {
  import: {
    id: "import",
    title: "Import from another platform",
    summary:
      "Bring an existing Botpress, Voiceflow, or Dialogflow project across with parity audit.",
    cta: "Open Migration Atelier",
    estimatedSeconds: 240,
  },
  template: {
    id: "template",
    title: "Start from a template",
    summary:
      "Working agents with sample KB, mock tools, eval suite, seeded conversations, traces, and cost estimate.",
    cta: "Browse templates",
    estimatedSeconds: 60,
  },
  blank: {
    id: "blank",
    title: "Start blank with the AI co-builder",
    summary:
      "An empty agent and the co-builder — first turn streams in under 60 seconds.",
    cta: "Open Workbench",
    estimatedSeconds: 60,
  },
};

export interface OnboardingTemplate {
  id: string;
  name: string;
  blurb: string;
  kbSources: number;
  mockTools: number;
  evalCases: number;
  seededConversations: number;
  costEstimateUsdPerMonth: number;
  channels: string[];
}

export const ONBOARDING_TEMPLATES: readonly OnboardingTemplate[] = [
  {
    id: "tmpl_support_agent",
    name: "Support agent",
    blurb: "Triage, deflect, and escalate L1 tickets with cited KB.",
    kbSources: 6,
    mockTools: 4,
    evalCases: 24,
    seededConversations: 30,
    costEstimateUsdPerMonth: 180,
    channels: ["web-widget", "email", "slack"],
  },
  {
    id: "tmpl_sales_sdr",
    name: "Sales SDR",
    blurb: "Qualify inbound, book meetings, and hand off to sellers.",
    kbSources: 4,
    mockTools: 5,
    evalCases: 18,
    seededConversations: 20,
    costEstimateUsdPerMonth: 220,
    channels: ["web-widget", "email"],
  },
  {
    id: "tmpl_scheduling_concierge",
    name: "Scheduling concierge",
    blurb: "Book, reschedule, and remind across calendars and time zones.",
    kbSources: 2,
    mockTools: 3,
    evalCases: 14,
    seededConversations: 18,
    costEstimateUsdPerMonth: 90,
    channels: ["web-widget", "sms"],
  },
  {
    id: "tmpl_voice_receptionist",
    name: "Voice receptionist",
    blurb: "Greet, route, and capture intent on inbound calls.",
    kbSources: 3,
    mockTools: 3,
    evalCases: 12,
    seededConversations: 16,
    costEstimateUsdPerMonth: 260,
    channels: ["voice"],
  },
  {
    id: "tmpl_it_helpdesk",
    name: "Internal IT helpdesk",
    blurb: "Reset passwords, file tickets, and answer policy questions.",
    kbSources: 8,
    mockTools: 5,
    evalCases: 22,
    seededConversations: 24,
    costEstimateUsdPerMonth: 140,
    channels: ["slack", "teams"],
  },
  {
    id: "tmpl_doc_search",
    name: "Document search assistant",
    blurb: "Cited search across long-form policy and product docs.",
    kbSources: 12,
    mockTools: 2,
    evalCases: 16,
    seededConversations: 14,
    costEstimateUsdPerMonth: 110,
    channels: ["web-widget"],
  },
  {
    id: "tmpl_procurement_qa",
    name: "Procurement Q&A",
    blurb: "Answer vendor, security review, and SOC 2 questionnaires with citations.",
    kbSources: 14,
    mockTools: 2,
    evalCases: 20,
    seededConversations: 12,
    costEstimateUsdPerMonth: 130,
    channels: ["web-widget", "email"],
  },
];

export interface SpotlightHint {
  id: "what-just-ran" | "click-any-turn" | "fork-from-turn";
  step: 1 | 2 | 3;
  title: string;
  body: string;
}

export const SPOTLIGHT_HINTS: readonly SpotlightHint[] = [
  {
    id: "what-just-ran",
    step: 1,
    title: "This is what just ran.",
    body: "The Workbench shows the latest turn, its tools, its retrieval, and its cost.",
  },
  {
    id: "click-any-turn",
    step: 2,
    title: "Click any turn to see what happened.",
    body: "Trace Theater opens with the policy snapshot, retrieval evidence, and tool calls.",
  },
  {
    id: "fork-from-turn",
    step: 3,
    title: "Fork from a turn to test a change.",
    body: "Forking creates a draft branch with the turn as the seed. Promote when evals pass.",
  },
];

/** §33.4 — first-week nudges. At most one per day. */
export const FIRST_WEEK_NUDGES = [
  "run eval suite",
  "connect tool",
  "add KB",
  "inspect cost",
  "invite reviewer",
] as const;

export type FirstWeekNudge = (typeof FIRST_WEEK_NUDGES)[number];

export interface WeeklyRecap {
  weekOf: string; // ISO date of week start
  promotions: number;
  rollbacks: number;
  evalsSaved: number;
  kbSourcesUpdated: number;
  costDeltaPercent: number; // positive => up, negative => down
  latencyDeltaPercent: number;
}

/** Returns the canonical recap line per §33.5. */
export function formatWeeklyRecap(recap: WeeklyRecap): string {
  const cost = formatDelta(recap.costDeltaPercent);
  const latency =
    recap.latencyDeltaPercent === 0
      ? "latency unchanged"
      : `latency ${formatDelta(recap.latencyDeltaPercent)}`;
  return `This week: ${recap.promotions} promotions, ${recap.rollbacks} rollbacks, ${recap.evalsSaved} evals saved, ${recap.kbSourcesUpdated} KB sources updated. Cost ${cost}, ${latency}.`;
}

function formatDelta(value: number): string {
  if (value === 0) return "unchanged";
  const sign = value > 0 ? "+" : "-";
  return `${sign}${Math.abs(value)}%`;
}

export const FIRST_QUARTER_HYGIENE = [
  "workspace hygiene",
  "stale tools",
  "untested agents",
  "expensive agents",
  "missing owners",
  "old knowledge sources",
  "eval gaps",
] as const;

/**
 * §33.7 — Concierge from real data.
 *
 * Reads a sample of recent conversations only after explicit consent and
 * surfaces the exact data scope so the user can revoke. The result includes
 * a recommended safe first improvement.
 */
export interface ConciergeConsent {
  acceptedAt: string; // ISO timestamp
  conversationsRequested: number;
  scopes: readonly ConciergeScope[];
  reviewer: string;
}

export type ConciergeScope =
  | "transcripts"
  | "tool-calls"
  | "kb-citations"
  | "user-feedback";

export interface ConciergeRecommendations {
  starterEvalIds: string[];
  kbHoles: string[];
  scenes: string[];
  riskyTools: string[];
  safeFirstImprovement: string;
}

export interface ConciergeRequest {
  scopes: readonly ConciergeScope[];
  conversationsRequested: number;
  reviewer: string;
  consentAcceptedAt: string;
}

export interface ConciergeResult {
  consent: ConciergeConsent;
  recommendations: ConciergeRecommendations;
}

export class ConciergeConsentError extends Error {}

/**
 * Run the concierge with explicit consent. Throws if scopes is empty or
 * conversationsRequested is outside the safe range — the caller cannot
 * implicitly read all data.
 */
export function runConcierge(req: ConciergeRequest): ConciergeResult {
  if (req.scopes.length === 0) {
    throw new ConciergeConsentError(
      "Concierge requires at least one explicit data scope.",
    );
  }
  if (req.conversationsRequested < 5 || req.conversationsRequested > 50) {
    throw new ConciergeConsentError(
      "Concierge sample must be between 5 and 50 conversations.",
    );
  }
  if (!req.reviewer.trim()) {
    throw new ConciergeConsentError(
      "Concierge consent requires a named reviewer for the audit log.",
    );
  }
  return {
    consent: {
      acceptedAt: req.consentAcceptedAt,
      conversationsRequested: req.conversationsRequested,
      scopes: req.scopes,
      reviewer: req.reviewer,
    },
    recommendations: {
      starterEvalIds: ["eval_handoff_clarity", "eval_refund_policy"],
      kbHoles: [
        "Refund policy after 90 days",
        "Tier-2 escalation routing rules",
      ],
      scenes: ["angry-customer-refund", "unknown-product-question"],
      riskyTools: ["create_refund", "send_email_external"],
      safeFirstImprovement:
        "Add a guarded 'Refund > $200' approval rail before touching billing tools.",
    },
  };
}
