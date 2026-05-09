import { describe, expect, it, vi } from "vitest";

import {
  buildLocalChannelBindings,
  listChannelBindings,
  upsertChannelBinding,
} from "./channel-bindings";

describe("channel-bindings client", () => {
  it("builds every supported channel as a peer binding", () => {
    const bindings = buildLocalChannelBindings("agt_1");
    expect(bindings.map((binding) => binding.channel_type)).toEqual([
      "web_chat",
      "whatsapp",
      "telegram",
      "slack",
      "teams",
      "sms",
      "email",
      "voice",
      "webhook_api",
    ]);
    expect(
      bindings.find((binding) => binding.channel_type === "voice"),
    ).toBeDefined();
    expect(bindings.every((binding) => binding.readiness.length > 0)).toBe(
      true,
    );
  });

  it("lists and upserts channel bindings through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST") {
        return new Response(
          JSON.stringify({
            ...buildLocalChannelBindings("agt_1")[1],
            status: "draft",
            provider: "Meta Cloud API",
          }),
          { status: 201, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({ items: buildLocalChannelBindings("agt_1") }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const listed = await listChannelBindings("agt_1", {
      baseUrl: "https://cp.test",
      fetcher,
    });
    const updated = await upsertChannelBinding(
      "agt_1",
      { channel_type: "whatsapp", provider: "Meta Cloud API" },
      { baseUrl: "https://cp.test", fetcher },
    );

    expect(listed.items).toHaveLength(9);
    expect(updated.provider).toBe("Meta Cloud API");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/channel-bindings",
      expect.objectContaining({ method: "GET" }),
    );
    expect(JSON.parse(String(fetcher.mock.calls[1]![1]?.body))).toMatchObject({
      channel_type: "whatsapp",
      provider: "Meta Cloud API",
    });
  });
});
