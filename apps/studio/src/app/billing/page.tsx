import { BillingPanel } from "@/components/billing/billing-panel";
import { InvoiceList } from "@/components/billing/invoice-list";
import { UpdatePaymentMethod } from "@/components/billing/update-payment-method";
import {
  FIXTURE_BILLING,
  FIXTURE_BILLING_NOW_MS,
  FIXTURE_INVOICES,
} from "@/lib/billing";

export const dynamic = "force-dynamic";

async function fixturePaymentMethodSubmit(_args: { cardholderName: string }) {
  // Server route would call Stripe here; the fixture echoes a stable last4.
  return { ok: true as const, last4: "4242" };
}

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
      <div className="flex flex-col gap-6">
        <BillingPanel
          billing={FIXTURE_BILLING}
          now_ms={FIXTURE_BILLING_NOW_MS}
        />
        <UpdatePaymentMethod
          initialLast4={FIXTURE_BILLING.payment_method_last4}
          submit={fixturePaymentMethodSubmit}
        />
        <InvoiceList invoices={FIXTURE_INVOICES} />
      </div>
    </main>
  );
}
