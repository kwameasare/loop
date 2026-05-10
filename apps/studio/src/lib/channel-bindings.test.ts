import { describe, expect, it, vi } from "vitest";

import {
  buildLocalChannelBindings,
  buildLocalPreviewMatrix,
  createChannelPreviewEvalCase,
  listChannelBindings,
  previewChannelMatrix,
  recordChannelActivity,
  upsertChannelBinding,
  updateChannelReadiness,
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
      if (url.includes("/readiness/")) {
        return new Response(
          JSON.stringify({
            ...buildLocalChannelBindings("agt_1")[1],
            status: "ready",
            readiness: [
              {
                id: "business_verified",
                label: "Business identity verified",
                status: "passed",
                evidence_ref: "provider/meta/business/waba_123",
                message: "verified",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
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
    const readiness = await updateChannelReadiness(
      "agt_1",
      "cb_1",
      "business_verified",
      {
        status: "passed",
        evidence_ref: "provider/meta/business/waba_123",
        message: "verified",
      },
      { baseUrl: "https://cp.test", fetcher },
    );

    expect(listed.items).toHaveLength(9);
    expect(updated.provider).toBe("Meta Cloud API");
    expect(readiness.readiness[0]?.status).toBe("passed");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/channel-bindings",
      expect.objectContaining({ method: "GET" }),
    );
    expect(JSON.parse(String(fetcher.mock.calls[1]![1]?.body))).toMatchObject({
      channel_type: "whatsapp",
      provider: "Meta Cloud API",
    });
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/channel-bindings/cb_1/readiness/business_verified",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("records channel activity through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        ...buildLocalChannelBindings("agt_1")[1],
        id: "cb_1",
        last_traffic_at: "2026-05-10T10:00:00Z",
        last_failure_at: "2026-05-10T10:00:00Z",
      }),
    );

    const activity = await recordChannelActivity(
      "agt_1",
      "cb_1",
      {
        status: "failure",
        trace_id: "trace_whatsapp_template_failure",
        occurred_at: "2026-05-10T10:00:00Z",
        failure_message: "Template language was rejected by provider.",
      },
      { baseUrl: "https://cp.test", fetcher },
    );

    expect(activity.last_traffic_at).toBe("2026-05-10T10:00:00Z");
    expect(activity.last_failure_at).toBe("2026-05-10T10:00:00Z");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/channel-bindings/cb_1/activity",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("trace_whatsapp_template_failure"),
      }),
    );
  });

  it("marks channel binding reads as degraded instead of pretending they are live", async () => {
    const listed = await listChannelBindings("agt_1", { baseUrl: "" });

    expect(listed.items).toHaveLength(9);
    expect(listed.degraded_reason).toMatch(/requires cp-api/i);
    expect(listed.items.every((binding) => binding.status === "not_configured"))
      .toBe(true);
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

  it("does not fabricate channel mutations or previews without cp-api", async () => {
    const previewInput = {
      scenario_title: "Duplicate charge",
      user_message: "I was charged twice.",
      expected_outcome: "Verify the charge and explain the refund path.",
      channel_types: ["whatsapp" as const],
    };

    await expect(
      upsertChannelBinding(
        "agt_1",
        { channel_type: "whatsapp", provider: "Meta Cloud API" },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      previewChannelMatrix("agt_1", previewInput, { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      updateChannelReadiness(
        "agt_1",
        "cb_1",
        "business_verified",
        { status: "passed", evidence_ref: "provider/meta/business/waba_123" },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      recordChannelActivity(
        "agt_1",
        "cb_1",
        { status: "success", trace_id: "trace_123" },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      createChannelPreviewEvalCase(
        "agt_1",
        {
          scenario_title: "Duplicate charge",
          channel_type: "whatsapp",
          binding_id: "cb_1",
          user_message: "I was charged twice.",
          rendered_preview: "Verify the charge.",
          expected_outcome: "Verify the charge and explain the refund path.",
          failure_reason: "Template missing.",
          source_ref: "test",
        },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic channel behavior explicitly opt-in", async () => {
    const previewInput = {
      scenario_title: "Duplicate charge",
      user_message: "I was charged twice.",
      expected_outcome: "Verify the charge and explain the refund path.",
      channel_types: ["whatsapp" as const],
    };

    const fixtureList = await listChannelBindings("agt_1", {
      baseUrl: "",
      allowFixture: true,
    });
    expect(fixtureList.items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ channel_type: "web_chat" }),
        expect.objectContaining({ channel_type: "voice" }),
      ]),
    );
    expect(fixtureList.degraded_reason).toBeUndefined();

    await expect(
      upsertChannelBinding(
        "agt_1",
        { channel_type: "whatsapp", provider: "Meta Cloud API" },
        { baseUrl: "", allowFixture: true },
      ),
    ).resolves.toMatchObject({
      channel_type: "whatsapp",
      provider: "Meta Cloud API",
      status: "draft",
    });

    await expect(
      previewChannelMatrix("agt_1", previewInput, {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      summary: expect.objectContaining({ channels: 1 }),
    });

    await expect(
      createChannelPreviewEvalCase(
        "agt_1",
        {
          ...buildLocalPreviewMatrix("agt_1", previewInput).rows[0]!
            .eval_case_seed,
          failure_reason: "Template missing.",
        },
        { baseUrl: "", allowFixture: true },
      ),
    ).resolves.toMatchObject({
      ok: true,
      suite_id: "local_channel_formatting_failures",
    });

    await expect(
      updateChannelReadiness(
        "agt_1",
        "cb_1",
        "business_verified",
        { status: "passed", evidence_ref: "provider/meta/business/waba_123" },
        { baseUrl: "", allowFixture: true },
      ),
    ).resolves.toMatchObject({
      id: "cb_1",
      readiness: [
        expect.objectContaining({
          id: "business_verified",
          status: "passed",
        }),
      ],
    });

    await expect(
      recordChannelActivity(
        "agt_1",
        "cb_1",
        {
          status: "failure",
          trace_id: "trace_123",
          occurred_at: "2026-05-10T10:00:00Z",
        },
        { baseUrl: "", allowFixture: true },
      ),
    ).resolves.toMatchObject({
      id: "cb_1",
      last_traffic_at: "2026-05-10T10:00:00Z",
      last_failure_at: "2026-05-10T10:00:00Z",
    });
  });
});
