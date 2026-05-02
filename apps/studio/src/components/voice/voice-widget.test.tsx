import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  VoiceCallState,
  VoiceMode,
  VoiceTransport,
} from "@/lib/voice-transport";

import { VoiceWidget } from "./voice-widget";

interface ControllableTransport extends VoiceTransport {
  /** Called by tests to push a state transition into the widget. */
  emit(state: VoiceCallState, detail?: string): void;
  /** Most recent value passed to ``setMicEnabled``. */
  micEnabled(): boolean;
  /** Mode reported by the most recent ``connect`` call. */
  lastMode(): VoiceMode | null;
  disconnectCount(): number;
  setConnectResult(res: { ok: boolean; error?: string }): void;
}

function makeTransport(): ControllableTransport {
  let onState: ((s: VoiceCallState, d?: string) => void) | null = null;
  let mic = false;
  let mode: VoiceMode | null = null;
  let disconnects = 0;
  let connectResult: { ok: boolean; error?: string } = { ok: true };
  return {
    async connect(opts) {
      onState = opts.onState;
      mode = opts.mode;
      return connectResult;
    },
    setMicEnabled(enabled) {
      mic = enabled;
    },
    async disconnect() {
      disconnects += 1;
      if (onState) onState("ended");
    },
    emit(state, detail) {
      if (onState) onState(state, detail);
    },
    micEnabled() {
      return mic;
    },
    lastMode() {
      return mode;
    },
    disconnectCount() {
      return disconnects;
    },
    setConnectResult(res) {
      connectResult = res;
    },
  };
}

describe("VoiceWidget", () => {
  it("renders idle state with a call button", () => {
    render(<VoiceWidget transport={makeTransport()} />);
    expect(screen.getByTestId("voice-call")).toBeInTheDocument();
    expect(screen.getByTestId("voice-state").textContent).toMatch(/Ready/);
  });

  it("starts a call and reports the connected state", async () => {
    const transport = makeTransport();
    render(<VoiceWidget transport={transport} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-call"));
    });
    await act(async () => {
      transport.emit("connected");
    });
    expect(transport.lastMode()).toBe("ptt");
    expect(screen.getByTestId("voice-state").textContent).toMatch(/On call/);
    expect(screen.getByTestId("voice-end")).toBeInTheDocument();
  });

  it("PTT mode toggles mic on mousedown/mouseup", async () => {
    const transport = makeTransport();
    render(<VoiceWidget transport={transport} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-call"));
    });
    await act(async () => {
      transport.emit("connected");
    });
    const btn = screen.getByTestId("voice-ptt");
    fireEvent.mouseDown(btn);
    expect(transport.micEnabled()).toBe(true);
    fireEvent.mouseUp(btn);
    expect(transport.micEnabled()).toBe(false);
  });

  it("always-on mode keeps mic open and hides PTT button", async () => {
    const transport = makeTransport();
    render(<VoiceWidget defaultMode="always_on" transport={transport} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-call"));
    });
    await act(async () => {
      transport.emit("connected");
    });
    expect(transport.lastMode()).toBe("always_on");
    expect(transport.micEnabled()).toBe(true);
    expect(screen.queryByTestId("voice-ptt")).toBeNull();
  });

  it("renders an error if the transport rejects connect", async () => {
    const transport = makeTransport();
    transport.setConnectResult({ ok: false, error: "Microphone blocked." });
    render(<VoiceWidget transport={transport} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-call"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("voice-error").textContent).toMatch(
        /blocked/,
      );
    });
    expect(screen.getByTestId("voice-state").textContent).toMatch(/failed/);
  });

  it("end call disconnects the transport", async () => {
    const transport = makeTransport();
    render(<VoiceWidget transport={transport} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-call"));
    });
    await act(async () => {
      transport.emit("connected");
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-end"));
    });
    expect(transport.disconnectCount()).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("voice-state").textContent).toMatch(/ended/);
  });
});
