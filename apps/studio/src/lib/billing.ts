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

export interface Invoice {
  id: string;
  number: string;
  /** Invoice date (UTC midnight ms). */
  date_ms: number;
  amount_cents: number;
  status: "paid" | "open" | "void";
  /** Stripe-hosted PDF URL. */
  pdf_url: string;
}

/** Paginate a sorted list of invoices (newest-first). */
export function paginateInvoices(
  invoices: Invoice[],
  page: number,
  page_size: number,
): { items: Invoice[]; total: number; pages: number } {
  const sorted = [...invoices].sort((a, b) => b.date_ms - a.date_ms);
  const total = sorted.length;
  const pages = Math.max(1, Math.ceil(total / page_size));
  const safePage = Math.max(1, Math.min(page, pages));
  const start = (safePage - 1) * page_size;
  return { items: sorted.slice(start, start + page_size), total, pages };
}

// ---------------------------------------------------------------- cp-api

export interface BillingClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required for billing calls");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

async function cpFetch<T>(
  method: string,
  path: string,
  opts: BillingClientOptions,
  body?: unknown,
): Promise<T | null> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const init: RequestInit = { method, headers, cache: "no-store" };
  if (body !== undefined) {
    headers["content-type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const res = await fetcher(`${cpApiBaseUrl(opts.baseUrl)}${path}`, init);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`cp-api ${method} ${path} -> ${res.status}`);
  if (res.status === 204) return null;
  return (await res.json()) as T;
}

/**
 * Fetch the workspace's billing summary.
 *
 * Blocked on cp-api PR: ``/v1/workspaces/{id}/billing`` is not yet
 * mounted in cp's app.py. The studio code calls the (eventual)
 * endpoint and renders a "billing not yet provisioned" empty state on
 * 404 so the page is usable today and seamlessly upgrades when the
 * route lands. ``billing_stripe_export.py`` already exists; only the
 * FastAPI shim is missing.
 */
export async function fetchBillingSummary(
  workspace_id: string,
  opts: BillingClientOptions = {},
): Promise<BillingSummary | null> {
  return cpFetch<BillingSummary>(
    "GET",
    `/workspaces/${encodeURIComponent(workspace_id)}/billing`,
    opts,
  );
}

/** Likewise blocked on cp-api PR. */
export async function fetchInvoices(
  workspace_id: string,
  opts: BillingClientOptions = {},
): Promise<Invoice[]> {
  const res = await cpFetch<{ items: Invoice[] }>(
    "GET",
    `/workspaces/${encodeURIComponent(workspace_id)}/billing/invoices`,
    opts,
  );
  return res?.items ?? [];
}

/**
 * Update the customer's payment method via Stripe Setup Intent. The
 * cp-api responds with the new last-4 on success. Blocked on the
 * cp-api PR; until then the call just 404s and the form surfaces an
 * "unavailable" error.
 */
export async function updatePaymentMethod(
  workspace_id: string,
  args: { cardholderName: string; setup_intent_id?: string },
  opts: BillingClientOptions = {},
): Promise<{ ok: true; last4: string } | { ok: false; reason: string }> {
  const res = await cpFetch<{ last4: string }>(
    "POST",
    `/workspaces/${encodeURIComponent(workspace_id)}/billing/payment-method`,
    opts,
    args,
  );
  if (res === null) {
    return { ok: false, reason: "Billing API not yet available" };
  }
  return { ok: true, last4: res.last4 };
}

// ---------------------------------------------------------------- fixtures

export const FIXTURE_INVOICES: Invoice[] = [
  {
    id: "in_001",
    number: "INV-2026-001",
    date_ms: Date.UTC(2026, 3, 1),
    amount_cents: 19_900,
    status: "paid",
    pdf_url: "https://billing.stripe.com/invoice/test_001/pdf",
  },
  {
    id: "in_002",
    number: "INV-2026-002",
    date_ms: Date.UTC(2026, 2, 1),
    amount_cents: 19_900,
    status: "paid",
    pdf_url: "https://billing.stripe.com/invoice/test_002/pdf",
  },
  {
    id: "in_003",
    number: "INV-2026-003",
    date_ms: Date.UTC(2026, 1, 1),
    amount_cents: 4_900,
    status: "paid",
    pdf_url: "https://billing.stripe.com/invoice/test_003/pdf",
  },
];

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
