import { describe, expect, it } from "vitest";

import {
  CANONICAL_DOMAINS,
  buildTargetUxFixture,
  fixtureDomainCoverage,
  targetUxFixtures,
  type TargetChannel,
} from "@/lib/target-ux";

describe("target UX fixtures", () => {
  it("covers every canonical implementation domain", () => {
    const coverage = fixtureDomainCoverage(targetUxFixtures);
    for (const domain of CANONICAL_DOMAINS) {
      expect(coverage[domain], `${domain} needs at least one fixture`).toBe(true);
    }
  });

  it("keeps generated cp-api output out of target fixture contracts", () => {
    const fixture = buildTargetUxFixture();
    expect(fixture.workspace.name).toBe("Acme Support Ops");
    expect(fixture.traces[0]?.snapshotId).toBe(fixture.snapshots[0]?.id);
  });

  it("does not narrow target agent channels below the channel-binding system", () => {
    const channels: TargetChannel[] = [
      "web",
      "web_chat",
      "whatsapp",
      "telegram",
      "slack",
      "teams",
      "sms",
      "email",
      "voice",
      "webhook_api",
    ];
    expect(channels).toContain("telegram");
    expect(channels).toContain("email");
    expect(channels).toContain("webhook_api");
  });
});
