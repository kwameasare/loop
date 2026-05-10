import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PairDebugAudioControl } from "./pair-debug-audio-control";

describe("PairDebugAudioControl", () => {
  const ORIGINAL_BASE_URL = process.env.LOOP_CP_API_BASE_URL;
  const ORIGINAL_RTC = window.RTCPeerConnection;

  afterEach(() => {
    if (ORIGINAL_BASE_URL === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE_URL;
    }
    Object.defineProperty(window, "RTCPeerConnection", {
      configurable: true,
      value: ORIGINAL_RTC,
    });
  });

  it("shows backend-required errors instead of opening a fake audio room", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    Object.defineProperty(window, "RTCPeerConnection", {
      configurable: true,
      value: function RTCPeerConnection() {},
    });
    render(
      <PairDebugAudioControl
        workspaceId="ws_1"
        agentId="agent_1"
        teammateCount={1}
        participantId="builder:maya"
      />,
    );

    const button = screen.getByRole("button", { name: "Start pair audio" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Human pair-debug audio is live/i),
    ).not.toBeInTheDocument();
  });
});
