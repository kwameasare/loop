import { describe, expect, it } from "vitest";

import {
  buildQuickBranchLink,
  buildShareLink,
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
