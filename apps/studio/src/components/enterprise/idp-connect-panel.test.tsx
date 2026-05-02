/**
 * Component tests for IdpConnectPanel (S615).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { IdpConnectPanel } from "./idp-connect-panel";
import {
  FIXTURE_IDP_CONNECTED,
  FIXTURE_IDP_NOT_CONFIGURED,
  FIXTURE_IDP_PENDING,
} from "@/lib/enterprise";

describe("IdpConnectPanel", () => {
  it("shows 'Not configured' badge when status is not_configured", () => {
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={vi.fn()}
      />,
    );
    const badge = screen.getByTestId("idp-status-badge");
    expect(badge.textContent).toMatch(/Not configured/);
  });

  it("shows 'Pending verification' badge when status is pending_verification", () => {
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_PENDING}
        onConnect={vi.fn()}
      />,
    );
    expect(screen.getByTestId("idp-status-badge").textContent).toMatch(
      /Pending verification/,
    );
    expect(screen.getByTestId("idp-entity-id").textContent).toMatch(/okta/);
    expect(screen.getByTestId("idp-acs-url").textContent).toMatch(/loop\.dev/);
  });

  it("shows 'Connected' badge when status is connected", () => {
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_CONNECTED}
        onConnect={vi.fn()}
      />,
    );
    expect(screen.getByTestId("idp-status-badge").textContent).toMatch(
      /Connected/,
    );
    expect(screen.getByTestId("idp-connected-at")).toBeInTheDocument();
  });

  it("defaults to URL input mode", () => {
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={vi.fn()}
      />,
    );
    expect(screen.getByTestId("idp-tab-url")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("idp-metadata-url-input")).toBeInTheDocument();
    expect(
      screen.queryByTestId("idp-metadata-xml-input"),
    ).not.toBeInTheDocument();
  });

  it("switches to XML input mode when 'Upload XML' tab is clicked", () => {
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("idp-tab-xml"));
    expect(screen.getByTestId("idp-tab-xml")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("idp-metadata-xml-input")).toBeInTheDocument();
    expect(
      screen.queryByTestId("idp-metadata-url-input"),
    ).not.toBeInTheDocument();
  });

  it("calls onConnect with url source and updates status to pending", async () => {
    const onConnect = vi.fn().mockResolvedValue(FIXTURE_IDP_PENDING);
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={onConnect}
      />,
    );

    fireEvent.change(screen.getByTestId("idp-metadata-url-input"), {
      target: { value: "https://idp.example.com/metadata" },
    });
    fireEvent.submit(screen.getByTestId("idp-connect-form"));

    await waitFor(() => {
      expect(onConnect).toHaveBeenCalledWith({
        url: "https://idp.example.com/metadata",
      });
      expect(screen.getByTestId("idp-status-badge").textContent).toMatch(
        /Pending verification/,
      );
    });
  });

  it("calls onConnect with xml source when in XML mode", async () => {
    const onConnect = vi.fn().mockResolvedValue(FIXTURE_IDP_PENDING);
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={onConnect}
      />,
    );

    fireEvent.click(screen.getByTestId("idp-tab-xml"));
    fireEvent.change(screen.getByTestId("idp-metadata-xml-input"), {
      target: { value: "<EntityDescriptor/>" },
    });
    fireEvent.submit(screen.getByTestId("idp-connect-form"));

    await waitFor(() => {
      expect(onConnect).toHaveBeenCalledWith({ xml: "<EntityDescriptor/>" });
    });
  });

  it("shows validation error when URL mode but input is empty", async () => {
    const onConnect = vi.fn();
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={onConnect}
      />,
    );
    fireEvent.submit(screen.getByTestId("idp-connect-form"));
    await waitFor(() => {
      expect(screen.getByTestId("idp-connect-error").textContent).toMatch(
        /required/i,
      );
    });
    expect(onConnect).not.toHaveBeenCalled();
  });

  it("shows validation error when XML mode but input is empty", async () => {
    const onConnect = vi.fn();
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={onConnect}
      />,
    );
    fireEvent.click(screen.getByTestId("idp-tab-xml"));
    fireEvent.submit(screen.getByTestId("idp-connect-form"));
    await waitFor(() => {
      expect(screen.getByTestId("idp-connect-error").textContent).toMatch(
        /required/i,
      );
    });
    expect(onConnect).not.toHaveBeenCalled();
  });

  it("shows error message when onConnect rejects", async () => {
    const onConnect = vi
      .fn()
      .mockRejectedValue(new Error("Network failure"));
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={onConnect}
      />,
    );
    fireEvent.change(screen.getByTestId("idp-metadata-url-input"), {
      target: { value: "https://idp.example.com/metadata" },
    });
    fireEvent.submit(screen.getByTestId("idp-connect-form"));
    await waitFor(() => {
      expect(screen.getByTestId("idp-connect-error").textContent).toMatch(
        /Network failure/,
      );
    });
  });

  it("status flips to Connected when onConnect returns connected status", async () => {
    const onConnect = vi.fn().mockResolvedValue(FIXTURE_IDP_CONNECTED);
    render(
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={onConnect}
      />,
    );
    fireEvent.change(screen.getByTestId("idp-metadata-url-input"), {
      target: { value: "https://idp.example.com/metadata" },
    });
    fireEvent.submit(screen.getByTestId("idp-connect-form"));
    await waitFor(() => {
      expect(screen.getByTestId("idp-status-badge").textContent).toMatch(
        /Connected/,
      );
    });
  });
});
