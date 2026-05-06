"use client";

import { useState } from "react";

import { ConversationEvidence } from "@/components/inbox/conversation-evidence";
import { ConversationViewer } from "@/components/inbox/conversation-viewer";
import { ResolutionToEval } from "@/components/inbox/resolution-to-eval";
import { SuggestedDraft } from "@/components/inbox/suggested-draft";
import {
  FIXTURE_CONVERSATION_ID,
  FIXTURE_TRANSCRIPT,
  fixtureSubscriber,
  type ConversationMessage,
} from "@/lib/conversation";
import {
  FIXTURE_EVIDENCE_CONTEXT,
  FIXTURE_SUGGESTED_DRAFT,
  type EvalCaseFromResolution,
} from "@/lib/inbox-resolution";

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

async function fixtureSaveEval(
  _draft: EvalCaseFromResolution,
): Promise<{ ok: boolean; suite_id: string }> {
  return { ok: true, suite_id: "operator-resolutions" };
}

export default function ConversationPage({
  params,
}: {
  params: { id: string };
}): JSX.Element {
  const conversation_id = params.id || FIXTURE_CONVERSATION_ID;
  const [insertedDraft, setInsertedDraft] = useState<string | null>(null);

  return (
    <main
      className="container mx-auto p-6"
      data-testid="inbox-conversation-page"
    >
      <header className="mb-4">
        <h1 className="text-xl font-semibold tracking-tight">
          Conversation {conversation_id}
        </h1>
        <p className="text-muted-foreground text-xs">
          Live tail of customer conversation. Take over to pause the agent and
          reply as a human operator. Every artefact you act on is captured into
          the eval suite when you resolve.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <ConversationViewer
            conversation_id={conversation_id}
            handback={fixtureHandback}
            initialTranscript={FIXTURE_TRANSCRIPT}
            postMessage={fixturePostMessage}
            subscribe={fixtureSubscriber}
            takeover={fixtureTakeover}
          />
          {insertedDraft ? (
            <p
              className="rounded border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900"
              data-testid="inserted-draft-banner"
            >
              Suggested draft inserted into composer.
            </p>
          ) : null}
        </div>

        <aside className="space-y-4">
          <SuggestedDraft
            draft={FIXTURE_SUGGESTED_DRAFT}
            onInsert={(text) => setInsertedDraft(text)}
          />
          <ConversationEvidence ctx={FIXTURE_EVIDENCE_CONTEXT} />
          <ResolutionToEval
            ctx={FIXTURE_EVIDENCE_CONTEXT}
            onSave={fixtureSaveEval}
          />
        </aside>
      </div>
    </main>
  );
}
