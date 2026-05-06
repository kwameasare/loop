/**
 * UX407 — Target UX quality bar dashboard.
 *
 * Section 37 + 39 + 42 of the canonical target UX standard.
 *
 * Tracks the seven quality bar categories per screen:
 *   Clarity, Control, Precision, Friendliness,
 *   Enterprise Readiness, Craft, Delight.
 *
 * Each failing category links back to the canonical standard evidence
 * (anchor + summary). A screen fails north-star quality if it fails
 * more than one category (§37.7).
 */

export const QUALITY_CATEGORIES = [
  "clarity",
  "control",
  "precision",
  "friendliness",
  "enterprise-readiness",
  "craft",
  "delight",
] as const;

export type QualityCategory = (typeof QUALITY_CATEGORIES)[number];

export const QUALITY_CATEGORY_LABELS: Record<QualityCategory, string> = {
  clarity: "Clarity",
  control: "Control",
  precision: "Precision",
  friendliness: "Friendliness",
  "enterprise-readiness": "Enterprise readiness",
  craft: "Craft",
  delight: "Delight",
};

/** Anchor in the canonical standard for each category. */
export const QUALITY_CATEGORY_ANCHORS: Record<QualityCategory, string> = {
  clarity: "§37.1",
  control: "§37.2",
  precision: "§37.3",
  friendliness: "§37.4",
  "enterprise-readiness": "§37.5",
  craft: "§37.6",
  delight: "§37.7",
};

export interface QualityChecklistItem {
  id: string;
  category: QualityCategory;
  prompt: string;
}

/** Canonical checklist drawn from §37.1–§37.7 of the standard. */
export const QUALITY_CHECKLIST: readonly QualityChecklistItem[] = [
  // Clarity
  { id: "cl-job", category: "clarity", prompt: "One primary job is named and obvious." },
  { id: "cl-object", category: "clarity", prompt: "Object or workflow has a clear name." },
  { id: "cl-action", category: "clarity", prompt: "Primary action is unmistakable." },
  { id: "cl-env", category: "clarity", prompt: "Environment/version visible when relevant." },
  { id: "cl-states", category: "clarity", prompt: "Empty, loading, error, and degraded states are designed." },
  // Control
  { id: "co-preview", category: "control", prompt: "High-impact changes have preview." },
  { id: "co-diff", category: "control", prompt: "Diff from production is visible." },
  { id: "co-undo", category: "control", prompt: "Non-production edits offer undo/recovery." },
  { id: "co-rollback", category: "control", prompt: "Production has a rollback path." },
  { id: "co-disabled", category: "control", prompt: "Disabled actions explain why." },
  // Precision
  { id: "pr-units", category: "precision", prompt: "Numbers include units." },
  { id: "pr-status", category: "precision", prompt: "Status labels are specific, not vague." },
  { id: "pr-evidence", category: "precision", prompt: "Health scores drill down to evidence." },
  { id: "pr-cite", category: "precision", prompt: "AI summaries cite sources." },
  { id: "pr-ops", category: "precision", prompt: "Operational tables sort/filter/export." },
  // Friendliness
  { id: "fr-next", category: "friendliness", prompt: "Next useful action is present." },
  { id: "fr-examples", category: "friendliness", prompt: "Examples are available." },
  { id: "fr-errors", category: "friendliness", prompt: "Errors say what failed and what to do." },
  { id: "fr-defaults", category: "friendliness", prompt: "Forms have tested defaults." },
  { id: "fr-stages", category: "friendliness", prompt: "Long workflows show named stages." },
  // Enterprise readiness
  { id: "er-audit", category: "enterprise-readiness", prompt: "Audit-relevant actions are recorded." },
  { id: "er-secrets", category: "enterprise-readiness", prompt: "Secret boundaries are visible." },
  { id: "er-approvals", category: "enterprise-readiness", prompt: "Approvals visible before block." },
  { id: "er-policy", category: "enterprise-readiness", prompt: "Policy violations name policy and owner." },
  { id: "er-export", category: "enterprise-readiness", prompt: "Evidence is exportable." },
  // Craft
  { id: "cr-stable", category: "craft", prompt: "Layout stable under long values." },
  { id: "cr-truncate", category: "craft", prompt: "No critical truncation without access." },
  { id: "cr-keyboard", category: "craft", prompt: "Keyboard reachable end-to-end." },
  { id: "cr-density", category: "craft", prompt: "Density controls available for tables." },
  { id: "cr-emphasis", category: "craft", prompt: "Visual emphasis maps to risk." },
  // Delight
  { id: "de-responsive", category: "delight", prompt: "At least one pleasant responsiveness moment." },
  { id: "de-progress", category: "delight", prompt: "Progress visible for operations over 1s." },
  { id: "de-success", category: "delight", prompt: "Success satisfying but not noisy." },
  { id: "de-motion", category: "delight", prompt: "Motion clarifies cause/effect." },
  { id: "de-reduced", category: "delight", prompt: "Reduced-motion path equally understandable." },
];

