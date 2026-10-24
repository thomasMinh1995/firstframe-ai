"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { revealWorkspaceTarget } from "./WorkspaceStage";
import { createPortal } from "react-dom";
import {
  available, continuation, initialTour, nextStep, previousStep, reduceTour, tourSteps, tourStorageKey, validAnalysis,
  type TourContext, type TourOperation, type TourRequest, type TourStep,
} from "./onboardingState";

export function useOnboarding(context: TourContext, busy: boolean, error: string | null) {
  const [state, setState] = useState(initialTour);
  const current = useRef(state);
  const contextRef = useRef(context);
  contextRef.current = context;
  const mounted = useRef(false);
  const update = useCallback((action: Parameters<typeof reduceTour>[1], persist = true) => {
    if (!mounted.current) return current.current;
    const before = current.current;
    const next = reduceTour(before, action);
    current.current = next;
    if (next !== before) setState(next);
    if (persist && next.record && next.record !== before.record) {
      try { localStorage.setItem(tourStorageKey, JSON.stringify(next.record)); } catch { /* Keep this session usable. */ }
    }
    return next;
  }, []);
  useEffect(() => {
    mounted.current = true;
    let raw: string | null | undefined;
    try { raw = localStorage.getItem(tourStorageKey); } catch { raw = undefined; }
    update({ type: "load", raw }, false);
    function changed(event: StorageEvent) {
      if (event.key === tourStorageKey || event.key === null) update({ type: "external", raw: event.newValue }, false);
    }
    window.addEventListener("storage", changed);
    return () => { mounted.current = false; window.removeEventListener("storage", changed); };
  }, [update]);
  useEffect(() => {
    const r = current.current.record;
    if (r && ["active", "waiting"].includes(r.status) && r.projectId !== context.projectId) update({ type: "pause" });
    else if (r?.status === "active" && (busy || !available(r.stepId, context))) {
      update({ type: "pause", hint: busy ? undefined : "Chưa thể mở bước này. Bạn có thể thử lại." });
    }
  }, [context.projectId, context.hasAnalysis, context.hasDraft, context.briefChanged, busy, update]);
  // A pre-existing error must not close help the user explicitly opens to correct it.
  useEffect(() => { if (error) update({ type: "pause" }); }, [error, update]);

  return {
    state,
    open: (resume = false) => update({ type: "open", resume, context: contextRef.current }),
    navigate: (step: TourStep) => update({ type: "navigate", step, context: contextRef.current }),
    practice: () => update({ type: "practice", context: contextRef.current }),
    dismiss: () => update({ type: "dismiss", context: contextRef.current }),
    complete: () => update({ type: "complete", context: contextRef.current }),
    pause: (hint?: string) => update({ type: "pause", hint }),
    begin: (kind: TourOperation) => {
      const before = current.current.request;
      const next = update({ type: "begin", kind, context: contextRef.current });
      return next.request !== before ? next.request : null;
    },
    succeeded: (ticket: TourRequest | null, resultId: string) => update({ type: "success", ticket, resultId }),
    failed: (ticket: TourRequest | null) => update({ type: "failed", ticket }),
  };
}

