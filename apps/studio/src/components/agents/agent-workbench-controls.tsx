import Link from "next/link";
import {
  GitBranch,
  PackageCheck,
  Rocket,
  ShieldCheck,
  SlidersHorizontal,
  TestTube2,
} from "lucide-react";

interface AgentWorkbenchControlsProps {
  agentId: string;
  disabledReason?: string | undefined;
}

const CONTROLS = [
  {
    id: "versions",
    label: "Versions",
    href: "versions",
    icon: GitBranch,
  },
  {
    id: "environment",
    label: "Environment",
    href: "deploys?panel=environments",
    icon: SlidersHorizontal,
  },
  {
    id: "tests",
    label: "Run tests",
    href: "simulator",
    icon: TestTube2,
  },
  {
    id: "change-set",
    label: "Open Change Set",
    href: "workflow",
    icon: PackageCheck,
  },
  {
    id: "promote",
    label: "Deploy",
    href: "deploys?panel=promotion",
    icon: Rocket,
  },
  {
    id: "governance",
    label: "Govern",
    href: "governance",
    icon: ShieldCheck,
  },
] as const;

export function AgentWorkbenchControls({
  agentId,
  disabledReason,
}: AgentWorkbenchControlsProps) {
  const base = `/agents/${encodeURIComponent(agentId)}`;
  return (
    <div
      className="flex flex-wrap gap-2"
      data-testid="agent-workbench-controls"
      aria-label="Agent workbench controls"
    >
      {CONTROLS.map((control) => {
        const Icon = control.icon;
        if (disabledReason) {
          return (
            <button
              key={control.id}
              type="button"
              disabled
              title={disabledReason}
              className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-md border bg-background px-2.5 py-1.5 text-xs font-medium text-muted-foreground opacity-60"
              data-testid={`agent-workbench-control-${control.id}`}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {control.label}
            </button>
          );
        }
        return (
          <Link
            key={control.id}
            href={`${base}/${control.href}`}
            className="inline-flex items-center gap-1.5 rounded-md border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            data-testid={`agent-workbench-control-${control.id}`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {control.label}
          </Link>
        );
      })}
    </div>
  );
}
