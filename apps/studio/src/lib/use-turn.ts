import { useCallback, useMemo, useState } from "react";

import { LoopClient } from "./loop-client";
import type { Operations } from "./openapi-types";
import type { TurnEvent } from "./sdk-types";
import type { SseFrame, SseReconnectState } from "./sse";

export type UseTurnState = {
  frames: TurnEvent[];
  done: boolean;
  error: Error | null;
  start: (
    agentId: string,
    body: Operations["PostAgentsByAgentIdInvoke"]["request"],
  ) => Promise<void>;
  reset: () => void;
};

export function useTurn(client: LoopClient): UseTurnState {
  const [frames, setFrames] = useState<TurnEvent[]>([]);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnect, setReconnect] = useState<SseReconnectState>({
    lastEventId: null,
    retryMs: 1000,
  });

  const reset = useCallback(() => {
    setFrames([]);
    setDone(false);
    setError(null);
    setReconnect({ lastEventId: null, retryMs: 1000 });
  }, []);

  const start = useCallback(
    async (
      agentId: string,
      body: Operations["PostAgentsByAgentIdInvoke"]["request"],
    ) => {
      setDone(false);
      setError(null);
      try {
        const result = await client.invokeTurn(agentId, body, reconnect);
        setReconnect(result.reconnect);
        setFrames((prev) => [
          ...prev,
          ...result.frames.map((frame: SseFrame<TurnEvent>) => frame.data),
        ]);
        setDone(result.frames.some((frame) => frame.data.type === "complete"));
      } catch (exc) {
        setError(exc instanceof Error ? exc : new Error(String(exc)));
        setDone(true);
      }
    },
    [client, reconnect],
  );

  return useMemo(
    () => ({ frames, done, error, start, reset }),
    [frames, done, error, start, reset],
  );
}
