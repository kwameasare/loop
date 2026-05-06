import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CommandPalette } from "@/components/command/command-palette";
import { CommandPaletteLauncher } from "@/components/command/command-palette-launcher";
import { InlineChatOps } from "@/components/command/inline-chatops";

describe("CommandPalette", () => {
  it("renders canonical commands and supports keyboard select", async () => {
    const onSelect = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <CommandPalette
        open={true}
        onOpenChange={onOpenChange}
        onSelect={onSelect}
      />,
    );

    const input = screen.getByTestId("command-input");
    await waitFor(() => expect(input).toHaveFocus());

    fireEvent.change(input, { target: { value: "Run" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0]?.id).toBe("cmd_run_eval");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("highlights the typed prefix and filters the candidate set", () => {
    render(
      <CommandPalette open={true} onOpenChange={() => {}} />,
    );
    const input = screen.getByTestId("command-input");
    fireEvent.change(input, { target: { value: "trace: refund" } });
    expect(screen.getByText("Search traces")).toBeInTheDocument();
    expect(screen.queryByTestId("command-item-cmd_import_project")).toBeNull();
  });

  it("shows the empty state when nothing matches", () => {
    render(<CommandPalette open={true} onOpenChange={() => {}} />);
    fireEvent.change(screen.getByTestId("command-input"), {
      target: { value: "zzznotreal" },
    });
    expect(
      screen.getByText(/No commands match/i),
    ).toBeInTheDocument();
  });

  it("respects disabled commands with a permission reason", () => {
    const onSelect = vi.fn();
    render(
      <CommandPalette
        open={true}
        onOpenChange={() => {}}
        onSelect={onSelect}
        commands={[
          {
            id: "cmd_locked",
            label: "Promote to production",
            hint: "Requires release manager approval",
            intent: "deploy",
            domain: "deploys",
            disabledReason: "Production deploy needs approval from Workspace admin.",
          },
        ]}
      />,
    );
    const item = screen.getByTestId("command-item-cmd_locked");
    expect(item).toBeDisabled();
    fireEvent.click(item);
    expect(onSelect).not.toHaveBeenCalled();
  });
});

describe("CommandPaletteLauncher", () => {
  it("opens the palette via Cmd+K", () => {
    render(<CommandPaletteLauncher />);
    expect(screen.queryByTestId("command-palette")).toBeNull();
    fireEvent.keyDown(document, { key: "k", metaKey: true });
    expect(screen.getByTestId("command-palette")).toBeInTheDocument();
  });
});

describe("InlineChatOps", () => {
  it("autocompletes slash commands and emits the typed string", () => {
    const onSubmit = vi.fn();
    render(<InlineChatOps onSubmit={onSubmit} />);
    const input = screen.getByTestId("chatops-input");
    fireEvent.change(input, { target: { value: "/sw" } });
    expect(screen.getByTestId("chatops-suggestions")).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "/swap model=fast" } });
    fireEvent.submit(input.closest("form")!);
    expect(onSubmit).toHaveBeenCalledWith("/swap model=fast");
  });

  it("requires a confirm pass for destructive commands", () => {
    const onSubmit = vi.fn();
    render(<InlineChatOps onSubmit={onSubmit} />);
    const input = screen.getByTestId("chatops-input");
    fireEvent.change(input, { target: { value: "/replay turn=3" } });
    fireEvent.submit(input.closest("form")!);
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("/replay");
    fireEvent.submit(input.closest("form")!);
    expect(onSubmit).toHaveBeenCalledWith("/replay turn=3");
  });

  it("disables the input when the preview is read-only", () => {
    render(
      <InlineChatOps disabledReason="Preview is read-only for viewers." />,
    );
    const input = screen.getByTestId("chatops-input") as HTMLInputElement;
    expect(input).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(
      /read-only/i,
    );
  });
});
