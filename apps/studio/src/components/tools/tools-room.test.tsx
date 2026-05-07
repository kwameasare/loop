import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createEmptyToolsRoomData,
  createToolsRoomData,
} from "@/lib/agent-tools";

import { ToolsRoom } from "./tools-room";

describe("ToolsRoom", () => {
  it("renders catalog, detail, safety, mock/live, usage, cost, and eval coverage", () => {
    render(<ToolsRoom data={createToolsRoomData("agent_support")} />);

    expect(screen.getByTestId("tools-room")).toHaveTextContent("Tools Room");
    expect(screen.getByTestId("tools-room-catalog")).toHaveTextContent(
      "lookup_order",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent("Schema");
    expect(screen.getByTestId("tools-room-auth")).toHaveTextContent(
      "Secret reference",
    );
    expect(screen.getByTestId("tools-room-safety")).toHaveTextContent(
      "Safety contract",
    );
    expect(screen.getByTestId("tools-room-mock-live")).toHaveTextContent(
      "Mock and live status",
    );
    expect(
      screen.getByRole("meter", { name: "Eval coverage" }),
    ).toHaveAttribute("aria-valuenow", "96");
  });

  it("shows production grant boundaries for money-moving tools", () => {
    render(<ToolsRoom data={createToolsRoomData("agent_support")} />);

    fireEvent.click(screen.getByTestId("tools-room-catalog-tool_issue_refund"));
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "issue_refund",
    );
    expect(
      screen.getByTestId("tools-room-production-boundary"),
    ).toHaveTextContent("Production grant blocked");
    expect(screen.getByTestId("tools-room-grant-production")).toBeDisabled();
  });

  it("drafts a typed tool from a curl request and redacts auth", () => {
    render(<ToolsRoom data={createToolsRoomData("agent_support")} />);

    expect(screen.getByTestId("tools-room-source-devtools")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("tools-room-draft-tool"));
    const draft = screen.getByTestId("tools-room-draft");
    expect(draft).toHaveTextContent("api_example_test");
    expect(draft).toHaveTextContent("Authorization header detected");
    expect(draft).toHaveTextContent("redacted");
    expect(draft).toHaveTextContent("Draft only");
    expect(draft).not.toHaveTextContent("Bearer <redacted>");

    fireEvent.click(screen.getByTestId("tools-room-add-library"));
    expect(draft).toHaveTextContent("Added to the draft tool library");
  });

  it("renders an empty state with the import flow still available", () => {
    render(<ToolsRoom data={createEmptyToolsRoomData("agent_empty")} />);

    expect(screen.getByText("Tool catalog is empty")).toBeInTheDocument();
    expect(screen.getByText("No tools bound yet")).toBeInTheDocument();
    expect(screen.getByTestId("tools-room-import")).toBeInTheDocument();
  });
});
