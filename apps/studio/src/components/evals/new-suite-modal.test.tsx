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

import { NewSuiteModal } from "./new-suite-modal";

describe("NewSuiteModal", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("renders just the trigger button when closed", () => {
    render(<NewSuiteModal existingNames={[]} />);
    expect(
      screen.getByRole("button", { name: "New suite" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("new-suite-form")).toBeNull();
  });

  it("opens the form on click", () => {
    render(<NewSuiteModal existingNames={[]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    expect(screen.getByTestId("new-suite-form")).toBeInTheDocument();
  });

  it("rejects invalid names", async () => {
    render(<NewSuiteModal existingNames={[]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Bad Name!" },
    });
    fireEvent.change(screen.getByTestId("new-suite-dataset-ref"), {
      target: { value: "datasets/support-smoke-v1" },
    });
    fireEvent.submit(screen.getByTestId("new-suite-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/lowercase/);
  });

  it("rejects duplicate names client-side", async () => {
    render(<NewSuiteModal existingNames={["smoke"]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "smoke" },
    });
    fireEvent.change(screen.getByTestId("new-suite-dataset-ref"), {
      target: { value: "datasets/support-smoke-v1" },
    });
    fireEvent.submit(screen.getByTestId("new-suite-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/already/);
  });

  it("requires dataset_ref", async () => {
    render(<NewSuiteModal existingNames={[]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "smoke" },
    });
    fireEvent.submit(screen.getByTestId("new-suite-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Dataset ref/);
  });

  it("requires at least one metric", async () => {
    render(<NewSuiteModal existingNames={[]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "smoke" },
    });
    fireEvent.change(screen.getByTestId("new-suite-dataset-ref"), {
      target: { value: "datasets/support-smoke-v1" },
    });

    // "accuracy" is selected by default; uncheck it to test validation.
    fireEvent.click(screen.getByTestId("new-suite-metric-accuracy"));
    fireEvent.submit(screen.getByTestId("new-suite-form"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Select at least one metric/,
    );
  });

  it("submits and navigates to suite detail", async () => {
    const createSuite = vi.fn().mockResolvedValue({ id: "evs_42" });
    render(
      <NewSuiteModal existingNames={[]} createSuite={createSuite} />,
    );

    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "smoke" },
    });
    fireEvent.change(screen.getByTestId("new-suite-dataset-ref"), {
      target: { value: "datasets/support-smoke-v1" },
    });
    fireEvent.click(screen.getByTestId("new-suite-metric-latency_p95"));

    fireEvent.submit(screen.getByTestId("new-suite-form"));

    await waitFor(() => {
      expect(createSuite).toHaveBeenCalledWith({
        name: "smoke",
        dataset_ref: "datasets/support-smoke-v1",
        metrics: ["accuracy", "latency_p95"],
      });
    });
    expect(push).toHaveBeenCalledWith("/evals/suites/evs_42");
  });
});
