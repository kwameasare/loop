import Link from "next/link";
import {
  FlaskConical,
  GitCompareArrows,
  PlayCircle,
  RadioTower,
  ShieldCheck,
  Wrench,
} from "lucide-react";

interface AgentTestDrawerProps {
  agentId: string;
}

const TEST_ACTIONS = [
  {
    id: "simulation",
    label: "One simulation",
    summary: "Probe the current draft in the agent simulator.",
    segment: "simulator",
    icon: PlayCircle,
  },
  {
    id: "related-evals",
    label: "Related evals",
    summary: "Open agent-scoped eval coverage and recent gates.",
    segment: "evals",
    icon: FlaskConical,
  },
  {
    id: "channel-preview",
    label: "Channel preview",
    summary: "Check web, WhatsApp, Telegram, SMS, email, and voice bindings.",
    segment: "channels",
    icon: RadioTower,
  },
  {
    id: "tool-dry-run",
    label: "Tool dry run",
    summary: "Inspect tool contracts, sandbox runs, and permission evidence.",
    segment: "tools",
    icon: Wrench,
  },
  {
    id: "replay-production",
    label: "Replay against production",
    summary: "Compare draft behavior with production trace evidence.",
    segment: "traces?mode=replay",
    icon: GitCompareArrows,
  },
  {
    id: "preflight",
    label: "Deploy preflight",
    summary: "Review release candidate gates before traffic moves.",
    segment: "deploys",
    icon: ShieldCheck,
  },
] as const;

export function AgentTestDrawer({ agentId }: AgentTestDrawerProps) {
  const base = `/agents/${encodeURIComponent(agentId)}`;
  return (
    <details
      id="agent-test-drawer"
      className="rounded-md border bg-card"
      data-testid="agent-test-drawer"
    >
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold">
        Test drawer
        <span className="ml-2 font-normal text-muted-foreground">
          simulation, evals, channels, tools, replay, preflight
        </span>
      </summary>
      <div className="grid gap-2 border-t p-3 sm:grid-cols-2 xl:grid-cols-3">
        {TEST_ACTIONS.map((action) => {
          const Icon = action.icon;
          return (
            <Link
              key={action.id}
              href={`${base}/${action.segment}`}
              className="rounded-md border bg-background p-3 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              data-testid={`agent-test-action-${action.id}`}
            >
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4" aria-hidden />
                <span className="text-sm font-medium">{action.label}</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {action.summary}
              </p>
            </Link>
          );
        })}
      </div>
    </details>
  );
}
