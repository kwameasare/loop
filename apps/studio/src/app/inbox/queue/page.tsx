import { InboxQueue } from "@/components/inbox/inbox-queue";
import {
  FIXTURE_AGENTS,
  FIXTURE_NOW_MS,
  FIXTURE_QUEUE,
  FIXTURE_TEAMS,
  FIXTURE_WORKSPACE_ID,
} from "@/lib/inbox";

export const dynamic = "force-dynamic";

export default function InboxQueuePage(): JSX.Element {
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Inbox queue</h1>
        <p className="text-muted-foreground text-sm">
          Cross-team queue. Filter by team, agent, or channel and click into
          any conversation to take it over.
        </p>
      </header>
      <InboxQueue
        agents={FIXTURE_AGENTS}
        items={FIXTURE_QUEUE}
        now_ms={FIXTURE_NOW_MS}
        teams={FIXTURE_TEAMS}
        workspace_id={FIXTURE_WORKSPACE_ID}
      />
    </main>
  );
}
