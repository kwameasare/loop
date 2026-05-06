"use client";

import { useMemo, useState } from "react";
import { TerminalSquare } from "lucide-react";

import {
  CHATOPS_COMMANDS,
  type ChatOpsCommand,
  filterChatOps,
} from "@/lib/command";
import { cn } from "@/lib/utils";

export interface InlineChatOpsProps {
  /** Called when a slash command is submitted with its full text. */
  onSubmit?: (command: string) => void;
  /** Disable the input when the live preview is read-only or unowned. */
  disabledReason?: string;
}

/**
 * Inline ChatOps autocomplete (section 27.6). Lives inside the live-preview
 * surface so expert builders can inject context, swap models, or replay turns
 * without leaving the conversation. Mutating commands route through the
 * normal deploy/approval model; here we only emit the literal command text.
 */
export function InlineChatOps({ onSubmit, disabledReason }: InlineChatOpsProps) {
  const [value, setValue] = useState("");
  const [confirmFor, setConfirmFor] = useState<ChatOpsCommand | null>(null);
  const suggestions = useMemo(() => filterChatOps(value), [value]);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabledReason) return;
    const trimmed = value.trim();
    if (!trimmed.startsWith("/")) return;
    const trigger = trimmed.split(/\s+/)[0]!;
    const known = CHATOPS_COMMANDS.find((cmd) => cmd.trigger === trigger);
    if (known?.confirm && confirmFor?.id !== known.id) {
      setConfirmFor(known);
      return;
    }
    setConfirmFor(null);
    onSubmit?.(trimmed);
    setValue("");
  }

  function applySuggestion(cmd: ChatOpsCommand) {
    const next = `${cmd.trigger} ${cmd.args.join(" ")}`.trim();
    setValue(next);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-2 rounded-md border bg-card p-3"
      aria-describedby="chatops-help"
      data-testid="inline-chatops"
    >
      <label className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <TerminalSquare className="h-4 w-4" aria-hidden={true} />
        Inline ChatOps
      </label>
      <input
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Try `/swap model=fast-draft` or `/diff against=v23`"
        aria-label="ChatOps command"
        disabled={Boolean(disabledReason)}
        className={cn(
          "h-9 w-full rounded-md border bg-background px-2 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring",
          disabledReason ? "cursor-not-allowed opacity-60" : "",
        )}
        data-testid="chatops-input"
      />
      {disabledReason ? (
        <p
          id="chatops-help"
          className="text-xs text-muted-foreground"
          role="status"
        >
          {disabledReason}
        </p>
      ) : (
        <p id="chatops-help" className="text-[0.68rem] text-muted-foreground">
          Slash commands run only against this preview. Mutating production
          still requires a deploy.
        </p>
      )}
      {suggestions.length > 0 ? (
        <ul
          role="listbox"
          aria-label="ChatOps suggestions"
          className="space-y-1"
          data-testid="chatops-suggestions"
        >
          {suggestions.map((cmd) => (
            <li key={cmd.id}>
              <button
                type="button"
                onClick={() => applySuggestion(cmd)}
                className="flex w-full items-start justify-between gap-2 rounded-md px-2 py-1 text-left text-xs hover:bg-accent/70"
              >
                <span className="font-mono">{cmd.trigger}</span>
                <span className="text-muted-foreground">{cmd.description}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {confirmFor ? (
        <p
          role="alert"
          className="rounded-md border border-warning/40 bg-warning/10 px-2 py-1 text-[0.7rem] text-warning-foreground"
        >
          Press Enter again to confirm <code>{confirmFor.trigger}</code>. This
          command is logged in the preview timeline.
        </p>
      ) : null}
    </form>
  );
}
