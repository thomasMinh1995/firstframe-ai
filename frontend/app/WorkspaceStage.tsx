"use client";

import { useEffect, useRef, type ReactNode } from "react";

export function revealWorkspaceTarget(target: HTMLElement | null) {
  const workspace = target?.closest<HTMLElement>("[data-desktop-stage]");
  const stage = target?.closest<HTMLElement>("[data-workspace-stage]")?.dataset.workspaceStage
    ?? target?.closest<HTMLElement>("[data-progress-stage]")?.dataset.progressStage;
  if (workspace && stage) {
    // Reveal synchronously so tour measurements and focus see the selected panel immediately.
    workspace.dataset.desktopStage = stage;
    workspace.dispatchEvent(new CustomEvent("workspace-stage-change", {detail: stage}));
  }
  for (let parent = target?.parentElement; parent; parent = parent.parentElement) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
  }
}

export function WorkspaceStage({ id, title, preview, complete, children, tourStep }: {
  id: string; title: string; preview: string; complete: boolean; children: ReactNode; tourStep?: "idea" | "choices";
}) {
  const element = useRef<HTMLDetailsElement>(null);
  const wasComplete = useRef(complete);
  useEffect(() => {
    if (complete && !wasComplete.current && element.current) element.current.open = false;
    wasComplete.current = complete;
  }, [complete]);
  return <details ref={element} className="panel workspace-stage" data-workspace-stage={id} open={!complete}>
    <summary><h2 id={id} tabIndex={-1} data-tour={tourStep}>{title}</h2><span className="stage-preview">{preview}</span>
      <span className="stage-toggle" aria-hidden="true">Mở / thu gọn</span></summary>
    <div className="form-stack">{children}</div>
  </details>;
}
