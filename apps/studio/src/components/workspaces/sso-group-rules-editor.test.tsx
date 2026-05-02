import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { SsoGroupRulesEditor, type SsoGroupRule } from "./sso-group-rules-editor";

describe("SsoGroupRulesEditor (S617)", () => {
  it("renders the empty-state row when no rules exist", () => {
    render(
      <SsoGroupRulesEditor rules={[]} onUpsert={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.getByTestId("sso-group-rules-empty")).toBeInTheDocument();
  });

  it("renders one row per existing rule with the role label", () => {
    const rules: SsoGroupRule[] = [
      { groupName: "loop-owners", role: "owner" },
      { groupName: "loop-editors", role: "editor" },
      { groupName: "loop-viewers", role: "viewer" },
    ];
    render(
      <SsoGroupRulesEditor rules={rules} onUpsert={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(
      screen.getByTestId("sso-group-rule-loop-owners").textContent,
    ).toMatch(/owner/i);
    expect(
      screen.getByTestId("sso-group-rule-loop-editors").textContent,
    ).toMatch(/editor/i);
    expect(
      screen.getByTestId("sso-group-rule-loop-viewers").textContent,
    ).toMatch(/viewer/i);
  });

  it("calls onUpsert with the trimmed group name and selected role", async () => {
    const onUpsert = vi.fn().mockResolvedValue(undefined);
    render(
      <SsoGroupRulesEditor rules={[]} onUpsert={onUpsert} onDelete={vi.fn()} />,
    );
    fireEvent.change(screen.getByTestId("sso-group-rules-name"), {
      target: { value: "  loop-admins  " },
    });
    fireEvent.change(screen.getByTestId("sso-group-rules-role"), {
      target: { value: "admin" },
    });
    fireEvent.click(screen.getByTestId("sso-group-rules-submit"));
    await waitFor(() => {
      expect(onUpsert).toHaveBeenCalledWith({
        groupName: "loop-admins",
        role: "admin",
      });
    });
  });

  it("rejects empty group name with a local error and does NOT call onUpsert", async () => {
    const onUpsert = vi.fn();
    render(
      <SsoGroupRulesEditor rules={[]} onUpsert={onUpsert} onDelete={vi.fn()} />,
    );
    fireEvent.click(screen.getByTestId("sso-group-rules-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("sso-group-rules-error").textContent).toMatch(
        /required/i,
      );
    });
    expect(onUpsert).not.toHaveBeenCalled();
  });

  it("calls onDelete when the remove button is clicked", () => {
    const onDelete = vi.fn();
    const rules: SsoGroupRule[] = [{ groupName: "loop-admins", role: "admin" }];
    render(
      <SsoGroupRulesEditor rules={rules} onUpsert={vi.fn()} onDelete={onDelete} />,
    );
    fireEvent.click(screen.getByTestId("sso-group-rule-delete-loop-admins"));
    expect(onDelete).toHaveBeenCalledWith("loop-admins");
  });

  it("surfaces the parent errorMessage", () => {
    render(
      <SsoGroupRulesEditor
        rules={[]}
        onUpsert={vi.fn()}
        onDelete={vi.fn()}
        errorMessage="cp-api 409: rule conflict"
      />,
    );
    expect(screen.getByTestId("sso-group-rules-error").textContent).toMatch(
      /409/,
    );
  });

  it("supports owner / editor / viewer assignment via the role select", async () => {
    const onUpsert = vi.fn().mockResolvedValue(undefined);
    render(
      <SsoGroupRulesEditor rules={[]} onUpsert={onUpsert} onDelete={vi.fn()} />,
    );
    for (const [groupName, role] of [
      ["g-owner", "owner"],
      ["g-editor", "editor"],
      ["g-viewer", "viewer"],
    ] as const) {
      fireEvent.change(screen.getByTestId("sso-group-rules-name"), {
        target: { value: groupName },
      });
      fireEvent.change(screen.getByTestId("sso-group-rules-role"), {
        target: { value: role },
      });
      fireEvent.click(screen.getByTestId("sso-group-rules-submit"));
      await waitFor(() =>
        expect(onUpsert).toHaveBeenCalledWith({ groupName, role }),
      );
    }
    expect(onUpsert).toHaveBeenCalledTimes(3);
  });
});
