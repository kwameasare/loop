import { describe, expect, it, vi } from "vitest";

import {
  buildLocalChannelBindings,
  buildLocalPreviewMatrix,
  createChannelPreviewEvalCase,
  listChannelBindings,
  previewChannelMatrix,
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

  it("builds a local channel preview matrix with formatting failures", () => {
    const bindings = buildLocalChannelBindings("agt_1").map((binding) =>
      binding.channel_type === "sms"
        ? { ...binding, status: "draft" as const }
        : binding,
    );
    const matrix = buildLocalPreviewMatrix(
      "agt_1",
      {
        scenario_title: "Duplicate charge",
        user_message: "I was charged twice.",
        expected_outcome:
          "Acknowledge the duplicate charge, verify the account, explain the refund path, mention the SLA, explain escalation, and include opt-out language for short-message channels.",
        channel_types: ["sms"],
      },
      bindings,
    );

    expect(matrix.rows).toHaveLength(1);
    expect(matrix.rows[0]?.channel_type).toBe("sms");
    expect(matrix.rows[0]?.formatting_failures[0]?.id).toBe("sms_too_long");
  });

  it("previews a channel matrix and saves a formatting failure through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/eval-cases")) {
        return new Response(
          JSON.stringify({
            ok: true,
            suite_id: "suite_1",
            case_id: "case_1",
            case: {},
          }),
          { status: 201, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify(
          buildLocalPreviewMatrix("agt_1", {
            scenario_title: "Duplicate charge",
            user_message: "I was charged twice.",
            expected_outcome: "Verify the charge and explain the refund path.",
            channel_types: ["whatsapp"],
          }),
        ),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const matrix = await previewChannelMatrix(
      "agt_1",
      {
        scenario_title: "Duplicate charge",
        user_message: "I was charged twice.",
        expected_outcome: "Verify the charge and explain the refund path.",
        channel_types: ["whatsapp"],
      },
      { baseUrl: "https://cp.test", fetcher },
    );
    const saved = await createChannelPreviewEvalCase(
      "agt_1",
      {
        ...matrix.rows[0]!.eval_case_seed,
        failure_reason: "WhatsApp template is missing.",
      },
      { baseUrl: "https://cp.test", fetcher },
    );

    expect(matrix.summary.channels).toBeGreaterThan(0);
    expect(saved.case_id).toBe("case_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/channel-bindings/preview-matrix",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/channel-bindings/preview-matrix/eval-cases",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
