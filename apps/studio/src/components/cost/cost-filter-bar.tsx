"use client";

import type { CostFilters } from "@/lib/costs";

interface Props {
  filters: CostFilters;
  agents: { id: string; name: string }[];
  channels: string[];
  models: string[];
  onChange: (f: CostFilters) => void;
  onReset: () => void;
}

const labelCls = "block text-xs font-medium text-muted-foreground mb-1";
const selectCls =
  "w-full rounded-md border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const inputCls =
  "w-full rounded-md border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export function CostFilterBar({
  filters,
  agents,
  channels,
  models,
  onChange,
  onReset,
}: Props): JSX.Element {
  function set<K extends keyof CostFilters>(key: K, value: CostFilters[K]) {
    onChange({ ...filters, [key]: value });
  }

  const hasActive = Object.values(filters).some(Boolean);

  return (
    <div
      data-testid="cost-filter-bar"
      className="flex flex-wrap items-end gap-3 rounded-lg border bg-card p-3"
    >
      {/* Agent filter */}
      <div className="min-w-[160px] flex-1">
        <label htmlFor="cf-agent" className={labelCls}>
          Agent
        </label>
        <select
          id="cf-agent"
          data-testid="filter-agent"
          className={selectCls}
          value={filters.agent_id}
          onChange={(e) => set("agent_id", e.target.value)}
        >
          <option value="">All agents</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      {/* Channel filter */}
      <div className="min-w-[140px] flex-1">
        <label htmlFor="cf-channel" className={labelCls}>
          Channel
        </label>
        <select
          id="cf-channel"
          data-testid="filter-channel"
          className={selectCls}
          value={filters.channel}
          onChange={(e) => set("channel", e.target.value)}
        >
          <option value="">All channels</option>
          {channels.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Model filter */}
      <div className="min-w-[160px] flex-1">
        <label htmlFor="cf-model" className={labelCls}>
          Model
        </label>
        <select
          id="cf-model"
          data-testid="filter-model"
          className={selectCls}
          value={filters.model}
          onChange={(e) => set("model", e.target.value)}
        >
          <option value="">All models</option>
          {models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* Date-from filter */}
      <div className="min-w-[140px] flex-1">
        <label htmlFor="cf-date-from" className={labelCls}>
          From
        </label>
        <input
          id="cf-date-from"
          data-testid="filter-date-from"
          type="date"
          className={inputCls}
          value={filters.date_from}
          onChange={(e) => set("date_from", e.target.value)}
        />
      </div>

      {/* Date-to filter */}
      <div className="min-w-[140px] flex-1">
        <label htmlFor="cf-date-to" className={labelCls}>
          To
        </label>
        <input
          id="cf-date-to"
          data-testid="filter-date-to"
          type="date"
          className={inputCls}
          value={filters.date_to}
          onChange={(e) => set("date_to", e.target.value)}
        />
      </div>

      {/* Reset */}
      {hasActive ? (
        <button
          data-testid="filter-reset"
          type="button"
          onClick={onReset}
          className="self-end rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          Reset
        </button>
      ) : null}
    </div>
  );
}
