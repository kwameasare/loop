"use client";

/**
 * Pricing page + plan-comparison matrix (S671).
 *
 * The component is purely presentational: it accepts the plan list as a
 * prop so the page can swap A/B variants without re-render churn. The
 * `variant` prop drives the live A/B test (control = "A", treatment =
 * "B"); both variants render identical accessibility semantics.
 */

export type PricingVariant = "A" | "B";

export interface PricingFeature {
  /** Stable id (used by the comparison-matrix row keys). */
  id: string;
  /** Human label rendered in the matrix. */
  label: string;
  /** Optional helper tooltip — rendered as plain text under the label. */
  description?: string;
}

export interface PricingPlan {
  id: string;
  name: string;
  /** Monthly price in USD cents. 0 for free, null for "Talk to sales". */
  price_cents: number | null;
  /** Short positioning line under the price. */
  tagline: string;
  /** Free-form list of headline bullets shown above the matrix. */
  highlights: ReadonlyArray<string>;
  /** Map of feature.id → "yes" | "no" | "limited" | string (custom). */
  matrix: Readonly<Record<string, string>>;
  /** Most-popular flag drives the highlight ring. */
  recommended?: boolean;
  /** CTA copy — defaults to "Get started". */
  cta_label?: string;
  cta_href: string;
}

export interface PricingPageProps {
  plans: ReadonlyArray<PricingPlan>;
  features: ReadonlyArray<PricingFeature>;
  variant: PricingVariant;
  /** Called with (plan_id, variant) when a CTA is activated. */
  onCtaClick?: (plan_id: string, variant: PricingVariant) => void;
}

function formatPrice(cents: number | null): string {
  if (cents === null) return "Talk to sales";
  if (cents === 0) return "Free";
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

function MatrixCell({ value }: { value: string | undefined }) {
  if (value === undefined || value === "no") {
    return (
      <span aria-label="not included" className="text-zinc-400">
        —
      </span>
    );
  }
  if (value === "yes") {
    return (
      <span aria-label="included" className="text-emerald-600">
        ✓
      </span>
    );
  }
  if (value === "limited") {
    return (
      <span aria-label="limited" className="text-amber-600">
        Limited
      </span>
    );
  }
  return <span className="text-zinc-700">{value}</span>;
}

export function PricingPage({
  plans,
  features,
  variant,
  onCtaClick,
}: PricingPageProps): JSX.Element {
  const heading =
    variant === "A"
      ? "Simple pricing for every team"
      : "Pick the plan that scales with you";
  return (
    <main
      data-testid="pricing-page"
      data-variant={variant}
      className="mx-auto max-w-6xl px-6 py-12"
    >
      <header className="mb-10 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">{heading}</h1>
        <p className="mt-2 text-zinc-600">
          Start free. Pay only for what you use. Cancel anytime.
        </p>
      </header>
      <section
        aria-label="Plans"
        className="grid gap-6 md:grid-cols-3"
      >
        {plans.map((plan) => (
          <article
            key={plan.id}
            data-testid={`plan-card-${plan.id}`}
            aria-label={`${plan.name} plan`}
            className={
              "rounded-2xl border p-6 " +
              (plan.recommended
                ? "border-blue-500 ring-2 ring-blue-200"
                : "border-zinc-200")
            }
          >
            {plan.recommended ? (
              <p
                aria-label="Most popular plan"
                className="mb-2 text-xs font-medium uppercase tracking-wide text-blue-600"
              >
                Most popular
              </p>
            ) : null}
            <h2 className="text-xl font-semibold">{plan.name}</h2>
            <p className="mt-1 text-sm text-zinc-600">{plan.tagline}</p>
            <p className="mt-4 text-3xl font-semibold">
              {formatPrice(plan.price_cents)}
              {plan.price_cents !== null && plan.price_cents > 0 ? (
                <span className="text-base font-normal text-zinc-500">
                  /mo
                </span>
              ) : null}
            </p>
            <ul className="mt-4 space-y-1 text-sm text-zinc-700">
              {plan.highlights.map((line) => (
                <li key={line}>• {line}</li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => onCtaClick?.(plan.id, variant)}
              className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 text-white"
            >
              {plan.cta_label ?? "Get started"}
            </button>
          </article>
        ))}
      </section>

      <section aria-label="Plan comparison" className="mt-16">
        <h2 className="text-2xl font-semibold">Compare plans</h2>
        <p className="mt-1 text-sm text-zinc-600">
          Every feature, every tier. Detailed limits in the docs.
        </p>
        <div className="mt-6 overflow-x-auto">
          <table
            data-testid="plan-comparison-matrix"
            className="w-full border-collapse text-left text-sm"
          >
            <caption className="sr-only">
              Plan comparison matrix
            </caption>
            <thead>
              <tr className="border-b">
                <th scope="col" className="py-3 pr-4 font-medium">
                  Feature
                </th>
                {plans.map((plan) => (
                  <th
                    key={plan.id}
                    scope="col"
                    className="py-3 pr-4 font-medium"
                  >
                    {plan.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {features.map((feature) => (
                <tr
                  key={feature.id}
                  data-testid={`matrix-row-${feature.id}`}
                  className="border-b border-zinc-100"
                >
                  <th
                    scope="row"
                    className="py-2 pr-4 text-left font-normal text-zinc-700"
                  >
                    <span>{feature.label}</span>
                    {feature.description ? (
                      <span className="block text-xs text-zinc-500">
                        {feature.description}
                      </span>
                    ) : null}
                  </th>
                  {plans.map((plan) => (
                    <td key={plan.id} className="py-2 pr-4">
                      <MatrixCell value={plan.matrix[feature.id]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default PricingPage;
