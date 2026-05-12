/**
 * UX409 — Studio route audit.
 *
 * Maps every Studio top-level route to its lifecycle verb in the canonical IA
 * (§5: Build / Test / Ship / Observe / Migrate / Govern, plus the implicit
 * Onboard and System buckets). Used by tests to guarantee no orphan surface
 * is shipped without a home.
 */

export const IA_LIFECYCLE_VERBS = [
  "build",
  "test",
  "ship",
  "observe",
  "migrate",
  "govern",
  "onboard",
  "system",
] as const;
export type IALifecycleVerb = (typeof IA_LIFECYCLE_VERBS)[number];

export interface IARouteEntry {
  route: string;
  verb: IALifecycleVerb;
  /** Title used in the IA index. Friendly-precise — no flow-first language. */
  label: string;
  /** Short purpose. Used as the IA tooltip and as the screen subtitle. */
  purpose: string;
  /** Anchor the route is defined under in the canonical UX standard. */
  anchor: string;
}

/**
 * Authoritative IA registry. Keep this list sorted by lifecycle verb to make
 * regressions obvious in code review.
 */
export const STUDIO_ROUTES: readonly IARouteEntry[] = [
  // Onboard
  {
    route: "/",
    verb: "onboard",
    label: "Welcome",
    purpose:
      "Public enterprise welcome page with signup and sign-in entry points.",
    anchor: "§7",
  },
  {
    route: "/welcome",
    verb: "onboard",
    label: "Welcome",
    purpose:
      "Public enterprise welcome page with signup and sign-in entry points.",
    anchor: "§7",
  },
  {
    route: "/signup",
    verb: "onboard",
    label: "Enterprise signup",
    purpose:
      "Public tenant request that enters system-admin review before workspace provisioning.",
    anchor: "§7",
  },
  {
    route: "/home",
    verb: "onboard",
    label: "Studio home",
    purpose:
      "Lifecycle entry — pick Build, Test, Ship, Observe, Migrate, or Govern.",
    anchor: "§5",
  },
  {
    route: "/onboarding",
    verb: "onboard",
    label: "Onboarding",
    purpose: "Three-doors entry, templates, and concierge consent (§7).",
    anchor: "§7",
  },
  {
    route: "/ia",
    verb: "onboard",
    label: "Information architecture",
    purpose: "Lifecycle index linking every Studio screen (§5).",
    anchor: "§5",
  },
  // Build
  {
    route: "/agents",
    verb: "build",
    label: "Agents",
    purpose: "Agent workspace listing (§5 Build).",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]",
    verb: "build",
    label: "Agent workbench",
    purpose: "Behavior, tools, knowledge, memory in one workspace (§5 Build).",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]/behavior",
    verb: "build",
    label: "Behavior editor",
    purpose:
      "Three-mode behavior editing with risk, telemetry, diff, and preview (§11).",
    anchor: "§11",
  },
  {
    route: "/agents/[agent_id]/contract",
    verb: "build",
    label: "Agent contract",
    purpose:
      "Commitment Document, ownership, boundaries, success metrics, and escalation policy.",
    anchor: "§11",
  },
  {
    route: "/agents/[agent_id]/map",
    verb: "build",
    label: "Agent map",
    purpose:
      "Instrumentation-first dependency, tool, memory, eval, hazard, and fork map (§8).",
    anchor: "§8",
  },
  {
    route: "/agents/[agent_id]/conductor",
    verb: "build",
    label: "Multi-Agent Conductor",
    purpose:
      "Sub-agent assets, handoff contracts, ownership, failure paths, and traceable delegation (§17).",
    anchor: "§17",
  },
  {
    route: "/agents/[agent_id]/memory",
    verb: "build",
    label: "Memory Studio",
    purpose:
      "Memory explorer, diffs, source traces, retention, safety flags, delete, and replay (§14).",
    anchor: "§14",
  },
  {
    route: "/agents/[agent_id]/channels",
    verb: "build",
    label: "Agent channels",
    purpose:
      "Agent-scoped bindings for web chat, WhatsApp, Telegram, Slack, Teams, SMS, email, and voice.",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]/evals",
    verb: "test",
    label: "Agent evals",
    purpose:
      "Agent-scoped eval coverage, source traces, expected behavior, and release gates.",
    anchor: "§15",
  },
  {
    route: "/channels",
    verb: "build",
    label: "Workspace channels",
    purpose:
      "Omnichannel entry point for web chat, WhatsApp, Telegram, Slack, Teams, SMS, email, and voice.",
    anchor: "§5",
  },
  {
    route: "/voice",
    verb: "build",
    label: "Voice channel stage",
    purpose:
      "Specialized staging and debug view for the voice channel binding; voice remains one peer channel.",
    anchor: "§16",
  },
  {
    route: "/voice/config",
    verb: "build",
    label: "Voice channel config",
    purpose:
      "Phone number routing, ASR/TTS providers, eval suites, and compliance checks for voice channel bindings.",
    anchor: "§16",
  },
  {
    route: "/agents/[agent_id]/deploys",
    verb: "ship",
    label: "Agent deploys",
    purpose: "Per-agent versions and environments.",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]/flow",
    verb: "build",
    label: "Agent behavior",
    purpose: "Behavior surface inside the agent workbench (§5 Build).",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]/inspector",
    verb: "observe",
    label: "Agent inspector",
    purpose: "Live trace, memory inspector, retrieval introspection.",
    anchor: "§8",
  },
  {
    route: "/agents/[agent_id]/governance",
    verb: "govern",
    label: "Agent governance",
    purpose:
      "Agent-scoped approvals, policy requirements, secrets, audit, and evidence export.",
    anchor: "§24",
  },
  {
    route: "/agents/[agent_id]/history",
    verb: "govern",
    label: "Agent history",
    purpose:
      "Handoff walkthrough from commitments, changes, approvals, deploys, incidents, and risks.",
    anchor: "§24",
  },
  {
    route: "/agents/[agent_id]/kb",
    verb: "build",
    label: "Agent knowledge",
    purpose: "Knowledge sources and retrieval evals (§5 Build).",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]/secrets",
    verb: "govern",
    label: "Agent secrets",
    purpose: "Per-agent credentials under workspace policy.",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]/observe",
    verb: "observe",
    label: "Agent observability",
    purpose:
      "Agent-scoped health, incidents, drift, cost, latency, channel failures, and production tail.",
    anchor: "§20",
  },
  {
    route: "/agents/[agent_id]/simulator",
    verb: "test",
    label: "Simulator Lab",
    purpose: "Multi-channel preview and Inline ChatOps commands (§15).",
    anchor: "§15",
  },
  {
    route: "/agents/[agent_id]/tools",
    verb: "build",
    label: "Tools Room",
    purpose:
      "Catalog, schema, auth, safety contract, mock/live, and draft-from-request flow (§12).",
    anchor: "§12",
  },
  {
    route: "/agents/[agent_id]/traces",
    verb: "observe",
    label: "Agent traces",
    purpose:
      "Agent-scoped trace evidence, replay references, span timeline, and eval conversion.",
    anchor: "§10",
  },
  {
    route: "/agents/[agent_id]/versions",
    verb: "ship",
    label: "Agent versions",
    purpose: "Versions, diffs, eval status, deploys (§5 Ship).",
    anchor: "§5",
  },
  {
    route: "/agents/[agent_id]/workflow",
    verb: "ship",
    label: "Agent workflow",
    purpose:
      "Branches, Change Sets, replay forks, tests, approvals, and release candidates.",
    anchor: "§23",
  },
  {
    route: "/marketplace",
    verb: "build",
    label: "Templates & marketplace",
    purpose: "Pre-built templates and shared skills (§7.3).",
    anchor: "§7.3",
  },
  {
    route: "/cobuilder",
    verb: "build",
    label: "Cobuilder",
    purpose: "Pair-build with Loop on agent edits (§22).",
    anchor: "§22",
  },
  // Test
  {
    route: "/evals",
    verb: "test",
    label: "Evals",
    purpose: "Eval foundry — suites, runs, replay (§15).",
    anchor: "§15",
  },
  {
    route: "/evals/runs/[run_id]",
    verb: "test",
    label: "Eval run",
    purpose: "Single eval run detail with diffs and proofs (§15.3).",
    anchor: "§15.3",
  },
  {
    route: "/evals/suites/[suite_id]",
    verb: "test",
    label: "Eval suite",
    purpose: "Suite builder and history (§15.2).",
    anchor: "§15.2",
  },
  {
    route: "/replay",
    verb: "test",
    label: "Replay",
    purpose: "Production replay against the future (§15.4).",
    anchor: "§15.4",
  },
  {
    route: "/replay/[id]",
    verb: "test",
    label: "Replay run",
    purpose: "Single replay session with divergence diff (§15.4).",
    anchor: "§15.4",
  },
  {
    route: "/scenes",
    verb: "test",
    label: "Scenes",
    purpose:
      "Workspace library of canonical production conversations for replay and builder handoff.",
    anchor: "§15.4",
  },
  {
    route: "/scenarios",
    verb: "test",
    label: "North-star scenarios",
    purpose: "Eight canonical scenarios (§36) for demo and validation.",
    anchor: "§36",
  },
  // Ship
  {
    route: "/deploys",
    verb: "ship",
    label: "Deploys",
    purpose: "Versions, environments, canaries, rollback (§5 Ship).",
    anchor: "§5",
  },
  {
    route: "/deploy/safety",
    verb: "ship",
    label: "Deploy safety",
    purpose: "Preflight, four-eyes, audit evidence (§13).",
    anchor: "§13",
  },
  {
    route: "/collaborate/review",
    verb: "ship",
    label: "Changeset review",
    purpose: "Second pair of eyes, parity diff, deploy approval (§17).",
    anchor: "§17",
  },
  // Observe
  {
    route: "/observe",
    verb: "observe",
    label: "Observatory",
    purpose: "Dashboards, anomaly cards, production tail, and ambient health (§20).",
    anchor: "§20",
  },
  {
    route: "/traces",
    verb: "observe",
    label: "Traces",
    purpose: "Trace theater, span table, fork-from-here (§8, §30.3).",
    anchor: "§8",
  },
  {
    route: "/traces/[id]",
    verb: "observe",
    label: "Trace detail",
    purpose: "Single trace with spans, retrieval, fork (§8).",
    anchor: "§8",
  },
  {
    route: "/xray",
    verb: "observe",
    label: "Agent X-Ray",
    purpose:
      "Observed behavior, prompt-section support gaps, cost drivers, and representative traces (§3.14, §12).",
    anchor: "§3.14",
  },
  {
    route: "/inbox",
    verb: "observe",
    label: "Operator inbox",
    purpose: "Real-time conversations, takeover, escalations (§19).",
    anchor: "§19",
  },
  {
    route: "/inbox/queue",
    verb: "observe",
    label: "Inbox queue",
    purpose: "Filterable operator queue with SLAs (§19).",
    anchor: "§19",
  },
  {
    route: "/inbox/conversation/[id]",
    verb: "observe",
    label: "Conversation",
    purpose: "Single conversation with handoff, trace, memory (§19).",
    anchor: "§19",
  },
  {
    route: "/costs",
    verb: "observe",
    label: "Cost",
    purpose: "Line-item cost, budget burn, eval/canary deltas (§20).",
    anchor: "§20",
  },
  {
    route: "/quality",
    verb: "observe",
    label: "Screen quality bar",
    purpose: "Per-screen quality reports against the §37 north-star.",
    anchor: "§37",
  },
  // Migrate
  {
    route: "/migrate",
    verb: "migrate",
    label: "Migrations",
    purpose: "Imports, mappings, parity, cutover, lineage (§18).",
    anchor: "§18",
  },
  {
    route: "/migrate/parity",
    verb: "migrate",
    label: "Parity",
    purpose: "Parity report and divergence triage (§18.6).",
    anchor: "§18",
  },
  // Govern
  {
    route: "/enterprise",
    verb: "govern",
    label: "Enterprise",
    purpose: "Members, roles, policies, audit, billing (§5 Govern).",
    anchor: "§5",
  },
  {
    route: "/enterprise/admin",
    verb: "govern",
    label: "Enterprise admin",
    purpose:
      "Workspace admin for inviting people, reviewing roles, SSO, and evidence.",
    anchor: "§24",
  },
  {
    route: "/enterprise/govern",
    verb: "govern",
    label: "Governance",
    purpose: "Policies, approvers, audit evidence (§24).",
    anchor: "§24",
  },
  {
    route: "/enterprise/audit",
    verb: "govern",
    label: "Audit Explorer",
    purpose:
      "Append-only workspace audit evidence with filters, pagination, and precise outcomes (§24.4).",
    anchor: "§24.4",
  },
  {
    route: "/billing",
    verb: "govern",
    label: "Billing",
    purpose: "Subscriptions and usage roll-up.",
    anchor: "§5",
  },
  {
    route: "/workspaces/new",
    verb: "govern",
    label: "New workspace",
    purpose: "Create a workspace under the right tenant (§4).",
    anchor: "§4",
  },
  {
    route: "/workspaces/[workspace_id]/members",
    verb: "govern",
    label: "Workspace members",
    purpose: "Members and roles for a workspace (§5 Govern).",
    anchor: "§5",
  },
  {
    route: "/workspaces/enterprise",
    verb: "govern",
    label: "Enterprise workspaces",
    purpose: "Cross-workspace governance for enterprise tenants (§24).",
    anchor: "§24",
  },
  // System
  {
    route: "/login",
    verb: "system",
    label: "Sign in",
    purpose: "Auth.",
    anchor: "§5",
  },
  {
    route: "/system/admin",
    verb: "system",
    label: "System admin",
    purpose:
      "Installation-level enterprise signup review, tenant provisioning, and onboarding oversight.",
    anchor: "§24",
  },
  {
    route: "/auth/callback",
    verb: "system",
    label: "Auth callback",
    purpose: "OIDC callback.",
    anchor: "§5",
  },
  {
    route: "/share/[token]",
    verb: "system",
    label: "Public share",
    purpose:
      "Server-redacted external evidence view with expiry and audit logging (§27.4).",
    anchor: "§27.4",
  },
  {
    route: "/voice-demo/[token]",
    verb: "system",
    label: "Voice demo",
    purpose:
      "Short-lived stakeholder voice access with mic check, trace capture, and rate limits (§16.5).",
    anchor: "§16.5",
  },
  {
    route: "/a11y",
    verb: "system",
    label: "Accessibility primitives",
    purpose:
      "Status glyphs, diff markers, skip-link, keyboard cheatsheet (§30).",
    anchor: "§30",
  },
  {
    route: "/responsive",
    verb: "system",
    label: "Responsive modes",
    purpose: "Mode switcher and second-monitor strip (§31).",
    anchor: "§31",
  },
  {
    route: "/polish",
    verb: "system",
    label: "Creative polish primitives",
    purpose: "Earned moments, ambient life, skeletons, completion marks (§29).",
    anchor: "§29",
  },
];

