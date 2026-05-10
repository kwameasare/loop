/**
 * P0.3: tests for the voice cp-api helpers.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchVoiceConfig,
  saveVoiceConfig,
} from "./voice-config";
import { fetchVoiceStageModel, provisionVoiceNumber } from "./voice-stage";
import { mintVoiceToken } from "./voice-transport";

const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("mintVoiceToken", () => {
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("returns the token on 200", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        token: "lk-tok-1",
        url: "wss://lk.test",
        room: "r-1",
        identity: "user-a",
      }),
    });
    const res = await mintVoiceToken({ agent_id: "a1" }, { fetcher });
    expect(res?.token).toBe("lk-tok-1");
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/voice/mint_token");
    expect(JSON.parse(init.body)).toEqual({ agent_id: "a1" });
  });

  it("returns null on 404 missing voice-token evidence", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await mintVoiceToken({ agent_id: "a1" }, { fetcher });
    expect(res).toBeNull();
  });

  it("throws on a non-404 error", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    await expect(mintVoiceToken({ agent_id: "a1" }, { fetcher })).rejects.toThrow(
      /500/,
    );
  });
});

describe("voice-config cp-api client", () => {
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("fetchVoiceConfig returns the cp body on 200", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        workspace_id: "ws1",
        numbers: [],
        asr_provider: "google",
        tts_provider: "polly",
      }),
    });
    const res = await fetchVoiceConfig("ws1", { fetcher });
    expect(res.asr_provider).toBe("google");
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/workspaces/ws1/voice/config");
  });

  it("fetchVoiceConfig does not fall back to fixture config when cp-api is unconfigured", async () => {
    await expect(fetchVoiceConfig("ws1", { baseUrl: "" })).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required for voice-config calls",
    );
  });

  it("fetchVoiceConfig marks 404 as degraded instead of pretending no numbers are configured", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await fetchVoiceConfig("ws1", { fetcher });
    expect(res.workspace_id).toBe("ws1");
    expect(res.numbers).toEqual([]);
    expect(res.degraded_reason).toMatch(/voice config route returned 404/i);
  });

  it("saveVoiceConfig PATCHes provider selections", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    const res = await saveVoiceConfig(
      "ws1",
      { asr_provider: "whisper", tts_provider: "openai" },
      { fetcher },
    );
    expect(res.ok).toBe(true);
    const [, init] = fetcher.mock.calls[0];
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({
      asr_provider: "whisper",
      tts_provider: "openai",
    });
  });

  it("saveVoiceConfig surfaces ok=false on 404", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await saveVoiceConfig(
      "ws1",
      { asr_provider: "deepgram", tts_provider: "elevenlabs" },
      { fetcher },
    );
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/not available/);
  });
});

describe("voice-stage cp-api client", () => {
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("fetchVoiceStageModel returns the composed stage model", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        agentName: "Voice Concierge",
        callState: "staging",
        queuedSpeech: "hello",
        transcript: [],
        waveform: [],
        spans: [],
        config: {
          asr: "Google Speech-to-Text v2",
          tts: "Amazon Polly Neural",
          bargeIn: true,
          voice: "Warm concierge",
          phoneNumber: "+15551234567",
        },
        evals: [],
        demoLinks: [],
      }),
    });

    const model = await fetchVoiceStageModel("ws1", { fetcher });

    expect(model.agentName).toBe("Voice Concierge");
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/workspaces/ws1/voice/stage");
  });

  it("fetchVoiceStageModel does not fall back to the stage fixture when cp-api is unconfigured", async () => {
    await expect(
      fetchVoiceStageModel("ws1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required to load voice stage");
  });

  it("provisionVoiceNumber does not mint deterministic phone numbers when cp-api is unconfigured", async () => {
    await expect(provisionVoiceNumber("ws1", { baseUrl: "" })).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required to provision voice numbers",
    );
  });
});
