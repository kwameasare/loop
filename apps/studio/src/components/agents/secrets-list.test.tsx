import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { SecretsList } from "./secrets-list";
import type { AgentSecret } from "@/lib/agent-secrets";

function fixture(): AgentSecret[] {
  return [
    {
      id: "sec_1",
      agent_id: "agt_1",
      name: "OPENAI_API_KEY",
      ref: "kms://prod/openai-key",
      created_at: "2026-04-01T00:00:00Z",
      rotated_at: "2026-04-15T00:00:00Z",
    },
  ];
}

describe("SecretsList", () => {
  it("lists each secret with name, ref, and rotated_at — never a value", () => {
    render(<SecretsList agentId="agt_1" initialSecrets={fixture()} />);
    expect(screen.getByTestId("secret-row-OPENAI_API_KEY")).toBeInTheDocument();
    expect(screen.getByTestId("secret-ref-OPENAI_API_KEY")).toHaveTextContent(
      "kms://prod/openai-key",
    );
    expect(
      screen.getByTestId("secret-rotated-OPENAI_API_KEY"),
    ).toHaveTextContent(/Rotated/);
    // No element should expose a raw secret value.
    expect(document.body.textContent ?? "").not.toMatch(/sk-/);
  });

  it("rotates a secret and updates rotated_at + toasts success", async () => {
    const rotateSecret = vi.fn().mockResolvedValue({
      secretId: "sec_1",
      rotated_at: "2026-05-01T12:00:00Z",
    });
    render(
      <SecretsList
        agentId="agt_1"
        initialSecrets={fixture()}
        rotateSecret={rotateSecret}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("secret-rotate-OPENAI_API_KEY"));
    });
    expect(rotateSecret).toHaveBeenCalledWith({ secretId: "sec_1" });
    expect(
      screen.getByTestId("secret-rotated-OPENAI_API_KEY"),
    ).toHaveTextContent(/Rotated/);
    expect(screen.getByTestId("secret-toast-success")).toHaveTextContent(
      /Rotated OPENAI_API_KEY/,
    );
  });

  it("surfaces an error toast when rotate fails", async () => {
    const rotateSecret = vi.fn().mockRejectedValue(new Error("kms denied"));
    render(
      <SecretsList
        agentId="agt_1"
        initialSecrets={fixture()}
        rotateSecret={rotateSecret}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("secret-rotate-OPENAI_API_KEY"));
    });
    expect(screen.getByTestId("secret-toast-error")).toHaveTextContent(
      /Rotate failed: kms denied/,
    );
  });

  it("opens the add modal, validates, and appends on success", async () => {
    const addSecret = vi.fn().mockResolvedValue({
      id: "sec_new",
      agent_id: "agt_1",
      name: "STRIPE_SECRET",
      ref: "kms://prod/stripe",
      created_at: "2026-05-01T00:00:00Z",
      rotated_at: null,
    });
    render(
      <SecretsList
        agentId="agt_1"
        initialSecrets={fixture()}
        addSecret={addSecret}
      />,
    );
    fireEvent.click(screen.getByTestId("add-secret-button"));

    // submit empty → button disabled (canSubmit is false)
    expect(
      (screen.getByTestId("add-secret-submit") as HTMLButtonElement).disabled,
    ).toBe(true);

    fireEvent.change(screen.getByTestId("add-secret-name"), {
      target: { value: "stripe_secret" },
    });
    fireEvent.change(screen.getByTestId("add-secret-ref"), {
      target: { value: "kms://prod/stripe" },
    });
    // name input should auto-uppercase (so it becomes valid)
    expect(
      (screen.getByTestId("add-secret-name") as HTMLInputElement).value,
    ).toBe("STRIPE_SECRET");
    expect(
      (screen.getByTestId("add-secret-submit") as HTMLButtonElement).disabled,
    ).toBe(false);

    await act(async () => {
      fireEvent.click(screen.getByTestId("add-secret-submit"));
    });
    expect(addSecret).toHaveBeenCalledWith({
      agentId: "agt_1",
      name: "STRIPE_SECRET",
      ref: "kms://prod/stripe",
    });
    expect(screen.queryByTestId("add-secret-modal")).not.toBeInTheDocument();
    expect(screen.getByTestId("secret-row-STRIPE_SECRET")).toBeInTheDocument();
    expect(screen.getByTestId("secret-toast-success")).toHaveTextContent(
      /Added secret STRIPE_SECRET/,
    );
  });

  it("blocks duplicate names with a friendly error", () => {
    render(<SecretsList agentId="agt_1" initialSecrets={fixture()} />);
    fireEvent.click(screen.getByTestId("add-secret-button"));
    fireEvent.change(screen.getByTestId("add-secret-name"), {
      target: { value: "OPENAI_API_KEY" },
    });
    fireEvent.change(screen.getByTestId("add-secret-ref"), {
      target: { value: "kms://prod/openai-key" },
    });
    // duplicate disables the submit button
    expect(
      (screen.getByTestId("add-secret-submit") as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});
