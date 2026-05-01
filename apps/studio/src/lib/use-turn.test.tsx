import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LoopClient } from "./loop-client";
import { useTurn } from "./use-turn";

describe("useTurn", () => {
  it("starts a streaming turn and exposes frames/done", async () => {
    const client = new LoopClient({ baseUrl: "https://api.test/v1" });
    vi.spyOn(client, "invokeTurn").mockResolvedValue({
      reconnect: { lastEventId: "2", retryMs: 1000 },
      frames: [
        { id: "1", event: "message", retry: null, data: { type: "token", payload: { text: "hi" }, ts: "t" } },
        { id: "2", event: "message", retry: null, data: { type: "complete", payload: {}, ts: "t" } },
      ],
    });
    const { result } = renderHook(() => useTurn(client));
    await act(async () => {
      await result.current.start("agt", {
        channel: "web",
        content: [{ type: "text", text: "hi" }],
        conversation_id: "conv",
        user_id: "u",
      });
    });
    expect(result.current.frames.map((f) => f.type)).toEqual(["token", "complete"]);
    expect(result.current.done).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("captures errors and reset clears state", async () => {
    const client = new LoopClient({ baseUrl: "https://api.test/v1" });
    vi.spyOn(client, "invokeTurn").mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useTurn(client));
    await act(async () => {
      await result.current.start("agt", {
        channel: "web",
        content: [{ type: "text", text: "hi" }],
        conversation_id: "conv",
        user_id: "u",
      });
    });
    expect(result.current.done).toBe(true);
    expect(result.current.error?.message).toBe("boom");
    act(() => result.current.reset());
    expect(result.current.frames).toEqual([]);
    expect(result.current.done).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
