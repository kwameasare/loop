"use client";

import { useCallback, useEffect, useState } from "react";
import { Search } from "lucide-react";

import { CommandPalette } from "./command-palette";
import type { CommandEntry } from "@/lib/command";

export interface CommandPaletteLauncherProps {
  /** Optional handler invoked when a user activates a command. */
  onSelect?: (entry: CommandEntry) => void;
  className?: string;
}

/**
 * Mounts the command palette globally and exposes the topbar trigger button.
 * Section 27.1 requires the palette to be reachable from anywhere with a
 * single keyboard shortcut, so we listen for ⌘K / Ctrl+K at the document
 * level. Inputs and textareas opt out by stopping propagation when needed.
 */
export function CommandPaletteLauncher({
  onSelect,
  className,
}: CommandPaletteLauncherProps) {
  const [open, setOpen] = useState(false);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const isPaletteShortcut =
      (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
    if (!isPaletteShortcut) return;
    event.preventDefault();
    setOpen((value) => !value);
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <>
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-keyshortcuts="Meta+K Control+K"
        onClick={() => setOpen(true)}
        className={
          className ??
          "inline-flex h-9 items-center gap-2 rounded-md border bg-card px-3 text-sm font-medium text-muted-foreground transition-colors duration-swift ease-standard hover:text-foreground"
        }
        data-testid="command-launcher"
      >
        <Search className="h-4 w-4" aria-hidden={true} />
        <span className="hidden sm:inline">Command</span>
        <kbd className="hidden rounded bg-muted px-1.5 py-0.5 text-[0.68rem] font-medium text-muted-foreground lg:inline">
          ⌘K
        </kbd>
      </button>
      <CommandPalette
        open={open}
        onOpenChange={setOpen}
        {...(onSelect ? { onSelect } : {})}
      />
    </>
  );
}
