"use client";

import { useState } from "react";

export type PaymentMethodSubmit = (args: {
  cardholderName: string;
}) => Promise<
  | { ok: true; last4: string }
  | { ok: false; error: string; code?: string; requiresAction?: boolean }
>;

export interface UpdatePaymentMethodProps {
  /**
   * Adapter around Stripe Elements ``confirmCardSetup``. The default
   * studio mounts a real Stripe Elements form; tests inject a stub
   * so we can exercise success / 3DS / error branches without the
   * Stripe SDK.
   */
  submit: PaymentMethodSubmit;
  initialLast4?: string | null;
  onUpdated?: (last4: string) => void;
}

export function UpdatePaymentMethod(props: UpdatePaymentMethodProps) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending3ds, setPending3ds] = useState(false);
  const [last4, setLast4] = useState<string | null>(
    props.initialLast4 ?? null,
  );
  const [toast, setToast] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setPending3ds(false);
    try {
      const res = await props.submit({ cardholderName: name.trim() });
      if (res.ok) {
        setLast4(res.last4);
        setToast(`Card ending in ${res.last4} saved.`);
        props.onUpdated?.(res.last4);
        setName("");
      } else {
        if (res.requiresAction) setPending3ds(true);
        setError(res.error || "We could not save this card.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="rounded-lg border bg-white p-5"
      data-testid="payment-method-form"
    >
      <h3 className="text-sm font-semibold uppercase text-zinc-500">
        Update payment method
      </h3>
      {last4 ? (
        <p
          className="mt-2 text-sm text-zinc-700"
          data-testid="payment-method-current"
        >
          Current card ends in {last4}.
        </p>
      ) : (
        <p
          className="mt-2 text-sm text-zinc-500"
          data-testid="payment-method-empty"
        >
          No card on file yet.
        </p>
      )}
      <form className="mt-3 flex flex-col gap-3" onSubmit={onSubmit}>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-xs uppercase text-zinc-500">
            Cardholder name
          </span>
          <input
            className="rounded border px-2 py-1"
            data-testid="payment-method-name"
            disabled={busy}
            onChange={(e) => setName(e.target.value)}
            required
            type="text"
            value={name}
          />
        </label>
        <div
          className="rounded border border-dashed border-zinc-300 bg-zinc-50 px-3 py-6 text-center text-xs text-zinc-500"
          data-testid="payment-method-elements-mount"
        >
          Stripe Elements card field renders here in production.
        </div>
        {error ? (
          <p
            className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
            data-testid="payment-method-error"
            role="alert"
          >
            {error}
            {pending3ds ? (
              <span
                className="ml-2 rounded bg-amber-100 px-2 py-0.5 text-amber-700"
                data-testid="payment-method-3ds-hint"
              >
                3DS verification required
              </span>
            ) : null}
          </p>
        ) : null}
        <div className="flex justify-end">
          <button
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            data-testid="payment-method-submit"
            disabled={busy || name.trim().length === 0}
            type="submit"
          >
            {busy ? "Saving…" : "Save card"}
          </button>
        </div>
      </form>
      {toast ? (
        <p
          aria-live="polite"
          className="mt-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700"
          data-testid="payment-method-toast"
          role="status"
        >
          {toast}
        </p>
      ) : null}
    </section>
  );
}
