import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { captureFrame } from "@/lib/flow-inspector";

import { VariableInspector } from "./variable-inspector";

describe("VariableInspector", () => {
  it("shows the empty hint when no frames have been captured", () => {
    render(<VariableInspector frames={[]} />);
    expect(screen.getByTestId("inspector-empty")).toBeInTheDocument();
    expect(screen.getByTestId("inspector-status").textContent).toBe("idle");
  });

  it("renders the latest frame's state and a 'running' status while live", () => {
    const frames = [
      captureFrame("start-1", "Start", { user: "ada" }, () => 1),
      captureFrame("ai-1", "Ask LLM", { user: "ada", reply: "hi" }, () => 2),
    ];
    render(<VariableInspector frames={frames} running />);
    expect(screen.getByTestId("inspector-status").textContent).toBe("running");
    // Latest frame is selected by default.
    expect(screen.getByTestId("inspector-var-user").textContent).toContain(
      '"ada"',
    );
    expect(screen.getByTestId("inspector-var-reply").textContent).toContain(
      '"hi"',
    );
    // Diff vs previous frame surfaces the new key.
    expect(
      screen.getByTestId("inspector-diff-reply").textContent,
    ).toContain("added");
  });

  it("clicking an earlier frame switches the displayed state", async () => {
    const frames = [
      captureFrame("a", "A", { x: 1 }, () => 1),
      captureFrame("b", "B", { x: 2 }, () => 2),
    ];
    render(<VariableInspector frames={frames} />);
    expect(screen.getByTestId("inspector-var-x").textContent).toContain("2");
    await act(async () => {
      fireEvent.click(screen.getByTestId("inspector-frame-0"));
    });
    expect(screen.getByTestId("inspector-var-x").textContent).toContain("1");
    // No diff shown for the very first frame.
    expect(screen.queryByTestId("inspector-diff")).toBeNull();
  });

  it("renders an explicit empty-state row when state has no keys", () => {
    const frames = [captureFrame("a", "A", {}, () => 1)];
    render(<VariableInspector frames={frames} />);
    expect(screen.getByTestId("inspector-state-empty")).toBeInTheDocument();
  });

  it("shows changed and removed kinds in the diff view", () => {
    const frames = [
      captureFrame("a", "A", { keep: 1, drop: 2 }, () => 1),
      captureFrame("b", "B", { keep: 9 }, () => 2),
    ];
    render(<VariableInspector frames={frames} />);
    expect(
      screen.getByTestId("inspector-diff-keep").textContent,
    ).toContain("changed");
    expect(
      screen.getByTestId("inspector-diff-drop").textContent,
    ).toContain("removed");
  });
});
