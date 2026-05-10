"use client";

import { useState } from "react";
import { formatCents, paginateInvoices, type Invoice } from "@/lib/billing";

export interface InvoiceListProps {
  invoices: Invoice[];
  /** Number of invoices per page. Default 10. */
  page_size?: number;
}

const STATUS_PILL: Record<Invoice["status"], string> = {
  paid: "border border-success/30 bg-success/10 text-success",
  open: "border border-warning/30 bg-warning/10 text-warning",
  void: "border border-border bg-muted text-muted-foreground",
};

function formatDate(ms: number): string {
  return new Date(ms).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function InvoiceList({ invoices, page_size = 10 }: InvoiceListProps) {
  const [page, setPage] = useState(1);
  const { items, total, pages } = paginateInvoices(invoices, page, page_size);

  return (
    <section data-testid="invoice-list" className="flex flex-col gap-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Invoices</h2>
        <p
          className="text-sm text-muted-foreground"
          data-testid="invoice-count"
        >
          {total} invoice{total !== 1 ? "s" : ""}
        </p>
      </header>

      {items.length === 0 ? (
        <p
          className="text-sm text-muted-foreground"
          data-testid="invoice-empty"
        >
          No invoices yet.
        </p>
      ) : (
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="px-4 py-2 font-medium">Invoice</th>
                <th className="px-4 py-2 font-medium">Date</th>
                <th className="px-4 py-2 font-medium">Amount</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {items.map((inv) => (
                <tr
                  key={inv.id}
                  data-testid={`invoice-row-${inv.id}`}
                  className="border-b last:border-0"
                >
                  <td className="px-4 py-2 font-mono text-xs">
                    {inv.number}
                  </td>
                  <td className="px-4 py-2">{formatDate(inv.date_ms)}</td>
                  <td
                    className="px-4 py-2 tabular-nums"
                    data-testid={`invoice-amount-${inv.id}`}
                  >
                    {formatCents(inv.amount_cents)}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_PILL[inv.status]}`}
                      data-testid={`invoice-status-${inv.id}`}
                    >
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <a
                      href={inv.pdf_url}
                      target="_blank"
                      rel="noreferrer"
                      data-testid={`invoice-download-${inv.id}`}
                      className="text-xs font-medium text-info hover:underline"
                      aria-label={`Download PDF for ${inv.number}`}
                    >
                      Download PDF
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pages > 1 ? (
        <nav
          className="flex items-center justify-end gap-2"
          aria-label="Invoice pagination"
          data-testid="invoice-pagination"
        >
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            data-testid="invoice-prev"
            className="rounded border bg-background px-3 py-1 text-sm hover:bg-muted disabled:opacity-40"
          >
            Previous
          </button>
          <span
            className="text-sm text-muted-foreground"
            data-testid="invoice-page-label"
          >
            {page} / {pages}
          </span>
          <button
            type="button"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
            data-testid="invoice-next"
            className="rounded border bg-background px-3 py-1 text-sm hover:bg-muted disabled:opacity-40"
          >
            Next
          </button>
        </nav>
      ) : null}
    </section>
  );
}
