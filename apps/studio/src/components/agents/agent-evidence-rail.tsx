"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ActivitySquare,
  ExternalLink,
  FlaskConical,
  GitCompareArrows,
  LockKeyhole,
  Rocket,
  TestTube2,
} from "lucide-react";

interface AgentEvidenceRailProps {
  agentId: string;
  pathname?: string;
  degradedReason?: string | undefined;
}

interface EvidenceLink {
  id: string;
  label: string;
  href: string;
}

interface EvidenceContext {
  title: string;
  summary: string;
  links: EvidenceLink[];
}

interface RailAction {
  id: string;
  label: string;
  href: string;
  icon: typeof TestTube2;
}

function railActions(agentId: string): RailAction[] {
  const base = `/agents/${encodeURIComponent(agentId)}`;
  return [
    {
      id: "simulate",
      label: "Simulate",
      href: `${base}/simulator`,
      icon: TestTube2,
    },
    {
      id: "evals",
      label: "Evals",
      href: `${base}/evals`,
      icon: FlaskConical,
    },
    {
      id: "replay",
      label: "Replay",
      href: `${base}/traces?mode=replay`,
      icon: GitCompareArrows,
    },
    {
      id: "preflight",
      label: "Preflight",
      href: `${base}/deploys?panel=promotion`,
      icon: Rocket,
    },
  ];
}

