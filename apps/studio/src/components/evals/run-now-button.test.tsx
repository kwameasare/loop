import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
}));

import { RunNowButton } from "./run-now-button";

describe("RunNowButton", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("starts a run and routes to run detail", async () => {
    const triggerRun = vi.fn().mockResolvedValue({ id: "evr_42" });
    render(<RunNowButton suiteId="evs_1" triggerRun={triggerRun} />);

    fireEvent.click(screen.getByTestId("eval-suite-run-now"));

    await waitFor(() => {
      expect(triggerRun).toHaveBeenCalledWith("evs_1");
    });
    expect(push).toHaveBeenCalledWith("/evals/runs/evr_42");
  });

  it("shows an error when run trigger fails", async () => {
    const triggerRun = vi.fn().mockRejectedValue(new Error("503"));
    render(<RunNowButton suiteId="evs_1" triggerRun={triggerRun} />);

    fireEvent.click(screen.getByTestId("eval-suite-run-now"));

    expect(await screen.findByTestId("eval-suite-run-error")).toHaveTextContent(
      "503",
    );
    expect(push).not.toHaveBeenCalled();
  });
});
