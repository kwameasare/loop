/**
 * Time-travel safety model (UX304).
 *
 * Backs three pre-promote / post-promote surfaces from canonical
 * §19.7–§19.9 and §23.5:
 *
 * - "What Could Break" — the top likely behavior changes vs. production.
 * - Regression bisect — old/new replay diffs with bisected commit and
 *   per-bisect confidence.
 * - Snapshots — signed, branchable point-in-time captures usable for
 *   incident, demo, or audit replay.
 *
 * The cp-api adapter will replace fixtures; the UI is a pure consumer.
 */

// ---------------------------------------------------------------------------
// What Could Break
// ---------------------------------------------------------------------------

export type LikelihoodTier = "high" | "medium" | "low";

export interface BehaviorChange {
  id: string;
  surface: string;
  summary: string;
  exemplarTranscriptId: string;
  oldBehavior: string;
  newBehavior: string;
  likelihood: LikelihoodTier;
  /** 0..100 — confidence that this change will surface in production. */
  confidence: number;
  evidenceRef: string;
}

const TIER_RANK: Record<LikelihoodTier, number> = {
  high: 3,
  medium: 2,
  low: 1,
};

export function topLikelyChanges(
  changes: readonly BehaviorChange[],
  k = 5,
): readonly BehaviorChange[] {
  return [...changes]
    .sort((a, b) => {
      const r = TIER_RANK[b.likelihood] - TIER_RANK[a.likelihood];
      return r !== 0 ? r : b.confidence - a.confidence;
    })
    .slice(0, k);
}

// ---------------------------------------------------------------------------
// Regression bisect
// ---------------------------------------------------------------------------

export type BisectStatus = "pass" | "regress" | "skip";

export interface BisectStep {
  commit: string;
  ts: string;
  status: BisectStatus;
  summary: string;
  evidenceRef: string;
}

export interface BisectResult {
  caseId: string;
  transcript: string;
  expected: string;
  observed: string;
  /** SHA of the commit identified as introducing the regression. */
  culpritCommit: string;
  /** 0..100 — confidence that the culprit is correct. */
  confidence: number;
  steps: readonly BisectStep[];
}

export function bisectStepsBetween(
  steps: readonly BisectStep[],
  startCommit: string,
  endCommit: string,
): readonly BisectStep[] {
  const startIdx = steps.findIndex((s) => s.commit === startCommit);
  const endIdx = steps.findIndex((s) => s.commit === endCommit);
  if (startIdx === -1 || endIdx === -1) return [];
  const lo = Math.min(startIdx, endIdx);
  const hi = Math.max(startIdx, endIdx);
  return steps.slice(lo, hi + 1);
}

// ---------------------------------------------------------------------------
// Snapshots
// ---------------------------------------------------------------------------

export type SnapshotPurpose = "incident" | "demo" | "audit" | "general";

export interface Snapshot {
  id: string;
  label: string;
  takenAt: string;
  /** SHA256 of the snapshot bundle. */
  sha256: string;
  /** Detached signature value over `sha256` by the signing key alias. */
  signature: string;
  /** KMS key alias that signed the snapshot. */
  signingKey: string;
  purpose: SnapshotPurpose;
  branchedFrom?: string;
  evidenceRef: string;
}

export class SnapshotSignatureError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SnapshotSignatureError";
  }
}

/**
 * Fixture-grade signature verifier. Real verification will resolve
 * `signingKey` against KMS and verify `signature` over `sha256`. For
 * the studio fixture the signature must be `"sig:" + sha256` and the
 * signing key alias must be non-empty.
 */
export function verifySnapshotSignature(snap: Snapshot): boolean {
  return (
    !!snap.signingKey &&
    snap.signature === `sig:${snap.sha256}`
  );
}

/** Throws if the signature does not verify. */
export function assertSnapshotSignature(snap: Snapshot): void {
  if (!verifySnapshotSignature(snap)) {
    throw new SnapshotSignatureError(
      `Snapshot ${snap.id} signature does not verify against ${snap.signingKey}.`,
    );
  }
}

export interface SnapshotBranch {
  id: string;
  parent: string;
  createdAt: string;
  purpose: SnapshotPurpose;
  evidenceRef: string;
}

