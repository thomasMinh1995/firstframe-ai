import { useEffect, useState } from "react";
import type { UiLanguage } from "./language";
import { progressCopy, planProgressGroups, type OperationStep } from "./progressState";

export function OperationProgress({ steps, failed, timing, language, dirty = false }: {
  steps: OperationStep[]; failed: boolean; language: UiLanguage; dirty?: boolean;
  timing: { kind: "analyze" | "plan" | "review" | "scene-suggestions"; startedAt: number; finishedAt: number | null };
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
  return <section id="workspace-operation" tabIndex={-1} className="panel status-panel" aria-label={copy.title}>
    <h2>{failed ? copy.failed : completed ? copy.done : copy.title}</h2>
    <p className="thinking-state" role="timer" aria-live="off">
      {copy[timing.kind]} · {timing.finishedAt === null ? copy.running : failed ? copy.stopped : copy.elapsed} {duration}
    </p>
    <p role="status" aria-live="polite">{failed ? (dirty ? copy.unsavedError : prepared ? copy.error : copy.prepareError)
      : completed ? (dirty ? copy.savedWithEdits : copy.saved) : active ? copy.stages[active.stage] ?? copy.other : copy.preparing}</p>
    {timing.kind === "plan" ? <ol className="thinking-timeline plan-process" aria-label={language === "vi" ? "Các bước tạo Story plan" : "Story plan steps"}>
      {planProgressGroups(steps).map((group, index) => <li key={group.id} className={`plan-process-group is-${group.status}`}>
        <div className="plan-process-title"><span className="thinking-marker" aria-hidden="true">{group.status === "completed" ? "✓" : index + 1}</span>
          <h3>{(language === "vi" ? ["Chuẩn bị từ lựa chọn của bạn", "Phát triển Story plan", "Đối chiếu và giữ kết quả"]
            : ["Prepare from your choices", "Develop the story plan", "Review and keep the result"])[index]}</h3></div>
        <ol className="plan-process-children">{group.children.map(step => <li key={`${step.stage}-${step.occurrence}`} data-progress-stage={step.stage} data-progress-status={step.status}>
          <span className={`process-state is-${step.status}`}>{step.status === "completed" ? "✓" : step.status === "active" ? "●" : step.status === "failed" ? "!" : "○"}</span>
          <div><span>{copy.stages[step.stage] ?? copy.other}{step.occurrence > 1 ? ` (${step.occurrence})` : ""}</span>
            <small>{step.status === "pending" ? timing.finishedAt !== null ? copy.notRun : copy.waiting : step.status === "failed" ? copy.failure : copy[step.status]}</small>
            {step.stage === "planning" && <p className="process-detail">{language === "vi"
              ? "Tên phim, nhân vật và các nhịp mở đầu → diễn biến → kết thúc được tạo cùng trong lượt này."
              : "The title, characters and beginning → middle → ending are developed together in this request."}</p>}
          </div>
        </li>)}</ol>
      </li>)}
    </ol> : <>    <ol className="thinking-timeline">
      {steps.map((step, index) => <li key={`${step.stage}-${step.occurrence}`}
        className={`thinking-step${step.status === "completed" ? " is-complete" : ""}${step.status === "active" ? " is-active" : ""}`}>
        <span className="thinking-marker" aria-hidden="true">{step.status === "completed" ? "✓" : index + 1}</span>
        <span><span className="thinking-label">{copy.stages[step.stage] ?? copy.other}{step.occurrence > 1 ? ` (${step.occurrence})` : ""}</span>
          <span className="thinking-state">{step.status === "failed" ? copy.failure : copy[step.status]}</span></span>
      </li>)}
    </ol></>}

  </section>;
}
