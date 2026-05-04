"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { triggerEvalSuiteRun } from "@/lib/evals";

export interface RunNowButtonProps {
  suiteId: string;
  triggerRun?: (suiteId: string) => Promise<{ id: string }>;
}

export function RunNowButton({
  suiteId,
  triggerRun = triggerEvalSuiteRun,
}: RunNowButtonProps) {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onRunNow() {
    setError(null);
    setRunning(true);
    try {
      const run = await triggerRun(suiteId);
      router.push(`/evals/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start run");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        type="button"
        onClick={onRunNow}
        disabled={running}
        data-testid="eval-suite-run-now"
      >
        {running ? "Starting…" : "Run now"}
      </Button>
      {error ? (
        <p className="text-sm text-red-600" role="alert" data-testid="eval-suite-run-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
