"use client";

import {
  SimulatorLab,
  type SimulatorInvoke,
} from "@/components/simulator/simulator-lab";
import { LoopClient } from "@/lib/loop-client";

export interface EmulatorPanelProps {
  agentId: string;
  /** Override for tests. Receives prompt, stream callback, and simulator config. */
  invoke?: SimulatorInvoke;
  /** Override the default LoopClient (used in production). */
  client?: LoopClient;
}

function defaultInvoke(client: LoopClient): SimulatorInvoke {
  return async (agentId, prompt, onFrame, config) => {
    const conversationId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `conv_${Date.now()}`;
    const metadata: Record<string, unknown> = {
      simulator: {
        model_alias: config.modelAlias,
        memory_mode: config.memoryMode,
        persona: config.personaId,
        seeded_context_id: config.seededContextId,
        disabled_tools: config.disabledTools,
        tool_mode: config.toolMode,
        diff_against: config.diffAgainst,
      },
    };
    if (config.injectedContext) {
      metadata.simulator = {
        ...(metadata.simulator as Record<string, unknown>),
        injected_context: config.injectedContext,
      };
    }
    if (config.replayTurn !== null) {
      metadata.simulator = {
        ...(metadata.simulator as Record<string, unknown>),
        replay_turn: config.replayTurn,
      };
    }

    const result = await client.invokeTurn(agentId, {
      conversation_id: conversationId,
      user_id: `studio-simulator-${config.personaId}`,
      channel: config.channel,
      content: [{ type: "text", text: prompt }],
      metadata,
    });
    for (const frame of result.frames) onFrame(frame.data);
  };
}

/**
 * Right-rail simulator lab. The agent detail layout owns the rail; this
 * wrapper keeps production transport wiring beside the agent components while
 * the canonical simulator surface lives under components/simulator.
 */
export function EmulatorPanel({ agentId, invoke, client }: EmulatorPanelProps) {
  const submit =
    invoke ??
    defaultInvoke(
      client ??
        new LoopClient({
          baseUrl:
            process.env.NEXT_PUBLIC_LOOP_API_URL ?? "http://localhost:8080/v1",
        }),
    );

  return <SimulatorLab agentId={agentId} invoke={submit} />;
}
