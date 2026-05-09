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
      screen.getByTestId("change-package-approval-owner"),
    ).toHaveTextContent("Agent owner");
    expect(screen.getByTestId("change-package-diff")).toHaveTextContent(
      "Adds verification",
    );
    expect(screen.getByTestId("change-package-evidence")).toHaveTextContent(
      "commit_1",
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
});
