import { CostDashboard } from "@/components/cost/cost-dashboard";
import { WorkspaceKpiCards } from "@/components/cost/workspace-kpi-cards";
import {
  computeWorkspaceKpis,
  FIXTURE_NOW_MS,
  FIXTURE_USAGE,
  FIXTURE_WORKSPACE_ID,
  monthBoundsUTC,
} from "@/lib/costs";

export const dynamic = "force-dynamic";

export default function CostsPage(): JSX.Element {
  const { period_start_ms, period_end_ms } = monthBoundsUTC(FIXTURE_NOW_MS);
  const kpis = computeWorkspaceKpis(FIXTURE_USAGE, {
    workspace_id: FIXTURE_WORKSPACE_ID,
    now_ms: FIXTURE_NOW_MS,
  });
  return (
    <div className="flex flex-col gap-6 p-6" data-testid="costs-page">
      <WorkspaceKpiCards kpis={kpis} />
      <CostDashboard
        records={FIXTURE_USAGE}
        workspace_id={FIXTURE_WORKSPACE_ID}
        period_start_ms={period_start_ms}
        period_end_ms={period_end_ms}
      />
    </div>
  );
}