type Tour = ReturnType<typeof useOnboarding>;
type Props = {
  tour: Tour; context: TourContext; ready: boolean; empty: boolean; busy: boolean; error: string | null;
  idea: string; answers: string[]; questionCount: number;
};
const titles: Record<TourStep, string> = {
  "new-project": "Bắt đầu câu chuyện đầu tiên", idea: "Câu chuyện bạn muốn kể", language: "Cùng làm rõ ý tưởng",
  choices: "Những lựa chọn thuộc về bạn", draft: "Viết tiếp bằng giọng của bạn", save: "Lưu lại để tiếp tục",
};
const targetLabels: Record<TourStep, string> = {
  "new-project": "Nút Dự án mới", idea: "Ô Khoảnh khắc, kỷ niệm hoặc tình huống của bạn",
  language: "Ngôn ngữ đầu ra", choices: "Những lựa chọn của bạn",
  draft: "Bản phát triển đang làm việc", save: "Thanh lưu thay đổi",
};
function copy(step: TourStep, p: Props) {
  switch (step) {
    case "new-project": return p.context.projectId
      ? "Dự án mới tạo không gian cho một câu chuyện khác. Nút này sẽ lưu thay đổi của dự án đang mở trước khi tạo dự án mới."
      : "Tạo không gian riêng cho câu chuyện của bạn. Bạn có thể lưu và quay lại viết tiếp bất cứ lúc nào.";
    case "idea": return "Ghi lại một khoảnh khắc bạn thấy, nghe hoặc nhớ, kèm điều muốn giữ ở ô bên dưới. Chưa cần có cốt truyện. Dùng Lưu thay đổi để quay lại viết tiếp, kể cả khi chưa chạy AI.";
    case "language": return validAnalysis(p.context)
      ? "Ngôn ngữ này áp dụng cho lần AI tiếp theo, không dịch nội dung đã có. Ý tưởng đã được làm rõ; bạn có thể tiếp tục xem các lựa chọn mà không chạy AI lại."
      : "Chọn Tiếng Việt hoặc English nếu ý tưởng quá ngắn hay chưa rõ ngôn ngữ. Sau đó tự bấm Cùng làm rõ ý tưởng; FirstFrame sẽ lưu trước khi gửi AI.";
    case "choices": return (p.questionCount
      ? "Trả lời theo ý bạn, hoặc chọn Để quyết định sau nếu chưa chắc. "
      : "Ý tưởng không có câu hỏi bổ sung; bạn có thể tạo bản phát triển ngay. ")
      + (p.context.hasDraft ? "Bạn cũng có thể xem bản đã có; tạo lại sẽ giữ đề xuất riêng tới khi bạn chọn nhận." : "Bạn quyết định khi nào tạo bản phát triển từ các lựa chọn của mình.");
    case "draft": return "Sửa trực tiếp tên phim, tóm tắt và từng phần theo ý bạn. Đây là bản phát triển câu chuyện, chưa phải kịch bản theo cảnh hoàn chỉnh.";
    case "save": return "Nhận phản hồi trên bản hiện tại sẽ lưu trước khi gửi AI; bạn tự quyết định cách sửa. Sau khi sửa tiếp, góp ý cũ thuộc bản trước — hãy lưu thay đổi trước khi rời đi.";
  }
}