function segmentFromPath(agentId: string, pathname: string): string {
  const base = `/agents/${agentId}`;
  if (!pathname.startsWith(base)) return "";
  return pathname.slice(base.length).replace(/^\//, "").split("/")[0] ?? "";
}

function evidenceContext(agentId: string, segment: string): EvidenceContext {
  const base = `/agents/${encodeURIComponent(agentId)}`;
  const contexts: Record<string, EvidenceContext> = {
    behavior: {
      title: "Behavior evidence",
      summary:
        "Failed traces, affected evals, production version, and approval requirements.",
      links: [
        {
          id: "failed-traces",
          label: "Related failed traces",
          href: `${base}/traces?filter=failed`,
        },
        {
          id: "affected-evals",
          label: "Affected evals",
          href: `${base}/evals?filter=affected`,
        },
        {
          id: "production-version",
          label: "Production version",
          href: `${base}/versions`,
        },
        {
          id: "approval-requirements",
          label: "Approval requirements",
          href: `${base}/governance`,
        },
      ],
    },
    tools: {
      title: "Tool evidence",
      summary:
        "Recent failures, permissions, secrets, latency, and audit trail.",
      links: [
        {
          id: "tool-failures",
          label: "Recent tool failures",
          href: `${base}/traces?span=tool`,
        },
        { id: "permissions", label: "Permissions", href: `${base}/tools` },
        { id: "secrets", label: "Secrets status", href: `${base}/secrets` },
        {
          id: "audit",
          label: "Audit events",
          href: `${base}/governance?view=audit`,
        },
      ],
    },
    kb: {
      title: "Knowledge evidence",
      summary:
        "Retrieval tests, stale documents, coverage gaps, and unanswered questions.",
      links: [
        {
          id: "retrieval-tests",
          label: "Retrieval tests",
          href: `${base}/kb?view=retrieval`,
        },
        {
          id: "stale-documents",
          label: "Stale documents",
          href: `${base}/kb?filter=stale`,
        },
        {
          id: "coverage-gaps",
          label: "Coverage gaps",
          href: `${base}/evals?source=knowledge`,
        },
        {
          id: "unanswered",
          label: "Unanswered questions",
          href: `${base}/traces?filter=unanswered`,
        },
      ],
    },
    memory: {
      title: "Memory evidence",
      summary:
        "Proposed writes, privacy flags, retention policy, and source traces.",
      links: [
        {
          id: "writes",
          label: "Proposed writes",
          href: `${base}/memory?view=writes`,
        },
        {
          id: "privacy",
          label: "Privacy flags",
          href: `${base}/memory?filter=privacy`,
        },
        {
          id: "retention",
          label: "Retention policy",
          href: `${base}/memory?view=retention`,
        },
        {
          id: "source-traces",
          label: "Source traces",
          href: `${base}/traces?span=memory`,
        },
      ],
    },
    channels: {
      title: "Channel evidence",
      summary:
        "Readiness, previews, transcripts, and compliance for every channel.",
      links: [
        {
          id: "readiness",
          label: "Readiness checks",
          href: `${base}/channels?view=readiness`,
        },
        {
          id: "previews",
          label: "Channel previews",
          href: `${base}/simulator?view=channels`,
        },
        {
          id: "transcripts",
          label: "Transcript capture",
          href: `${base}/traces?filter=channel`,
        },
        {
          id: "compliance",
          label: "Compliance readiness",
          href: `${base}/governance?view=channels`,
        },
      ],
    },
    deploys: {
      title: "Deployment evidence",
      summary:
        "Release candidate, eval gates, rollout state, and rollback target.",
      links: [
        {
          id: "release-candidate",
          label: "Release candidate",
          href: `${base}/deploys?panel=release-candidate`,
        },
        {
          id: "eval-gates",
          label: "Eval gates",
          href: `${base}/evals?view=gates`,
        },
        {
          id: "rollout",
          label: "Rollout state",
          href: `${base}/deploys?panel=rollout`,
        },
        {
          id: "rollback",
          label: "Rollback target",
          href: `${base}/deploys?panel=rollback`,
        },
      ],
    },
    history: {
      title: "Continuity evidence",
      summary:
        "Owners, open risks, incidents, transfers, and source artifacts.",
      links: [
        { id: "owners", label: "Owners", href: `${base}/history#owners` },
        {
          id: "open-risks",
          label: "Open risks",
          href: `${base}/history#risks`,
        },
        {
          id: "incidents",
          label: "Recent incidents",
          href: `${base}/observe?view=incidents`,
        },
        {
          id: "artifacts",
          label: "Source artifacts",
          href: `${base}/history#walkthrough`,
        },
      ],
    },
  };
  return (
    contexts[segment] ?? {
      title: "Workbench evidence",
      summary:
        "State, traces, evals, deploys, and governance for this agent.",
      links: [
        { id: "state", label: "State evidence", href: `${base}` },
        { id: "traces", label: "Traces", href: `${base}/traces` },
        { id: "evals", label: "Evals", href: `${base}/evals` },
        { id: "deploys", label: "Deployments", href: `${base}/deploys` },
      ],
    }
  );
}

export function AgentEvidenceRail({
  agentId,
  pathname,
  degradedReason,
}: AgentEvidenceRailProps) {
  const currentPathname = usePathname();
  const segment = segmentFromPath(agentId, pathname ?? currentPathname ?? "");
  const context = evidenceContext(agentId, segment);
  const actions = railActions(agentId);

  return (
    <div className="space-y-3" data-testid="agent-evidence-rail">
      <section
        className="instrument-panel rounded-md p-3"
        data-testid="agent-evidence-context"
      >
        <div className="flex items-start gap-2">
          <ActivitySquare className="mt-0.5 h-4 w-4 text-primary" aria-hidden />
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">{context.title}</h2>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {context.summary}
            </p>
          </div>
        </div>
        <ul className="mt-3 flex flex-wrap gap-2">
          {context.links.map((link) => (
            <li key={link.id}>
              <Link
                href={link.href}
                className="inline-flex items-center gap-1.5 rounded-full border bg-background/80 px-2.5 py-1 text-xs font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                data-testid={`agent-evidence-link-${link.id}`}
              >
                {link.label}
                <ExternalLink className="h-3 w-3" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      </section>
      {degradedReason ? (
        <section
          className="instrument-panel rounded-md p-3"
          data-testid="agent-emulator-disabled"
        >
          <div className="flex items-center gap-2">
            <LockKeyhole className="h-4 w-4 text-warning" aria-hidden />
            <h2 className="text-sm font-semibold">Testing unavailable</h2>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Live test actions stay locked until this agent loads from the
            control plane.
          </p>
          <p className="mt-3 rounded-md border border-warning/40 bg-warning/10 p-2 text-xs leading-5 text-warning">
            {degradedReason}
          </p>
        </section>
      ) : (
        <section
          className="instrument-panel rounded-md p-3"
          data-testid="agent-rail-actions"
        >
          <h2 className="text-sm font-semibold">Test actions</h2>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {actions.map((action) => {
              const Icon = action.icon;
              return (
                <Link
                  key={action.id}
                  href={action.href}
                  className="inline-flex items-center gap-1.5 rounded-md border bg-background/80 px-2.5 py-2 text-xs font-medium transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  data-testid={`agent-rail-action-${action.id}`}
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden />
                  {action.label}
                </Link>
              );
            })}
          </div>
          <Link
            href="#agent-test-drawer"
            className="mt-3 inline-flex w-full items-center justify-center rounded-md border bg-background px-2.5 py-2 text-xs font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            data-testid="agent-rail-action-open-drawer"
          >
            Open full test drawer
          </Link>
        </section>
      )}
    </div>
  );
}
