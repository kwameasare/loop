import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { EmulatorPanel } from "./emulator-panel";
import type { TurnEvent } from "@/lib/sdk-types";

describe("EmulatorPanel", () => {
  it("posts the prompt and renders streamed tokens, tool calls, and final answer", async () => {
    let push: (event: TurnEvent) => void = () => {};
    const invoke = vi.fn(
      (
        _agent: string,
        _prompt: string,
        onFrame: (event: TurnEvent) => void,
      ) => {
        push = onFrame;
        return Promise.resolve();
      },
    );
    render(<EmulatorPanel agentId="agt_1" invoke={invoke} />);

    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "hello" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-send"));
    });
    expect(invoke).toHaveBeenCalledWith(
      "agt_1",
      "hello",
      expect.any(Function),
    );

    await act(async () => {
      push({ type: "token", text: "Hi" } as unknown as TurnEvent);
      push({ type: "token", text: " there" } as unknown as TurnEvent);
      push({
        type: "tool_call_start",
        name: "search",
        args: { q: "weather" },
      } as unknown as TurnEvent);
      push({
        type: "tool_call_end",
        name: "search",
        result: { hits: 3 },
      } as unknown as TurnEvent);
      push({
        type: "complete",
        response: { content: [{ type: "text", text: "Hi there" }] },
      } as unknown as TurnEvent);
    });

    expect(screen.getByTestId("emulator-tokens")).toHaveTextContent("Hi there");
    const call = screen.getByTestId("emulator-tool-call-search");
    expect(call).toHaveTextContent(/ok/);
    expect(call).toHaveTextContent(/weather/);
    expect(call).toHaveTextContent(/hits/);
    expect(screen.getByTestId("emulator-final")).toHaveTextContent("Hi there");
  });

  it("flags failed tool calls and degrade frames", async () => {
    let push: (event: TurnEvent) => void = () => {};
    const invoke = vi.fn(
      (_a: string, _p: string, onFrame: (event: TurnEvent) => void) => {
        push = onFrame;
        return Promise.resolve();
      },
    );
    render(<EmulatorPanel agentId="agt_1" invoke={invoke} />);
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "hi" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-send"));
    });
    await act(async () => {
      push({
        type: "tool_call_start",
        name: "search",
        args: {},
      } as unknown as TurnEvent);
      push({
        type: "tool_call_end",
        name: "search",
        error: "timeout",
      } as unknown as TurnEvent);
      push({
        type: "degrade",
        degrade_reason: "budget_soft",
      } as unknown as TurnEvent);
    });
    expect(
      screen.getByTestId("emulator-tool-call-search"),
    ).toHaveTextContent(/error/);
    expect(screen.getByTestId("emulator-degrade")).toHaveTextContent(
      /budget_soft/,
    );
  });

  it("renders an error tile when the request rejects", async () => {
    const invoke = vi.fn().mockRejectedValue(new Error("network down"));
    render(<EmulatorPanel agentId="agt_1" invoke={invoke} />);
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "anyone there?" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-send"));
    });
    expect(screen.getByTestId("emulator-error")).toHaveTextContent(
      /network down/,
    );
  });

  it("disables Send while the prompt is empty", () => {
    render(<EmulatorPanel agentId="agt_1" invoke={vi.fn()} />);
    expect(
      (screen.getByTestId("emulator-send") as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});
