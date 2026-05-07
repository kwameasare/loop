"use client";

import { useEffect, useId, useMemo, useState, type FormEvent } from "react";
import { History, Play, RotateCcw } from "lucide-react";

import { InlineChatOps } from "@/components/command/inline-chatops";
import { PersonaSimulatorPanel } from "@/components/simulator/persona-simulator";
import { EvidenceCallout, LiveBadge, StatePanel } from "@/components/target";
import {
  DEFAULT_SIMULATOR_CONFIG,
  SIMULATOR_CHANNELS,
  SIMULATOR_MEMORY_MODES,
  SIMULATOR_MODELS,
  SIMULATOR_PERSONAS,
  buildSimulatorRun,
  parseSimulatorCommand,
  type SimulatorConfig,
  type SimulatorMemoryMode,
  type SimulatorModelAlias,
  type SimulatorPersonaId,
  type SimulatorSeededContextId,
  type SimulatorToolMode,
} from "@/lib/emulator-lab";
import type { TurnEvent } from "@/lib/sdk-types";
import { cn } from "@/lib/utils";

export type SimulatorInvoke = (
  agentId: string,
  prompt: string,
  onFrame: (event: TurnEvent) => void,
  config: SimulatorConfig,
) => Promise<void>;

interface ToolCallTile {
  key: string;
  name: string;
  status: "running" | "ok" | "error";
  argsPreview?: string;
  resultPreview?: string;
}

interface PanelState {
  tokens: string;
  toolCalls: ToolCallTile[];
  finalAnswer: string | null;
  degradeReason: string | null;
  done: boolean;
  error: string | null;
}

interface TimelineItem {
  id: string;
  label: string;
  detail: string;
  ok: boolean;
}

export interface SimulatorLabProps {
  agentId: string;
  invoke: SimulatorInvoke;
  initialConfig?: SimulatorConfig;
}

const INITIAL_STATE: PanelState = {
  tokens: "",
  toolCalls: [],
  finalAnswer: null,
  degradeReason: null,
  done: false,
  error: null,
};

const CHANNEL_HOTKEYS = [
  { key: "1", channel: "slack" },
  { key: "2", channel: "whatsapp" },
  { key: "3", channel: "sms" },
  { key: "4", channel: "voice" },
] as const;

function channelHotkey(channelId: string): string | null {
  return (
    CHANNEL_HOTKEYS.find((item) => item.channel === channelId)?.key ?? null
  );
}

