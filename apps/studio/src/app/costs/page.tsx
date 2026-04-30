import { CostDashboard } from "@/components/cost/cost-dashboard";
import {
  FIXTURE_NOW_MS,
  FIXTURE_USAGE,
  FIXTURE_WORKSPACE_ID,
  monthBoundsUTC,
} from "@/lib/costs";

export const dynamic = "force-dynamic";

export default function CostsPage(): JSX.Element {
  const { period_start_ms, period_end_ms } = monthBoundsUTC(FIXTURE_NOW_MS);
  return (
    <CostDashboard
      records={FIXTURE_USAGE}
      workspace_id={FIXTURE_WORKSPACE_ID}
      period_start_ms={period_start_ms}
      period_end_ms={period_end_ms}
    />
  );
}
