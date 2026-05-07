import { describe, expect, it } from "vitest";

import {
  appendMessage,
  fetchConversationDetail,
  FIXTURE_TRANSCRIPT,
  handbackConversation,
  postOperatorMessage,
  takeoverConversation,
  type ConversationMessage,
} from "./conversation";

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("appendMessage", () => {
  it("appends a new message and keeps order ascending", () => {
    const next: ConversationMessage = {
      id: "m4",
      conversation_id: "c",
      role: "operator",
      body: "Hi, I'm here now.",
      created_at_ms: Date.UTC(2026, 4, 1, 11, 57),
    };
    const out = appendMessage(FIXTURE_TRANSCRIPT, next);
    expect(out).toHaveLength(4);
    expect(out[3].id).toBe("m4");
  });

  it("ignores duplicate ids", () => {
    const dup: ConversationMessage = { ...FIXTURE_TRANSCRIPT[1] };
    const out = appendMessage(FIXTURE_TRANSCRIPT, dup);
    expect(out).toHaveLength(FIXTURE_TRANSCRIPT.length);
  });

  it("inserts in chronological order even when delivered out-of-order", () => {
    const old: ConversationMessage = {
      id: "m0",
      conversation_id: "c",
      role: "user",
      body: "earlier message",
      created_at_ms: 1,
    };
    const out = appendMessage(FIXTURE_TRANSCRIPT, old);
    expect(out[0].id).toBe("m0");
  });
});

describe("conversation cp-api adapter", () => {
  it("maps conversation detail messages and ownership from cp-api", async () => {
    const fetcher = async () =>
      response({
        summary: {
          id: "conv-1",
          state: "in-takeover",
          operator_taken_over: true,
        },
        messages: [
          {
            id: "msg-1",
            conversation_id: "conv-1",
            role: "user",
            body: "hello",
            created_at: "2026-05-07T12:00:00Z",
          },
        ],
      });

    const detail = await fetchConversationDetail("conv-1", {
      baseUrl: "https://cp.test/v1",
      fetcher: fetcher as unknown as typeof fetch,
    });

    expect(detail.ownership).toBe("operator");
    expect(detail.messages[0]).toMatchObject({
      id: "msg-1",
      role: "user",
      body: "hello",
    });
  });

  it("posts takeover, handback, and operator messages to cp-api", async () => {
    const urls: string[] = [];
    const fetcher = async (input: RequestInfo | URL) => {
      const url = String(input);
      urls.push(url);
      if (url.endsWith("/operator-messages")) {
        return response(
          {
            id: "op-1",
            conversation_id: "conv-1",
            role: "operator",
            body: "I can help.",
            created_at: "2026-05-07T12:01:00Z",
          },
          201,
        );
      }
      return response({ ok: true });
    };
    const opts = {
      baseUrl: "https://cp.test/v1",
      fetcher: fetcher as unknown as typeof fetch,
    };

    await expect(takeoverConversation("conv-1", opts)).resolves.toMatchObject({
      ok: true,
    });
    await expect(handbackConversation("conv-1", opts)).resolves.toMatchObject({
      ok: true,
    });
    const posted = await postOperatorMessage(
      { conversation_id: "conv-1", body: "I can help." },
      opts,
    );

    expect(posted.message?.id).toBe("op-1");
    expect(urls).toEqual([
      "https://cp.test/v1/conversations/conv-1/takeover",
      "https://cp.test/v1/conversations/conv-1/handback",
      "https://cp.test/v1/conversations/conv-1/operator-messages",
    ]);
  });
});
