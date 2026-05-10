import {
  ConfidenceMeter,
  EvidenceCallout,
  MetricCountUp,
  StatePanel,
} from "@/components/target";
import { ImportWizard } from "./import-wizard";
import { MigrationEntry } from "./migration-entry";
import { SourceGrid } from "./source-grid";
import { ThreePaneReview } from "./three-pane-review";
import {
  EMPTY_MIGRATION_READINESS,
  countReviewItemsBySeverity,
  type MigrationReadiness,
  type ReviewItem,
} from "@/lib/migration";
import type { ReactNode } from "react";

export interface MigrationScreenProps {
  /**
   * Optional override used by routes, tests, and stories. The component's
   * default is intentionally empty so it never implies an import happened.
   */
  className?: string;
  readiness?: MigrationReadiness;
  reviewItems?: readonly ReviewItem[];
  migrationRunsSlot?: ReactNode;
}

/**
 * Migration Atelier composite surface (canonical §18.1-§18.4). Composes the
 * entry choices, supported sources grid, the import wizard, and the
 * three-pane review using only shared target primitives — no local badges,
 * confidence meters, or risk halos are rebuilt here.
 */
export function MigrationScreen({
  className,
  readiness = EMPTY_MIGRATION_READINESS,
  reviewItems = [],
  migrationRunsSlot,
}: MigrationScreenProps) {
  const severityCounts = countReviewItemsBySeverity(reviewItems);
  const hasMigrationEvidence =
    reviewItems.length > 0 || readiness.parityTotal > 0;
  const blockingPath =
    !hasMigrationEvidence
      ? "Start or select an import to load lineage, parity, and review evidence."
      : severityCounts.blocking > 0
      ? "Resolve blocking decisions before staging cutover."
      : "No blocking decisions outstanding. Cutover preflight unlocked.";

  return (
    <main
      className={`mx-auto flex w-full max-w-7xl flex-col gap-8 p-4 lg:p-6 ${className ?? ""}`}
      data-testid="migration-screen"
    >
      <header className="flex flex-col gap-3 border-b pb-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Migrate · Atelier
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Bring your agent in with parity proof and a rollback route.
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Migration is a first-class entry into Loop Studio. Every supported
          source advertises whether its importer is verified, planned, or
          aspirational. Import never ends with &ldquo;done&rdquo; — it ends with
          parity measured, deploy gated, and rollback armed.
        </p>
      </header>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCountUp
          label="Migration readiness"
          value={readiness.overallScore}
          suffix="%"
          delta={`${readiness.parityPassing}/${readiness.parityTotal} parity tests passing`}
        />
        <MetricCountUp
          label="Cleanly imported"
          value={readiness.cleanlyImported}
          delta={`${readiness.needsReview} need review`}
        />
        <MetricCountUp
          label="Secrets to reconnect"
          value={readiness.secretsToReconnect}
          delta="Vault-backed; never sent to studio"
        />
        <MetricCountUp
          label="Unsupported items"
          value={readiness.unsupported}
          delta="Marked intentionally and tracked in lineage"
        />
      </section>

      <StatePanel
        state={
          !hasMigrationEvidence
            ? "empty"
            : severityCounts.blocking > 0
              ? "degraded"
              : "success"
        }
        title={
          !hasMigrationEvidence
            ? "No migration evidence loaded"
            : severityCounts.blocking > 0
            ? `Promotion blocked by ${severityCounts.blocking} decision${
                severityCounts.blocking === 1 ? "" : "s"
              }`
            : "Parity gates clear"
        }
        action={
          <ConfidenceMeter
            value={readiness.overallScore}
            label="Overall readiness"
          />
        }
      >
        {blockingPath} Advisory: {severityCounts.advisory}, FYI:{" "}
        {severityCounts.fyi}.
      </StatePanel>

      <MigrationEntry />

      <SourceGrid />

      {migrationRunsSlot}

      <ImportWizard />

      <EvidenceCallout
        title="Lineage stays after cutover"
        tone="info"
        source="Canonical §18.11"
      >
        Original archive, parsed inventory, mapping decisions, parity runs,
        cutover events, and rollback plan remain available for at least the
        retention window so any decision is auditable months later.
      </EvidenceCallout>

      <ThreePaneReview items={reviewItems} />
    </main>
  );
}
