import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildLocalChangePackage,
  expireChangePackageApprovals,
  recordChangePackageApproval,
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
    expect(local.pre_approved_classes).toEqual([]);
    expect(local.release_candidate_id).toBe("rc-current");
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

  it("requires cp-api for the current change package by default", async () => {
    await expect(
      fetchCurrentChangePackage("agt_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps current change package fallback explicitly opt-in", async () => {
    await expect(
      fetchCurrentChangePackage("agt_1", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toEqual({ item: null });
  });

  it("does not fabricate preflight or approval mutations without cp-api", async () => {
    const local = buildLocalChangePackage("agt_1");

    await expect(
      generateChangePackage(
        "agt_1",
        { summary: "Promote draft.", to_version_id: "v2" },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      submitChangePackage("agt_1", "cp_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      recordChangePackageApproval(
        "agt_1",
        "cp_1",
        { approval_id: "owner", decision: "approve" },
        { baseUrl: "", fallbackPackage: local },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      expireChangePackageApprovals(
        "agt_1",
        "cp_1",
        { approval_ids: ["owner"], reason: "SLA elapsed." },
        { baseUrl: "", fallbackPackage: local },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic preflight and approval mutations explicitly opt-in", async () => {
    const local = {
      ...buildLocalChangePackage("agt_1"),
      required_approvals: [
        {
          id: "owner",
          role: "Agent owner",
          required: true,
          satisfied: false,
          reason: "Owner approval required.",
        },
      ],
    };

    await expect(
      generateChangePackage(
        "agt_1",
        { summary: "Promote draft.", to_version_id: "v2" },
        { baseUrl: "", allowFixture: true },
      ),
    ).resolves.toMatchObject({ status: "generated", summary: "Promote draft." });

    await expect(
      submitChangePackage("agt_1", "cp_1", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({ id: "cp_1", status: "submitted" });

    await expect(
      recordChangePackageApproval(
        "agt_1",
        "cp_1",
        { approval_id: "owner", decision: "approve", comment: "Looks safe." },
        { baseUrl: "", allowFixture: true, fallbackPackage: local },
      ),
    ).resolves.toMatchObject({
      id: "cp_1",
      status: "approved",
      approval_status: "approved",
    });

    await expect(
      expireChangePackageApprovals(
        "agt_1",
        "cp_1",
        { approval_ids: ["owner"], reason: "SLA elapsed." },
        { baseUrl: "", allowFixture: true, fallbackPackage: local },
      ),
    ).resolves.toMatchObject({
      id: "cp_1",
      status: "changes_requested",
      approval_status: "expired",
      required_approvals: [
        expect.objectContaining({
          id: "owner",
          state: "expired",
          expired_reason: "SLA elapsed.",
        }),
      ],
    });
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
      {
        summary: "Promote draft.",
        to_version_id: "v2",
        release_candidate_id: "rc_2",
      },
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
      release_candidate_id: "rc_2",
    });
  });

  it("records approval decisions through the content-hash endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            ...buildLocalChangePackage("agt_1"),
            id: "cp_1",
            status: "approved",
            approval_status: "approved",
            required_approvals: [
              {
                id: "owner",
                role: "Agent owner",
                required: true,
                satisfied: true,
                state: "approved",
                reason: "Owner approved.",
                content_hash: "hash_123",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );

    const reviewed = await recordChangePackageApproval(
      "agt_1",
      "cp_1",
      { approval_id: "owner", decision: "approve", comment: "Looks safe." },
      { fetcher },
    );

    expect(reviewed.status).toBe("approved");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/change-packages/cp_1/approvals",
      expect.objectContaining({ method: "POST" }),
    );
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      approval_id: "owner",
      decision: "approve",
      comment: "Looks safe.",
    });
  });

  it("expires requested approvals through the approval expiry endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            ...buildLocalChangePackage("agt_1"),
            id: "cp_1",
            status: "changes_requested",
            approval_status: "expired",
            required_approvals: [
              {
                id: "compliance",
                role: "Compliance reviewer",
                required: true,
                satisfied: false,
                state: "expired",
                reason: "Compliance approval required.",
                expired_reason: "Compliance review SLA elapsed.",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );

    const expired = await expireChangePackageApprovals(
      "agt_1",
      "cp_1",
      {
        approval_ids: ["compliance"],
        reason: "Compliance review SLA elapsed.",
      },
      { fetcher },
    );

    expect(expired.approval_status).toBe("expired");
    expect(expired.required_approvals[0]?.state).toBe("expired");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/change-packages/cp_1/approvals/expire",
      expect.objectContaining({ method: "POST" }),
    );
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      approval_ids: ["compliance"],
      reason: "Compliance review SLA elapsed.",
    });
  });
});
