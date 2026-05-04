import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MembersTable } from "./members-table";

const owner = {
  workspace_id: "ws1",
  user_sub: "00000000-0000-0000-0000-000000000001",
  role: "owner" as const,
};
const admin = {
  workspace_id: "ws1",
  user_sub: "00000000-0000-0000-0000-000000000002",
  role: "admin" as const,
};
const member = {
  workspace_id: "ws1",
  user_sub: "00000000-0000-0000-0000-000000000003",
  role: "member" as const,
};

describe("MembersTable", () => {
  it("renders an empty state when there are no members", () => {
    render(
      <MembersTable
        members={[]}
        currentUserSub="anyone"
        onChangeRole={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    expect(screen.getByTestId("members-empty")).toBeInTheDocument();
  });

  it("renders a row per member with the role select", () => {
    render(
      <MembersTable
        members={[owner, admin, member]}
        currentUserSub={admin.user_sub}
        onChangeRole={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    const rows = screen.getAllByTestId("members-row");
    expect(rows).toHaveLength(3);
    // The "(you)" annotation appears on the active user's row.
    const adminRow = rows.find(
      (r) => r.getAttribute("data-user-sub") === admin.user_sub,
    );
    expect(adminRow?.textContent).toContain("(you)");
  });

  it("disables remove + role select for the sole owner", () => {
    render(
      <MembersTable
        members={[owner, admin]}
        currentUserSub={admin.user_sub}
        onChangeRole={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    const ownerRow = screen
      .getAllByTestId("members-row")
      .find((r) => r.getAttribute("data-user-sub") === owner.user_sub)!;
    expect(
      ownerRow.querySelector<HTMLButtonElement>("[data-testid='members-remove']")!
        .disabled,
    ).toBe(true);
    expect(
      ownerRow.querySelector<HTMLSelectElement>(
        "[data-testid='members-role-select']",
      )!.disabled,
    ).toBe(true);
  });

  it("disables remove on the current user even if not the owner", () => {
    render(
      <MembersTable
        members={[owner, admin, member]}
        currentUserSub={admin.user_sub}
        onChangeRole={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    const adminRow = screen
      .getAllByTestId("members-row")
      .find((r) => r.getAttribute("data-user-sub") === admin.user_sub)!;
    expect(
      adminRow.querySelector<HTMLButtonElement>("[data-testid='members-remove']")!
        .disabled,
    ).toBe(true);
  });

  it("calls onChangeRole with the new role when the select changes", async () => {
    const onChangeRole = vi.fn().mockResolvedValue(undefined);
    render(
      <MembersTable
        members={[owner, admin, member]}
        currentUserSub={admin.user_sub}
        onChangeRole={onChangeRole}
        onRemove={vi.fn()}
      />,
    );
    const memberRow = screen
      .getAllByTestId("members-row")
      .find((r) => r.getAttribute("data-user-sub") === member.user_sub)!;
    const select = memberRow.querySelector<HTMLSelectElement>(
      "[data-testid='members-role-select']",
    )!;
    fireEvent.change(select, { target: { value: "viewer" } });
    await waitFor(() =>
      expect(onChangeRole).toHaveBeenCalledWith(member.user_sub, "viewer"),
    );
  });

  it("calls onRemove when the Remove button is pressed", async () => {
    const onRemove = vi.fn().mockResolvedValue(undefined);
    render(
      <MembersTable
        members={[owner, admin, member]}
        currentUserSub={admin.user_sub}
        onChangeRole={vi.fn()}
        onRemove={onRemove}
      />,
    );
    const memberRow = screen
      .getAllByTestId("members-row")
      .find((r) => r.getAttribute("data-user-sub") === member.user_sub)!;
    fireEvent.click(
      memberRow.querySelector<HTMLButtonElement>(
        "[data-testid='members-remove']",
      )!,
    );
    await waitFor(() =>
      expect(onRemove).toHaveBeenCalledWith(member.user_sub),
    );
  });

  it("shows an error when the mutation rejects", async () => {
    const onRemove = vi.fn().mockRejectedValue(new Error("403 forbidden"));
    render(
      <MembersTable
        members={[owner, admin, member]}
        currentUserSub={admin.user_sub}
        onChangeRole={vi.fn()}
        onRemove={onRemove}
      />,
    );
    const memberRow = screen
      .getAllByTestId("members-row")
      .find((r) => r.getAttribute("data-user-sub") === member.user_sub)!;
    fireEvent.click(
      memberRow.querySelector<HTMLButtonElement>(
        "[data-testid='members-remove']",
      )!,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(/403 forbidden/);
  });
});
