import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AddMemberForm } from "./add-member-form";

describe("AddMemberForm", () => {
  it("rejects a non-UUID user_sub before calling onAdd", async () => {
    const onAdd = vi.fn();
    render(<AddMemberForm onAdd={onAdd} />);
    fireEvent.change(screen.getByLabelText(/user sub/i), {
      target: { value: "not-a-uuid" },
    });
    fireEvent.submit(screen.getByTestId("add-member-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/UUID/);
    expect(onAdd).not.toHaveBeenCalled();
  });

  it("submits a valid UUID + role and clears the input on success", async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined);
    render(<AddMemberForm onAdd={onAdd} />);
    fireEvent.change(screen.getByLabelText(/user sub/i), {
      target: { value: "11111111-1111-1111-1111-111111111111" },
    });
    fireEvent.change(screen.getByLabelText(/role/i), {
      target: { value: "admin" },
    });
    fireEvent.submit(screen.getByTestId("add-member-form"));
    await waitFor(() =>
      expect(onAdd).toHaveBeenCalledWith({
        user_sub: "11111111-1111-1111-1111-111111111111",
        role: "admin",
      }),
    );
    expect(screen.getByLabelText<HTMLInputElement>(/user sub/i).value).toBe(
      "",
    );
  });

  it("renders an error when onAdd rejects", async () => {
    const onAdd = vi.fn().mockRejectedValue(new Error("409 already a member"));
    render(<AddMemberForm onAdd={onAdd} />);
    fireEvent.change(screen.getByLabelText(/user sub/i), {
      target: { value: "11111111-1111-1111-1111-111111111111" },
    });
    fireEvent.submit(screen.getByTestId("add-member-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/already/);
  });
});
