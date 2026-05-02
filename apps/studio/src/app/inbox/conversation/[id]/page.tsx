import { ConversationViewer } from "@/components/inbox/conversation-viewer";
import {
  FIXTURE_CONVERSATION_ID,
  FIXTURE_TRANSCRIPT,
  fixtureSubscriber,
  type ConversationMessage,
} from "@/lib/conversation";

export const dynamic = "force-dynamic";

async function fixtureTakeover() {
  return { ok: true as const };
}

async function fixtureHandback() {
  return { ok: true as const };
}

async function fixturePostMessage({
  conversation_id,
  body,
}: {
  conversation_id: string;
  body: string;
}) {
  const message: ConversationMessage = {
    id: `op-${Date.now()}`,
    conversation_id,
    role: "operator",
    body,
    created_at_ms: Date.now(),
  };
  return { ok: true as const, message };
}

export default function ConversationPage({
  params,
}: {
  params: { id: string };
}): JSX.Element {
  const conversation_id = params.id || FIXTURE_CONVERSATION_ID;
  return (
    <main className="container mx-auto p-6">
      <header className="mb-4">
        <h1 className="text-xl font-semibold tracking-tight">
          Conversation {conversation_id}
        </h1>
        <p className="text-muted-foreground text-xs">
          Live tail of customer conversation. Click &ldquo;Takeover&rdquo; to
          pause the agent and reply as a human operator.
        </p>
      </header>
      <ConversationViewer
        conversation_id={conversation_id}
        handback={fixtureHandback}
        initialTranscript={FIXTURE_TRANSCRIPT}
        postMessage={fixturePostMessage}
        subscribe={fixtureSubscriber}
        takeover={fixtureTakeover}
      />
    </main>
  );
}
