import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import de from "@/locales/de/common.json";
import en from "@/locales/en/common.json";
import es from "@/locales/es/common.json";
import fr from "@/locales/fr/common.json";
import ja from "@/locales/ja/common.json";

import { type TargetStateKind } from "./copy";
import { TargetState } from "./target-state";

const STATES: TargetStateKind[] = [
  "loading",
  "empty",
  "error",
  "degraded",
  "stale",
  "permissionBlocked",
];

const COPY_FIELDS = [
  "eyebrow",
  "title",
  "description",
  "evidenceLabel",
  "primaryAction",
  "secondaryAction",
  "stageLabel",
  "requestIdLabel",
  "updatedAtLabel",
] as const;

const LOCALES = { en, es, de, fr, ja };

describe("TargetState", () => {
  it("renders a named loading state with a skeleton and status role", () => {
    render(
      <TargetState
        state="loading"
        objectName="Traces"
        stage="Querying recent traces"
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Traces is loading");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Querying recent traces",
    );
    expect(screen.getByTestId("target-state-skeleton")).toBeInTheDocument();
  });

  it("renders error evidence with request id and recovery actions", () => {
    const retry = vi.fn();
    render(
      <TargetState
        state="error"
        objectName="Deploy gates"
        requestId="req_42"
        primaryAction={{ onClick: retry }}
        secondaryAction={{ href: "mailto:support@loop.dev" }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Deploy gates could not load",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("req_42");
    expect(screen.getByRole("link", { name: "Report" })).toHaveAttribute(
      "href",
      "mailto:support@loop.dev",
    );
  });

  it("renders degraded, stale, and permission-blocked cues without relying on color", () => {
    const { rerender } = render(
      <TargetState
        state="degraded"
        objectName="Tools room"
        evidence="Status page incident loop-status-17"
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Degraded");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Status page incident loop-status-17",
    );

    rerender(
      <TargetState
        state="stale"
        objectName="Agent map"
        updatedAt="2026-05-06 10:14 UTC"
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Stale");
    expect(screen.getByRole("status")).toHaveTextContent(
      "2026-05-06 10:14 UTC",
    );

    rerender(
      <TargetState
        state="permissionBlocked"
        objectName="production grant"
        evidence="Policy: tools.grant requires workspace admin"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Permission blocked");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Policy: tools.grant requires workspace admin",
    );
  });

  it("ships complete i18n keys for every target and section state", () => {
    for (const [lang, locale] of Object.entries(LOCALES)) {
      for (const namespace of ["targetStates", "sectionStates"] as const) {
        for (const state of STATES) {
          for (const field of COPY_FIELDS) {
            expect(
              locale[namespace][state],
              `${lang}.${namespace}.${state}.${field}`,
            ).toHaveProperty(field);
          }
        }
      }
    }
  });
});
