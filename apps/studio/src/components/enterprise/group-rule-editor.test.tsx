/**
 * Tests for GroupRuleEditor (S617).
 *
 * Covers:
 *   - renders initial rules from props
 *   - renders empty state (no rows)
 *   - "Add rule" appends a blank viewer row
 *   - "Remove" button deletes the correct row
 *   - group input changes update the row
 *   - role select changes update the row (owner / editor / viewer)
 *   - "Save" calls onSave with current rules
 *   - validation error shown when group is empty
 *   - validation error shown for duplicate groups
 *   - success message shown after successful save
 *   - error message shown when onSave rejects
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GroupRuleEditor } from "./group-rule-editor";

const noop = vi.fn().mockResolvedValue(undefined);

describe("GroupRuleEditor", () => {
  it("renders initial rules passed as props", () => {
    render(
      <GroupRuleEditor
        initialRules={[
          { group: "admins", role: "admin" },
          { group: "viewers", role: "viewer" },
        ]}
        onSave={noop}
      />,
    );

    expect(screen.getByTestId("group-rule-group-input-0")).toHaveValue("admins");
    expect(screen.getByTestId("group-rule-role-select-0")).toHaveValue("admin");
    expect(screen.getByTestId("group-rule-group-input-1")).toHaveValue("viewers");
    expect(screen.getByTestId("group-rule-role-select-1")).toHaveValue("viewer");
  });

  it("renders empty state with no rows when initialRules is empty", () => {
    render(<GroupRuleEditor initialRules={[]} onSave={noop} />);
    expect(screen.queryByTestId("group-rule-row-0")).toBeNull();
  });

  it("adds a blank viewer row when Add rule is clicked", () => {
    render(<GroupRuleEditor initialRules={[]} onSave={noop} />);

    fireEvent.click(screen.getByTestId("group-rule-add"));

    expect(screen.getByTestId("group-rule-row-0")).toBeInTheDocument();
    expect(screen.getByTestId("group-rule-group-input-0")).toHaveValue("");
    expect(screen.getByTestId("group-rule-role-select-0")).toHaveValue("viewer");
  });

  it("removes the correct row when Remove is clicked", () => {
    render(
      <GroupRuleEditor
        initialRules={[
          { group: "admins", role: "admin" },
          { group: "editors", role: "editor" },
        ]}
        onSave={noop}
      />,
    );

    fireEvent.click(screen.getByTestId("group-rule-remove-0"));

    // Row 0 should now be the former "editors" row
    expect(screen.getByTestId("group-rule-group-input-0")).toHaveValue("editors");
    expect(screen.queryByTestId("group-rule-row-1")).toBeNull();
  });

  it("updates group name when user types in the input", () => {
    render(
      <GroupRuleEditor
        initialRules={[{ group: "admins", role: "admin" }]}
        onSave={noop}
      />,
    );

    const input = screen.getByTestId("group-rule-group-input-0");
    fireEvent.change(input, { target: { value: "super-admins" } });

    expect(input).toHaveValue("super-admins");
  });

  it("changes role when the select is updated — owner", () => {
    render(
      <GroupRuleEditor
        initialRules={[{ group: "admins", role: "admin" }]}
        onSave={noop}
      />,
    );

    fireEvent.change(screen.getByTestId("group-rule-role-select-0"), {
      target: { value: "owner" },
    });
    expect(screen.getByTestId("group-rule-role-select-0")).toHaveValue("owner");
  });

  it("changes role when the select is updated — editor", () => {
    render(
      <GroupRuleEditor
        initialRules={[{ group: "g", role: "admin" }]}
        onSave={noop}
      />,
    );

    fireEvent.change(screen.getByTestId("group-rule-role-select-0"), {
      target: { value: "editor" },
    });
    expect(screen.getByTestId("group-rule-role-select-0")).toHaveValue("editor");
  });

  it("calls onSave with current rules when Save is clicked", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <GroupRuleEditor
        initialRules={[{ group: "admins", role: "admin" }]}
        onSave={onSave}
      />,
    );

    fireEvent.click(screen.getByTestId("group-rule-save"));

    await waitFor(() => expect(onSave).toHaveBeenCalledWith([{ group: "admins", role: "admin" }]));
  });

  it("shows validation error when a group name is empty", () => {
    const onSave = vi.fn();
    render(<GroupRuleEditor initialRules={[{ group: "", role: "viewer" }]} onSave={onSave} />);

    fireEvent.click(screen.getByTestId("group-rule-save"));

    expect(screen.getByTestId("group-rule-error")).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("shows validation error for duplicate group names", () => {
    const onSave = vi.fn();
    render(
      <GroupRuleEditor
        initialRules={[
          { group: "admins", role: "admin" },
          { group: "admins", role: "editor" },
        ]}
        onSave={onSave}
      />,
    );

    fireEvent.click(screen.getByTestId("group-rule-save"));

    expect(screen.getByTestId("group-rule-error")).toHaveTextContent(/duplicate/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("shows success message after save resolves", async () => {
    render(
      <GroupRuleEditor
        initialRules={[{ group: "editors", role: "editor" }]}
        onSave={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    fireEvent.click(screen.getByTestId("group-rule-save"));

    expect(await screen.findByTestId("group-rule-success")).toBeInTheDocument();
  });

  it("shows error message when onSave rejects", async () => {
    render(
      <GroupRuleEditor
        initialRules={[{ group: "viewers", role: "viewer" }]}
        onSave={vi.fn().mockRejectedValue(new Error("Server unavailable"))}
      />,
    );

    fireEvent.click(screen.getByTestId("group-rule-save"));

    expect(await screen.findByTestId("group-rule-error")).toHaveTextContent(
      /Server unavailable/i,
    );
  });
});