export interface ScreenQualityCategoryResult {
  category: QualityCategory;
  /** Item ids that pass. */
  passed: string[];
  /** Item ids that fail. */
  failed: string[];
  /** Free-text evidence link to standard anchor or related artifact. */
  evidence: string;
}

export interface ScreenQualityReport {
  screen: string; // e.g., /agents/{id}/workbench
  area: string; // e.g., Workbench, Trace, Eval
  ownerAgent: string;
  reviewedAt: string; // ISO date
  reviewer: string;
  results: ScreenQualityCategoryResult[];
  notes?: string;
}

export interface ScreenQualityScore {
  /** Categories that fully pass (no failed items). */
  passing: QualityCategory[];
  /** Categories that have at least one failed item. */
  failing: QualityCategory[];
  /** True iff at most one category fails (§37.7 north-star). */
  meetsNorthStar: boolean;
  /** 0..1 share of total checklist items that pass. */
  ratio: number;
  totalItems: number;
  passedItems: number;
}

export function scoreScreen(report: ScreenQualityReport): ScreenQualityScore {
  const passing: QualityCategory[] = [];
  const failing: QualityCategory[] = [];
  let total = 0;
  let passed = 0;
  for (const r of report.results) {
    total += r.passed.length + r.failed.length;
    passed += r.passed.length;
    if (r.failed.length === 0) passing.push(r.category);
    else failing.push(r.category);
  }
  return {
    passing,
    failing,
    meetsNorthStar: failing.length <= 1,
    ratio: total === 0 ? 0 : passed / total,
    totalItems: total,
    passedItems: passed,
  };
}

export interface QualityRollup {
  totalScreens: number;
  meetingNorthStar: number;
  failingByCategory: Record<QualityCategory, number>;
  reviewerCoverage: Record<string, number>;
}

export function rollupReports(
  reports: readonly ScreenQualityReport[],
): QualityRollup {
  const failingByCategory = Object.fromEntries(
    QUALITY_CATEGORIES.map((c) => [c, 0]),
  ) as Record<QualityCategory, number>;
  const reviewerCoverage: Record<string, number> = {};
  let meeting = 0;
  for (const rep of reports) {
    const score = scoreScreen(rep);
    if (score.meetsNorthStar) meeting += 1;
    for (const cat of score.failing) {
      failingByCategory[cat] += 1;
    }
    reviewerCoverage[rep.reviewer] = (reviewerCoverage[rep.reviewer] ?? 0) + 1;
  }
  return {
    totalScreens: reports.length,
    meetingNorthStar: meeting,
    failingByCategory,
    reviewerCoverage,
  };
}

/** Build an empty review with all checklist items marked failed. */
export function blankReview(
  screen: string,
  reviewer: string,
  reviewedAt: string,
  area = "",
  ownerAgent = "",
): ScreenQualityReport {
  const byCat = new Map<QualityCategory, string[]>();
  for (const item of QUALITY_CHECKLIST) {
    const list = byCat.get(item.category) ?? [];
    list.push(item.id);
    byCat.set(item.category, list);
  }
  return {
    screen,
    area,
    ownerAgent,
    reviewer,
    reviewedAt,
    results: QUALITY_CATEGORIES.map((cat) => ({
      category: cat,
      passed: [],
      failed: byCat.get(cat) ?? [],
      evidence: QUALITY_CATEGORY_ANCHORS[cat],
    })),
  };
}

/** Toggle a single checklist item between passed and failed. */
export function toggleChecklistItem(
  report: ScreenQualityReport,
  itemId: string,
): ScreenQualityReport {
  const item = QUALITY_CHECKLIST.find((i) => i.id === itemId);
  if (!item) return report;
  return {
    ...report,
    results: report.results.map((r) => {
      if (r.category !== item.category) return r;
      const wasPassed = r.passed.includes(itemId);
      return {
        ...r,
        passed: wasPassed ? r.passed.filter((x) => x !== itemId) : [...r.passed, itemId],
        failed: wasPassed ? [...r.failed, itemId] : r.failed.filter((x) => x !== itemId),
      };
    }),
  };
}

