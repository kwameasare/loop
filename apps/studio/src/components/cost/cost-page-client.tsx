"use client";

import { useMemo } from "react";

import { CostCapacityPanel } from "@/components/cost/cost-capacity-panel";
import { CostDashboard } from "@/components/cost/cost-dashboard";
import { CostFilterBar } from "@/components/cost/cost-filter-bar";
import { CostTimeSeriesChart } from "@/components/cost/cost-time-series-chart";
import { WorkspaceKpiCards } from "@/components/cost/workspace-kpi-cards";
import { thirtyDayWindowUTC } from "@/lib/cost-series";
import {
  computeWorkspaceKpis,
  buildCostCapacityModel,
  filterRecords,
  monthBoundsUTC,
  type UsageRecord,
} from "@/lib/costs";
import { buildLatencyBudgetModel } from "@/lib/latency";
import { useCostFilters } from "@/lib/use-cost-filters";

interface Props {
  records: UsageRecord[];
  workspace_id: string;
  now_ms: number;
}

/**
 * S285: Client shell for the costs page.
 *
 * Owns the filter state (URL-synced + localStorage-persisted via useCostFilters)
 * and passes the filtered record set down to all sub-components.
 */
export function CostPageClient({
  records,
  workspace_id,
  now_ms,
}: Props): JSX.Element {
  const { filters, setFilters, resetFilters } = useCostFilters();

  // Derive option lists from the unfiltered record set
  const agents = useMemo(() => {
    const seen = new Map<string, string>();
    for (const r of records) seen.set(r.agent_id, r.agent_name);
    return [...seen.entries()].map(([id, name]) => ({ id, name }));
  }, [records]);

  const channels = useMemo(() => {
    const seen = new Set<string>();
    for (const r of records) if (r.channel) seen.add(r.channel);
    return [...seen].sort();
  }, [records]);

  const models = useMemo(() => {
    const seen = new Set<string>();
    for (const r of records) if (r.model) seen.add(r.model);
    return [...seen].sort();
  }, [records]);

  const filtered = useMemo(
    () => filterRecords(records, filters),
    [records, filters],
  );

  const { period_start_ms, period_end_ms } = monthBoundsUTC(now_ms);
  const kpis = computeWorkspaceKpis(filtered, {
    workspace_id,
    now_ms,
  });
  const window = thirtyDayWindowUTC(now_ms);
  const costCapacity = useMemo(
    () =>
      buildCostCapacityModel(filtered, {
        workspace_id,
        now_ms,
      }),
    [filtered, now_ms, workspace_id],
  );
  const latencyBudget = useMemo(() => buildLatencyBudgetModel(800), []);

  return (
    <div className="flex flex-col gap-6 p-6" data-testid="costs-page">
      <CostFilterBar
        filters={filters}
        agents={agents}
        channels={channels}
        models={models}
        onChange={setFilters}
        onReset={resetFilters}
      />
      <WorkspaceKpiCards kpis={kpis} />
      <CostCapacityPanel model={costCapacity} latency={latencyBudget} />
      <CostTimeSeriesChart
        records={filtered}
        workspace_id={workspace_id}
        window_start_ms={window.window_start_ms}
        window_end_ms={window.window_end_ms}
      />
      <CostDashboard
        records={filtered}
        workspace_id={workspace_id}
        period_start_ms={period_start_ms}
        period_end_ms={period_end_ms}
      />
    </div>
  );
}
