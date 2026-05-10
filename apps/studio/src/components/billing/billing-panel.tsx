"use client";

import {
  computeUsageRatio,
  formatCents,
  projectCycleUsage,
  type BillingSummary,
} from "@/lib/billing";

export interface BillingPanelProps {
  billing: BillingSummary;
  now_ms: number;
}

const STATUS_BAR: Record<"ok" | "warn" | "over", string> = {
  ok: "bg-success",
  warn: "bg-warning",
  over: "bg-destructive",
};

const STATUS_TEXT: Record<"ok" | "warn" | "over", string> = {
  ok: "On track",
  warn: "Approaching cap",
  over: "Over included quota",
};

function formatDate(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function BillingPanel({ billing, now_ms }: BillingPanelProps) {
  const usage = computeUsageRatio(
    billing.mtd_messages,
    billing.plan.included_messages,
  );
  const projected = projectCycleUsage({
    now_ms,
    cycle_start_ms: billing.cycle_start_ms,
    cycle_end_ms: billing.cycle_end_ms,
    used: billing.mtd_messages,
  });
  const projectedOverage = Math.max(
    0,
    projected - billing.plan.included_messages,
  );
  const projectedOverageCost =
    projectedOverage * billing.plan.overage_per_message_cents;
  const barWidth = Math.min(100, Math.round(usage.ratio * 100));

  return (
    <section
      className="flex flex-col gap-6"
      data-testid="billing-panel"
    >
      <header className="rounded-lg border bg-card p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase text-muted-foreground">
              Current plan
            </p>
            <h2
              className="mt-1 text-2xl font-semibold tracking-tight"
              data-testid="billing-plan-name"
            >
              {billing.plan.name}
            </h2>
            <p className="text-sm text-muted-foreground">
              <span data-testid="billing-plan-price">
                {formatCents(billing.plan.monthly_price_cents)}
              </span>{" "}
              / month · {billing.plan.included_messages.toLocaleString()}{" "}
              messages included
            </p>
          </div>
          <a
            className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            data-testid="billing-change-plan"
            href={billing.customer_portal_url}
            rel="noreferrer"
            target="_blank"
          >
            Change plan
          </a>
        </div>
        <ul className="mt-4 grid gap-1 text-sm text-muted-foreground sm:grid-cols-2">
          {billing.plan.features.map((f) => (
            <li className="flex items-center gap-2" key={f}>
              <span
                aria-hidden
                className="size-1.5 rounded-full bg-muted-foreground"
              />
              {f}
            </li>
          ))}
        </ul>
      </header>

      <article
        className="rounded-lg border bg-card p-5"
        data-testid="billing-usage"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase text-muted-foreground">
            This cycle
          </h3>
          <span className="text-xs text-muted-foreground">
            {formatDate(billing.cycle_start_ms)} →{" "}
            {formatDate(billing.cycle_end_ms)}
          </span>
        </div>
        <div className="mt-3 flex items-baseline gap-3">
          <span
            className="text-3xl font-semibold tracking-tight"
            data-testid="billing-usage-used"
          >
            {usage.used.toLocaleString()}
          </span>
          <span className="text-sm text-muted-foreground">
            / {usage.cap.toLocaleString()} messages
          </span>
          <span
            className={
              usage.status === "ok"
                ? "rounded border border-success/30 bg-success/10 px-2 py-0.5 text-xs text-success"
                : usage.status === "warn"
                  ? "rounded border border-warning/30 bg-warning/10 px-2 py-0.5 text-xs text-warning"
                  : "rounded border border-destructive/30 bg-destructive/10 px-2 py-0.5 text-xs text-destructive"
            }
            data-testid="billing-usage-status"
          >
            {STATUS_TEXT[usage.status]}
          </span>
        </div>
        <div
          aria-label="Cycle usage"
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={barWidth}
          className="mt-3 h-3 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
        >
          <div
            className={`h-full ${STATUS_BAR[usage.status]}`}
            data-testid="billing-usage-bar"
            style={{ width: `${barWidth}%` }}
          />
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-xs uppercase text-muted-foreground">
              MTD spend
            </dt>
            <dd
              className="font-semibold"
              data-testid="billing-usage-mtd-cost"
            >
              {formatCents(billing.mtd_cost_cents)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-muted-foreground">
              Projected end-of-cycle
            </dt>
            <dd
              className="font-semibold"
              data-testid="billing-usage-projection"
            >
              {projected.toLocaleString()} msgs
              {projectedOverage > 0 ? (
                <span className="ml-2 text-xs text-destructive">
                  +{formatCents(projectedOverageCost)} overage
                </span>
              ) : null}
            </dd>
          </div>
        </dl>
      </article>

      <article
        className="rounded-lg border bg-card p-5 text-sm"
        data-testid="billing-payment"
      >
        <h3 className="text-sm font-semibold uppercase text-muted-foreground">
          Payment method
        </h3>
        <p className="mt-2">
          {billing.payment_method_last4 ? (
            <span data-testid="billing-payment-last4">
              Card ending in {billing.payment_method_last4}
            </span>
          ) : (
            <span data-testid="billing-payment-empty">
              No payment method on file.
            </span>
          )}
        </p>
        <a
          className="mt-3 inline-block text-sm text-info hover:underline"
          data-testid="billing-portal-link"
          href={billing.customer_portal_url}
          rel="noreferrer"
          target="_blank"
        >
          Manage in Stripe portal →
        </a>
      </article>
    </section>
  );
}