export function OnboardingTour(props: Props) {
  const { tour, context, ready, empty, busy, error } = props;
  const { state } = tour;
  const record = state.record;
  const focusFrame = useRef(0);
  const opener = useRef<HTMLElement | null>(null);
  useEffect(() => () => cancelAnimationFrame(focusFrame.current), []);
  const focusAfter = (destination: string | HTMLElement | null) => {
    cancelAnimationFrame(focusFrame.current);
    focusFrame.current = requestAnimationFrame(() => {
      const active = document.activeElement;
      if (active?.matches("input, textarea, select")
        && !(typeof destination === "string" ? active.matches(destination) : active === destination)) return;
      if (typeof destination === "string" && destination.startsWith("#answer-") && !document.querySelector(destination)) {
        const opener = document.querySelector<HTMLButtonElement>(`[data-answer-open="${destination.slice(1)}"]`);
        revealWorkspaceTarget(opener); opener?.click();
        return;
      }
      const element = typeof destination === "string" ? document.querySelector<HTMLElement>(destination) : destination;
      revealWorkspaceTarget(element);
      const target = element?.isConnected && element !== document.body && element.getClientRects().length
        && !element.matches(":disabled") ? element : document.getElementById("workspace-title");
      target?.scrollIntoView({ block: "center", behavior: "auto" });
      target?.focus({ preventScroll: true });
    });
  };
  const open = (button: HTMLElement, resume = false) => { opener.current = button; tour.open(resume); };
  const dismiss = () => {
    const destination = record?.status === "active" ? opener.current : document.activeElement as HTMLElement | null;
    tour.dismiss(); focusAfter(destination);
  };
  const practice = () => {
    if (!record) return;
    const step = record.stepId;
    let selector = `[data-tour="${step}"]`;
    if (step === "language") selector = !props.idea.trim() ? "#idea"
      : document.querySelector('[data-tour-action="analyze"]:enabled') ? '[data-tour-action="analyze"]' : "#response-language";
    if (step === "choices") {
      const index = Array.from({ length: props.questionCount }, (_, i) => i).find(i => !props.answers[i]?.trim());
      selector = index === undefined ? '[data-choice-review]' : `#answer-${index}`;
    }
    if (step === "draft") {
      const editor = document.querySelector<HTMLButtonElement>('[data-draft-open="logline"]');
      if (editor && !editor.disabled) {
        tour.practice();
        cancelAnimationFrame(focusFrame.current);
        focusFrame.current = requestAnimationFrame(() => {
          if (!document.activeElement?.matches("input, textarea, select")) { revealWorkspaceTarget(editor); editor.click(); }
        });
        return;
      }
      selector = "#draft-logline";
    }
    tour.practice(); focusAfter(selector);
  };
  const welcome = state.initialized && state.offerAllowed && !record && ready && empty && !context.projectId && !busy && !error;
  const resumable = record?.status === "waiting" || record?.status === "paused";
  const next = record ? nextStep(record.stepId, context) : null;
  const previous = record ? previousStep(record.stepId, context) : null;
  const active = record?.status === "active" && ready && !busy;
  useEffect(() => {
    if (!welcome && !resumable) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented || event.isComposing || document.querySelector("dialog[open]")) return;
      event.preventDefault(); dismiss();
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [welcome, resumable, dismiss]);

  return <>
    <button id="tour-help" className="secondary tour-help" disabled={!ready || busy || !state.initialized}
      onClick={event => open(event.currentTarget)}>Hướng dẫn sử dụng</button>
    {welcome && <section className="tour-notice" aria-label="Chào mừng đến với FirstFrame">
      <div><strong>Bắt đầu cùng FirstFrame</strong><p>Xem hướng dẫn ngắn, rồi thực hành từng bước với câu chuyện của bạn.</p></div>
      <button onClick={event => open(event.currentTarget)}>Bắt đầu hướng dẫn</button>
      <button className="secondary" onClick={dismiss}>Bỏ qua</button>
    </section>}
    {resumable && <section className="tour-notice" aria-label="Tiến độ hướng dẫn">
      <p role="status">{state.hint ?? (record.status === "paused" ? "Hướng dẫn đang tạm dừng. Bạn có thể tiếp tục khi sẵn sàng."
        : "Bạn đang thực hành. Tiếp tục hướng dẫn khi sẵn sàng, hoặc bỏ qua để tự khám phá.")}</p>
      <button disabled={!ready || busy || !continuation(state, context)} onClick={event => open(event.currentTarget, true)}>Tiếp tục hướng dẫn</button>
      <button className="secondary" onClick={dismiss}>Bỏ qua</button>
    </section>}
    {active && createPortal(<TourDialog step={record.stepId} title={titles[record.stepId]} description={copy(record.stepId, props)}
      onMissing={() => tour.pause("Chưa thể mở bước này. Bạn có thể thử lại hoặc bỏ qua.")}
      onDismiss={dismiss}>
      <div className="tour-footer">
        <span>Bước {tourSteps.indexOf(record.stepId) + 1}/6</span>
        <button className="secondary" disabled={!previous} onClick={() => previous && tour.navigate(previous)}>Trước</button>
        {record.stepId !== "save" && <button className={next ? "secondary" : ""} onClick={practice}>Thực hành</button>}
        {next && <button onClick={() => tour.navigate(next)}>Tiếp</button>}
        {record.stepId === "save" && <button onClick={() => {
          tour.complete(); focusAfter(document.querySelector('[data-tour-action="save"]:enabled') ? '[data-tour-action="save"]' : "#save-status");
        }}>Hoàn tất hướng dẫn</button>}
      </div>
      <button className="tour-skip" onClick={dismiss}>Bỏ qua hướng dẫn</button>
    </TourDialog>, document.body)}
  </>;
}

