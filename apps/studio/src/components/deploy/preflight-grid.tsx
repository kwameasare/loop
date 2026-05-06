import { DiffRibbon } from "@/components/target/diff-ribbon";
import { RiskHalo } from "@/components/target/risk-halo";
import { cn } from "@/lib/utils";
import {
  type PreflightDiff,
  type PreflightSeverity,
  PREFLIGHT_DIFFS,
  diffBySeverity,
} from "@/lib/deploy-flight";

const SEVERITY_BADGE: Record<PreflightSeverity, string> = {
  info: "border-border bg-muted text-muted-foreground",
  advisory: "border-info bg-info/10 text-info",
  high: "border-warning bg-warning/10 text-warning",
  blocking: "border-destructive bg-destructive/10 text-destructive",
};

const SEVERITY_TO_RISK: Record<PreflightSeverity, "low" | "medium" | "high"> = {
  info: "low",
  advisory: "low",
  high: "medium",
  blocking: "high",
};

const DIMENSION_LABEL: Record<PreflightDiff["dimension"], string> = {
  behavior: "Behavior diff",
  tool: "Tool diff",
  knowledge: "Knowledge diff",
  memory: "Memory policy diff",
  channel: "Channel diff",
  budget: "Budget diff",
};

export interface PreflightGridProps {
  diffs?: ReadonlyArray<PreflightDiff>;
}

export function PreflightGrid({ diffs = PREFLIGHT_DIFFS }: PreflightGridProps) {
  const counts = diffBySeverity(diffs);
  return (
    <section className="space-y-3" data-testid="preflight-grid">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Preflight diffs</h2>
        <p className="text-xs text-muted-foreground">
          {counts.high + counts.blocking} risk · {counts.advisory} advisory ·{" "}
          {counts.info} info
        </p>
      </header>
      <ul
        className="grid gap-3 lg:grid-cols-2"
        data-testid="preflight-grid-list"
      >
        {diffs.map((d) => (
          <li key={d.dimension} data-testid={`preflight-${d.dimension}`}>
            <RiskHalo level={SEVERITY_TO_RISK[d.severity]}>
              <div className="space-y-2 p-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {DIMENSION_LABEL[d.dimension]}
                  </span>
                  <span
                    className={cn(
                      "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium",
                      SEVERITY_BADGE[d.severity],
                    )}
                    data-testid={`preflight-severity-${d.dimension}`}
                  >
                    {d.severity}
                  </span>
                </div>
                <DiffRibbon
                  label={DIMENSION_LABEL[d.dimension]}
                  before={d.before}
                  after={d.after}
                  impact={d.impact}
                />
                <p
                  className="font-mono text-[11px] text-muted-foreground"
                  data-testid={`preflight-evidence-${d.dimension}`}
                >
                  evidence · {d.evidenceRef}
                </p>
              </div>
            </RiskHalo>
          </li>
        ))}
      </ul>
    </section>
  );
}
