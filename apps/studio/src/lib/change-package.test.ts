import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildLocalChangePackage,
  fetchCurrentChangePackage,
  generateChangePackage,
  submitChangePackage,
} from "./change-package";

describe("change package client", () => {
  const original = process.env.LOOP_CP_API_BASE_URL;

  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = original;
    vi.restoreAllMocks();
  });

  it("builds an honest local draft when preflight has not run", () => {
    const local = buildLocalChangePackage("agt_1");
    expect(local.status).toBe("draft");
    expect(local.summary).toMatch(/No preflight Change Package/);
    expect(local.content_hash).toBe("unconfigured");
  });

  it("fetches the current change package", async () => {
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            item: { ...buildLocalChangePackage("agt_1"), id: "cp_1" },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );

    const result = await fetchCurrentChangePackage("agt_1", { fetcher });

    expect(result.item?.id).toBe("cp_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/change-packages/current",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("generates and submits preflight packages", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/submit")) {
        return new Response(
          JSON.stringify({
            ...buildLocalChangePackage("agt_1"),
            id: "cp_1",
            status: "submitted",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          ...buildLocalChangePackage("agt_1"),
          id: "cp_1",
          status: "generated",
          summary: "Promote draft.",
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      );
    });

    const generated = await generateChangePackage(
      "agt_1",
      { summary: "Promote draft.", to_version_id: "v2" },
      { fetcher },
    );
    const submitted = await submitChangePackage("agt_1", generated.id, {
      fetcher,
    });

    expect(generated.status).toBe("generated");
    expect(submitted.status).toBe("submitted");
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      summary: "Promote draft.",
      to_version_id: "v2",
    });
  });
});
