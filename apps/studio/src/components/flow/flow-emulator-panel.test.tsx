import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { makeFixtureEmulatorTransport } from "@/lib/emulator-transport";
import type { TurnEvent } from "@/lib/sdk-types";

import { FlowEmulatorPanel } from "./flow-emulator-panel";

const at = "2025-01-01T00:00:00Z";

describe("FlowEmulatorPanel", () => {
  it("renders an empty state and disables Play until input is non-empty", () => {
    const fx = makeFixtureEmulatorTransport([]);
    render(<FlowEmulatorPanel agentId="a1" transport={fx.transport} />);
    expect(screen.getByTestId("emulator-empty")).toBeInTheDocument();
    expect(screen.getByTestId("emulator-status").textContent).toBe("idle");
    expect(
      (screen.getByTestId("emulator-play") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("streams tokens into a chat preview and ends on complete", async () => {
    const fx = makeFixtureEmulatorTransport([
      { type: "token", payload: { text: "Hel" }, ts: at },
      { type: "token", payload: { delta: "lo!" }, ts: at },
      { type: "complete", payload: {}, ts: at },
    ]);
    render(<FlowEmulatorPanel agentId="a1" transport={fx.transport} />);
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "hi" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-play"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("emulator-text-1").textContent).toContain(
        "Hello!",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("emulator-status").textContent).toBe("idle");
    });
    expect(screen.getByTestId("emulator-msg-0").getAttribute("data-role")).toBe(
      "user",
    );
    expect(screen.getByTestId("emulator-msg-1").getAttribute("data-role")).toBe(
      "assistant",
    );
  });

  it("forwards every TurnEvent to onTurnEvent", async () => {
    const events: TurnEvent[] = [
      { type: "token", payload: { text: "x" }, ts: at },
      { type: "complete", payload: {}, ts: at },
    ];
    const fx = makeFixtureEmulatorTransport(events);
    const seen: TurnEvent[] = [];
    render(
      <FlowEmulatorPanel
        agentId="a1"
        onTurnEvent={(e) => seen.push(e)}
        transport={fx.transport}
      />,
    );
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "go" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-play"));
    });
    await waitFor(() => {
      expect(seen.map((e) => e.type)).toEqual(["token", "complete"]);
    });
  });

  it("surfaces a degrade event as an inline error", async () => {
    const fx = makeFixtureEmulatorTransport([
      { type: "degrade", payload: { reason: "model_timeout" }, ts: at },
    ]);
    render(<FlowEmulatorPanel agentId="a1" transport={fx.transport} />);
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "ping" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-play"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("emulator-error-1").textContent).toBe(
        "model_timeout",
      );
    });
  });

  it("Stop cancels the in-flight stream", async () => {
    const fx = makeFixtureEmulatorTransport([]);
    render(<FlowEmulatorPanel agentId="a1" transport={fx.transport} />);
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "hold" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-play"));
    });
    expect(screen.getByTestId("emulator-status").textContent).toBe("streaming");
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-stop"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("emulator-status").textContent).toBe("idle");
    });
  });

  it("ignores Play when the input is whitespace only", () => {
    const fx = makeFixtureEmulatorTransport([]);
    const startSpy = vi.spyOn(fx.transport, "start");
    render(<FlowEmulatorPanel agentId="a1" transport={fx.transport} />);
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByTestId("emulator-play"));
    expect(startSpy).not.toHaveBeenCalled();
  });
});
