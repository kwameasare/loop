import { describe, expect, it, vi } from "vitest";

import { createPairDebugAudioSession } from "./pair-debug-audio";

describe("pair-debug audio client", () => {
  it("creates pair-debug audio sessions through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_input, init) => {
      expect(JSON.parse(String(init?.body))).toMatchObject({
        agent_id: "agent_1",
        participant_id: "builder:maya",
      });
      return Response.json({
        id: "pair_live_1",
        workspace_id: "ws_1",
        agent_id: "agent_1",
        participant_id: "builder:maya",
        transport: "webrtc",
        signaling_url: "wss://signal.test/pair_live_1",
        ice_servers: [{ urls: ["stun:stun.example.test:3478"] }],
        participants: ["builder:maya", "builder:diego"],
        expires_at: "2026-05-09T12:15:00Z",
      });
    });

    const session = await createPairDebugAudioSession("ws_1", "agent_1", {
      baseUrl: "https://cp.test",
      fetcher,
      participantId: "builder:maya",
    });

    expect(session.id).toBe("pair_live_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws_1/pair-debug/audio/session",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not fabricate pair-debug audio sessions without cp-api", async () => {
    await expect(
      createPairDebugAudioSession("ws_1", "agent_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic pair-debug sessions explicitly opt-in", async () => {
    await expect(
      createPairDebugAudioSession("ws_1", "agent_1", {
        baseUrl: "",
        allowFixture: true,
        participantId: "builder:maya",
      }),
    ).resolves.toMatchObject({
      id: "pair-audio-agent_1",
      participant_id: "builder:maya",
      transport: "webrtc",
    });
  });
});