/**
 * Phrases that must NEVER appear in product copy. The canonical UX standard
 * §41 anti-patterns calls out flow-first language and competing IA.
 */
export const FORBIDDEN_COPY = [
  "flow editor",
  "flow-first",
  "flow first",
  "second navigation",
  "competing taxonomy",
  "mystery health",
  "fake progress",
] as const;

export interface CopyAuditFinding {
  /** The line of copy under audit. */
  text: string;
  /** Forbidden phrases observed inside `text`. */
  matches: string[];
}

/**
 * Returns the forbidden phrases observed in the provided copy lines. Studio
 * copy must read friendly-precise (§37) and never leak old flow-first
 * vocabulary.
 */
export function auditCopy(lines: ReadonlyArray<string>): CopyAuditFinding[] {
  const findings: CopyAuditFinding[] = [];
  for (const line of lines) {
    const matches = FORBIDDEN_COPY.filter((phrase) =>
      line.toLowerCase().includes(phrase),
    );
    if (matches.length > 0)
      findings.push({ text: line, matches: [...matches] });
  }
  return findings;
}

export interface OrphanRouteFinding {
  route: string;
  reason: string;
}

/**
 * Validates that every concrete Studio page is registered in STUDIO_ROUTES.
 * Catches pages added without a canonical IA home.
 */
export function findOrphanRoutes(
  candidateRoutes: ReadonlyArray<string>,
): OrphanRouteFinding[] {
  const known = new Set(STUDIO_ROUTES.map((entry) => entry.route));
  const orphans: OrphanRouteFinding[] = [];
  for (const route of candidateRoutes) {
    if (!known.has(route)) {
      orphans.push({ route, reason: "missing-from-STUDIO_ROUTES" });
    }
  }
  return orphans;
}

export function groupByVerb(): Record<IALifecycleVerb, IARouteEntry[]> {
  const groups = Object.fromEntries(
    IA_LIFECYCLE_VERBS.map((verb) => [verb, [] as IARouteEntry[]]),
  ) as Record<IALifecycleVerb, IARouteEntry[]>;
  for (const entry of STUDIO_ROUTES) {
    groups[entry.verb].push(entry);
  }
  return groups;
}
