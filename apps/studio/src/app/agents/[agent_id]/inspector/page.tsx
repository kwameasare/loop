"use client";

import { useState } from "react";

import { VariableInspector } from "@/components/flow/variable-inspector";
import { captureFrame, type FlowFrame } from "@/lib/flow-inspector";

const STEPS: { nodeId: string; label: string; state: Record<string, unknown> }[] = [
  { nodeId: "start-1", label: "Start", state: { user: "ada" } },
  {
    nodeId: "ai-1",
    label: "Ask LLM",
    state: { user: "ada", reply: "Hi Ada!" },
  },
  {
    nodeId: "msg-1",
    label: "Send message",
    state: { user: "ada", reply: "Hi Ada!", sent: true },
  },
];

export default function InspectorDemoPage() {
  const [frames, setFrames] = useState<FlowFrame[]>([]);
  const [running, setRunning] = useState(false);

  function start() {
    setFrames([]);
    setRunning(true);
    let i = 0;
    const tick = () => {
      const step = STEPS[i];
      setFrames((prev) => [
        ...prev,
        captureFrame(step.nodeId, step.label, step.state as never),
      ]);
      i += 1;
      if (i < STEPS.length) {
        setTimeout(tick, 350);
      } else {
        setRunning(false);
      }
    };
    setTimeout(tick, 200);
  }

  return (
    <main className="flex min-h-screen">
      <section className="flex flex-1 flex-col gap-4 p-8">
        <header className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Emulator</h1>
          <button
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-zinc-300"
            data-testid="inspector-run"
            disabled={running}
            onClick={start}
            type="button"
          >
            {running ? "Running…" : "Run flow"}
          </button>
        </header>
        <p className="text-sm text-zinc-600">
          Click <em>Run flow</em> to step the demo flow and watch the variable
          inspector update on each node visit.
        </p>
      </section>
      <VariableInspector frames={frames} running={running} />
    </main>
  );
}
