import { useId, useEffect, useState } from "react";
import type { UiLanguage } from "./language";
import { progressCopy, processTitles, operationProgressGroups, type OperationKind, type OperationStep } from "./progressState";

const inlineCopy = {
  vi: { running: "Đang xử lý", stopped: "Đã dừng", done: "Đã hoàn tất", substep: "Bước con", show: "Xem bước con", hide: "Thu gọn", processing: "FirstFrame đang xử lý bước này.", interrupted: "Chưa rõ kết quả", summary: "Đã xong", units: "bước con" },
  en: { running: "Processing", stopped: "Stopped", done: "Completed", substep: "Substep", show: "Show substeps", hide: "Collapse", processing: "FirstFrame is working on this step.", interrupted: "Result unknown", summary: "Completed", units: "substeps" },
};

function ProcessGroup({ group, title, index, language, finished }: {
  group: ReturnType<typeof operationProgressGroups>[number]; title: string; index: number; language: UiLanguage; finished: boolean;
}) {
  const id = useId();
  const copy = progressCopy[language];
  const ui = inlineCopy[language];
  // Automatically follow status changes; users may inspect any group in between.
  const [expanded, setExpanded] = useState<{ status: string; open: boolean } | null>(null);
  const open = expanded?.status === group.status ? expanded.open : ["active", "failed", "interrupted"].includes(group.status);
  const activeIndex = group.children.findIndex(step => step.status === "active");
  const state = group.status === "pending" ? finished ? copy.notRun : copy.waiting
    : group.status === "failed" ? copy.failure : group.status === "interrupted" ? ui.interrupted : copy[group.status];
  return <li className={`process-group is-${group.status}`} data-process-group={group.id}>
    <div className="process-parent">
      <span className="thinking-marker" aria-hidden="true">{group.status === "completed" ? "✓" : group.status === "failed" || group.status === "interrupted" ? "!" : index + 1}</span>
      <h3><button type="button" aria-expanded={open} aria-controls={id} disabled={!group.children.length}
        onClick={() => setExpanded({ status: group.status, open: !open })}>
        <span className="process-parent-title">{title}</span>
        <span className="process-parent-meta">{state}{activeIndex >= 0 ? ` · ${ui.substep} ${activeIndex + 1}/${group.children.length}` : ""}</span>
        {group.children.length > 0 && <span className="process-toggle">{open ? ui.hide : `${ui.show} (${group.children.length})`} <span aria-hidden="true">{open ? "⌃" : "⌄"}</span></span>}
      </button></h3>
    </div>
    <ol id={id} className="process-children" hidden={!open}>
      {group.children.map(step => <li key={`${step.stage}-${step.occurrence}`} className={`process-child is-${step.status}`} data-progress-stage={step.stage} data-progress-status={step.status}>
        <span className={`process-state is-${step.status}`} aria-hidden="true">{step.status === "completed" ? "✓" : step.status === "active" ? <span className="process-spinner" /> : step.status === "failed" || step.status === "interrupted" ? "!" : "○"}</span>
        <div className="process-child-label">{copy.stages[step.stage] ?? copy.other}{step.occurrence > 1 ? ` (${step.occurrence})` : ""}
          {step.status === "active" && <small>{ui.processing}</small>}
        </div>
        <span className="process-child-state">{step.status === "pending" ? finished ? copy.notRun : copy.waiting : step.status === "failed" ? copy.failure : step.status === "interrupted" ? ui.interrupted : copy[step.status]}</span>
      </li>)}
    </ol>
  </li>;
}

export function OperationProgress({ steps, failed, timing, language, dirty = false }: {
  steps: OperationStep[]; failed: boolean; language: UiLanguage; dirty?: boolean;
  timing: { kind: OperationKind; startedAt: number; finishedAt: number | null };
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
  const ui = inlineCopy[language];
  const active = steps.find(step => step.status === "active");
  const completed = timing.finishedAt !== null && !failed;
  const prepared = steps.some(step => step.stage === "prepare" && step.status === "completed");
  const groups = operationProgressGroups(timing.kind, steps, failed ? "failed" : completed ? "completed" : "running");
  const children = groups.flatMap(group => group.children);
  const title = failed ? copy.failed : completed ? copy.done : copy.title;
  return <section id="workspace-operation" tabIndex={-1} className="panel status-panel inline-process" aria-label={copy.title}>
    <div className="process-heading">
      <div><h2>{title}</h2><p className="thinking-state" role="timer" aria-live="off">
        {copy[timing.kind]} · {timing.finishedAt === null ? copy.running : failed ? copy.stopped : copy.elapsed} {duration}
      </p></div>
      <span className={`process-badge${failed ? " is-failed" : ""}`}>{!failed && !completed && <span className="process-spinner" aria-hidden="true" />}{failed ? ui.stopped : completed ? ui.done : ui.running}</span>
    </div>
    <p className="process-notice" role="status" aria-live="polite">{failed ? (dirty ? copy.unsavedError : prepared ? copy.error : copy.prepareError)
      : completed ? (dirty ? copy.savedWithEdits : copy.saved) : active ? copy.stages[active.stage] ?? copy.other : copy.preparing}</p>
    <ol className="process-groups" aria-label={copy.title}>
      {groups.map(group => {
        const index = ["prepare", "develop", "review"].indexOf(group.id);
        return <ProcessGroup key={`${timing.kind}-${timing.startedAt}-${group.id}`} group={group} index={index}
          title={processTitles[language][timing.kind][index]} language={language} finished={timing.finishedAt !== null || failed} />;
      })}
    </ol>
    <p className="process-summary">{ui.summary} {children.filter(step => step.status === "completed").length}/{children.length} {ui.units}</p>
  </section>;
}
