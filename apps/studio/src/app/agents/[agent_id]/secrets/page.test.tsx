import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentSecretsPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("AgentSecretsPage", () => {
  afterEach(() => {
    if (ORIGINAL_BASE === undefined) delete process.env.LOOP_CP_API_BASE_URL;
    else process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
    vi.unstubAllGlobals();
  });

  it("surfaces a degraded vault state instead of a false empty secrets list", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        new Response("missing", { status: 404 }),
      ),
    );

    render(await AgentSecretsPage({ params: { agent_id: "agent_secret" } }));

    expect(screen.getByTestId("secrets-degraded")).toHaveTextContent(
      "vault route returned 404",
    );
    expect(screen.queryByTestId("secrets-empty")).not.toBeInTheDocument();
    expect(screen.getByTestId("add-secret-button")).toBeDisabled();
  });
});
