import { ConversationViewer } from "@/components/inbox/conversation-viewer";
import {
  FIXTURE_CONVERSATION_ID,
  FIXTURE_TRANSCRIPT,
  fixtureSubscriber,
} from "@/lib/conversation";

export const dynamic = "force-dynamic";

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
          Live tail of customer conversation. New messages append in
          real-time as the data plane streams them.
        </p>
      </header>
      <ConversationViewer
        conversation_id={conversation_id}
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={fixtureSubscriber}
      />
    </main>
  );
}
