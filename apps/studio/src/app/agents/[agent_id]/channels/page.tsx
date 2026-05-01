export default function AgentChannelsPage() {
  return (
    <div className="flex flex-col gap-2" data-testid="agent-channels">
      <h2 className="text-lg font-medium">Channels</h2>
      <p className="text-sm text-muted-foreground">
        Bind this agent to web, WhatsApp, voice, or Slack channels. The
        channel registry UI ships in a follow-up story.
      </p>
    </div>
  );
}
