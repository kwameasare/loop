import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  EMPTY_COMMITMENT_BODY,
  acceptCommitment,
  buildLocalCommitmentDocument,
  fetchCurrentCommitment,
  missingCommitmentFields,
  parseList,
  saveCommitmentDraft,
} from "./agent-commitment";

describe("agent commitment client", () => {
  const original = process.env.LOOP_CP_API_BASE_URL;

  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = original;
    vi.restoreAllMocks();
  });

  it("parses list fields from comma and newline separated text", () => {
    expect(parseList("web, whatsapp\nvoice")).toEqual([
      "web",
      "whatsapp",
      "voice",
    ]);
  });

  it("reports required commitment gaps without inventing data", () => {
    const local = buildLocalCommitmentDocument("agt_1");

    expect(local.version).toBe(0);
    expect(local.created_from).toBe("studio:local_unconfigured");
    expect(missingCommitmentFields(local.body)).toContain("target_users");
  });

  it("fetches the current Commitment Document from cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            ...buildLocalCommitmentDocument("agt_1"),
            id: "commit_1",
            version: 1,
            workspace_id: "ws_1",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );

    const result = await fetchCurrentCommitment("agt_1", {
      fetcher,
      token: "tok",
    });

    expect(result.id).toBe("commit_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/commitment/current",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("requires cp-api for the current Commitment Document by default", async () => {
    await expect(
      fetchCurrentCommitment("agt_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps local current Commitment Document fallback explicitly opt-in", async () => {
    await expect(
      fetchCurrentCommitment("agt_1", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      id: "commitment_unconfigured",
      created_from: "studio:local_unconfigured",
    });
  });

  it("saves a draft Commitment Document", async () => {
    const body = {
      ...EMPTY_COMMITMENT_BODY,
      business_responsibility: "Handle plan changes",
    };
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            ...buildLocalCommitmentDocument("agt_1", body),
            version: 2,
          }),
          { status: 201, headers: { "content-type": "application/json" } },
        ),
    );

    const result = await saveCommitmentDraft(
      "agt_1",
      { body, created_from: "studio:test" },
      { fetcher },
    );

    expect(result.version).toBe(2);
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      created_from: "studio:test",
      body: { business_responsibility: "Handle plan changes" },
    });
  });

  it("does not fabricate Commitment Document mutations without cp-api", async () => {
    const body = {
      ...EMPTY_COMMITMENT_BODY,
      business_responsibility: "Handle plan changes",
    };

    await expect(
      saveCommitmentDraft(
        "agt_1",
        { body, created_from: "studio:test" },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      acceptCommitment("agt_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic Commitment Document mutations explicitly opt-in", async () => {
    const body = {
      ...EMPTY_COMMITMENT_BODY,
      business_responsibility: "Handle plan changes",
    };

    await expect(
      saveCommitmentDraft(
        "agt_1",
        { body, created_from: "studio:test" },
        { baseUrl: "", allowFixture: true },
      ),
    ).resolves.toMatchObject({
      body: { business_responsibility: "Handle plan changes" },
      status: "draft",
    });

    await expect(
      acceptCommitment("agt_1", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({ status: "draft", version: 0 });
  });
});
