import { BillingPanel } from "@/components/billing/billing-panel";
import {
  FIXTURE_BILLING,
  FIXTURE_BILLING_NOW_MS,
} from "@/lib/billing";

export const dynamic = "force-dynamic";

export default function BillingPage(): JSX.Element {
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="text-muted-foreground text-sm">
          Manage your plan, monitor usage against your included quota, and
          launch the Stripe Customer Portal for invoices and payment
          methods.
        </p>
      </header>
      <BillingPanel
        billing={FIXTURE_BILLING}
        now_ms={FIXTURE_BILLING_NOW_MS}
      />
    </main>
  );
}
