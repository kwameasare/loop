"use client";

import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ConversationEvidence } from "@/components/inbox/conversation-evidence";
import { ConversationViewer } from "@/components/inbox/conversation-viewer";
import { ResolutionToEval } from "@/components/inbox/resolution-to-eval";
import { SuggestedDraft } from "@/components/inbox/suggested-draft";
import {
  createDegradedConversationDetail,
  createPollingSubscriber,
  fetchConversationDetail,
  handbackConversation,
  postOperatorMessage,
  takeoverConversation,
  type ConversationDetailView,
} from "@/lib/conversation";
import {
  createEvidenceContextFromConversation,
  saveResolutionEvalCase,
  suggestOperatorDraftFromConversation,
} from "@/lib/inbox-resolution";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function ConversationPage({
  params,
}: {
  params: { id: string };
}): JSX.Element {
  return (
    <RequireAuth>
      <ConversationPageBody conversation_id={params.id} />
    </RequireAuth>
  );
}

function ConversationPageBody({
  conversation_id,
}: {
  conversation_id: string;
}): JSX.Element {
  const [insertedDraft, setInsertedDraft] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetailView | null>(null);
  const { active } = useActiveWorkspace();
  const activeWorkspaceId = active?.id;
  const subscriber = useMemo(() => createPollingSubscriber(), []);
  const evidence = useMemo(
    () =>
      detail && !detail.degraded_reason
        ? createEvidenceContextFromConversation({
            conversation_id,
            messages: detail.messages,
          })
        : null,
    [conversation_id, detail],
  );
  const suggestedDraft = useMemo(
    () =>
      detail && !detail.degraded_reason
        ? suggestOperatorDraftFromConversation(detail.messages)
        : detail?.degraded_reason
          ? "Conversation evidence is unavailable. Studio will not suggest a reply without the transcript."
          : "Loading the conversation evidence before suggesting a reply.",
    [detail],
  );

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    void fetchConversationDetail(conversation_id)
      .then((next) => {
        if (cancelled) return;
        setDetail(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setDetail(
          createDegradedConversationDetail(
            conversation_id,
            err instanceof Error ? err.message : "Could not load conversation",
          ),
        );
      });
    return () => {
      cancelled = true;
    };
  }, [conversation_id]);

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
          {detail ? (
            <ConversationViewer
              conversation_id={conversation_id}
              handback={({ conversation_id: id }) => handbackConversation(id)}
              initialOwnership={detail.ownership}
              initialTranscript={detail.messages}
              postMessage={postOperatorMessage}
              subscribe={subscriber}
              takeover={({ conversation_id: id }) => takeoverConversation(id)}
              {...(detail.degraded_reason
                ? { degradedReason: detail.degraded_reason }
                : {})}
            />
          ) : (
            <section className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">
              Loading conversation...
            </section>
          )}
          {insertedDraft ? (
            <p
              className="rounded border border-info/30 bg-info/10 px-3 py-2 text-xs text-info"
              data-testid="inserted-draft-banner"
            >
              Suggested draft inserted into composer.
            </p>
          ) : null}
        </div>

        <aside className="space-y-4">
          <SuggestedDraft
            draft={suggestedDraft}
            onInsert={(text) => setInsertedDraft(text)}
          />
          {evidence ? (
            <>
              <ConversationEvidence ctx={evidence} />
              <ResolutionToEval
                ctx={evidence}
                onSave={(draft) =>
                  activeWorkspaceId
                    ? saveResolutionEvalCase(activeWorkspaceId, draft)
                    : Promise.resolve({
                        ok: false,
                        error: "No active workspace selected.",
                      })
                }
              />
            </>
          ) : (
            <section className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
              Loading evidence context...
            </section>
          )}
        </aside>
      </div>
    </main>
  );
}
