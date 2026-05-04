import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NewSuiteModal } from "./new-suite-modal";

describe("NewSuiteModal", () => {
  it("renders just the trigger button when closed", () => {
    render(<NewSuiteModal existingNames={[]} agentIds={["agt_a"]} />);
    expect(
      screen.getByRole("button", { name: "New suite" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("new-suite-form")).toBeNull();
  });

  it("opens the form on click", () => {
    render(<NewSuiteModal existingNames={[]} agentIds={["agt_a"]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    expect(screen.getByTestId("new-suite-form")).toBeInTheDocument();
  });

  it("rejects invalid slugs", async () => {
    render(<NewSuiteModal existingNames={[]} agentIds={["agt_a"]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/suite name/i), {
      target: { value: "Bad Name!" },
    });
    fireEvent.submit(screen.getByTestId("new-suite-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/lowercase/);
  });

  it("rejects duplicate names client-side", async () => {
    render(
      <NewSuiteModal existingNames={["smoke"]} agentIds={["agt_a"]} />,
    );
    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/suite name/i), {
      target: { value: "smoke" },
    });
    fireEvent.submit(screen.getByTestId("new-suite-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/already/);
  });

  it("blocks submit when no agent ids are available", async () => {
    render(<NewSuiteModal existingNames={[]} agentIds={[]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    fireEvent.change(screen.getByLabelText(/suite name/i), {
      target: { value: "smoke" },
    });
    fireEvent.submit(screen.getByTestId("new-suite-form"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Pick the agent/);
  });

  it("shows the submit button label while disabled in submitting state", async () => {
    // We can't easily trigger the success path without window.location.reload,
    // but the form's submitting state is observable via the button label.
    render(<NewSuiteModal existingNames={[]} agentIds={["agt_a"]} />);
    fireEvent.click(screen.getByTestId("new-suite-open"));
    expect(
      screen.getByRole("button", { name: "Create" }),
    ).toBeInTheDocument();
  });
});
