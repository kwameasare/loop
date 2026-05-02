/**
 * Billing fixtures + helpers for the studio billing tab.
 *
 * The data plane will eventually own these shapes; for now the
 * studio uses synthetic fixtures so the page renders end-to-end
 * without depending on Stripe.
 */

export type PlanId = "free" | "starter" | "growth" | "scale";

export interface Plan {
  id: PlanId;
  name: string;
  monthly_price_cents: number;
  included_messages: number;
  overage_per_message_cents: number;
  features: string[];
}

export interface BillingSummary {
  workspace_id: string;
  plan: Plan;
  cycle_start_ms: number;
  cycle_end_ms: number;
  mtd_messages: number;
  mtd_cost_cents: number;
  payment_method_last4: string | null;
  customer_portal_url: string;
}

export const PLANS: Record<PlanId, Plan> = {
  free: {
    id: "free",
    name: "Free",
    monthly_price_cents: 0,
    included_messages: 1_000,
    overage_per_message_cents: 1,
    features: ["1 agent", "Community support", "7-day trace retention"],
  },
  starter: {
    id: "starter",
    name: "Starter",
    monthly_price_cents: 4900,
    included_messages: 25_000,
    overage_per_message_cents: 1,
    features: ["3 agents", "Email support", "30-day trace retention"],
  },
  growth: {
    id: "growth",
    name: "Growth",
    monthly_price_cents: 19900,
    included_messages: 150_000,
    overage_per_message_cents: 1,
    features: [
      "Unlimited agents",
      "Priority support",
      "90-day trace retention",
      "Custom domains",
    ],
  },
  scale: {
    id: "scale",
    name: "Scale",
    monthly_price_cents: 99900,
    included_messages: 1_000_000,
    overage_per_message_cents: 1,
    features: [
      "Dedicated infra",
      "24/7 support",
      "1-year retention",
      "SSO + SCIM",
      "Custom SLA",
    ],
  },
};

export const FIXTURE_BILLING_NOW_MS = Date.UTC(2026, 4, 18, 12, 0, 0);

export const FIXTURE_BILLING: BillingSummary = {
  workspace_id: "ws-fixture",
  plan: PLANS.growth,
  cycle_start_ms: Date.UTC(2026, 4, 1, 0, 0, 0),
  cycle_end_ms: Date.UTC(2026, 5, 1, 0, 0, 0),
  mtd_messages: 91_245,
  mtd_cost_cents: 19_900,
  payment_method_last4: "4242",
  customer_portal_url: "https://billing.stripe.com/p/login/test_fixture",
};

export interface UsageRatio {
  used: number;
  cap: number;
  ratio: number;
  status: "ok" | "warn" | "over";
}

/**
 * Compute usage ratio against a plan's included quota.
 *
 * - ``ratio`` is clamped to [0, ∞) but kept >1.0 if the workspace
 *   is over its included quota so the bar can render an overage
 *   stripe.
 * - ``status`` is "ok" below 75%, "warn" between 75% and 100%,
 *   and "over" once the cap is exceeded.
 */
export function computeUsageRatio(used: number, cap: number): UsageRatio {
  const safeCap = Math.max(0, cap);
  const safeUsed = Math.max(0, used);
  if (safeCap === 0) {
    return {
      used: safeUsed,
      cap: 0,
      ratio: safeUsed > 0 ? 1 : 0,
      status: safeUsed > 0 ? "over" : "ok",
    };
  }
  const ratio = safeUsed / safeCap;
  let status: UsageRatio["status"] = "ok";
  if (ratio >= 1) status = "over";
  else if (ratio >= 0.75) status = "warn";
  return { used: safeUsed, cap: safeCap, ratio, status };
}

/**
 * Project the number of included messages used by the end of the
 * cycle assuming the current daily run-rate continues.
 */
export function projectCycleUsage(args: {
  now_ms: number;
  cycle_start_ms: number;
  cycle_end_ms: number;
  used: number;
}): number {
  const total = args.cycle_end_ms - args.cycle_start_ms;
  const elapsed = args.now_ms - args.cycle_start_ms;
  if (elapsed <= 0 || total <= 0) return args.used;
  const rate = args.used / elapsed;
  return Math.round(rate * total);
}

export function formatCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100);
  const remainder = abs % 100;
  return `${sign}$${dollars.toLocaleString("en-US")}.${remainder
    .toString()
    .padStart(2, "0")}`;
}
