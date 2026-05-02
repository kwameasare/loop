import type { TurnEvent } from "./sdk-types";

export interface EmulatorTurnRequest {
  agentId: string;
  /** User text being sent to ``/v1/turns``. */
  text: string;
}

/**
 * Minimal adapter the emulator panel uses to invoke ``/v1/turns``.
 *
 * The adapter is responsible for streaming the SSE frames and yielding
 * each {@link TurnEvent} as it arrives. The panel does not care whether
 * the transport is fetch+SSE, WebSocket, or an in-memory fixture.
 */
export interface EmulatorTransport {
  start(req: EmulatorTurnRequest): AsyncIterable<TurnEvent>;
}

/**
 * Builds an in-memory transport that streams a fixed list of events with
 * an optional delay. Tests drive ``flushAll()`` to advance the stream.
 */
export function makeFixtureEmulatorTransport(events: TurnEvent[]) {
  let resolve: ((evt: IteratorResult<TurnEvent>) => void) | null = null;
  const queue: TurnEvent[] = [...events];
  let closed = false;

  function pull(): Promise<IteratorResult<TurnEvent>> {
    if (queue.length > 0) {
      const value = queue.shift()!;
      return Promise.resolve({ value, done: false });
    }
    if (closed) return Promise.resolve({ value: undefined as never, done: true });
    return new Promise((r) => {
      resolve = r;
    });
  }

  return {
    transport: {
      start(): AsyncIterable<TurnEvent> {
        return {
          [Symbol.asyncIterator]() {
            return {
              next() {
                return pull();
              },
              async return() {
                closed = true;
                if (resolve) {
                  const r = resolve;
                  resolve = null;
                  r({ value: undefined as never, done: true });
                }
                return { value: undefined as never, done: true };
              },
            };
          },
        };
      },
    } as EmulatorTransport,
    /** Push another event into the open stream. */
    push(evt: TurnEvent) {
      if (resolve) {
        const r = resolve;
        resolve = null;
        r({ value: evt, done: false });
      } else {
        queue.push(evt);
      }
    },
    /** Mark the stream as completed (iterator returns ``done=true``). */
    end() {
      closed = true;
      if (resolve) {
        const r = resolve;
        resolve = null;
        r({ value: undefined as never, done: true });
      }
    },
  };
}

/**
 * Pull token text out of a {@link TurnEvent} of type ``token``. The shape
 * of ``payload`` is intentionally permissive because the runtime emits a
 * range of ``{ text }`` / ``{ delta }`` envelopes.
 */
export function extractTokenText(evt: TurnEvent): string {
  if (evt.type !== "token") return "";
  const payload = evt.payload as { text?: unknown; delta?: unknown };
  if (typeof payload.text === "string") return payload.text;
  if (typeof payload.delta === "string") return payload.delta;
  return "";
}
