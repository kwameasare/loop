import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentContractPanel } from "./agent-contract-panel";
import {
  type CommitmentBody,
  type CommitmentDocument,
  EMPTY_COMMITMENT_BODY,
  buildLocalCommitmentDocument,
} from "@/lib/agent-commitment";

function makeDocument(
  body: CommitmentBody = EMPTY_COMMITMENT_BODY,
  overrides: Partial<CommitmentDocument> = {},
): CommitmentDocument {
  return {
    ...buildLocalCommitmentDocument("agt_1", body),
    id: "commit_1",
    workspace_id: "ws_1",
    version: 1,
    content_hash: "abcdef1234567890",
    ...overrides,
  };
}

function fill(testId: string, value: string) {
  fireEvent.change(screen.getByTestId(testId), { target: { value } });
}

const COMPLETE_BODY: CommitmentBody = {
  ...EMPTY_COMMITMENT_BODY,
  business_responsibility: "Resolve billing cancellations safely.",
  target_users: "Enterprise customers.",
  owner_user_id: "maya@acme.test",
  backup_owner_user_id: "diego@acme.test",
  worst_case_failure: "Promises a refund outside policy.",
  channels: ["web", "whatsapp", "voice"],
  systems_touched: ["billing", "crm"],
  regions: ["us-east-1"],
  languages: ["en"],
};

describe("AgentContractPanel", () => {
  it("shows required gaps and blocks acceptance until the contract is complete", () => {
    render(
      <AgentContractPanel
        agentId="agt_1"
        initialDocument={makeDocument()}
        saveDraft={vi.fn()}
        acceptCommitment={vi.fn()}
      />,
    );

    expect(screen.getByTestId("contract-missing-fields")).toHaveTextContent(
      "Business responsibility",
    );
    expect(
      (screen.getByTestId("contract-accept") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("disables save and accept when the Commitment backend is unavailable", () => {
    render(
      <AgentContractPanel
        agentId="agt_1"
        initialDocument={makeDocument(COMPLETE_BODY)}
        degradedReason="LOOP_CP_API_BASE_URL is required for cp-api calls."
        saveDraft={vi.fn()}
        acceptCommitment={vi.fn()}
      />,
    );

    const degraded = screen.getByTestId("contract-degraded");
    expect(degraded).toHaveTextContent("Agent Contract is degraded");
    expect(degraded).toHaveTextContent(
      "save and accept are disabled until backend evidence is available",
    );
    expect(degraded).toHaveTextContent(
      "LOOP_CP_API_BASE_URL is required for cp-api calls",
    );
    expect(
      (screen.getByTestId("contract-save-draft") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("contract-accept") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("saves a detailed contract draft", async () => {
    const saveDraft = vi.fn(async (_agentId: string, input) =>
      makeDocument(input.body, {
        id: "commit_saved",
        version: 2,
        content_hash: "savedhash123",
      }),
    );
    render(
      <AgentContractPanel
        agentId="agt_1"
        initialDocument={makeDocument()}
        saveDraft={saveDraft}
        acceptCommitment={vi.fn()}
      />,
    );

    fill(
      "contract-business-responsibility",
      COMPLETE_BODY.business_responsibility,
    );
    fill("contract-target-users", COMPLETE_BODY.target_users);
    fill("contract-owner", COMPLETE_BODY.owner_user_id);
    fill("contract-worst-case-failure", COMPLETE_BODY.worst_case_failure);
    fill("contract-channels", "web, whatsapp, voice");
    fill("contract-systems", "billing, crm");
    fill("contract-regions", "us-east-1");
    fill("contract-languages", "en");
    fireEvent.click(screen.getByTestId("contract-save-draft"));

    await waitFor(() => {
      expect(saveDraft).toHaveBeenCalledWith(
        "agt_1",
        expect.objectContaining({
          body: expect.objectContaining({
            business_responsibility: COMPLETE_BODY.business_responsibility,
            channels: ["web", "whatsapp", "voice"],
          }),
        }),
      );
    });
    expect(await screen.findByTestId("contract-success")).toHaveTextContent(
      "Draft v2 saved",
    );
  });

  it("saves the latest fields before accepting the contract", async () => {
    const saveDraft = vi.fn(async (_agentId: string, input) =>
      makeDocument(input.body, {
        id: "commit_saved",
        version: 1,
        content_hash: "readyhash123",
      }),
    );
    const acceptCommitment = vi.fn(async () =>
      makeDocument(COMPLETE_BODY, {
        id: "commit_saved",
        version: 1,
        status: "accepted",
        accepted_at: "2026-05-09T12:00:00Z",
        content_hash: "readyhash123",
      }),
    );
    render(
      <AgentContractPanel
        agentId="agt_1"
        initialDocument={makeDocument(COMPLETE_BODY)}
        saveDraft={saveDraft}
        acceptCommitment={acceptCommitment}
      />,
    );

    expect(screen.getByTestId("contract-ready")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("contract-accept"));

    await waitFor(() => {
      expect(saveDraft).toHaveBeenCalled();
      expect(acceptCommitment).toHaveBeenCalledWith("agt_1");
    });
    expect(screen.getByTestId("contract-status")).toHaveTextContent("accepted");
  });
});
