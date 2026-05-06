/**
 * Canonical command palette registry.
 *
 * Implements section 27.1 of the canonical UX standard: jump-to navigations,
 * action commands, prefix-aware queries, and ChatOps slash-commands.
 *
 * The registry is a pure data + filter module so the palette UI can stay thin
 * and so other surfaces (inline ChatOps, find-in-context) can reuse the same
 * source of truth. Consumers must not invent local command lists; instead they
 * should extend this module.
 */

import type { CanonicalDomain, TargetCommand } from "@/lib/target-ux/types";

/** Recognised command-palette prefixes (section 27.1 typed prefixes). */
export const COMMAND_PREFIXES = [
  "agent",
  "trace",
  "eval",
  "import",
  "cost",
  "tool",
  "deploy",
  "snapshot",
  "scene",
] as const;

export type CommandPrefix = (typeof COMMAND_PREFIXES)[number];

export type CommandIntent =
  | "navigate"
  | "create"
  | "review"
  | "simulate"
  | "deploy";

export interface CommandEntry {
  id: string;
  label: string;
  hint: string;
  intent: CommandIntent;
  domain: CanonicalDomain;
  /**
   * Optional prefixes that should match this command in addition to the label.
   * For example, `trace:` should surface every `domain: "traces"` entry.
   */
  prefixes?: CommandPrefix[];
  shortcut?: string;
  href?: string;
  /** Hidden tokens that help fuzzy match without being shown to the user. */
  keywords?: string[];
  /**
   * Section 23.4 permission clarity: when set, the command is rendered in the
   * palette but visually disabled with this reason on hover/focus.
   */
  disabledReason?: string;
}

/**
 * Canonical baseline commands derived from section 27.1. The palette always
 * starts from this list and merges any fixture-provided commands so feature
 * teams can extend without forking the palette.
 */
export const CANONICAL_COMMANDS: CommandEntry[] = [
  {
    id: "cmd_jump_agent",
    label: "Jump to agent",
    hint: "Open the agent workbench",
    intent: "navigate",
    domain: "agents",
    prefixes: ["agent"],
    shortcut: "G then A",
    href: "/agents",
    keywords: ["go", "open", "switch"],
  },
  {
    id: "cmd_jump_trace",
    label: "Jump to trace",
    hint: "Open the trace theater",
    intent: "navigate",
    domain: "traces",
    prefixes: ["trace"],
    shortcut: "G then T",
    href: "/traces",
    keywords: ["debug", "waterfall", "span"],
  },
  {
    id: "cmd_jump_conversation",
    label: "Jump to conversation",
    hint: "Open the inbox conversation viewer",
    intent: "navigate",
    domain: "inbox",
    prefixes: ["agent"],
    href: "/inbox",
    keywords: ["chat", "thread"],
  },
  {
    id: "cmd_run_eval",
    label: "Run eval suite",
    hint: "Trigger the selected eval against the current draft",
    intent: "simulate",
    domain: "evals",
    prefixes: ["eval"],
    keywords: ["test", "regression"],
  },
  {
    id: "cmd_replay_turn",
    label: "Replay turn",
    hint: "Replay the selected production turn against the draft",
    intent: "simulate",
    domain: "traces",
    prefixes: ["trace"],
    keywords: ["rewind", "what-if"],
  },
  {
    id: "cmd_deploy_version",
    label: "Deploy version",
    hint: "Open the canary preflight",
    intent: "deploy",
    domain: "deploys",
    prefixes: ["deploy"],
    keywords: ["ship", "release", "promote"],
  },
  {
    id: "cmd_rollback",
    label: "Rollback",
    hint: "Revert to the previous signed snapshot",
    intent: "deploy",
    domain: "deploys",
    prefixes: ["deploy"],
    keywords: ["revert", "undo"],
  },
  {
    id: "cmd_import_project",
    label: "Import project",
    hint: "Bring in a Botpress / Dialogflow / Rasa export",
    intent: "create",
    domain: "migration",
    prefixes: ["import"],
    keywords: ["botpress", "dialogflow", "rasa", "copilot-studio", "migrate"],
  },
  {
    id: "cmd_create_tool",
    label: "Create tool",
    hint: "Wire a new MCP/HTTP tool",
    intent: "create",
    domain: "tools",
    prefixes: ["tool"],
    keywords: ["function", "skill"],
  },
  {
    id: "cmd_open_kb",
    label: "Open knowledge source",
    hint: "Inspect indexed documents and freshness",
    intent: "navigate",
    domain: "memory",
    keywords: ["kb", "knowledge", "docs"],
  },
  {
    id: "cmd_switch_environment",
    label: "Switch environment",
    hint: "Move between dev, staging, and production",
    intent: "navigate",
    domain: "deploys",
    keywords: ["env", "stage", "prod"],
  },
  {
    id: "cmd_compare_versions",
    label: "Compare versions",
    hint: "Open the semantic diff viewer",
    intent: "review",
    domain: "snapshots",
    prefixes: ["snapshot"],
    keywords: ["diff", "version"],
  },
  {
    id: "cmd_copy_ids",
    label: "Copy IDs",
    hint: "Copy the selected agent/trace/snapshot IDs to clipboard",
    intent: "review",
    domain: "command",
    keywords: ["clipboard", "id"],
  },
  {
    id: "cmd_open_docs",
    label: "Open docs",
    hint: "Search the Loop documentation",
    intent: "navigate",
    domain: "command",
    href: "/docs",
    keywords: ["help", "manual"],
  },
  {
    id: "cmd_view_costs",
    label: "View costs",
    hint: "Open the cost dashboard for the active scope",
    intent: "review",
    domain: "costs",
    prefixes: ["cost"],
    keywords: ["spend", "budget"],
  },
];

