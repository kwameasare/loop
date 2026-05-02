"use client";

import {
  formatDeltaPercent,
  formatUSD,
  type WorkspaceKpis,
} from "@/lib/costs";

export interface WorkspaceKpiCardsProps {
  kpis: WorkspaceKpis;
}

interface CardSpec {
  testid: string;
  label: string;
  amount_cents: number;
  delta_label: string;
  delta_value: string;
  caption?: string;
}

/**
 * The three workspace KPI cards rendered above the cost dashboard:
 * - Today (vs yesterday)
 * - Month-to-date (vs prior month at the same elapsed-day mark)
 * - Projected end-of-month (linear extrapolation of the MTD run-rate)
 *
 * Values match the ClickHouse query the control-plane evaluates so the
 * dashboard agrees with the API to the cent.
 */
export function WorkspaceKpiCards({ kpis }: WorkspaceKpiCardsProps) {
  // Compare MTD against the prior-month total scaled to the same
  // elapsed-day mark so the delta is apples-to-apples.
  const prior_mtd_equivalent = Math.round(
    (kpis.prev_month_cents / kpis.days_in_month) * kpis.days_elapsed,
  );

  const cards: CardSpec[] = [
    {
      testid: "kpi-today",
      label: "Today",
      amount_cents: kpis.today_cents,
      delta_label: "vs yesterday",
      delta_value: formatDeltaPercent(kpis.today_cents, kpis.yesterday_cents),
    },
    {
      testid: "kpi-mtd",
      label: "Month to date",
      amount_cents: kpis.mtd_cents,
      delta_label: "vs prior month (same days elapsed)",
      delta_value: formatDeltaPercent(kpis.mtd_cents, prior_mtd_equivalent),
      caption: `${kpis.days_elapsed} of ${kpis.days_in_month} days`,
    },
    {
      testid: "kpi-eom",
      label: "Projected EOM",
      amount_cents: kpis.projected_eom_cents,
      delta_label: "vs prior month total",
      delta_value: formatDeltaPercent(
        kpis.projected_eom_cents,
        kpis.prev_month_cents,
      ),
    },
  ];

  return (
    <section
      className="grid gap-4 md:grid-cols-3"
      data-testid="workspace-kpi-cards"
    >
      {cards.map((card) => {
        const isUp = card.delta_value.startsWith("+");
        const isDown = card.delta_value.startsWith("−");
        const tone = isUp
          ? "text-red-700"
          : isDown
            ? "text-emerald-700"
            : "text-muted-foreground";
        return (
          <article
            className="rounded-lg border p-5 shadow-sm"
            data-testid={card.testid}
            key={card.testid}
          >
            <p className="text-muted-foreground text-xs uppercase tracking-wider">
              {card.label}
            </p>
            <p
              className="mt-2 text-3xl font-semibold tabular-nums"
              data-testid={`${card.testid}-amount`}
            >
              {formatUSD(card.amount_cents)}
            </p>
            <p
              className={`mt-1 text-xs tabular-nums ${tone}`}
              data-testid={`${card.testid}-delta`}
            >
              {card.delta_value} {card.delta_label}
            </p>
            {card.caption ? (
              <p
                className="text-muted-foreground mt-1 text-xs"
                data-testid={`${card.testid}-caption`}
              >
                {card.caption}
              </p>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
