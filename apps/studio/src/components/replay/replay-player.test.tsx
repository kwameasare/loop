import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import { ReplayPlayer } from "./replay-player";
import { FIXTURE_REPLAY } from "@/lib/replay";

describe("ReplayPlayer", () => {
  it("starts at the first step and shows the user prompt", () => {
    render(<ReplayPlayer trace={FIXTURE_REPLAY} />);
    const bubbles = screen.getAllByTestId("replay-bubble");
    expect(bubbles).toHaveLength(1);
    expect(bubbles[0]).toHaveAttribute("data-role", "user");
    expect(screen.getByTestId("replay-cursor")).toHaveTextContent(
      `1 / ${FIXTURE_REPLAY.events.length}`,
    );
  });

  it("scrubbing forward through tokens collapses to one agent bubble", () => {
    render(<ReplayPlayer trace={FIXTURE_REPLAY} />);
    const scrubber = screen.getByTestId("replay-scrubber");
    fireEvent.change(scrubber, { target: { value: "5" } });
    const agentBubbles = screen
      .getAllByTestId("replay-bubble")
      .filter((b) => b.getAttribute("data-role") === "agent");
    expect(agentBubbles).toHaveLength(1);
    expect(agentBubbles[0]).toHaveTextContent("Your order shipped.");
  });

  it("clicking next jumps to the next boundary, skipping tokens", () => {
    render(<ReplayPlayer trace={FIXTURE_REPLAY} />);
    fireEvent.click(screen.getByTestId("replay-next")); // 0 -> tool_call_end (2)
    expect(screen.getByTestId("replay-cursor")).toHaveTextContent("3 / 7");
    fireEvent.click(screen.getByTestId("replay-next")); // 2 -> agent_message (6)
    expect(screen.getByTestId("replay-cursor")).toHaveTextContent("7 / 7");
  });

  it("clicking prev rewinds to the previous boundary", () => {
    render(<ReplayPlayer trace={FIXTURE_REPLAY} />);
    fireEvent.click(screen.getByTestId("replay-last"));
    fireEvent.click(screen.getByTestId("replay-prev"));
    expect(screen.getByTestId("replay-cursor")).toHaveTextContent("3 / 7");
  });

  it("renders the active event detail with attributes", () => {
    render(<ReplayPlayer trace={FIXTURE_REPLAY} />);
    fireEvent.change(screen.getByTestId("replay-scrubber"), {
      target: { value: "2" },
    });
    const detail = screen.getByTestId("replay-event-detail");
    expect(detail).toHaveTextContent("Tool call finished");
    expect(detail).toHaveTextContent("status");
    expect(detail).toHaveTextContent("shipped");
  });

  it("renders an empty state when there are no events", () => {
    render(
      <ReplayPlayer
        trace={{ id: "x", conversation_id: "y", events: [] }}
      />,
    );
    expect(screen.queryAllByTestId("replay-bubble")).toHaveLength(0);
    expect(
      screen.getByTestId("replay-event-detail"),
    ).toHaveTextContent("No event selected");
  });

  it("runs a target-version replay and renders the side-by-side diff", () => {
    render(<ReplayPlayer trace={FIXTURE_REPLAY} />);

    fireEvent.change(screen.getByTestId("replay-target-version"), {
      target: { value: "agent-canary" },
    });
    fireEvent.click(screen.getByTestId("replay-run"));

    expect(screen.getByTestId("replay-run-status")).toHaveTextContent(
      `agent-canary:${FIXTURE_REPLAY.events.length}`,
    );
    const changed = screen
      .getAllByTestId("replay-diff-row")
      .filter((row) => row.getAttribute("data-status") === "changed");
    expect(changed).toHaveLength(1);
    expect(changed[0]).toHaveTextContent("agent-canary");
  });
});