function summarize(value: unknown, max = 80): string {
  if (value === undefined || value === null) return "";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function frameValue(event: TurnEvent, key: string): unknown {
  const loose = event as TurnEvent & Record<string, unknown>;
  if (loose[key] !== undefined) return loose[key];
  return event.payload?.[key];
}

function frameText(event: TurnEvent): string {
  return summarize(
    frameValue(event, "text") ?? frameValue(event, "delta"),
    400,
  );
}

function responseText(event: TurnEvent): string {
  const response = frameValue(event, "response") as
    | { content?: { type?: string; text?: string | null }[] }
    | undefined;
  const parts = response?.content ?? [];
  return parts
    .filter((part) => part.type === "text")
    .map((part) => part.text ?? "")
    .join("");
}

function applyEvent(state: PanelState, event: TurnEvent): PanelState {
  switch (event.type) {
    case "token": {
      return { ...state, tokens: state.tokens + frameText(event) };
    }
    case "tool_call":
    case "tool_call_start": {
      const name = summarize(frameValue(event, "name") ?? "tool", 48);
      return {
        ...state,
        toolCalls: [
          ...state.toolCalls,
          {
            key: `${name}-${state.toolCalls.length}`,
            name,
            status: "running",
            argsPreview: summarize(frameValue(event, "args")),
          },
        ],
      };
    }
    case "tool_call_end":
    case "tool_result": {
      const name = summarize(frameValue(event, "name") ?? "tool", 48);
      const idx = [...state.toolCalls]
        .reverse()
        .findIndex((call) => call.name === name && call.status === "running");
      if (idx === -1) return state;
      const realIdx = state.toolCalls.length - 1 - idx;
      const updated = state.toolCalls.slice();
      const failed = frameValue(event, "error") !== undefined;
      const current = updated[realIdx];
      if (!current) return state;
      updated[realIdx] = {
        ...current,
        status: failed ? "error" : "ok",
        resultPreview: failed
          ? summarize(frameValue(event, "error"))
          : summarize(frameValue(event, "result")),
      };
      return { ...state, toolCalls: updated };
    }
    case "degrade": {
      return {
        ...state,
        degradeReason:
          summarize(
            frameValue(event, "degrade_reason") ?? frameValue(event, "reason"),
          ) || "unknown",
      };
    }
    case "complete": {
      const text = responseText(event);
      return {
        ...state,
        finalAnswer: text || state.tokens,
        done: true,
      };
    }
    default:
      return state;
  }
}

export function SimulatorLab({
  agentId,
  invoke,
  initialConfig = DEFAULT_SIMULATOR_CONFIG,
}: SimulatorLabProps) {
  const [config, setConfig] = useState<SimulatorConfig>(initialConfig);
  const [prompt, setPrompt] = useState("");
  const [state, setState] = useState<PanelState>(INITIAL_STATE);
  const [running, setRunning] = useState(false);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const inputId = useId();

  const selectedChannel =
    SIMULATOR_CHANNELS.find((channel) => channel.id === config.channel) ??
    SIMULATOR_CHANNELS[0]!;
  const run = useMemo(
    () => buildSimulatorRun(config, agentId),
    [agentId, config],
  );

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      ) {
        return;
      }
      const mapping = CHANNEL_HOTKEYS.find((item) => item.key === event.key);
      if (!mapping) return;
      const channel = SIMULATOR_CHANNELS.find(
        (item) => item.id === mapping.channel,
      );
      if (!channel) return;
      event.preventDefault();
      updateConfig({ channel: channel.id });
      appendTimeline(`Channel ${event.key}`, `Switched to ${channel.label}`);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function updateConfig(next: Partial<SimulatorConfig>) {
    setConfig((prev) => ({ ...prev, ...next }));
  }

  function appendTimeline(label: string, detail: string, ok = true) {
    setTimeline((prev) => [
      {
        id: `${Date.now()}-${prev.length}`,
        label,
        detail,
        ok,
      },
      ...prev.slice(0, 5),
    ]);
  }

  function handleCommand(command: string) {
    const result = parseSimulatorCommand(command, config);
    setConfig(result.nextConfig);
    appendTimeline(command, result.message, result.ok);
    if (!result.ok) {
      setState((prev) => ({ ...prev, error: result.message, done: true }));
    } else {
      setState((prev) => ({ ...prev, error: null }));
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = prompt.trim();
    if (!text || running) return;
    if (text.startsWith("/")) {
      handleCommand(text);
      setPrompt("");
      return;
    }
    setRunning(true);
    setState(INITIAL_STATE);
    appendTimeline(
      "Turn queued",
      `${selectedChannel.label} as ${run.personaLabel}`,
    );
    try {
      await invoke(
        agentId,
        text,
        (frame) => {
          setState((prev) => applyEvent(prev, frame));
        },
        config,
      );
      setPrompt("");
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Simulator request failed.",
        done: true,
      }));
    } finally {
      setRunning(false);
    }
  }

  function toggleTool(toolName: string) {
    setConfig((prev) => ({
      ...prev,
      disabledTools: prev.disabledTools.includes(toolName)
        ? prev.disabledTools.filter((name) => name !== toolName)
        : [...prev.disabledTools, toolName],
    }));
  }

  function resetLab() {
    setConfig(DEFAULT_SIMULATOR_CONFIG);
    setState(INITIAL_STATE);
    setPrompt("");
    setTimeline([]);
  }

  return (
    <section
      className="flex h-full min-w-0 flex-col gap-4 rounded-lg border bg-card p-4"
      data-testid="emulator-panel"
      aria-label="Simulator and conversation lab"
    >
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Simulator Lab</h2>
            <p className="text-xs text-muted-foreground">{agentId}</p>
          </div>
          <LiveBadge tone={running ? "live" : "draft"} pulse={running}>
            {running ? "streaming" : selectedChannel.label}
          </LiveBadge>
        </div>
        <div
          className="grid grid-cols-3 gap-2"
          role="group"
          aria-label="Channel shell"
          data-testid="sim-channel-tabs"
        >
          {SIMULATOR_CHANNELS.map((channel) => (
            <button
              key={channel.id}
              type="button"
              aria-pressed={config.channel === channel.id}
              data-testid={`sim-channel-${channel.id}`}
              className={cn(
                "rounded-md border px-2 py-1.5 text-xs font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring",
                config.channel === channel.id
                  ? "border-primary bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:bg-muted",
              )}
              onClick={() => updateConfig({ channel: channel.id })}
            >
              {channel.label}
              {channelHotkey(channel.id) ? (
                <span className="ml-1 text-[10px] opacity-70">
                  {channelHotkey(channel.id)}
                </span>
              ) : null}
            </button>
          ))}
        </div>
      </header>

      <PersonaSimulatorPanel agentId={agentId} />

      <div className="grid gap-3 text-xs sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="font-medium">Persona user</span>
          <select
            className="h-9 rounded-md border bg-background px-2"
            value={config.personaId}
            data-testid="sim-persona"
            onChange={(event) =>
              updateConfig({
                personaId: event.target.value as SimulatorPersonaId,
              })
            }
          >
            {SIMULATOR_PERSONAS.map((persona) => (
              <option key={persona.id} value={persona.id}>
                {persona.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">Model swap</span>
          <select
            className="h-9 rounded-md border bg-background px-2"
            value={config.modelAlias}
            data-testid="sim-model"
            onChange={(event) =>
              updateConfig({
                modelAlias: event.target.value as SimulatorModelAlias,
              })
            }
          >
            {SIMULATOR_MODELS.map((model) => (
              <option key={model.id} value={model.id}>
                {model.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">Memory mode</span>
          <select
            className="h-9 rounded-md border bg-background px-2"
            value={config.memoryMode}
            data-testid="sim-memory"
            onChange={(event) =>
              updateConfig({
                memoryMode: event.target.value as SimulatorMemoryMode,
              })
            }
          >
            {SIMULATOR_MEMORY_MODES.map((mode) => (
              <option key={mode.id} value={mode.id}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">Seeded context</span>
          <select
            className="h-9 rounded-md border bg-background px-2"
            value={config.seededContextId}
            data-testid="sim-seed"
            onChange={(event) =>
              updateConfig({
                seededContextId: event.target.value as SimulatorSeededContextId,
              })
            }
          >
            <option value="trace_refund_742">Trace refund 742</option>
            <option value="scene_escalation_legal_threat">
              Escalation scene
            </option>
            <option value="blank">Blank run</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 sm:col-span-2">
          <span className="font-medium">Tool mode</span>
          <select
            className="h-9 rounded-md border bg-background px-2"
            value={config.toolMode}
            data-testid="sim-tool-mode"
            onChange={(event) =>
              updateConfig({
                toolMode: event.target.value as SimulatorToolMode,
              })
            }
          >
            <option value="mock">Mock tools</option>
            <option value="live">Live tools</option>
          </select>
        </label>
      </div>

      <fieldset
        className="rounded-md border p-3"
        data-testid="sim-tool-disable"
      >
        <legend className="px-1 text-xs font-semibold">Tool disable set</legend>
        <div className="mt-2 grid gap-2">
          {run.toolCalls.map((tool) => (
            <label
              key={tool.name}
              className="flex items-start gap-2 text-xs text-muted-foreground"
            >
              <input
                type="checkbox"
                checked={config.disabledTools.includes(tool.name)}
                onChange={() => toggleTool(tool.name)}
                aria-label={`Disable ${tool.name}`}
              />
              <span>
                <span className="font-medium text-foreground">{tool.name}</span>{" "}
                - {tool.status}; {tool.evidence}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <section
        className="rounded-md border bg-muted/30 p-3"
        data-testid="sim-channel-shell"
        aria-label={`${selectedChannel.label} preview shell`}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">
              {selectedChannel.previewLabel}
            </h3>
            <p className="text-xs text-muted-foreground">
              {selectedChannel.constraint}
            </p>
          </div>
          <span className="rounded-md border bg-background px-2 py-1 text-xs">
            {run.latencyMs} ms
          </span>
        </div>
        <div className="space-y-2 text-sm">
          <p className="rounded-md border bg-background p-2">
            <span className="block text-xs font-medium text-muted-foreground">
              {selectedChannel.composer}
            </span>
            {SIMULATOR_PERSONAS.find((p) => p.id === config.personaId)?.prompt}
          </p>
          <p className="rounded-md border bg-background p-2">
            <span className="block text-xs font-medium text-muted-foreground">
              Draft reply
            </span>
            {run.draftOutput}
          </p>
        </div>
      </section>

      <InlineChatOps onSubmit={handleCommand} />

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label htmlFor={inputId} className="text-xs font-medium">
          Simulated turn
        </label>
        <textarea
          id={inputId}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={3}
          disabled={running}
          data-testid="emulator-input"
          placeholder="Send a customer turn or type /replay turn=3 with-memory=cleared"
          className="rounded-md border bg-background px-2 py-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <div className="flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={resetLab}
            className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
            data-testid="sim-reset"
          >
            <RotateCcw className="h-4 w-4" aria-hidden={true} />
            Reset
          </button>
          <button
            type="submit"
            disabled={!prompt.trim() || running}
            data-testid="emulator-send"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
          >
            <Play className="h-4 w-4" aria-hidden={true} />
            {running ? "Streaming" : "Send"}
          </button>
        </div>
      </form>

      <section
        className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-y-auto"
        data-testid="emulator-stream"
      >
        {state.error ? (
          <StatePanel state="error" title="Simulator command stopped">
            <span data-testid="emulator-error">{state.error}</span>
          </StatePanel>
        ) : null}
        {run.unsupported.length > 0 ? (
          <StatePanel state="degraded" title="Voice preview is transcript-only">
            <span data-testid="sim-unsupported">
              {run.unsupported.join(" ")}
            </span>
          </StatePanel>
        ) : null}
        <EvidenceCallout
          title="Seeded context"
          source={run.traceId}
          tone={config.seededContextId === "blank" ? "warning" : "info"}
          confidence={config.seededContextId === "blank" ? 42 : 78}
        >
          <span data-testid="sim-context">
            {run.contextLabel}. {run.contextEvidence}
          </span>
        </EvidenceCallout>

        {state.tokens ? (
          <div
            data-testid="emulator-tokens"
            className="whitespace-pre-wrap text-sm"
          >
            {state.tokens}
          </div>
        ) : null}
        {state.toolCalls.length > 0 ? (
          <ul className="flex flex-col gap-2" data-testid="emulator-tool-calls">
            {state.toolCalls.map((call) => (
              <li
                key={call.key}
                data-testid={`emulator-tool-call-${call.name}`}
                className={cn(
                  "rounded-md border p-2 text-xs",
                  call.status === "ok"
                    ? "border-success/40 bg-success/5"
                    : call.status === "error"
                      ? "border-destructive/40 bg-destructive/5"
                      : "border-warning/50 bg-warning/5",
                )}
              >
                <div className="flex items-center justify-between">
                  <code className="font-medium">{call.name}</code>
                  <span className="text-muted-foreground">{call.status}</span>
                </div>
                {call.argsPreview ? (
                  <code className="block text-muted-foreground">
                    args: {call.argsPreview}
                  </code>
                ) : null}
                {call.resultPreview ? (
                  <code className="block text-muted-foreground">
                    result: {call.resultPreview}
                  </code>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        {state.degradeReason ? (
          <StatePanel state="degraded" title="Turn degraded">
            <span data-testid="emulator-degrade">{state.degradeReason}</span>
          </StatePanel>
        ) : null}
        {state.finalAnswer ? (
          <div
            className="rounded-md border bg-background p-2 text-sm"
            data-testid="emulator-final"
          >
            <p className="text-xs uppercase text-muted-foreground">
              Final answer
            </p>
            <p className="whitespace-pre-wrap">{state.finalAnswer}</p>
          </div>
        ) : null}

        <div className="grid min-w-0 gap-3" data-testid="sim-result-view">
          <section className="min-w-0 rounded-md border p-3">
            <h3 className="text-sm font-semibold">Exact model input/output</h3>
            <pre className="mt-2 max-h-48 max-w-full overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted p-2 text-xs">
              {run.modelInput}
            </pre>
            <p className="mt-2 rounded-md border bg-background p-2 text-sm">
              {run.modelOutput}
            </p>
          </section>

          <section
            className="min-w-0 rounded-md border p-3"
            data-testid="sim-version-diff"
          >
            <div className="mb-2 flex items-center gap-2">
              <History className="h-4 w-4 text-muted-foreground" aria-hidden />
              <h3 className="text-sm font-semibold">
                Side-by-side version diff
              </h3>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="min-w-0 rounded-md border bg-background p-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Production {config.diffAgainst}
                </p>
                <p className="mt-1 text-sm">{run.productionOutput}</p>
              </div>
              <div className="min-w-0 rounded-md border bg-background p-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Draft preview
                </p>
                <p className="mt-1 text-sm">{run.draftOutput}</p>
              </div>
            </div>
            <dl className="mt-3 grid gap-2 text-xs">
              {run.diffRows.map((row) => (
                <div
                  key={row.label}
                  className="grid min-w-0 gap-1 rounded-md border bg-muted/30 p-2"
                >
                  <dt className="font-semibold">{row.label}</dt>
                  <dd>Production: {row.production}</dd>
                  <dd>Draft: {row.draft}</dd>
                  <dd className="text-muted-foreground">
                    Evidence: {row.evidence}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="min-w-0 rounded-md border p-3">
            <h3 className="text-sm font-semibold">Run evidence</h3>
            <dl className="mt-2 grid gap-2 text-xs">
              <div className="rounded-md bg-muted p-2">
                <dt className="font-medium">Cost and latency</dt>
                <dd>
                  ${run.costUsd.toFixed(3)} per turn; {run.latencyMs} ms end to
                  end.
                </dd>
              </div>
              <div className="rounded-md bg-muted p-2">
                <dt className="font-medium">Replay command</dt>
                <dd data-testid="sim-replay">{run.replayLabel}</dd>
              </div>
              <div className="rounded-md bg-muted p-2">
                <dt className="font-medium">Policy flags</dt>
                <dd>{run.policyFlags.join(" ")}</dd>
              </div>
            </dl>
          </section>

          <section className="min-w-0 rounded-md border p-3">
            <h3 className="text-sm font-semibold">Tool calls</h3>
            <ul className="mt-2 grid gap-2 text-xs">
              {run.toolCalls.map((tool) => (
                <li
                  key={tool.name}
                  className="rounded-md bg-muted p-2"
                  data-testid={`sim-tool-${tool.name}`}
                >
                  <span className="font-medium">{tool.name}</span> -{" "}
                  {tool.status}. {tool.evidence}
                </li>
              ))}
            </ul>
          </section>

          <section className="min-w-0 rounded-md border p-3">
            <h3 className="text-sm font-semibold">Retrieval and memory</h3>
            <div className="mt-2 grid gap-2 text-xs">
              {run.retrievedChunks.map((chunk) => (
                <div key={chunk.source} className="rounded-md bg-muted p-2">
                  <p className="font-medium">{chunk.source}</p>
                  <p>{chunk.excerpt}</p>
                  <p className="text-muted-foreground">{chunk.evidence}</p>
                </div>
              ))}
              {run.memoryEvents.map((memory) => (
                <div
                  key={`${memory.kind}-${memory.label}`}
                  className="rounded-md bg-muted p-2"
                >
                  <p className="font-medium">
                    {memory.kind}: {memory.label}
                  </p>
                  <p className="text-muted-foreground">{memory.evidence}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="min-w-0 rounded-md border p-3">
            <h3 className="text-sm font-semibold">Eval and trace waterfall</h3>
            <div className="mt-2 grid gap-2 text-xs">
              {run.evalScores.map((score) => (
                <div key={score.scorer} className="rounded-md bg-muted p-2">
                  <p className="font-medium">
                    {score.scorer}: {score.score}
                  </p>
                  <p className="text-muted-foreground">{score.evidence}</p>
                </div>
              ))}
              {run.waterfall.map((span) => (
                <div
                  key={`${span.label}-${span.durationMs}`}
                  className="grid grid-cols-[minmax(0,1fr)_4rem] gap-2 rounded-md bg-muted p-2"
                >
                  <div>
                    <p className="font-medium">{span.label}</p>
                    <p className="text-muted-foreground">{span.evidence}</p>
                  </div>
                  <p className="text-right font-mono">{span.durationMs} ms</p>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="rounded-md border p-3" data-testid="sim-timeline">
          <h3 className="text-sm font-semibold">Local test timeline</h3>
          {timeline.length === 0 ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Run a turn or submit a ChatOps command to log local test evidence.
            </p>
          ) : (
            <ol className="mt-2 grid gap-2 text-xs">
              {timeline.map((item) => (
                <li
                  key={item.id}
                  className={cn(
                    "rounded-md border p-2",
                    item.ok
                      ? "border-info/40 bg-info/5"
                      : "border-destructive/40 bg-destructive/5",
                  )}
                >
                  <p className="font-medium">{item.label}</p>
                  <p className="text-muted-foreground">{item.detail}</p>
                </li>
              ))}
            </ol>
          )}
        </section>
      </section>
    </section>
  );
}
