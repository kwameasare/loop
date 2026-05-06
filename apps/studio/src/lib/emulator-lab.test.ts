import { describe, expect, it } from "vitest";

import {
  DEFAULT_SIMULATOR_CONFIG,
  SIMULATOR_CHANNELS,
  buildSimulatorRun,
  parseSimulatorCommand,
} from "./emulator-lab";

describe("emulator-lab", () => {
  it("builds a multi-channel simulator run with trace-backed evidence", () => {
    const run = buildSimulatorRun(
      {
        ...DEFAULT_SIMULATOR_CONFIG,
        channel: "email",
        modelAlias: "quality",
        memoryMode: "snapshot",
      },
      "agent_support",
    );

    expect(SIMULATOR_CHANNELS.map((channel) => channel.id)).toEqual([
      "web",
      "slack",
      "whatsapp",
      "sms",
      "email",
      "voice",
    ]);
    expect(run.channelLabel).toBe("Email");
    expect(run.modelInput).toContain("model=quality");
    expect(run.contextEvidence).toContain("trace_refund_742");
    expect(run.diffRows.some((row) => row.label === "Memory")).toBe(true);
  });

  it("parses model, persona, replay, diff, inject, and disable commands", () => {
    let config = DEFAULT_SIMULATOR_CONFIG;

    config = parseSimulatorCommand("/swap model=fast-draft", config).nextConfig;
    config = parseSimulatorCommand(
      "/as-user persona=angry-customer",
      config,
    ).nextConfig;
    config = parseSimulatorCommand(
      '/inject ctx="user is on premium tier"',
      config,
    ).nextConfig;
    config = parseSimulatorCommand(
      "/disable tool=lookup_order",
      config,
    ).nextConfig;
    config = parseSimulatorCommand(
      "/replay turn=3 with-memory=cleared",
      config,
    ).nextConfig;
    config = parseSimulatorCommand("/diff against=v23.1.3", config).nextConfig;

    expect(config.modelAlias).toBe("fast-draft");
    expect(config.personaId).toBe("angry-customer");
    expect(config.injectedContext).toBe("user is on premium tier");
    expect(config.disabledTools).toContain("lookup_order");
    expect(config.replayTurn).toBe(3);
    expect(config.memoryMode).toBe("cleared");
    expect(config.diffAgainst).toBe("v23.1.3");
  });

  it("returns explicit unsupported and error evidence", () => {
    const voice = buildSimulatorRun(
      { ...DEFAULT_SIMULATOR_CONFIG, channel: "voice" },
      "agent_support",
    );
    const bad = parseSimulatorCommand(
      "/disable tool=does_not_exist",
      DEFAULT_SIMULATOR_CONFIG,
    );

    expect(voice.unsupported[0]).toContain("Live microphone capture");
    expect(bad.ok).toBe(false);
    expect(bad.message).toContain("Tool is not available");
  });
});
