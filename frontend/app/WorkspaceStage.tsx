"use client";

import { useEffect, useRef, type ReactNode } from "react";

export function revealWorkspaceTarget(target: HTMLElement | null) {
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
