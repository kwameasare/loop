import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import EvalRunPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("EvalRunPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders degraded state instead of not-found when cp-api is unavailable", async () => {
    render(await EvalRunPage({ params: { run_id: "evr_evs_support_smoke_002" } }));

    expect(screen.getByTestId("eval-run-page")).toBeInTheDocument();
    expect(screen.getByText("Eval Run is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/missing control-plane evidence into a false not-found/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required to load eval run details/i),
    ).toBeInTheDocument();
  });

  it("renders degraded state instead of not-found when cp-api returns 404", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        new Response("missing", { status: 404 }),
      ),
    );

    render(await EvalRunPage({ params: { run_id: "evr_missing" } }));

    expect(screen.getByTestId("eval-run-page")).toBeInTheDocument();
    expect(screen.getByText("Eval Run is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/eval run detail route returned 404/i),
    ).toBeInTheDocument();
  });
});