type Placement = { left: number; top: number; width: number; maxHeight: number; hole: { left: number; top: number; width: number; height: number } | null };
function TourDialog({ step, title, description, onMissing, onDismiss, children }: {
  step: TourStep; title: string; description: string; onMissing: () => void; onDismiss: () => void; children: React.ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const missing = useRef(onMissing);
  missing.current = onMissing;
  const [placement, setPlacement] = useState<Placement | null>(null);
  useLayoutEffect(() => {
    const layer = dialog.current!;
    const panel = card.current!;
    const targets = document.querySelectorAll<HTMLElement>(`[data-tour="${step}"]`);
    const target = targets.length === 1 ? targets[0] : null;
    revealWorkspaceTarget(target);
    if (!target || !target.getClientRects().length || getComputedStyle(target).visibility === "hidden") { missing.current(); return; }
    target.scrollIntoView({ block: "center", behavior: "auto" });
    layer.showModal();
    let frame = 0;
    const viewport = window.visualViewport;
    function measure() {
      if (!target?.isConnected || !target.getClientRects().length || getComputedStyle(target).visibility === "hidden") { missing.current(); return; }
      const r = target.getBoundingClientRect();
      if (!r.width || !r.height) { missing.current(); return; }
      const x = viewport?.offsetLeft ?? 0, y = viewport?.offsetTop ?? 0;
      const w = viewport?.width ?? window.innerWidth, h = viewport?.height ?? window.innerHeight;
      const margin = 16, gap = 16, width = Math.min(380, w - 2 * margin), maxHeight = h - 2 * margin;
      panel.style.width = `${width}px`;
      panel.style.maxHeight = `${maxHeight}px`;
      const height = panel.getBoundingClientRect().height;
      const clampX = (v: number) => Math.max(x + margin, Math.min(v, x + w - width - margin));
      const clampY = (v: number) => Math.max(y + margin, Math.min(v, y + h - height - margin));
      let left = clampX(r.left), top = 0, fits = true;
      if (w <= 600 && r.bottom + gap <= y + h - height - margin) top = y + h - height - margin;
      else if (w > 600 && r.right + gap + width <= x + w - margin) { left = r.right + gap; top = clampY(r.top); }
      else if (w > 600 && r.left - gap - width >= x + margin) { left = r.left - gap - width; top = clampY(r.top); }
      else if (r.bottom + gap + height <= y + h - margin) top = r.bottom + gap;
      else if (r.top - gap - height >= y + margin) top = r.top - gap - height;
      else { fits = false; left = clampX(x + (w - width) / 2); top = clampY(y + (h - height) / 2); }
      const visible = r.top >= y && r.bottom <= y + h && r.left >= x && r.right <= x + w;
      // Resizing can move the target outside the viewport before scroll catches up.
      setPlacement({ left: clampX(left), top: clampY(top), width, maxHeight, hole: fits && visible
        ? { left: r.left - 6, top: r.top - 6, width: r.width + 12, height: r.height + 12 } : null });
    }
    function schedule() { cancelAnimationFrame(frame); frame = requestAnimationFrame(measure); }
    measure();
    const focusFrame = requestAnimationFrame(() => panel.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true }));
    const resize = new ResizeObserver(schedule);
    resize.observe(target); resize.observe(panel);
    const mutations = new MutationObserver(schedule);
    const workspace = document.querySelector(".workspace");
    if (workspace) mutations.observe(workspace, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "class", "style"] });
    window.addEventListener("scroll", schedule, true);
    window.addEventListener("resize", schedule);
    viewport?.addEventListener("resize", schedule); viewport?.addEventListener("scroll", schedule);
    return () => {
      cancelAnimationFrame(frame); cancelAnimationFrame(focusFrame); resize.disconnect(); mutations.disconnect();
      window.removeEventListener("scroll", schedule, true); window.removeEventListener("resize", schedule);
      viewport?.removeEventListener("resize", schedule); viewport?.removeEventListener("scroll", schedule);
      layer.close();
      if (document.activeElement === document.body || document.activeElement?.matches(":disabled")) {
        document.getElementById("workspace-title")?.focus({ preventScroll: true });
      }
    };
  }, [step]);
  return <dialog ref={dialog} className="tour-layer" aria-labelledby="tour-title" aria-describedby="tour-description"
    onCancel={event => { event.preventDefault(); onDismiss(); }}
    onKeyDown={event => {
      if (event.key !== "Tab") return;
      const buttons = [...card.current!.querySelectorAll<HTMLButtonElement>("button:enabled")];
      const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
      // WebKit's default keyboard navigation may skip buttons even inside a modal.
      event.preventDefault();
      const next = index < 0 ? (event.shiftKey ? buttons.length - 1 : 0)
        : (index + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length;
      buttons[next]?.focus();
    }}>
    {placement?.hole ? <div className="tour-spotlight" aria-hidden="true" style={placement.hole} /> : <div className="tour-dim" aria-hidden="true" />}
    <div ref={card} className="tour-card" style={placement ? { left: placement.left, top: placement.top, width: placement.width, maxHeight: placement.maxHeight } : { visibility: "hidden" }}>
      <button className="tour-close" aria-label="Đóng hướng dẫn" onClick={onDismiss}>×</button>
      <p className="eyebrow">FirstFrame · Hướng dẫn</p>
      <h2 id="tour-title" tabIndex={-1}>{title}</h2>
      <p id="tour-description"><strong>{targetLabels[step]}.</strong> {description}</p>
      {children}
    </div>
  </dialog>;
}
