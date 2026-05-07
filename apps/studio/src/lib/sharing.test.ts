import { describe, expect, it, vi } from "vitest";

import {
  buildQuickBranchLink,
  buildShareLink,
  createServerShareLink,
  previewRedaction,
  recordAccess,
  revokeShareLink,
} from "@/lib/sharing";

const FROZEN = new Date("2026-05-06T12:00:00Z");
const now = () => FROZEN;

describe("buildShareLink", () => {
  it("builds a deterministic url that includes scope and expiry", () => {
    const link = buildShareLink(
      {
        artifact: "trace",
        artifactId: "trace_refund_742",
        scope: "named-people",
        expiresAt: "2026-05-13T12:00:00.000Z",
        recipients: ["alex@acme.test"],
        redactions: { categories: ["pii"] },
      },
      now,
    );
    expect(link.id).toMatch(/^share_/);
    expect(link.url).toContain("/share/trace/");
    expect(link.url).toContain("scope=named-people");
    expect(link.url).toContain("redact=pii");
    expect(link.active).toBe(true);
  });

  it("creates server-backed share links with redaction metadata", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      expect(String(input)).toBe("https://cp.test/v1/workspaces/ws-1/shares");
      expect(JSON.parse(String(init?.body))).toMatchObject({
        source_type: "trace",
        source_id: "trace_refund_742",
        redactions: ["pii", "secrets"],
      });
      return new Response(
        JSON.stringify({
          id: "share_live_1",
          url: "/share/live/1",
          expires_at: "2026-05-13T12:00:00.000Z",
          redactions: ["pii", "secrets"],
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      );
    });

    const link = await createServerShareLink(
      "ws-1",
      {
        artifact: "trace",
        artifactId: "trace_refund_742",
        scope: "link-anyone",
        expiresAt: "2026-05-13T12:00:00.000Z",
        redactions: { categories: ["pii", "secrets"] },
      },
      { baseUrl: "https://cp.test/v1", fetcher },
      now,
    );

    expect(link.id).toBe("share_live_1");
    expect(link.redactionBanner).toContain("2 redaction");
  });
});

describe("revokeShareLink", () => {
  it("flips the link to inactive and appends an audit event", () => {
    const link = buildShareLink(
      {
        artifact: "deploy-diff",
        artifactId: "deploy_42",
        scope: "branch-reviewers",
        expiresAt: "2026-05-13T12:00:00.000Z",
        redactions: { categories: [] },
      },
      now,
    );
    const result = revokeShareLink(link, "you", { events: [] }, now);
    expect(result.link.active).toBe(false);
    expect(result.log.events).toHaveLength(1);
    expect(result.log.events[0]?.outcome).toBe("revoked");
  });
});

describe("recordAccess", () => {
  it("captures the recipient view in the access log", () => {
    const link = buildShareLink(
      {
        artifact: "eval-result",
        artifactId: "eval_42",
        scope: "workspace",
        expiresAt: "2026-05-13T12:00:00.000Z",
        redactions: { categories: [] },
      },
      now,
    );
    const log = recordAccess(link, "alex", "viewed", { events: [] }, now);
    expect(log.events).toHaveLength(1);
    expect(log.events[0]?.actor).toBe("alex");
  });
});

describe("previewRedaction", () => {
  it("redacts pii email and phone but leaves regular prose alone", () => {
    const out = previewRedaction(
      "ping alex@acme.test or +1 (415) 555 1234 about the refund",
      { categories: ["pii"] },
    );
    expect(out).toContain("[redacted: pii email]");
    expect(out).toContain("[redacted: pii phone]");
    expect(out).toContain("about the refund");
  });

  it("redacts secrets and pricing when their categories are enabled", () => {
    const out = previewRedaction(
      "token sk_ABCDEFGH123 and price $129.99",
      { categories: ["secrets", "pricing"] },
    );
    expect(out).toContain("[redacted: secret]");
    expect(out).toContain("[redacted: pricing]");
  });

  it("is a no-op when no categories are provided", () => {
    const out = previewRedaction("hello world", { categories: [] });
    expect(out).toBe("hello world");
  });
});

describe("buildQuickBranchLink", () => {
  it("encodes agent and branch and lists the focused surfaces", () => {
    const url = buildQuickBranchLink({
      agentId: "agent support",
      branch: "feature/refund clarity",
      surfaces: { canary: false },
    });
    expect(url).toContain("/review/agent%20support/feature%2Frefund%20clarity");
    expect(url).toContain("show=summary");
    expect(url).not.toContain("canary");
  });

  it("defaults to all surfaces enabled", () => {
    const url = buildQuickBranchLink({
      agentId: "a",
      branch: "b",
    });
    const decoded = decodeURIComponent(url);
    expect(decoded).toContain(
      "show=summary,behavior-diff,eval-status,preflight-blockers,canary,actions",
    );
  });
});
