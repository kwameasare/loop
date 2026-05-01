import type { TurnEvent } from "./sdk-types";

export type SseFrame<T = unknown> = {
  id: string | null;
  event: string;
  data: T;
  retry: number | null;
};

export type SseReconnectState = {
  lastEventId: string | null;
  retryMs: number;
};

function parseRawEvent(raw: string): SseFrame<string> | null {
  let id: string | null = null;
  let event = "message";
  let retry: number | null = null;
  const data: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (line.length === 0 || line.startsWith(":")) continue;
    const sep = line.indexOf(":");
    const field = sep === -1 ? line : line.slice(0, sep);
    const value = sep === -1 ? "" : line.slice(sep + 1).replace(/^ /, "");
    if (field === "id") id = value;
    if (field === "event") event = value || "message";
    if (field === "retry") {
      const parsed = Number.parseInt(value, 10);
      if (Number.isFinite(parsed) && parsed >= 0) retry = parsed;
    }
    if (field === "data") data.push(value);
  }
  if (data.length === 0) return null;
  return { id, event, retry, data: data.join("\n") };
}

export function parseSseText<T = unknown>(
  text: string,
  decode: (raw: string) => T = (raw) => JSON.parse(raw) as T,
): SseFrame<T>[] {
  const normalized = text.replace(/\r\n/g, "\n");
  return normalized
    .split(/\n\n+/)
    .map(parseRawEvent)
    .filter((frame): frame is SseFrame<string> => frame !== null)
    .map((frame) => ({
      ...frame,
      data: decode(frame.data),
    }));
}

export function nextReconnectState<T>(
  frames: readonly SseFrame<T>[],
  previous: SseReconnectState = { lastEventId: null, retryMs: 1000 },
): SseReconnectState {
  let lastEventId = previous.lastEventId;
  let retryMs = previous.retryMs;
  for (const frame of frames) {
    if (frame.id !== null) lastEventId = frame.id;
    if (frame.retry !== null) retryMs = frame.retry;
  }
  return { lastEventId, retryMs };
}

export async function readTurnEventStream(
  response: Response,
  onFrame: (frame: SseFrame<TurnEvent>) => void,
): Promise<SseReconnectState> {
  const body = await response.text();
  const frames = parseSseText<TurnEvent>(body);
  for (const frame of frames) onFrame(frame);
  return nextReconnectState(frames);
}

export function lastEventHeaders(state: SseReconnectState): HeadersInit {
  return state.lastEventId === null ? {} : { "Last-Event-Id": state.lastEventId };
}