export function branchSnapshot(
  source: Snapshot,
  opts: { id: string; createdAt: string; purpose: SnapshotPurpose; evidenceRef: string },
): SnapshotBranch {
  assertSnapshotSignature(source);
  return {
    id: opts.id,
    parent: source.id,
    createdAt: opts.createdAt,
    purpose: opts.purpose,
    evidenceRef: opts.evidenceRef,
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

export const FIXTURE_BEHAVIOR_CHANGES: readonly BehaviorChange[] = [
  {
    id: "bc_1",
    surface: "flow.refund.escalate",
    summary: "Escalation now offers a callback option before transferring to operator.",
    exemplarTranscriptId: "tr_001",
    oldBehavior: "Transfers to operator immediately.",
    newBehavior: "Offers callback; transfers if declined.",
    likelihood: "high",
    confidence: 88,
    evidenceRef: "audit/wcb/bc_1",
  },
  {
    id: "bc_2",
    surface: "flow.refund.completed",
    summary: "Completion message references new return-window policy.",
    exemplarTranscriptId: "tr_014",
    oldBehavior: "States 30-day return window.",
    newBehavior: "States 14-day return window with reason link.",
    likelihood: "high",
    confidence: 81,
    evidenceRef: "audit/wcb/bc_2",
  },
  {
    id: "bc_3",
    surface: "flow.refund.askReason",
    summary: "Reason prompt re-ordered to ask account email first.",
    exemplarTranscriptId: "tr_022",
    oldBehavior: "Asks order id, then email.",
    newBehavior: "Asks email, then order id.",
    likelihood: "medium",
    confidence: 64,
    evidenceRef: "audit/wcb/bc_3",
  },
  {
    id: "bc_4",
    surface: "tool.shopify.read",
    summary: "Retry on 502 reduced from 2 → 1.",
    exemplarTranscriptId: "tr_031",
    oldBehavior: "Retries up to 2 times on 502.",
    newBehavior: "Retries once on 502.",
    likelihood: "medium",
    confidence: 57,
    evidenceRef: "audit/wcb/bc_4",
  },
  {
    id: "bc_5",
    surface: "kb.escalation",
    summary: "New chunk added covering carrier delays.",
    exemplarTranscriptId: "tr_044",
    oldBehavior: "Generic escalation copy.",
    newBehavior: "Carrier-specific escalation copy.",
    likelihood: "low",
    confidence: 41,
    evidenceRef: "audit/wcb/bc_5",
  },
];

export const FIXTURE_BISECT: BisectResult = {
  caseId: "bs_001",
  transcript: "Refund of $250 on order 88412 — over policy ceiling.",
  expected: "flow.refund.escalate",
  observed: "flow.refund.completed",
  culpritCommit: "9a3f1b2",
  confidence: 92,
  steps: [
    {
      commit: "1a2b3c4",
      ts: "2025-02-19T08:00:00Z",
      status: "pass",
      summary: "Baseline production.",
      evidenceRef: "audit/bisect/1a2b3c4",
    },
    {
      commit: "5e6f7a8",
      ts: "2025-02-20T11:21:00Z",
      status: "pass",
      summary: "KB chunk added — no behavior delta.",
      evidenceRef: "audit/bisect/5e6f7a8",
    },
    {
      commit: "9a3f1b2",
      ts: "2025-02-21T07:42:00Z",
      status: "regress",
      summary: "Refund-ceiling guard refactored — culprit.",
      evidenceRef: "audit/bisect/9a3f1b2",
    },
    {
      commit: "c4d5e6f",
      ts: "2025-02-21T09:11:00Z",
      status: "regress",
      summary: "Confirms regression on follow-up replay.",
      evidenceRef: "audit/bisect/c4d5e6f",
    },
  ],
};

const SHA_PROD = "sha256:" + "f".repeat(63) + "1";
const SHA_PRE = "sha256:" + "e".repeat(63) + "2";
const SHA_INC = "sha256:" + "d".repeat(63) + "3";

export const FIXTURE_SNAPSHOTS: readonly Snapshot[] = [
  {
    id: "snap_prod_2025_02_21",
    label: "Production · 2025-02-21 09:00 UTC",
    takenAt: "2025-02-21T09:00:00Z",
    sha256: SHA_PROD,
    signature: `sig:${SHA_PROD}`,
    signingKey: "kms/snapshot-signer",
    purpose: "general",
    evidenceRef: "audit/snapshot/snap_prod_2025_02_21",
  },
  {
    id: "snap_pre_promote",
    label: "Pre-promote · refunds-bot v34",
    takenAt: "2025-02-21T09:14:00Z",
    sha256: SHA_PRE,
    signature: `sig:${SHA_PRE}`,
    signingKey: "kms/snapshot-signer",
    purpose: "audit",
    evidenceRef: "audit/snapshot/snap_pre_promote",
  },
  {
    id: "snap_incident_drill",
    label: "Incident drill · over-refund",
    takenAt: "2025-02-21T09:30:00Z",
    sha256: SHA_INC,
    signature: `sig:${SHA_INC}`,
    signingKey: "kms/snapshot-signer",
    purpose: "incident",
    branchedFrom: "snap_prod_2025_02_21",
    evidenceRef: "audit/snapshot/snap_incident_drill",
  },
];
