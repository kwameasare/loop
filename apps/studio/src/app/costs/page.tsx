import { CostDashboard } from "@/components/cost/cost-dashboard";
import { CostTimeSeriesChart } from "@/components/cost/cost-time-series-chart";
import { WorkspaceKpiCards } from "@/components/cost/workspace-kpi-cards";
import { thirtyDayWindowUTC } from "@/lib/cost-series";
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
  const window = thirtyDayWindowUTC(FIXTURE_NOW_MS);
  return (
    <div className="flex flex-col gap-6 p-6" data-testid="costs-page">
      <WorkspaceKpiCards kpis={kpis} />
      <CostTimeSeriesChart
        records={FIXTURE_USAGE}
        workspace_id={FIXTURE_WORKSPACE_ID}
        window_start_ms={window.window_start_ms}
        window_end_ms={window.window_end_ms}
      />
      <CostDashboard
        records={FIXTURE_USAGE}
        workspace_id={FIXTURE_WORKSPACE_ID}
        period_start_ms={period_start_ms}
        period_end_ms={period_end_ms}
      />
    </div>
  );
}
