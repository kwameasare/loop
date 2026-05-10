import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PreApprovedClass } from "@/lib/pre-approved-classes";

import { PreApprovedClassesPanel } from "./pre-approved-classes-panel";

const CLASS: PreApprovedClass = {
  id: "pac_123",
  workspace_id: "workspace_1",
  agent_id: "agent_1",
  granted_by_user_id: "security@example.com",
  granted_to_user_id: "builder@example.com",
  team_id: "",
  allowed_change_types: ["instruction"],
  excluded_change_types: ["tool", "memory", "channel", "budget"],
  risk_ceiling: "low",
  expires_at: "2026-05-16T00:00:00Z",
  status: "active",
  reason: "Instruction-only copy fixes.",
  created_at: "2026-05-09T00:00:00Z",
  updated_at: "2026-05-09T00:00:00Z",
  revoked_at: null,
  expired_at: null,
  invalidated_at: null,
  used_by_change_packages: ["cp_1"],
};

describe("PreApprovedClassesPanel", () => {
  it("creates narrow pre-approved classes and revokes active classes", async () => {
    const createClass = vi.fn(async () => ({
      ...CLASS,
      id: "pac_new",
      granted_to_user_id: "owner@example.com",
      allowed_change_types: ["instruction", "tone"],
      excluded_change_types: ["tool"],
    }));
    const revokeClass = vi.fn(async () => ({
      ...CLASS,
      status: "revoked" as const,
      revoked_at: "2026-05-10T00:00:00Z",
    }));

    render(
      <PreApprovedClassesPanel
        agentId="agent_1"
        initialItems={[CLASS]}
        createClass={createClass}
        revokeClass={revokeClass}
      />,
    );

    expect(screen.getByTestId("preapproved-class-pac_123")).toHaveTextContent(
      "risk <= low",
    );
    expect(screen.getByTestId("preapproved-usage-pac_123")).toHaveTextContent(
      "Used by",
    );
    expect(screen.getByTestId("preapproved-usage-link-cp_1")).toHaveAttribute(
      "href",
      "/agents/agent_1/deploys?change_package_id=cp_1",
    );
    fireEvent.change(screen.getByTestId("preapproved-user"), {
      target: { value: "owner@example.com" },
    });
    fireEvent.change(screen.getByTestId("preapproved-allowed"), {
      target: { value: "instruction,tone" },
    });
    fireEvent.change(screen.getByTestId("preapproved-excluded"), {
      target: { value: "tool" },
    });
    fireEvent.change(screen.getByTestId("preapproved-reason"), {
      target: { value: "Copy-only launch window." },
    });
    fireEvent.click(screen.getByTestId("preapproved-create"));

    expect(await screen.findByText(/Created pre-approved class pac_new/i)).toBeInTheDocument();
    expect(createClass).toHaveBeenCalledWith(
      "agent_1",
      expect.objectContaining({
        granted_to_user_id: "owner@example.com",
        allowed_change_types: ["instruction", "tone"],
        excluded_change_types: ["tool"],
        risk_ceiling: "low",
        reason: "Copy-only launch window.",
      }),
    );

    fireEvent.click(screen.getByTestId("preapproved-revoke-pac_123"));
    expect(await screen.findByText(/Revoked pre-approved class pac_123/i)).toBeInTheDocument();
    expect(revokeClass).toHaveBeenCalledWith("agent_1", "pac_123");
  });

  it("shows expired corridors as automatically revoked evidence", () => {
    render(
      <PreApprovedClassesPanel
        agentId="agent_1"
        initialItems={[
          {
            ...CLASS,
            status: "expired",
            expired_at: "2026-05-10T00:00:00Z",
            revoked_at: "2026-05-10T00:00:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText(/0 active pre-approved classes/i)).toBeInTheDocument();
    expect(screen.getByText(/1 closed corridor retained/i)).toBeInTheDocument();
    expect(screen.getByTestId("preapproved-lifecycle-pac_123")).toHaveTextContent(
      "Automatically expired and revoked 2026-05-10T00:00:00Z.",
    );
    expect(screen.getByTestId("preapproved-revoke-pac_123")).toBeDisabled();
  });

  it("requires a grantee and allowed change types before creating", async () => {
    const createClass = vi.fn();

    render(
      <PreApprovedClassesPanel
        agentId="agent_1"
        initialItems={[]}
        createClass={createClass}
      />,
    );

    fireEvent.click(screen.getByTestId("preapproved-create"));
    expect(await screen.findByText("Grant the class to a user or a team.")).toBeInTheDocument();
    expect(createClass).not.toHaveBeenCalled();

    fireEvent.change(screen.getByTestId("preapproved-user"), {
      target: { value: "owner@example.com" },
    });
    fireEvent.change(screen.getByTestId("preapproved-allowed"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByTestId("preapproved-create"));
    expect(await screen.findByText("Add at least one allowed change type.")).toBeInTheDocument();
  });

  it("requires explicit exclusions and blocks long-lived corridors", async () => {
    const createClass = vi.fn();

    render(
      <PreApprovedClassesPanel
        agentId="agent_1"
        initialItems={[]}
        createClass={createClass}
      />,
    );
    expect(screen.queryByRole("option", { name: "High" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId("preapproved-user"), {
      target: { value: "owner@example.com" },
    });
    fireEvent.change(screen.getByTestId("preapproved-excluded"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByTestId("preapproved-create"));
    expect(
      await screen.findByText("Name the excluded change types so the corridor stays narrow."),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByTestId("preapproved-excluded"), {
      target: { value: "tool,memory,channel,budget" },
    });
    fireEvent.change(screen.getByTestId("preapproved-expires"), {
      target: {
        value: new Date(Date.now() + 31 * 24 * 60 * 60 * 1000)
          .toISOString()
          .slice(0, 16),
      },
    });
    fireEvent.click(screen.getByTestId("preapproved-create"));
    expect(
      await screen.findByText("Pre-approved classes cannot run longer than 30 days."),
    ).toBeInTheDocument();
    expect(createClass).not.toHaveBeenCalled();
  });
});
