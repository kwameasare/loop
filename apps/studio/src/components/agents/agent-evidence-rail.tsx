"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ActivitySquare, ExternalLink } from "lucide-react";

import { EmulatorPanel } from "@/components/agents/emulator-panel";

interface AgentEvidenceRailProps {
  agentId: string;
  pathname?: string;
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
        "Use failed traces, affected evals, production version, risk flags, and approval requirements while editing behavior.",
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
        "Review recent tool failures, latency, permissions, secrets status, and audit events before granting or changing tools.",
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
        "Keep retrieval tests, stale documents, coverage gaps, and recent unanswered questions visible beside knowledge edits.",
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
        "Inspect proposed writes, privacy flags, retention policy, and source traces while changing memory behavior.",
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
        "Check channel readiness, transcript capture, compliance status, and preview runs for every binding.",
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
        "Keep release candidate, eval gates, rollout state, rollback target, and audit evidence together before traffic moves.",
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
        "Review owners, open risks, incidents, transfers, and source artifacts before handing off responsibility.",
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
        "State, traces, evals, deploys, and governance remain available while you work inside this agent.",
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
}: AgentEvidenceRailProps) {
  const currentPathname = usePathname();
  const segment = segmentFromPath(agentId, pathname ?? currentPathname ?? "");
  const context = evidenceContext(agentId, segment);

  return (
    <div className="space-y-4" data-testid="agent-evidence-rail">
      <section
        className="instrument-panel rounded-2xl p-4"
        data-testid="agent-evidence-context"
      >
        <div className="flex items-center gap-2">
          <ActivitySquare className="h-4 w-4" aria-hidden />
          <h2 className="text-sm font-semibold">{context.title}</h2>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">{context.summary}</p>
        <ul className="mt-3 space-y-2">
          {context.links.map((link) => (
            <li key={link.id}>
              <Link
                href={link.href}
                className="flex items-center justify-between gap-2 rounded-md border bg-background px-2.5 py-2 text-xs font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                data-testid={`agent-evidence-link-${link.id}`}
              >
                {link.label}
                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <EmulatorPanel agentId={agentId} evidenceMode="empty" />
    </div>
  );
}
