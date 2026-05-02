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
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  over: "bg-red-500",
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
      <header className="rounded-lg border bg-white p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase text-zinc-500">Current plan</p>
            <h2
              className="mt-1 text-2xl font-semibold tracking-tight"
              data-testid="billing-plan-name"
            >
              {billing.plan.name}
            </h2>
            <p className="text-sm text-zinc-600">
              <span data-testid="billing-plan-price">
                {formatCents(billing.plan.monthly_price_cents)}
              </span>{" "}
              / month · {billing.plan.included_messages.toLocaleString()}{" "}
              messages included
            </p>
          </div>
          <a
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            data-testid="billing-change-plan"
            href={billing.customer_portal_url}
            rel="noreferrer"
            target="_blank"
          >
            Change plan
          </a>
        </div>
        <ul className="mt-4 grid gap-1 text-sm text-zinc-700 sm:grid-cols-2">
          {billing.plan.features.map((f) => (
            <li className="flex items-center gap-2" key={f}>
              <span aria-hidden className="size-1.5 rounded-full bg-zinc-400" />
              {f}
            </li>
          ))}
        </ul>
      </header>

      <article
        className="rounded-lg border bg-white p-5"
        data-testid="billing-usage"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase text-zinc-500">
            This cycle
          </h3>
          <span className="text-xs text-zinc-500">
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
          <span className="text-sm text-zinc-500">
            / {usage.cap.toLocaleString()} messages
          </span>
          <span
            className={
              usage.status === "ok"
                ? "rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700"
                : usage.status === "warn"
                  ? "rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700"
                  : "rounded bg-red-100 px-2 py-0.5 text-xs text-red-700"
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
          className="mt-3 h-3 w-full overflow-hidden rounded-full bg-zinc-100"
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
            <dt className="text-xs uppercase text-zinc-500">MTD spend</dt>
            <dd
              className="font-semibold"
              data-testid="billing-usage-mtd-cost"
            >
              {formatCents(billing.mtd_cost_cents)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-zinc-500">
              Projected end-of-cycle
            </dt>
            <dd
              className="font-semibold"
              data-testid="billing-usage-projection"
            >
              {projected.toLocaleString()} msgs
              {projectedOverage > 0 ? (
                <span className="ml-2 text-xs text-red-600">
                  +{formatCents(projectedOverageCost)} overage
                </span>
              ) : null}
            </dd>
          </div>
        </dl>
      </article>

      <article
        className="rounded-lg border bg-white p-5 text-sm"
        data-testid="billing-payment"
      >
        <h3 className="text-sm font-semibold uppercase text-zinc-500">
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
          className="mt-3 inline-block text-sm text-blue-600 hover:underline"
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
