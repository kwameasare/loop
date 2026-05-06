import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createBlockedConductorData,
  createConductorData,
} from "@/lib/conductor";

import { ConductorStudio } from "./conductor-studio";

describe("ConductorStudio", () => {
  it("renders sub-agent assets, contracts, ownership, and traceable delegation", () => {
    render(<ConductorStudio data={createConductorData("agent_support")} />);

    expect(screen.getByTestId("conductor-studio")).toHaveTextContent(
      "Multi-agent conductor",
    );
    expect(screen.getByTestId("conductor-assets")).toHaveTextContent(
      "Refund Specialist",
    );
    expect(screen.getByTestId("conductor-assets")).toHaveTextContent(
      "Revenue Operations",
    );
    expect(screen.getByTestId("conductor-contracts")).toHaveTextContent(
      "Cancellation intent to refund policy",
    );
    expect(screen.getByTestId("conductor-contract-detail")).toHaveTextContent(
      "intent, channel, order_id, confidence",
    );
    expect(screen.getByTestId("conductor-contract-detail")).toHaveTextContent(
      "session read, scratch read/write, durable user read only",
    );
    expect(screen.getByTestId("conductor-delegation")).toHaveTextContent(
      "trace_refund_742#span_context",
    );
  });

  it("switches inspector and shows failure paths for a degraded sub-agent", () => {
    render(<ConductorStudio data={createConductorData("agent_support")} />);

    fireEvent.click(
      screen.getByTestId("conductor-agent-sub_retention_guardian"),
    );

    expect(screen.getByTestId("conductor-inspector")).toHaveTextContent(
      "Retention Guardian",
    );
    expect(screen.getByTestId("conductor-inspector")).toHaveTextContent(
      "No tool grants for this sub-agent",
    );
    expect(screen.getByTestId("conductor-failure")).toHaveTextContent(
      "Legal-threat language escalates to inbox",
    );
  });

  it("makes handoff violations explicit with fallback and evidence", () => {
    render(<ConductorStudio data={createConductorData("agent_support")} />);

    fireEvent.click(
      screen.getByTestId("conductor-contract-contract_refund_to_retention"),
    );

    expect(screen.getByTestId("conductor-contract-detail")).toHaveTextContent(
      "customer_segment missing",
    );
    expect(screen.getByTestId("conductor-contract-detail")).toHaveTextContent(
      "Hold the answer and create an inbox task",
    );
    expect(screen.getByTestId("conductor-contract-detail")).toHaveTextContent(
      "trace_refund_742#handoff_review",
    );
  });

  it("renders the permission-blocked conductor state without hiding topology", () => {
    render(
      <ConductorStudio data={createBlockedConductorData("agent_support")} />,
    );

    expect(screen.getByText("Conductor editing locked")).toBeInTheDocument();
    expect(screen.getByTestId("conductor-request-approval")).toBeDisabled();
    expect(screen.getByTestId("conductor-topology")).toHaveTextContent(
      "violated contract",
    );
    expect(screen.getByTestId("conductor-contracts")).toHaveTextContent(
      "Blocked by workspace policy",
    );
  });
});
