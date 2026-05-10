import { describe, expect, it, vi } from "vitest";

import {
  acceptMigrationRepair,
  advanceMigrationCutover,
  createMigrationImport,
  listMigrationImports,
  localMigrationRun,
  migrationSourceById,
  rollbackMigrationCutover,
} from "./migration-runs";

describe("migration-runs client", () => {
  it("does not fabricate an empty import list when cp-api is unconfigured", async () => {
    await expect(listMigrationImports("ws_1")).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required",
    );
  });

  it("keeps an empty import fixture explicitly opt-in", async () => {
    await expect(
      listMigrationImports("ws_1", { allowFixture: true }),
    ).resolves.toEqual({ items: [] });
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

  it("posts import, repair acceptance, advance, and rollback requests to durable endpoints", async () => {
    const baseRun = localMigrationRun("ws_1");
    const run = {
      ...baseRun,
      status: "mapped" as const,
      inventory: [
        ...baseRun.inventory,
        {
          id: "inv_integrations",
          kind: "integrations",
          label: "Integrations",
          count: 2,
          loop_target: "tool contracts",
          confidence: 58,
          severity: "blocking" as const,
          evidence_ref: "audit/migration/local/inventory/integrations",
        },
      ],
      readiness: {
        ...baseRun.readiness,
        blocking_count: 1,
      },
    };
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/migrations/imports")) {
        return Response.json(run, { status: 201 });
      }
      if (url.includes("/repairs/rep_inv_integrations/accept")) {
        return Response.json({
          ...run,
          inventory: run.inventory.map((item) =>
            item.id === "inv_integrations"
              ? { ...item, severity: "ok", resolved_by_repair_id: "rep_inv_integrations" }
              : item,
          ),
        });
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
      acceptMigrationRepair(
        "ws_1",
        run.id,
        { repair_id: "rep_inv_integrations" },
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
    const repairCall = fetcher.mock.calls.find(([input]) =>
      String(input).includes("/repairs/rep_inv_integrations/accept"),
    );
    expect(repairCall?.[1]).toMatchObject({ method: "POST" });
    expect(JSON.parse(String((repairCall?.[1] as RequestInit).body))).toMatchObject({
      repair_id: "rep_inv_integrations",
    });
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
      acceptMigrationRepair(
        "ws_1",
        run.id,
        { repair_id: "rep_inv_integrations" },
        { fallbackRun: run },
      ),
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
      acceptMigrationRepair(
        "ws_1",
        run.id,
        { repair_id: "rep_inv_intents" },
        { fallbackRun: run, allowFixture: true },
      ),
    ).resolves.toMatchObject({
      inventory: expect.arrayContaining([
        expect.objectContaining({
          id: "inv_intents",
          severity: "ok",
        }),
      ]),
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
