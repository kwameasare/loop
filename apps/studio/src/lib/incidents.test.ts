import { describe, expect, it, vi } from "vitest";

import {
  createIncidentFixChangePackage,
  listAgentIncidents,
  listWorkspaceIncidents,
  seedIncidentEvalCases,
  transitionIncident,
} from "./incidents";

describe("incidents client", () => {
  it("keeps local incident response records explicitly opt-in", async () => {
    const incidents = await listWorkspaceIncidents("ws_1", {
      baseUrl: "",
      allowFixture: true,
    });

    expect(incidents.items[0]?.status).toBe("contained");
    expect(incidents.items[0]?.rollback_action_ref).toContain("rollback");
  });

  it("loads agent incidents from the agent-scoped endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({ items: [{ id: "inc_1", status: "open" }] }),
    );

    await listAgentIncidents("agt_1", {
      baseUrl: "https://cp.test/v1",
      fetcher,
      token: "tok",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/incidents",
      expect.objectContaining({
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
  });

  it("posts incident eval seeding to the incident route", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        ok: true,
        suite_id: "suite_1",
        case_ids: ["case_1"],
        incident: { id: "inc_1" },
      }),
    );

    const response = await seedIncidentEvalCases("agt_1", "inc_1", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(response.case_ids).toEqual(["case_1"]);
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/incidents/inc_1/eval-cases",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not fabricate incident state without cp-api", async () => {
    await expect(
      listWorkspaceIncidents("ws_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(listAgentIncidents("agt_1", { baseUrl: "" })).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required",
    );

    await expect(
      seedIncidentEvalCases("agt_1", "inc_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      createIncidentFixChangePackage("agt_1", "inc_1", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      transitionIncident("agt_1", "inc_1", "resolve", "resolved", {
        baseUrl: "",
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic incident actions explicitly opt-in", async () => {
    await expect(
      seedIncidentEvalCases("agt_1", "inc_1", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      ok: true,
      suite_id: "suite_incident_regressions_local",
    });

    await expect(
      createIncidentFixChangePackage("agt_1", "inc_1", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      ok: true,
      change_package: expect.objectContaining({ id: "cp_inc_1" }),
    });

    await expect(
      transitionIncident("agt_1", "inc_1", "resolve", "resolved", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      id: "inc_1",
      status: "resolved",
    });
  });
});