/**
 * Section 27.6 inline ChatOps slash-commands. These never mutate production;
 * they are routed through the live preview only and the palette uses them for
 * autocomplete in the live preview surface.
 */
export interface ChatOpsCommand {
  id: string;
  /** The literal slash trigger, e.g. `/swap`. */
  trigger: string;
  description: string;
  /** Argument hints rendered after the trigger as `key=` placeholders. */
  args: string[];
  /** Whether this command is destructive enough to require confirmation. */
  confirm?: boolean;
}

export const CHATOPS_COMMANDS: ChatOpsCommand[] = [
  {
    id: "chatops_swap",
    trigger: "/swap",
    description: "Swap the model used by the live preview",
    args: ["model="],
  },
  {
    id: "chatops_disable",
    trigger: "/disable",
    description: "Temporarily disable a tool in this preview only",
    args: ["tool="],
  },
  {
    id: "chatops_inject",
    trigger: "/inject",
    description: "Inject a context variable for this turn",
    args: ['ctx="..."'],
  },
  {
    id: "chatops_as_user",
    trigger: "/as-user",
    description: "Replay as a labeled persona",
    args: ["persona="],
  },
  {
    id: "chatops_replay",
    trigger: "/replay",
    description: "Replay a specific turn with optional memory clear",
    args: ["turn=", "with-memory=cleared"],
    confirm: true,
  },
  {
    id: "chatops_diff",
    trigger: "/diff",
    description: "Diff the current preview against another version",
    args: ["against="],
  },
];

/** Parse a typed prefix from a query, returning prefix and remainder. */
export function parsePrefix(query: string): {
  prefix: CommandPrefix | null;
  rest: string;
} {
  const trimmed = query.trim();
  const match = trimmed.match(/^([a-z][a-z-]*):\s*(.*)$/i);
  if (!match) return { prefix: null, rest: trimmed };
  const candidate = match[1]!.toLowerCase() as CommandPrefix;
  if ((COMMAND_PREFIXES as readonly string[]).includes(candidate)) {
    return { prefix: candidate, rest: match[2] ?? "" };
  }
  return { prefix: null, rest: trimmed };
}

/**
 * Score a command against a query. Lower is better. Returns null when the
 * command should be filtered out entirely.
 */
function scoreCommand(entry: CommandEntry, query: string): number | null {
  if (!query) return 100;
  const haystack = [entry.label, entry.hint, ...(entry.keywords ?? [])]
    .join(" ")
    .toLowerCase();
  const needle = query.toLowerCase();
  if (haystack.includes(needle)) {
    // Earlier matches rank higher; prefix matches rank highest.
    const idx = haystack.indexOf(needle);
    if (entry.label.toLowerCase().startsWith(needle)) return idx;
    return idx + 5;
  }
  // Token-level fallback: every word in the query must appear somewhere.
  const tokens = needle.split(/\s+/).filter(Boolean);
  if (tokens.every((token) => haystack.includes(token))) {
    return 50 + tokens.length;
  }
  return null;
}

export interface CommandFilterResult {
  entries: CommandEntry[];
  prefix: CommandPrefix | null;
}

/**
 * Filter and rank commands for the palette. Honors typed prefixes (section
 * 27.1) by restricting the candidate set to commands that declare the prefix
 * before scoring against the remainder.
 */
export function filterCommands(
  query: string,
  options: { commands?: CommandEntry[]; extra?: TargetCommand[] } = {},
): CommandFilterResult {
  const base = options.commands ?? CANONICAL_COMMANDS;
  const extras: CommandEntry[] = (options.extra ?? []).map((cmd) => {
    const entry: CommandEntry = {
      id: cmd.id,
      label: cmd.label,
      hint: `Quick action from this workspace`,
      intent: cmd.intent,
      domain: cmd.domain,
    };
    if (cmd.shortcut) entry.shortcut = cmd.shortcut;
    return entry;
  });
  const all = [...base, ...extras];
  const { prefix, rest } = parsePrefix(query);
  const candidates = prefix
    ? all.filter((entry) => entry.prefixes?.includes(prefix))
    : all;
  const ranked = candidates
    .map((entry) => ({ entry, score: scoreCommand(entry, rest) }))
    .filter((item): item is { entry: CommandEntry; score: number } =>
      item.score !== null,
    )
    .sort((a, b) => a.score - b.score)
    .map((item) => item.entry);
  return { entries: ranked, prefix };
}

/**
 * Filter ChatOps slash-commands for inline autocomplete. Section 27.6.
 */
export function filterChatOps(query: string): ChatOpsCommand[] {
  const trimmed = query.trim();
  if (!trimmed.startsWith("/")) return [];
  const needle = trimmed.toLowerCase();
  return CHATOPS_COMMANDS.filter((cmd) =>
    cmd.trigger.toLowerCase().startsWith(needle),
  );
}
