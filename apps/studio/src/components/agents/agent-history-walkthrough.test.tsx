import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { localAgentHandoff } from "@/lib/agent-handoff";
import { AgentHistoryWalkthrough } from "./agent-history-walkthrough";

describe("AgentHistoryWalkthrough", () => {
  it("shows open risks, walkthrough sections, and transfers ownership", async () => {
    render(
      <AgentHistoryWalkthrough
        agentId="agent_1"
        initialModel={localAgentHandoff("agent_1")}
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
    const commitmentLinks = screen.getAllByTestId(
      "handoff-evidence-link-commitment_commitment_unconfigured",
    );
    expect(commitmentLinks[0]).toHaveAttribute(
      "href",
      "/agents/agent_1/contract?commitment_id=commitment_unconfigured",
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
});
