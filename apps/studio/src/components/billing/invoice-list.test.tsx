/**
 * S328: Tests for invoice list + pagination + paginateInvoices helper.
 */
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { InvoiceList } from "./invoice-list";
import { paginateInvoices, type Invoice } from "@/lib/billing";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeInvoice(n: number): Invoice {
  return {
    id: `in_${String(n).padStart(3, "0")}`,
    number: `INV-2026-${String(n).padStart(3, "0")}`,
    date_ms: Date.UTC(2026, n - 1, 1),
    amount_cents: n * 1000,
    status: "paid",
    pdf_url: `https://billing.stripe.com/invoice/test_${n}/pdf`,
  };
}

const THREE_INVOICES = [makeInvoice(3), makeInvoice(1), makeInvoice(2)]; // unsorted intentionally
const TWELVE_INVOICES = Array.from({ length: 12 }, (_, i) => makeInvoice(i + 1));

// ---------------------------------------------------------------------------
// paginateInvoices unit tests
// ---------------------------------------------------------------------------

describe("paginateInvoices", () => {
  it("returns all items on page 1 when count <= page_size", () => {
    const { items, total, pages } = paginateInvoices(THREE_INVOICES, 1, 10);
    expect(total).toBe(3);
    expect(pages).toBe(1);
    expect(items).toHaveLength(3);
  });

  it("sorts newest first", () => {
    const { items } = paginateInvoices(THREE_INVOICES, 1, 10);
    expect(items[0].id).toBe("in_003");
    expect(items[2].id).toBe("in_001");
  });

  it("paginates correctly", () => {
    const p1 = paginateInvoices(TWELVE_INVOICES, 1, 10);
    expect(p1.items).toHaveLength(10);
    expect(p1.pages).toBe(2);

    const p2 = paginateInvoices(TWELVE_INVOICES, 2, 10);
    expect(p2.items).toHaveLength(2);
  });

  it("clamps page to valid range", () => {
    const { items } = paginateInvoices(THREE_INVOICES, 99, 10);
    expect(items).toHaveLength(3);
  });
});

// ---------------------------------------------------------------------------
// InvoiceList component tests
// ---------------------------------------------------------------------------

describe("InvoiceList", () => {
  it("shows empty state when no invoices", () => {
    render(<InvoiceList invoices={[]} />);
    expect(screen.getByTestId("invoice-empty")).toBeInTheDocument();
  });

  it("renders a row per invoice", () => {
    render(<InvoiceList invoices={THREE_INVOICES} />);
    expect(screen.getByTestId("invoice-row-in_001")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-row-in_002")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-row-in_003")).toBeInTheDocument();
  });

  it("displays the formatted amount", () => {
    render(<InvoiceList invoices={[makeInvoice(1)]} />);
    expect(screen.getByTestId("invoice-amount-in_001")).toHaveTextContent("$10.00");
  });

  it("shows the correct status badge", () => {
    render(<InvoiceList invoices={[makeInvoice(1)]} />);
    expect(screen.getByTestId("invoice-status-in_001")).toHaveTextContent("paid");
  });

  it("renders a download link with the pdf_url", () => {
    render(<InvoiceList invoices={[makeInvoice(1)]} />);
    const link = screen.getByTestId("invoice-download-in_001");
    expect(link).toHaveAttribute("href", "https://billing.stripe.com/invoice/test_1/pdf");
  });

  it("does not show pagination when only one page", () => {
    render(<InvoiceList invoices={THREE_INVOICES} page_size={10} />);
    expect(screen.queryByTestId("invoice-pagination")).toBeNull();
  });

  it("shows pagination and navigates pages", () => {
    render(<InvoiceList invoices={TWELVE_INVOICES} page_size={5} />);
    expect(screen.getByTestId("invoice-pagination")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-page-label")).toHaveTextContent("1 / 3");

    // Previous disabled on first page
    expect(screen.getByTestId("invoice-prev")).toBeDisabled();

    // Go to page 2
    fireEvent.click(screen.getByTestId("invoice-next"));
    expect(screen.getByTestId("invoice-page-label")).toHaveTextContent("2 / 3");

    // Go back to page 1
    fireEvent.click(screen.getByTestId("invoice-prev"));
    expect(screen.getByTestId("invoice-page-label")).toHaveTextContent("1 / 3");
  });

  it("shows correct invoice count", () => {
    render(<InvoiceList invoices={THREE_INVOICES} />);
    expect(screen.getByTestId("invoice-count")).toHaveTextContent("3 invoices");
  });
});