/** Sample reports — used by the dashboard until real telemetry is wired. */
export const SAMPLE_QUALITY_REPORTS: readonly ScreenQualityReport[] = [
  {
    screen: "/agents/[id]/workbench",
    area: "Workbench",
    ownerAgent: "support_triage",
    reviewer: "ux-thor",
    reviewedAt: "2026-05-04",
    results: QUALITY_CATEGORIES.map((cat) => ({
      category: cat,
      passed: QUALITY_CHECKLIST.filter((i) => i.category === cat).map((i) => i.id),
      failed: [],
      evidence: QUALITY_CATEGORY_ANCHORS[cat],
    })),
  },
  {
    screen: "/traces/[id]",
    area: "Trace Theater",
    ownerAgent: "support_triage",
    reviewer: "ux-thor",
    reviewedAt: "2026-05-05",
    results: [
      {
        category: "clarity",
        passed: ["cl-job", "cl-object", "cl-action", "cl-env", "cl-states"],
        failed: [],
        evidence: "§37.1",
      },
      {
        category: "control",
        passed: ["co-preview", "co-diff", "co-undo", "co-rollback", "co-disabled"],
        failed: [],
        evidence: "§37.2",
      },
      {
        category: "precision",
        passed: ["pr-units", "pr-status", "pr-evidence", "pr-ops"],
        failed: ["pr-cite"],
        evidence: "§37.3 — AI summary on Trace cites span ID but not source policy snapshot.",
      },
      {
        category: "friendliness",
        passed: ["fr-next", "fr-examples", "fr-errors", "fr-defaults", "fr-stages"],
        failed: [],
        evidence: "§37.4",
      },
      {
        category: "enterprise-readiness",
        passed: ["er-audit", "er-secrets", "er-approvals", "er-policy", "er-export"],
        failed: [],
        evidence: "§37.5",
      },
      {
        category: "craft",
        passed: ["cr-stable", "cr-truncate", "cr-keyboard", "cr-density", "cr-emphasis"],
        failed: [],
        evidence: "§37.6",
      },
      {
        category: "delight",
        passed: ["de-responsive", "de-progress", "de-success", "de-motion", "de-reduced"],
        failed: [],
        evidence: "§37.7",
      },
    ],
  },
  {
    screen: "/migrate/[id]",
    area: "Migration Atelier",
    ownerAgent: "import_botpress_acme",
    reviewer: "ux-orion",
    reviewedAt: "2026-05-03",
    results: [
      {
        category: "clarity",
        passed: ["cl-object", "cl-action", "cl-env"],
        failed: ["cl-job", "cl-states"],
        evidence: "§37.1 — primary job ambiguous between import and parity audit; degraded state missing.",
      },
      {
        category: "control",
        passed: ["co-preview", "co-undo", "co-rollback", "co-disabled"],
        failed: ["co-diff"],
        evidence: "§37.2 — production diff hidden behind expandable.",
      },
      {
        category: "precision",
        passed: ["pr-units", "pr-status", "pr-evidence", "pr-cite", "pr-ops"],
        failed: [],
        evidence: "§37.3",
      },
      {
        category: "friendliness",
        passed: ["fr-next", "fr-examples", "fr-defaults", "fr-stages"],
        failed: ["fr-errors"],
        evidence: "§37.4 — error copy on parity drop says 'unknown error', no remediation.",
      },
      {
        category: "enterprise-readiness",
        passed: ["er-audit", "er-secrets", "er-policy", "er-export"],
        failed: ["er-approvals"],
        evidence: "§37.5 — cutover step does not surface required approvers.",
      },
      {
        category: "craft",
        passed: ["cr-stable", "cr-truncate", "cr-keyboard", "cr-density", "cr-emphasis"],
        failed: [],
        evidence: "§37.6",
      },
      {
        category: "delight",
        passed: ["de-responsive", "de-progress", "de-success", "de-motion", "de-reduced"],
        failed: [],
        evidence: "§37.7",
      },
    ],
    notes: "Below north-star threshold (§37.7): four categories failing. Triage required.",
  },
];
