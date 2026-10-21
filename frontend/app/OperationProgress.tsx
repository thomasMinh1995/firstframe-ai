import { useEffect, useState } from "react";
import type { UiLanguage } from "./language";
import { progressCopy, type OperationStep } from "./progressState";

export function OperationProgress({ steps, failed, timing, language, dirty = false }: {
  steps: OperationStep[]; failed: boolean; language: UiLanguage; dirty?: boolean;
  timing: { kind: "analyze" | "plan" | "review"; startedAt: number; finishedAt: number | null };
}) {
  const [now, setNow] = useState(timing.startedAt);
  useEffect(() => {
    if (timing.finishedAt !== null) return;
    setNow(performance.now());
    const interval = window.setInterval(() => setNow(performance.now()), 1000);
    return () => window.clearInterval(interval);
  }, [timing.startedAt, timing.finishedAt]);
  const seconds = Math.max(0, Math.floor(((timing.finishedAt ?? now) - timing.startedAt) / 1000));
  const duration = `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const copy = progressCopy[language];
  const active = steps.find((step) => step.status === "active");
  const completed = timing.finishedAt !== null && !failed;
  const prepared = steps.some((step) => step.stage === "prepare" && step.status === "completed");
  return <section className="panel status-panel" aria-label={copy.title}>
    <h2>{failed ? copy.failed : completed ? copy.done : copy.title}</h2>
    <p className="thinking-state" role="timer" aria-live="off">
      {copy[timing.kind]} · {timing.finishedAt === null ? copy.running : failed ? copy.stopped : copy.elapsed} {duration}
    </p>
    <p role="status" aria-live="polite">{failed ? (dirty ? copy.unsavedError : prepared ? copy.error : copy.prepareError)
      : completed ? (dirty ? copy.savedWithEdits : copy.saved) : active ? copy.stages[active.stage] ?? copy.other : copy.preparing}</p>
    <ol className="thinking-timeline">
      {steps.map((step, index) => <li key={`${step.stage}-${step.occurrence}`}
        className={`thinking-step${step.status === "completed" ? " is-complete" : ""}${step.status === "active" ? " is-active" : ""}`}>
        <span className="thinking-marker" aria-hidden="true">{step.status === "completed" ? "✓" : index + 1}</span>
        <span><span className="thinking-label">{copy.stages[step.stage] ?? copy.other}{step.occurrence > 1 ? ` (${step.occurrence})` : ""}</span>
          <span className="thinking-state">{step.status === "failed" ? copy.failure : copy[step.status]}</span></span>
      </li>)}
    </ol>
  </section>;
}
