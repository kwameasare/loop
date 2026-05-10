import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChangePackagePanel } from "./change-package-panel";
import {
  type ChangePackage,
  buildLocalChangePackage,
} from "@/lib/change-package";

function makePackage(overrides: Partial<ChangePackage> = {}): ChangePackage {
  return {
    ...buildLocalChangePackage("agt_1"),
    id: "cp_1",
    status: "generated",
    summary: "Promote draft to canary.",
    commitment_document_id: "commit_1",
    commitment_document_version: 2,
    release_candidate_id: "rc_refund_v2",
    content_hash: "abcdef1234567890",
    semantic_diff: [
      {
        dimension: "behavior",
        summary: "Adds verification before refund answer.",
        evidence_ref: "trace/replay/refund",
      },
    ],
    required_approvals: [
      {
        id: "owner",
        role: "Agent owner",
        required: true,
        satisfied: false,
        reason: "Owner must approve Commitment v2.",
      },
    ],
    evidence: {
      commitment: "commit_1",
      replay_results: "replay/run/refund",
    },
    ...overrides,
  };
}

describe("ChangePackagePanel", () => {
  it("renders the current package summary, hash, approvals, diff, and evidence", () => {
    render(
      <ChangePackagePanel agentId="agt_1" initialPackage={makePackage()} />,
    );

    expect(screen.getByTestId("change-package-status")).toHaveTextContent(
      "generated",
    );
    expect(screen.getByTestId("change-package-summary")).toHaveTextContent(
      "Promote draft to canary",
    );
    expect(screen.getByTestId("change-package-commitment")).toHaveTextContent(
      "commit_1 v2",
    );
    expect(
      screen.getByTestId("change-package-release-candidate"),
    ).toHaveTextContent("rc_refund_v2");
    expect(
      screen.getByTestId("change-package-approval-owner"),
    ).toHaveTextContent("Agent owner");
    expect(screen.getByTestId("change-package-diff")).toHaveTextContent(
      "Adds verification",
    );
    expect(
      screen.getByTestId("change-package-version-manifest"),
    ).toHaveTextContent("Behavior policy changes");
    expect(
      screen.getByTestId("change-package-version-manifest"),
    ).toHaveTextContent("rc_refund_v2");
    expect(
      screen.getByTestId("change-package-version-manifest"),
    ).toHaveTextContent("Rollback target");
    expect(screen.getByTestId("change-package-evidence")).toHaveTextContent(
      "commit_1",
    );
    expect(screen.getByTestId("change-package-preapprovals")).toHaveTextContent(
      "No pre-approved class",
    );
  });

  it("focuses a Change Package opened from an evidence link", () => {
    render(
      <ChangePackagePanel
        agentId="agt_1"
        focusedChangePackageId="cp_1"
        initialPackage={makePackage()}
      />,
    );

    expect(screen.getByTestId("change-package-panel")).toHaveAttribute(
      "data-focused",
      "true",
    );
    expect(screen.getByTestId("change-package-focused")).toHaveTextContent(
      "Change Package cp_1 is focused",
    );
  });

  it("focuses the Change Package panel from Workbench controls", () => {
    render(
      <ChangePackagePanel
        agentId="agt_1"
        focusedPanel="change-package"
        initialPackage={makePackage()}
      />,
    );

    expect(screen.getByTestId("change-package-panel")).toHaveAttribute(
      "data-focused",
      "true",
    );
    expect(
      screen.getByTestId("change-package-focused-workbench-panel"),
    ).toHaveTextContent("Change Package evidence is highlighted");
  });

  it("focuses release candidate and rollback panels from evidence links", () => {
    const view = render(
      <ChangePackagePanel
        agentId="agt_1"
        focusedPanel="release-candidate"
        initialPackage={makePackage()}
      />,
    );

    expect(screen.getByTestId("change-package-focused-panel")).toHaveTextContent(
      "release candidate evidence is highlighted",
    );
    expect(
      screen.getByTestId("change-package-release-candidate-card"),
    ).toHaveAttribute("data-focused", "true");
    expect(
      screen.getByTestId("change-package-release-candidate-card"),
    ).toHaveTextContent("rc_refund_v2");

    view.unmount();
    render(
      <ChangePackagePanel
        agentId="agt_1"
        focusedPanel="rollback"
        initialPackage={makePackage({
          rollback_target_version_id: "last-known-safe",
        })}
      />,
    );

    expect(screen.getByTestId("change-package-focused-panel")).toHaveTextContent(
      "rollback target evidence is highlighted",
    );
    expect(screen.getByTestId("change-package-rollback-card")).toHaveAttribute(
      "data-focused",
      "true",
    );
    expect(screen.getByTestId("change-package-rollback-card")).toHaveTextContent(
      "last-known-safe",
    );
  });

  it("warns when a package is stale and approvals must be re-requested", () => {
    render(
      <ChangePackagePanel
        agentId="agt_1"
        initialPackage={makePackage({
          stale_at: "2026-05-09T13:00:00Z",
          status: "stale",
        })}
      />,
    );

    expect(screen.getByTestId("change-package-stale-warning")).toHaveTextContent(
      "approvals must be re-requested",
    );
    expect(screen.getByTestId("change-package-status")).toHaveTextContent(
      "stale",
    );
  });

  it("surfaces expired approval requests inline", () => {
    render(
      <ChangePackagePanel
        agentId="agt_1"
        initialPackage={makePackage({
          status: "changes_requested",
          approval_status: "expired",
          required_approvals: [
            {
              id: "compliance",
              role: "Compliance reviewer",
              required: true,
              satisfied: false,
              state: "expired",
              reason: "Compliance review required.",
              expired_reason: "Compliance review SLA elapsed.",
            },
          ],
        })}
      />,
    );

    expect(
      screen.getByTestId("change-package-approval-expired-compliance"),
    ).toHaveTextContent("Compliance review SLA elapsed.");
    expect(
      screen.getByTestId("change-package-approval-compliance"),
    ).toHaveTextContent("expired");
  });

  it("shows pre-approved class usage without hiding excluded boundaries", () => {
    render(
      <ChangePackagePanel
        agentId="agt_1"
        initialPackage={makePackage({
          approval_status: "approved",
          required_approvals: [
            {
              id: "owner",
              role: "Agent owner",
              required: true,
              satisfied: true,
              state: "pre_approved",
              reason: "Covered by pre-approved class pac_123.",
            },
          ],
          pre_approved_classes: [
            {
              id: "pac_123",
              allowed_change_types: ["instruction"],
              excluded_change_types: ["tool", "memory", "channel", "budget"],
              risk_ceiling: "low",
              expires_at: "2026-05-16T00:00:00Z",
              status: "active",
              matched_change_types: ["instruction"],
              matched_risk: "low",
            },
          ],
        })}
      />,
    );

    expect(screen.getByTestId("change-package-preapprovals")).toHaveTextContent(
      "pac_123",
    );
    expect(screen.getByTestId("change-package-preapprovals")).toHaveTextContent(
      "Excluded: tool, memory, channel, budget",
    );
  });

  it("generates preflight from an empty package", async () => {
    const generateChangePackage = vi.fn(async () =>
      makePackage({ id: "cp_new" }),
    );
    render(
      <ChangePackagePanel
        agentId="agt_1"
        initialPackage={null}
        generateChangePackage={generateChangePackage}
        submitChangePackage={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId("change-package-generate"));

    await waitFor(() => {
      expect(generateChangePackage).toHaveBeenCalledWith(
        "agt_1",
        expect.objectContaining({
          target_environment: "production",
          summary: "Generate preflight evidence for the current draft.",
        }),
      );
    });
    expect(screen.getByTestId("change-package-status")).toHaveTextContent(
      "generated",
    );
  });

  it("disables preflight actions when the Change Package backend is unavailable", () => {
    render(
      <ChangePackagePanel
        agentId="agt_1"
        initialPackage={makePackage()}
        degradedReason="LOOP_CP_API_BASE_URL is required for cp-api calls."
        generateChangePackage={vi.fn()}
        submitChangePackage={vi.fn()}
      />,
    );

    expect(screen.getByTestId("change-package-degraded")).toHaveTextContent(
      "Change Package backend unavailable",
    );
    expect(
      (screen.getByTestId("change-package-generate") as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("change-package-submit") as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it("submits a generated package for approval", async () => {
    const submitChangePackage = vi.fn(async () =>
      makePackage({
        status: "submitted",
        submitted_at: "2026-05-09T12:00:00Z",
      }),
    );
    render(
      <ChangePackagePanel
        agentId="agt_1"
        initialPackage={makePackage()}
        generateChangePackage={vi.fn()}
        submitChangePackage={submitChangePackage}
      />,
    );

    fireEvent.click(screen.getByTestId("change-package-submit"));

    await waitFor(() => {
      expect(submitChangePackage).toHaveBeenCalledWith("agt_1", "cp_1");
    });
    expect(screen.getByTestId("change-package-status")).toHaveTextContent(
      "submitted",
    );
  });

  it("records approval decisions against the package content hash", async () => {
    const reviewed = makePackage({
      status: "approved",
      approval_status: "approved",
      required_approvals: [
        {
          id: "owner",
          role: "Agent owner",
          required: true,
          satisfied: true,
          state: "approved",
          reason: "Owner must approve Commitment v2.",
          content_hash: "abcdef1234567890",
        },
      ],
    });
    const recordChangePackageApproval = vi.fn(async () => reviewed);
    render(
      <ChangePackagePanel
        agentId="agt_1"
        initialPackage={makePackage({ status: "submitted" })}
        generateChangePackage={vi.fn()}
        submitChangePackage={vi.fn()}
        recordChangePackageApproval={recordChangePackageApproval}
      />,
    );

    fireEvent.click(screen.getByTestId("change-package-approve-owner"));

    await waitFor(() => {
      expect(recordChangePackageApproval).toHaveBeenCalledWith(
        "agt_1",
        "cp_1",
        expect.objectContaining({
          approval_id: "owner",
          decision: "approve",
        }),
        expect.objectContaining({ content_hash: "abcdef1234567890" }),
      );
    });
    expect(screen.getByTestId("change-package-status")).toHaveTextContent(
      "approved",
    );
    expect(
      screen.getByTestId("change-package-approval-owner"),
    ).toHaveTextContent("hash abcdef123456");
  });
});
