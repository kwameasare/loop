import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  localAgentHandoff,
  type OwnershipTransferInput,
} from "@/lib/agent-handoff";
import { AgentHistoryWalkthrough } from "./agent-history-walkthrough";

describe("AgentHistoryWalkthrough", () => {
  const ORIGINAL_BASE_URL = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (ORIGINAL_BASE_URL === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE_URL;
    }
  });

  it("shows open risks, walkthrough sections, and transfers ownership", async () => {
    const transferAgentOwner = vi.fn(
      async (_agentId: string, input: OwnershipTransferInput) => {
        const base = localAgentHandoff("agent_1");
        return {
          ...base,
          owner_user_id: input.new_owner_user_id,
          backup_owner_user_id: input.backup_owner_user_id ?? "",
          transfers: [
            {
              id: "handoff_transfer_1",
              workspace_id: base.commitment.workspace_id,
              agent_id: "agent_1",
              previous_owner_user_id: base.owner_user_id,
              new_owner_user_id: input.new_owner_user_id,
              backup_owner_user_id: input.backup_owner_user_id ?? "",
              reason: input.reason ?? "",
              acknowledged_risk_ids: input.acknowledged_risk_ids ?? [],
              open_risk_ids: base.open_risks.map((risk) => risk.id),
              walkthrough_section_ids: base.walkthrough_sections.map(
                (section) => section.id,
              ),
              notification: {
                recipient: input.new_owner_user_id,
                channel: "in_app",
                status: "sent",
                sent_at: "2026-05-09T00:00:00Z",
                summary: "History walkthrough sent.",
              },
              history_walkthrough_id: "walkthrough_1",
              created_by_user_id: "owner",
              created_at: "2026-05-09T00:00:00Z",
            },
          ],
        };
      },
    );

    const initialModel = {
      ...localAgentHandoff("agent_1"),
      walkthrough_sections: localAgentHandoff(
        "agent_1",
      ).walkthrough_sections.map((section) =>
        section.id === "tool-grants"
          ? {
              ...section,
              count: 1,
              evidence_refs: ["tool-contract/tc_refund"],
            }
          : section,
      ),
    };

    render(
      <AgentHistoryWalkthrough
        agentId="agent_1"
        initialModel={initialModel}
        transferAgentOwner={transferAgentOwner}
      />,
    );

    expect(screen.getByTestId("handoff-current-owner")).toHaveTextContent(
      "Unassigned",
    );
    expect(
      screen.getByTestId("handoff-risk-commitment_missing_fields"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("walkthrough-section-commitments"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("walkthrough-section-tool-grants"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("walkthrough-section-memory-policies"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("walkthrough-section-eval-coverage"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("walkthrough-section-risk-posture"),
    ).toBeInTheDocument();
    const commitmentLinks = screen.getAllByTestId(
      "handoff-evidence-link-commitment_commitment_unconfigured",
    );
    expect(commitmentLinks[0]).toHaveAttribute(
      "href",
      "/agents/agent_1/contract?commitment_id=commitment_unconfigured",
    );
    expect(
      screen.getByTestId("handoff-evidence-link-tool-contract_tc_refund"),
    ).toHaveAttribute(
      "href",
      "/agents/agent_1/tools?tool_contract_id=tc_refund",
    );

    fireEvent.change(screen.getByTestId("handoff-new-owner"), {
      target: { value: "new-owner@acme.test" },
    });
    fireEvent.change(screen.getByTestId("handoff-backup-owner"), {
      target: { value: "backup@acme.test" },
    });
    fireEvent.click(screen.getByTestId("handoff-transfer"));

    await waitFor(() =>
      expect(screen.getByTestId("handoff-current-owner")).toHaveTextContent(
        "new-owner@acme.test",
      ),
    );
    expect(screen.getByTestId("handoff-transfers")).toHaveTextContent(
      "new-owner@acme.test",
    );
    expect(screen.getByTestId("handoff-transfers")).toHaveTextContent(
      "Walkthrough sent to new-owner@acme.test",
    );
    expect(screen.getByTestId("handoff-transfers")).toHaveTextContent(
      "risks: commitment_missing_fields",
    );
    expect(screen.getByTestId("handoff-notice")).toHaveTextContent(
      /Ownership transfer recorded/i,
    );
  });

  it("does not transfer ownership locally when cp-api is missing", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(
      <AgentHistoryWalkthrough
        agentId="agent_1"
        initialModel={localAgentHandoff("agent_1")}
      />,
    );

    fireEvent.change(screen.getByTestId("handoff-new-owner"), {
      target: { value: "new-owner@acme.test" },
    });
    fireEvent.click(screen.getByTestId("handoff-transfer"));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("handoff-current-owner")).toHaveTextContent(
      "Unassigned",
    );
    expect(screen.queryByTestId("handoff-transfers")).not.toBeInTheDocument();
  });

  it("keeps the selected evidence ref visible during handoff review", () => {
    const initialModel = {
      ...localAgentHandoff("agent_1"),
      walkthrough_sections: localAgentHandoff("agent_1").walkthrough_sections.map(
        (section) =>
          section.id === "important-comments"
            ? {
                ...section,
                evidence_refs: ["comment/cmt_handoff"],
              }
            : section,
      ),
    };

    render(
      <AgentHistoryWalkthrough
        agentId="agent_1"
        focusedEvidenceRef="comment/cmt_handoff"
        initialModel={initialModel}
      />,
    );

    expect(screen.getByTestId("handoff-focused-evidence")).toHaveTextContent(
      "comment/cmt_handoff",
    );
    expect(
      screen.getByTestId("handoff-evidence-link-comment_cmt_handoff"),
    ).toHaveClass("text-info");
  });
});
