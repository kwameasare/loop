import { describe, expect, it, vi } from "vitest";

import { EMPTY_FILTERS } from "@/components/workspaces/audit-log-page";
import {
  AUDIT_EVENTS_CP_API_REQUIRED,
  filterAuditRows,
  listAuditEvents,
} from "./audit-events";

describe("audit-events", () => {
  it("loads and maps cp-api audit events", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "ev-1",
              occurred_at: "2026-05-07T10:00:00Z",
              workspace_id: "ws-1",
              actor_sub: "sam@example.com",
              action: "agent.promote",
              resource_type: "agent_version",
              resource_id: "ver-1",
              outcome: "success",
            },
          ],
          total: 1,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const result = await listAuditEvents("ws-1", {
      baseUrl: "https://cp.example.test/v1",
      fetcher,
    });

    expect(result.events[0]).toMatchObject({
      actorSub: "sam@example.com",
      action: "agent.promote",
      resourceType: "agent_version",
    });
  });

  it("fails closed when cp-api base URL is not configured", async () => {
    await expect(listAuditEvents("ws-1")).rejects.toThrow(
      AUDIT_EVENTS_CP_API_REQUIRED,
    );
  });

  it("filters rows by action and outcome", () => {
    const rows = [
      {
        id: "a",
        occurredAt: "2026-05-07T10:00:00Z",
        actorSub: "ops@example.com",
        action: "voice.config.updated",
        resourceType: "voice",
        resourceId: "ws-1",
        ip: null,
        outcome: "success" as const,
      },
      {
        id: "b",
        occurredAt: "2026-05-07T11:00:00Z",
        actorSub: "sec@example.com",
        action: "memory.delete",
        resourceType: "memory",
        resourceId: "pref",
        ip: null,
        outcome: "denied" as const,
      },
    ];

    expect(
      filterAuditRows(rows, {
        ...EMPTY_FILTERS,
        action: "memory",
        outcome: "denied",
      }).map((row) => row.id),
    ).toEqual(["b"]);
  });
});
