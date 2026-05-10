import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import EvalSuitePage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("EvalSuitePage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders degraded state instead of not-found when cp-api is unavailable", async () => {
    render(await EvalSuitePage({ params: { suite_id: "evs_support_smoke" } }));

    expect(screen.getByTestId("eval-suite-page")).toBeInTheDocument();
    expect(screen.getByText("Eval Suite is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/will not show local fixture runs as production evidence/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required to load eval suite details/i),
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

    render(await EvalSuitePage({ params: { suite_id: "evs_missing" } }));

    expect(screen.getByTestId("eval-suite-page")).toBeInTheDocument();
    expect(screen.getByText("Eval Suite is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/eval suite detail route returned 404/i),
    ).toBeInTheDocument();
  });
});
