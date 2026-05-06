import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DiffLine } from "@/components/__a11y__/diff-line";
import { KeyboardCheatsheet } from "@/components/__a11y__/keyboard-cheatsheet";
import { LanguagePicker } from "@/components/__a11y__/language-picker";
import { SkipLink } from "@/components/__a11y__/skip-link";
import { StatusGlyph } from "@/components/__a11y__/status-glyph";

describe("StatusGlyph", () => {
  it("communicates status via shape, label and ARIA name (no colour reliance)", () => {
    render(<StatusGlyph variant="fail" label="Eval suite #42" />);
    const node = screen.getByTestId("status-glyph-fail");
    expect(node).toHaveAttribute("aria-label", "Fail: Eval suite #42");
    expect(node).toHaveAttribute("data-stroke", "double");
    expect(node.textContent).toContain("◆");
  });

  it("hides the visible label but keeps the screen-reader announcement", () => {
    render(<StatusGlyph variant="pass" visualLabel={false} />);
    const node = screen.getByTestId("status-glyph-pass");
    expect(node.querySelector(".sr-only")).not.toBeNull();
  });
});

describe("DiffLine", () => {
  it("prefixes added/removed lines with + and -", () => {
    render(
      <>
        <DiffLine kind="added">added</DiffLine>
        <DiffLine kind="removed">removed</DiffLine>
        <DiffLine kind="unchanged">same</DiffLine>
      </>,
    );
    expect(screen.getByTestId("diff-line-added").textContent).toContain("+");
    expect(screen.getByTestId("diff-line-removed").textContent).toContain("-");
    expect(screen.getByTestId("diff-line-unchanged").textContent).toContain("·");
  });
});

describe("SkipLink", () => {
  it("targets the main landmark and renders the localised label", () => {
    render(<SkipLink targetId="main-content" label="Skip to main content" />);
    const link = screen.getByTestId("skip-link") as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe("#main-content");
    expect(link.textContent).toBe("Skip to main content");
  });
});

describe("KeyboardCheatsheet", () => {
  it("groups shortcuts by scope and exposes the canonical canvas list-view shortcut", () => {
    render(<KeyboardCheatsheet />);
    const canvas = screen.getByTestId("keyboard-scope-canvas");
    expect(within(canvas).getByTestId("shortcut-combo-list-view")).toBeInTheDocument();
    expect(within(canvas).getByTestId("shortcut-combo-reorder-up")).toBeInTheDocument();
    const trace = screen.getByTestId("keyboard-scope-trace");
    expect(within(trace).getByTestId("shortcut-combo-trace-table")).toBeInTheDocument();
  });
});

describe("LanguagePicker", () => {
  it("emits the selected language code", () => {
    const onChange = vi.fn();
    render(
      <LanguagePicker current="en" onChange={onChange} label="Language" />,
    );
    fireEvent.change(screen.getByTestId("language-picker-select"), {
      target: { value: "ja" },
    });
    expect(onChange).toHaveBeenCalledWith("ja");
  });
});
