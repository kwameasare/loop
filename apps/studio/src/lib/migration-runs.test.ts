import { describe, expect, it, vi } from "vitest";

import {
  advanceMigrationCutover,
  createMigrationImport,
  listMigrationImports,
  localMigrationRun,
  migrationSourceById,
  rollbackMigrationCutover,
} from "./migration-runs";

describe("migration-runs client", () => {
  it("falls back to empty list when no cp-api base URL is configured", async () => {
    await expect(listMigrationImports("ws_1")).resolves.toEqual({ items: [] });
  });

  it("defines import profiles for non-Botpress migration sources", () => {
    expect(migrationSourceById("dialogflow_cx").acceptedInputs).toContain(
      "CX agent export zip",
    );
    expect(migrationSourceById("rasa").defaultArchive).toBe("rasa-project.zip");
    expect(migrationSourceById("conversation_transcripts").description).toMatch(
      /transcripts/i,
    );
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
          source: "dialogflow_cx",
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

  it("does not fabricate migration mutations when cp-api is not configured", async () => {
    const run = localMigrationRun("ws_1");

    await expect(
      createMigrationImport("ws_1", {
        archive_name: "acme.bpz",
        target_agent_name: "Acme Import",
        source: "botpress",
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      advanceMigrationCutover(
        "ws_1",
        run.id,
        { stage_id: "canary_1pct" },
        { fallbackRun: run },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      rollbackMigrationCutover(
        "ws_1",
        run.id,
        { trigger_id: "manual" },
        { fallbackRun: run },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic migration fixtures explicitly opt-in", async () => {
    const run = localMigrationRun("ws_1");

    await expect(
      createMigrationImport(
        "ws_1",
        {
          archive_name: "rasa-project.zip",
          target_agent_name: "Rasa Import",
          source: "rasa",
        },
        { allowFixture: true },
      ),
    ).resolves.toMatchObject({
      archive_name: "rasa-project.zip",
      source: "rasa",
      target_agent_name: "Rasa Import",
    });

    await expect(
      advanceMigrationCutover(
        "ws_1",
        run.id,
        { stage_id: "canary_1pct" },
        { fallbackRun: run, allowFixture: true },
      ),
    ).resolves.toMatchObject({ status: "cutover_active" });

    await expect(
      rollbackMigrationCutover(
        "ws_1",
        run.id,
        { trigger_id: "manual" },
        { fallbackRun: run, allowFixture: true },
      ),
    ).resolves.toMatchObject({ status: "rolled_back" });
  });
});
