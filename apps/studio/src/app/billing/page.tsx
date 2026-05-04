"use client";

/**
 * P0.3: ``/billing`` — Stripe billing surface.
 *
 * Wires the panels to cp-api. The cp ``/v1/workspaces/{id}/billing``
 * routes are blocked: the underlying ``billing_stripe_export.py``
 * service module exists but no FastAPI shim is mounted yet (see
 * lib/billing.ts ``fetchBillingSummary``). When cp returns 404 we
 * render a clear "billing not yet provisioned" empty state instead
 * of the old fixture so customers don't mistake it for live data.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { BillingPanel } from "@/components/billing/billing-panel";
import { InvoiceList } from "@/components/billing/invoice-list";
import { UpdatePaymentMethod } from "@/components/billing/update-payment-method";
import {
  fetchBillingSummary,
  fetchInvoices,
  updatePaymentMethod,
  type BillingSummary,
  type Invoice,
} from "@/lib/billing";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function BillingPage(): JSX.Element {
  return (
    <RequireAuth>
      <BillingPageBody />
    </RequireAuth>
  );
}

function BillingPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [summary, setSummary] = useState<BillingSummary | null | undefined>(
    undefined,
  );
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void Promise.all([
      fetchBillingSummary(active.id),
      fetchInvoices(active.id),
    ])
      .then(([s, i]) => {
        if (cancelled) return;
        setSummary(s);
        setInvoices(i);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load billing");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading || !active) {
    return (
      <main className="container mx-auto p-6">
        <p
          className="text-sm text-muted-foreground"
          data-testid="billing-loading"
        >
          Loading billing…
        </p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      </main>
    );
  }
  if (summary === undefined) {
    return (
      <main className="container mx-auto p-6">
        <p
          className="text-sm text-muted-foreground"
          data-testid="billing-loading"
        >
          Loading billing…
        </p>
      </main>
    );
  }
  if (summary === null) {
    return (
      <main className="container mx-auto p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        </header>
        <div className="rounded-lg border p-4" role="status">
          <h2 className="text-base font-medium">
            Billing is not yet provisioned for this workspace.
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            The cp-api billing endpoints are still rolling out. This page will
            light up automatically once the workspace is enrolled in Stripe.
          </p>
        </div>
      </main>
    );
  }

  async function handlePaymentSubmit(args: { cardholderName: string }): Promise<
    { ok: true; last4: string } | { ok: false; error: string }
  > {
    if (!active) return { ok: false, error: "No active workspace" };
    const res = await updatePaymentMethod(active.id, args);
    if (res.ok) return { ok: true, last4: res.last4 };
    return { ok: false, error: res.reason };
  }

  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="text-muted-foreground text-sm">
          Manage your plan, monitor usage against your included quota, and
          launch the Stripe Customer Portal for invoices and payment methods.
        </p>
      </header>
      <div className="flex flex-col gap-6">
        <BillingPanel billing={summary} now_ms={Date.now()} />
        <UpdatePaymentMethod
          initialLast4={summary.payment_method_last4}
          submit={handlePaymentSubmit}
        />
        <InvoiceList invoices={invoices ?? []} />
      </div>
    </main>
  );
}
