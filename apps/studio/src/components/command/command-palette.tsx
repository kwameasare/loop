"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Command as CommandIcon, CornerDownLeft } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  CANONICAL_COMMANDS,
  type CommandEntry,
  type CommandPrefix,
  filterCommands,
} from "@/lib/command";
import { targetUxFixtures } from "@/lib/target-ux";
import { cn } from "@/lib/utils";

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Optional override for tests so the palette is deterministic. */
  commands?: CommandEntry[];
  /** Called when the user activates a command. */
  onSelect?: (entry: CommandEntry) => void;
}

const PREFIX_HINTS: Record<CommandPrefix, string> = {
  agent: "Search agents",
  trace: "Search traces",
  eval: "Search eval suites",
  import: "Bring in an external project",
  cost: "Inspect spend",
  tool: "Search tools",
  deploy: "Deploys and rollbacks",
  snapshot: "Browse signed snapshots",
  scene: "Open scene library",
};

export function CommandPalette({
  open,
  onOpenChange,
  commands,
  onSelect,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const result = useMemo(
    () =>
      filterCommands(query, {
        ...(commands ? { commands } : {}),
        extra: targetUxFixtures.commands,
      }),
    [query, commands],
  );

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(0);
    }
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    if (open) {
      // Focus the input shortly after the dialog mounts so Radix has wired the
      // portal. Without the timeout the focus race shows a blank caret.
      const timer = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [open]);

  function handleSelect(entry: CommandEntry) {
    if (entry.disabledReason) return;
    onSelect?.(entry);
    onOpenChange(false);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (result.entries.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % result.entries.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) =>
        index === 0 ? result.entries.length - 1 : index - 1,
      );
    } else if (event.key === "Enter") {
      event.preventDefault();
      const entry = result.entries[activeIndex];
      if (entry) handleSelect(entry);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-xl gap-0 p-0"
        data-testid="command-palette"
      >
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <DialogDescription className="sr-only">
          Type to find an agent, trace, eval, deploy, or quick action.
        </DialogDescription>
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <CommandIcon
            className="h-4 w-4 text-muted-foreground"
            aria-hidden={true}
          />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Try `agent: support`, `trace: t-9b23`, or `import: botpress`"
            aria-label="Command query"
            className="h-8 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            data-testid="command-input"
          />
          {result.prefix ? (
            <span
              className="rounded-sm bg-muted px-2 py-0.5 text-[0.68rem] uppercase tracking-wide text-muted-foreground"
              aria-label={`Filtering by ${result.prefix}`}
            >
              {PREFIX_HINTS[result.prefix]}
            </span>
          ) : null}
        </div>
        <ul
          role="listbox"
          aria-label="Command results"
          className="max-h-[60vh] overflow-y-auto p-2"
          data-testid="command-results"
        >
          {result.entries.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-muted-foreground">
              No commands match. Try a different prefix or remove filters.
            </li>
          ) : (
            result.entries.map((entry, index) => {
              const isActive = index === activeIndex;
              return (
                <li
                  key={entry.id}
                  role="option"
                  aria-selected={isActive}
                  aria-disabled={Boolean(entry.disabledReason) || undefined}
                >
                  <button
                    type="button"
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => handleSelect(entry)}
                    disabled={Boolean(entry.disabledReason)}
                    title={entry.disabledReason ?? undefined}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left transition-colors duration-swift ease-standard",
                      isActive ? "bg-accent text-accent-foreground" : "",
                      entry.disabledReason
                        ? "cursor-not-allowed opacity-60"
                        : "hover:bg-accent/70",
                    )}
                    data-testid={`command-item-${entry.id}`}
                  >
                    <span className="flex flex-col">
                      <span className="text-sm font-medium">{entry.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {entry.disabledReason ?? entry.hint}
                      </span>
                    </span>
                    <span className="flex items-center gap-2 text-xs text-muted-foreground">
                      {entry.shortcut ? (
                        <kbd className="rounded bg-muted px-1.5 py-0.5">
                          {entry.shortcut}
                        </kbd>
                      ) : null}
                      {isActive ? (
                        <CornerDownLeft className="h-3 w-3" aria-hidden={true} />
                      ) : null}
                    </span>
                  </button>
                </li>
              );
            })
          )}
        </ul>
        <footer className="flex items-center justify-between border-t px-4 py-2 text-[0.68rem] uppercase tracking-wide text-muted-foreground">
          <span>↑↓ navigate · Enter select · Esc close</span>
          <span>{CANONICAL_COMMANDS.length}+ canonical actions</span>
        </footer>
      </DialogContent>
    </Dialog>
  );
}
