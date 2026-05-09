import { describe, expect, it, vi } from "vitest";

import {
  advanceMigrationCutover,
  createMigrationImport,
  listMigrationImports,
  localMigrationRun,
  rollbackMigrationCutover,
} from "./migration-runs";

describe("migration-runs client", () => {
  it("falls back to empty list when no cp-api base URL is configured", async () => {
    await expect(listMigrationImports("ws_1")).resolves.toEqual({ items: [] });
  });

  it("posts import, advance, and rollback requests to the durable migration endpoints", async () => {
    const run = localMigrationRun("ws_1");
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/migrations/imports")) {
        return Response.json(run, { status: 201 });
      }
      if (url.includes("/cutover/advance")) {
        return Response.json({ ...run, status: "cutover_active" });
      }
      if (url.includes("/cutover/rollback")) {
        return Response.json({ ...run, status: "rolled_back" });
      }
      return Response.json({ items: [run] });
    });

    await expect(
      createMigrationImport(
        "ws_1",
        {
          archive_name: "acme.bpz",
          target_agent_name: "Acme Import",
        },
        { baseUrl: "https://cp.example.test", fetcher },
      ),
    ).resolves.toMatchObject({ id: run.id });
    await expect(
      advanceMigrationCutover(
        "ws_1",
        run.id,
        { stage_id: "shadow" },
        { baseUrl: "https://cp.example.test", fetcher },
      ),
    ).resolves.toMatchObject({ status: "cutover_active" });
    await expect(
      rollbackMigrationCutover(
        "ws_1",
        run.id,
        { trigger_id: "manual" },
        { baseUrl: "https://cp.example.test", fetcher },
      ),
    ).resolves.toMatchObject({ status: "rolled_back" });
  });
});
