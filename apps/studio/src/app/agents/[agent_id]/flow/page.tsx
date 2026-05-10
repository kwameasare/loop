import Link from "next/link";

import { SectionEmpty } from "@/components/section-states";

export const dynamic = "force-dynamic";

export default function FlowPage({
  params,
}: {
  params: { agent_id: string };
}): JSX.Element {
  const encodedAgentId = encodeURIComponent(params.agent_id);
  return (
    <main
      className="container mx-auto flex max-w-3xl flex-col gap-4 p-6"
      data-testid="legacy-flow-route"
    >
      <SectionEmpty
        title="Legacy route retired"
        description="Agent editing now lives in the workbench. Use Behavior for instructions and policies, or Agent Map for dependency comprehension."
        evidence="No legacy graph-first editing state is loaded from this route."
        primaryAction={{
          label: "Open Behavior",
          href: `/agents/${encodedAgentId}/behavior`,
        }}
        secondaryAction={{
          label: "Open Agent Map",
          href: `/agents/${encodedAgentId}/map`,
        }}
      />
      <p className="text-sm text-muted-foreground">
        Existing deep links are preserved so old bookmarks do not break, but
        this path no longer competes with the agent workbench model.
      </p>
      <Link
        href={`/agents/${encodedAgentId}`}
        className="w-fit rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        Back to workbench
      </Link>
    </main>
  );
}
