import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { UpdatePaymentMethod } from "./update-payment-method";

describe("UpdatePaymentMethod", () => {
  it("submits the cardholder name and shows a success toast on ok", async () => {
    let received = "";
    const submit = async ({ cardholderName }: { cardholderName: string }) => {
      received = cardholderName;
      return { ok: true as const, last4: "4242" };
    };
    render(<UpdatePaymentMethod submit={submit} />);
    fireEvent.change(screen.getByTestId("payment-method-name"), {
      target: { value: "Ada Lovelace" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("payment-method-submit"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("payment-method-toast").textContent).toMatch(
        /4242/,
      );
    });
    expect(received).toBe("Ada Lovelace");
    expect(screen.getByTestId("payment-method-current").textContent).toMatch(
      /4242/,
    );
  });

  it("shows the Stripe error string on a hard failure", async () => {
    const submit = async () => ({
      ok: false as const,
      error: "Your card was declined.",
      code: "card_declined",
    });
    render(<UpdatePaymentMethod submit={submit} />);
    fireEvent.change(screen.getByTestId("payment-method-name"), {
      target: { value: "Test" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("payment-method-submit"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("payment-method-error").textContent).toMatch(
        /declined/,
      );
    });
    expect(screen.queryByTestId("payment-method-3ds-hint")).toBeNull();
  });

  it("flags 3DS verification when requiresAction is set", async () => {
    const submit = async () => ({
      ok: false as const,
      error: "Additional authentication required.",
      requiresAction: true,
    });
    render(<UpdatePaymentMethod submit={submit} />);
    fireEvent.change(screen.getByTestId("payment-method-name"), {
      target: { value: "Test" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("payment-method-submit"));
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("payment-method-3ds-hint"),
      ).toBeInTheDocument();
    });
  });

  it("disables submit until cardholder name is provided", () => {
    const submit = async () => ({ ok: true as const, last4: "0000" });
    render(<UpdatePaymentMethod submit={submit} />);
    expect(screen.getByTestId("payment-method-submit")).toBeDisabled();
    fireEvent.change(screen.getByTestId("payment-method-name"), {
      target: { value: "Anyone" },
    });
    expect(screen.getByTestId("payment-method-submit")).not.toBeDisabled();
  });
});
