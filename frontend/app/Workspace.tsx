"use client";

import { useEffect, useRef, useState } from "react";
import {useProjectAutosave} from "./useProjectAutosave";
import { useRouter } from "next/navigation";
import { WorkspaceStage, revealWorkspaceTarget } from "./WorkspaceStage";
import { SavedLibrary } from "./SavedLibrary";
import { CardFeedback } from "./CardFeedback";
import { readRevisionNotes, validatedTargets } from "./revisionNotes";
import { StoryFeedback } from "./StoryResultCards";
import { StoryPlanEditor, type DraftField } from "./StoryPlanEditor";
import type { Scene, SceneSuggestionInput } from "./sceneTypes";
import { ScreenplayEditor } from "./ScreenplayEditor";
import { SceneHistory, SavedOutline, SceneOutlineEditor } from "./SceneOutlineEditor";
import { ClarificationConversation } from "./ClarificationConversation";
import "./storyWorkspace.css";
import { AuthorIntentCard, FeedbackIntent, IntentDetails } from "./AuthorIntentCard";
import { OperationProgress } from "./OperationProgress";
import { OnboardingTour, useOnboarding } from "./OnboardingTour";
import type { TourStep } from "./onboardingState";
import { applyProgress, progressLanguage, type OperationStep } from "./progressState";
import { feedbackGuidance, sectionLabels } from "./storyLabels";
import { responseLanguageLabels, type ResponseLanguage } from "./language";
import type { EvaluationFinding, RevisionNote } from "./apiClient";
import {
  editableProject, listProjects, projectRequest, streamProjectOperation,
  type Project, type ProjectSummary,
} from "./projectsApi";

export default function Workspace({ library = false }: { library?: boolean }) {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [busy, setBusy] = useState<string | null>("Đang mở dự án…");
  const {project, saved, saving, error: saveError, autosave} = useProjectAutosave(!busy && !library);
  const {setProject, setSaved} = autosave;
  const operation = useRef(false);
  const [draftEditorRevision, setDraftEditorRevision] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedFeedback, setSelectedFeedback] = useState<{
    projectId: string; artifactId: string; criterionId: string; message: string;
  } | null>(null);
  const [pendingStage, setPendingStage] = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<{ id: string; label: string } | null>(null);
  const [workspaceLoadState, setWorkspaceLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [projectsListed, setProjectsListed] = useState(false);
  const [steps, setSteps] = useState<OperationStep[]>([]);
  const [operationFailed, setOperationFailed] = useState(false);
  const [operationTiming, setOperationTiming] = useState<{
    kind: "analyze" | "plan" | "review" | "scene-suggestions" | "scene-sketches" | "screenplay-proposals" | "screenplay-reviews"; startedAt: number; finishedAt: number | null;
  } | null>(null);
  const dirty = project !== null && saved !== null
    && JSON.stringify(editableProject(project)) !== JSON.stringify(editableProject(saved));
  const briefChanged = project !== null && saved !== null && (project.idea !== saved.idea
    || JSON.stringify(project.constraints) !== JSON.stringify(saved.constraints));
  const feedbackChanged = project !== null && saved !== null && JSON.stringify({
    response_language: project.response_language,
    idea: project.idea, constraints: project.constraints, answers: project.answers, draft: project.draft,
    questions: project.analysis?.missing_information ?? [],
  }) !== JSON.stringify({
    response_language: saved.response_language,
    idea: saved.idea, constraints: saved.constraints, answers: saved.answers, draft: saved.draft,
    questions: saved.analysis?.missing_information ?? [],
  });
  const decisionKey = JSON.stringify([project?.id, project?.idea, project?.constraints, project?.response_language,
    project?.analysis?.artifact_id, project?.analysis?.missing_information, project?.answers]);
  const currentFeedback = project?.feedback_is_current && !feedbackChanged;
  const selectableFeedback = currentFeedback && !busy && !!project?.draft && !!project.feedback?.artifact_id
    && saved?.feedback_source?.project_id === project.id
    && saved.feedback_source.artifact_id === project.feedback.artifact_id;
  const tourContext = { projectId: project?.id ?? null, hasAnalysis: !!project?.analysis,
    hasDraft: !!project?.draft, briefChanged };
  const tour = useOnboarding(tourContext, !!busy, error);
  useEffect(() => {
    if (saved) setProjects(items => [saved, ...items.filter(item => item.id !== saved.id)]);
  }, [saved]);
  useEffect(() => { if (dirty) setNotice(null); }, [dirty]);
  useEffect(() => {
    if (!selectedFeedback || selectedCard) return;
    const frame = requestAnimationFrame(() => {
      const note = document.getElementById("selected-feedback-title");
      revealWorkspaceTarget(note);
      note?.scrollIntoView({ block: "center" });
      note?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [selectedFeedback, selectedCard]);

  useEffect(() => {
    if (selectedCard && !document.querySelector(`[data-card-id="${selectedCard.id}"]`)) setSelectedCard(null);
  }, [selectedCard, saved?.revision, project?.id]);

  useEffect(() => {
    if (!pendingStage) return;
    const frame = requestAnimationFrame(() => {
      const target = document.getElementById(pendingStage);
      if (target) {
        revealWorkspaceTarget(target);
        const focus = pendingStage === "workspace-choices"
          ? document.querySelector<HTMLElement>(".clarification-current textarea") ?? target : target;
        focus.scrollIntoView({ block: pendingStage === "workspace-draft" ? "start" : "center" }); focus.focus({ preventScroll: true });
      }
      setPendingStage(null);
    });
    return () => cancelAnimationFrame(frame);
  }, [pendingStage]);

  useEffect(() => {
    if (!operationTiming || !["plan", "analyze"].includes(operationTiming.kind) || operationTiming.finishedAt !== null) return;
    const frame = requestAnimationFrame(() => {
      const target = document.getElementById("workspace-operation");
      revealWorkspaceTarget(target);
      target?.scrollIntoView({ block: "start" }); target?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [operationTiming?.startedAt]);

  function syncProjectUi(next: Project, previous: Project | null) {
    setSelectedFeedback(current => current?.projectId === next.id
      && current.artifactId === next.feedback?.artifact_id ? current : null);
    if (next.id !== previous?.id) setSelectedCard(null);
    if (JSON.stringify(previous?.draft) !== JSON.stringify(next.draft)
        || (!autosave.dirty && previous?.feedback?.artifact_id !== next.feedback?.artifact_id)) setDraftEditorRevision(n => n + 1);
    setWorkspaceLoadState("ready");
  }
  function accept(next: Project) {
    syncProjectUi(next, autosave.getSnapshot().project);
    autosave.accept(next);
  }
  async function inspectProject(refreshSelections = false) {
    const previous = autosave.getSnapshot().project;
    const next = await autosave.inspect(refreshSelections);
    if (next) syncProjectUi(next, previous);
  }
  useEffect(() => {
    let cancelled = false;
    async function openLastProject() {
      try {
        const items = await listProjects();
        const requested = new URLSearchParams(window.location.search).get("project");
        const selected = items.find(item => item.id === requested) ?? items[0];
        const last = selected ? await projectRequest(`/${selected.id}`) : null;
        if (!cancelled) {
          setProjects(items); autosave.accept(last);
          setProjectsListed(true); setWorkspaceLoadState("ready");
        }
      } catch (caught) {
        if (!cancelled) { setError(message(caught)); setWorkspaceLoadState("error"); }
      } finally { if (!cancelled) setBusy(null); }
    }
    void openLastProject();
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    function warnBeforeLeaving(event: BeforeUnloadEvent) {
      if (dirty || busy || saving || saveError) { event.preventDefault(); event.returnValue = ""; }
    }
    window.addEventListener("beforeunload", warnBeforeLeaving);
    return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
  }, [dirty, busy, saving, saveError]);

  async function run(label: string, action: () => Promise<void>, showProgress = false) {
    if (operation.current) return;
    operation.current = true;
    autosave.setEnabled(false);
    if (!showProgress) { setSteps([]); setOperationFailed(false); setOperationTiming(null); }
    setBusy(label); setError(null); setNotice(null);
    try { await autosave.idle(); await action(); } catch (caught) { setError(message(caught)); }
    finally { operation.current = false; setBusy(null); autosave.setEnabled(!library); }
  }
  const persist = (retry = false) => autosave.flush("autosave", retry);
  const currentRevision = () => autosave.getSnapshot().project!.revision;
  function action(kind: "analyze" | "plan" | "review", confirmedKey?: string) {
    if (kind === "plan" && confirmedKey !== decisionKey) return;
    const tourRequest = kind === "review" ? null : tour.begin(kind);
    const labels = { analyze: project?.analysis && !briefChanged ? "Đang đọc câu trả lời và tìm câu hỏi tiếp theo…" : "Đang tìm câu hỏi cần làm rõ…", plan: "Đang phát triển câu chuyện…",
      review: "Đang đọc và góp ý bản đã sửa…" };
    setOperationFailed(false);
    setOperationTiming({ kind, startedAt: performance.now(), finishedAt: null });
    setSteps([{ stage: "prepare", status: "active", occurrence: 1 }]);
    let questionDelta = 0;
    void run(labels[kind], async () => {
      try {
        const next = await persist();
        if (!next) throw new Error("Hãy mở dự án trước khi tiếp tục.");
        setSteps((items) => items.map((step) => step.stage === "prepare" ? { ...step, status: "completed" } : step));
        const result = await streamProjectOperation(next, kind, (event) => {
          setSteps((items) => applyProgress(items, event));
        }, progressLanguage(next.response_language));
        questionDelta = (result.analysis?.missing_information.length ?? 0) - (next.analysis?.missing_information.length ?? 0);
        accept(result);
        if (kind === "plan") {
          const generation = result.plan_generations?.at(-1);
          if (generation && generation.critic_status !== "reviewed") {
            tour.failed(tourRequest);
            setOperationFailed(true);
            setError(generation.applied_revision === null
              ? "Đã giữ bản đề xuất; chưa có góp ý hợp lệ. Bản đang viết vẫn được giữ. Bạn có thể xem và chọn nhận bản đề xuất rồi review riêng."
              : "Đã lưu bản nháp; chưa có góp ý hợp lệ. Bạn có thể đọc, tự sửa và nhận phản hồi trên bản hiện tại mà không tạo lại.");
            return;
          }
          if (generation?.applied_revision === null) {
            tour.failed(tourRequest);
            setNotice("Đã giữ bản đề xuất cùng góp ý riêng. Bản đang viết chỉ thay khi bạn chọn nhận.");
            return;
          }
        }
        if (kind !== "review") setPendingStage(kind === "analyze" ? "workspace-choices" : "workspace-draft");
        tour.succeeded(tourRequest, result.id);
      } catch (caught) {
        tour.failed(tourRequest);
        setOperationFailed(true);
        setSteps((items) => items.map((step) => step.status === "active" ? { ...step, status: "failed" } : step));
        throw caught;
      } finally {
        const finishedAt = performance.now();
        setOperationTiming((timing) => timing ? { ...timing, finishedAt } : timing);
      }
      setNotice(kind === "analyze" ? questionDelta > 0 ? `Có thêm ${questionDelta} câu hỏi. Các lựa chọn trước vẫn được giữ; chưa tạo bản phát triển.`
        : "Chưa có câu hỏi mới. Các lựa chọn vẫn được giữ; bạn có thể sửa hoặc xem lại để quyết định tạo bản phát triển."
        : kind === "plan" ? "Đã tạo và lưu bản phát triển. Bạn có thể sửa trực tiếp bên dưới."
          : "Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.");
    }, true);
  }
  function updateDraftField(field: DraftField, value: string) {
    setProject(current => {
      if (!current?.draft) return current;
      const draft = current.draft;
      return { ...current, draft: typeof field === "number"
        ? { ...draft, sections: draft.sections.map((section, index) => index === field ? { ...section, content: value } : section) }
        : { ...draft, [field]: value } };
    });
  }
  function chooseFeedback(finding: EvaluationFinding) {
    if (!selectableFeedback || !project?.feedback?.artifact_id) return;
    setSelectedCard(null);
    setSelectedFeedback({ projectId: project.id, artifactId: project.feedback.artifact_id,
      criterionId: finding.criterion_id, message: finding.message });
  }
  function chooseTarget(note: RevisionNote, targetId: string) {
    if (!selectableFeedback || !project?.feedback
      || !readRevisionNotes(project.feedback)?.includes(note)) return;
    const targets = validatedTargets(note, saved?.feedback_source, project.feedback.artifact_id);
    if (!targets?.some(target => target.target_id === targetId)) return;
    const target = targets.find(item => item.target_id === targetId)!;
    setSelectedFeedback(null);
    setSelectedCard(document.querySelector(`[data-card-id="${targetId}"]`) ? { id: targetId, label: target.label } : null);
    requestAnimationFrame(() => {
      const field = document.querySelector<HTMLElement>(`[data-revision-target="${targetId}"]`);
      revealWorkspaceTarget(field);
      field?.scrollIntoView({ block: "center" });
      const input = field?.querySelector<HTMLInputElement | HTMLTextAreaElement>("input, textarea");
      if (input) input.focus({ preventScroll: true });
      else field?.querySelector<HTMLButtonElement>(".story-edit-button")?.click();
    });
  }
  function downloadBackup() {
    if (!project) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(project, null, 2)],
      { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = `firstframe-${project.id}.json`; link.click();
    URL.revokeObjectURL(url);
  }

  const proposals = project && <>
        {!!project.plan_generations?.length && <section className="panel version-history" aria-label="Các bản do AI tạo">
          <h2>Các bản do AI tạo</h2>
          <p>Bản đầu được lưu trực tiếp. Các lần tạo lại giữ thành đề xuất; bản đang viết chỉ thay khi bạn chọn nhận.
            Mở xem không lưu hoặc gọi AI. Lưu hoặc tải bản sao các sửa đang có trước khi mở lại dự án.</p>
          {[...project.plan_generations].reverse().map(generation => <details key={generation.id}>
            <summary>{generation.draft.title} · {generation.applied_revision === null ? "Bản đề xuất" : "Đã dùng làm bản nháp"}
              {generation.critic_status !== "reviewed" || !generation.feedback_source ? " · Chưa có góp ý hợp lệ" : " · Có góp ý riêng"}</summary>
            <p className="storage-note preserve-lines">Lượt tạo {generation.id} · nguồn revision {generation.source_revision}.
              {generation.applied_revision !== null && ` Đã nhận tại revision ${generation.applied_revision}. Bản đang viết có thể đã được sửa hoặc review sau đó.`}</p>
            {(generation.critic_status !== "reviewed" || !generation.feedback_source) && <p className="form-message">
              Bản phác thảo đã được giữ; lượt tạo này chưa có góp ý hợp lệ. Bạn có thể dùng bản này,
              tự sửa và nhận phản hồi riêng mà không cần tạo lại.</p>}
            <details className="feedback-context">
              <summary>Ý đồ khi tạo bản này</summary>
              <IntentDetails context={generation.context} />
            </details>
            <p className="preserve-lines">{generation.draft.logline}</p>
            {generation.draft.sections.map((section, i) => <div key={i}>
              <h3>{sectionLabels[section.title] ?? section.title}</h3>
              <p className="preserve-lines">{section.content}</p>
            </div>)}
            {generation.feedback && generation.feedback_source && <>
              <FeedbackIntent source={generation.feedback_source} projectId={project.id} artifactId={generation.feedback.artifact_id} />
              <StoryFeedback evaluation={generation.feedback} uiLanguage="vi" source={generation.feedback_source} />
            </>}
            {generation.applied_revision === null && <>
              {!project.applicable_plan_ids?.includes(generation.id) && <p className="form-message">
                Nguồn hoặc bản đang viết đã thay đổi; đề xuất này chỉ để tham khảo.</p>}
              {dirty && <p className="form-message">Có sửa chưa lưu. Chưa thể nhận đề xuất để bảo vệ bản đang viết.</p>}
              <button disabled={!!busy || dirty || !project.applicable_plan_ids?.includes(generation.id)} onClick={() =>
                void run("Đang giữ lịch sử và nhận bản đề xuất…", async () => {
                  accept(await projectRequest(`/${project.id}/plans/${generation.id}/accept`, "POST", { revision: currentRevision() }));
                  setSelectedFeedback(null);
                  setNotice("Đã nhận bản đề xuất. Bản trước được giữ trong lịch sử; có thể sửa và nhận phản hồi riêng.");
                })}>Dùng bản đề xuất này</button>
            </>}
          </details>)}
        </section>}
  </>;

  const projectToolbar = (
      <nav className="project-toolbar panel" aria-label="Dự án">
        <label htmlFor="project-picker">Dự án của bạn</label>
        <select id="project-picker" value={project?.id ?? ""} disabled={!!busy}
          onChange={(event) => {
            const id = event.target.value;
            tour.pause();
            void run("Đang lưu và mở dự án…", async () => {
              await persist(); accept(await projectRequest(`/${id}`));
            });
          }}>
          <option value="" disabled>Chọn dự án</option>
          {projects.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
        {!library && <button data-tour="new-project" disabled={!!busy} onClick={() => {
          const ticket = tour.begin("create");
          void run("Đang tạo dự án…", async () => {
            try {
              await persist();
              const created = await projectRequest("", "POST");
              accept(created); tour.succeeded(ticket, created.id);
            } catch (caught) { tour.failed(ticket); throw caught; }
          });
        }}>Dự án mới</button>}
        <p className="storage-note">Dự án được lưu cục bộ trên máy này. Chưa có đồng bộ tài khoản.</p>
      </nav>
  );

  return (
    <main className={`page-shell story-workspace${library ? " library-workspace" : ""}`} data-desktop-stage="workspace-idea"
      onCompositionStartCapture={() => autosave.setComposing(true)} onCompositionEndCapture={() => autosave.setComposing(false)}><div className="workspace">
      <header className="intro">
        <p className="eyebrow">Câu chuyện của bạn. Kịch bản đầu tiên của bạn.</p>
        <h1 id="workspace-title" tabIndex={-1}>FirstFrame</h1>
        <p className="workspace-mode-label">{library ? "Bản đã lưu" : "Không gian viết"}</p>
        <a className="workspace-page-link" href={library ? "/" : "/library"} onClick={event => {
          event.preventDefault();
          if (busy) return;
          void run("Đang mở trang…", async () => {
            const next = await persist();
            router.push(`${library ? "/" : "/library"}${next ? `?project=${encodeURIComponent(next.id)}` : ""}`);
          });
        }}>{library ? "← Quay lại viết" : "Bản đã lưu"}</a>
        <p className="tagline">Một khoảnh khắc nhỏ cũng đủ để bắt đầu.</p>
        <p className="summary">Ghi lại điều bạn thấy, nghe hoặc nhớ. Cùng làm rõ điều muốn kể,
          đọc bản phác thảo câu chuyện rồi tự sửa theo ý bạn.</p>
        <details className="workspace-tools">
          <summary>Demo và công cụ đánh giá</summary>
          <a className="demo-entry secondary" href="/demo">Xem demo local từ kịch bản có sẵn</a>{" "}
          <a className="demo-entry secondary" href="/datasets">Đánh giá chất lượng dataset</a>
        </details>
        {library && projectToolbar}
      </header>
      <div className="workspace-layout">
      {!library && <WorkspaceNavigation project={project} briefChanged={briefChanged} analyzing={!!busy && operationTiming?.kind === "analyze"} creatingPlan={!!busy && operationTiming?.kind === "plan"}
        tourStep={tour.state.record?.status === "active" && !busy ? tour.state.record.stepId : undefined} />}
      <div className="workspace-content">
      {!library && <OnboardingTour tour={tour} context={tourContext} ready={workspaceLoadState === "ready"}
        empty={projectsListed && !projects.length} busy={!!busy} error={error}
        idea={project?.idea ?? ""} answers={project?.answers ?? []}
        questionCount={project?.analysis?.missing_information.length ?? 0} />}
      {!library && projectToolbar}
      {busy && !steps.length && <p className="operation-status" role="status">{busy}</p>}
      {!project && error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="operation-status" role="status">{notice}</p>}
      {!project && !busy && <section className="panel empty-project">
        <h2>Ghi lại khoảnh khắc của bạn</h2>
        <p>Chọn “Dự án mới”, kể một khoảnh khắc bạn nhớ rồi lưu để quay lại viết tiếp.
          Chưa cần biết toàn bộ câu chuyện sẽ đi tới đâu.</p>
        {error && <button onClick={() => window.location.reload()}>Thử kết nối lại</button>}
      </section>}
      {project && <>
        {!library && <div className="save-toolbar" data-tour="save" tabIndex={-1}>
          <span className="save-project-title">{project.title}</span>
          <p id="save-status" role="status" tabIndex={-1}>{saving ? "Đang lưu…" : saveError ? "Chưa lưu được · Bản đang sửa vẫn được giữ" : dirty ? "Có thay đổi · Sẽ tự lưu" : "Đã lưu"}</p>
          {saveError && <button disabled={!!busy || saving} onClick={() => void run("Đang đối chiếu kết quả lưu…", async () => {
            await persist(true); setNotice("Đã lưu thay đổi."); document.getElementById("save-status")?.focus();
          })}>Thử lưu lại</button>}
          <details className="save-more"><summary>Tùy chọn bản lưu</summary><div>
          <button data-tour-action="save" disabled={!!busy || saving || !dirty} onClick={() => void run("Đang lưu…", async () => {
            await persist(true); setNotice("Đã lưu thay đổi.");
          })}>Lưu thay đổi</button>
          <button className="secondary" onClick={downloadBackup}>Tải bản sao JSON</button>
          <button className="secondary" disabled={!!busy || saving} onClick={() => {
            if ((dirty || saveError) && !window.confirm("Mở lại sẽ bỏ phần chưa xác nhận lưu trên màn hình. Hãy tải bản sao JSON trước nếu cần giữ. Bạn muốn mở lại bản trên máy chủ?")) return;
            tour.pause();
            void run("Đang mở lại bản đã lưu…", async () => {
              accept(await projectRequest(`/${project.id}`));
              setNotice("Đã mở lại bản đã lưu. Không tạo lại hoặc gọi AI.");
            });
          }}>Mở lại bản đã lưu</button>
          </div></details>
          {(error || saveError) && <p className="error" role="alert">{error || saveError}</p>}
        </div>}
        {library && error && <p className="error" role="alert">{error}</p>}
      {!!steps.length && operationTiming && <div data-progress-stage={`workspace-${operationTiming.kind === "analyze" ? "choices" : ["plan", "review"].includes(operationTiming.kind) ? "draft" : operationTiming.kind.startsWith("scene-") ? "outline" : "script"}`}>
        <OperationProgress steps={steps} failed={operationFailed}
          timing={operationTiming} dirty={dirty} language={progressLanguage(project?.response_language ?? "auto")} />
      </div>}
        {!library && <fieldset disabled={!!busy} className="project-fields">
          <WorkspaceStage key={`${project.id}:idea`} id="workspace-idea" tourStep="idea" title="1. Khoảnh khắc bạn muốn kể"
            complete={!!project.analysis && !briefChanged} preview={project.idea || "Bắt đầu bằng một khoảnh khắc nhỏ."}>
            <label htmlFor="project-title">Tên dự án</label>
            <input id="project-title" maxLength={200} value={project.title}
              onChange={(event) => setProject({ ...project, title: event.target.value })} />
            <label htmlFor="response-language">Ngôn ngữ đầu ra</label>
            <select id="response-language" data-tour="language" value={project.response_language} onChange={(event) =>
              setProject({ ...project, response_language: event.target.value as ResponseLanguage })}>
              {Object.entries(responseLanguageLabels).map(([value, label]) =>
                <option key={value} value={value}>{label}</option>)}
            </select>
            <details>
              <summary>Về ngôn ngữ đầu ra</summary>
              <p className="storage-note">Hỗ trợ tiếng Việt và tiếng Anh. Với ý tưởng quá ngắn,
                không dấu hoặc chưa rõ ngôn ngữ, hãy chọn ngôn ngữ đầu ra.
                Lựa chọn áp dụng cho lần làm rõ, phát triển hoặc góp ý tiếp theo;
                không tự dịch bản đang viết hay gọi AI.</p>
            </details>
            <label htmlFor="idea">Khoảnh khắc, kỷ niệm hoặc tình huống của bạn</label>
            <p className="storage-note" id="idea-help">Một cử chỉ, âm thanh hay chuyện vui/khó xử đều có thể bắt đầu câu chuyện.
              Chưa cần có cốt truyện hoặc biết cách viết kịch bản.</p>
            <textarea id="idea" maxLength={5000} value={project.idea} rows={5}
              aria-describedby="idea-help"
              placeholder="Ví dụ: Tôi về muộn. Mẹ để phần cơm trên bàn, chỉ hỏi có cần hâm lại không. Tôi nhớ tiếng chiếc quạt quay trong lúc hai mẹ con ngồi ăn."
              onChange={(event) => setProject({ ...project, idea: event.target.value })} />
            <label htmlFor="constraints">Điều bạn muốn giữ hoặc giới hạn thực hiện (tùy chọn)</label>
            <textarea id="constraints" className="short-textarea" rows={3}
              value={project.constraints.join("\n")}
              placeholder="Mỗi dòng một ý, ví dụ: giữ sự lặng lẽ; chưa cần kết thúc rõ; chỉ hai nhân vật."
              onChange={(event) => setProject({ ...project, constraints: event.target.value.split("\n") })} />
            {briefChanged && (project.analysis || project.draft) && <p className="form-message">Ý tưởng đã thay đổi. Làm rõ lại trước khi tạo
              bản phát triển mới; bản thảo và câu trả lời trước đó sẽ được giữ trong lịch sử.</p>}
            {(!project.analysis || briefChanged) && <button data-tour-action="analyze" disabled={!project.idea.trim()}
              onClick={() => action("analyze")}>Cùng làm rõ ý tưởng</button>}
          </WorkspaceStage>
          {saved && <details className="workspace-author-context">
            <summary>Ý đồ và lựa chọn đã lưu <span>{dirty ? "Có thay đổi chưa lưu" : "Bản đã lưu"}</span></summary>
            <AuthorIntentCard context={saved.author_context} revision={saved.revision} dirty={dirty} canEditAnswers={!briefChanged} />
          </details>}
          {project.analysis && !briefChanged && <WorkspaceStage key={`${project.id}:choices:${project.analysis.artifact_id}`}
            id="workspace-choices" tourStep="choices" title="2. Những lựa chọn của bạn" complete={!!project.draft}
            preview={`${project.analysis.missing_information.filter((_, i) => project.answers[i]?.trim()).length}/${project.analysis.missing_information.length} câu đã trả lời · Mở để xem hoặc sửa`}>
            <div>
            <ClarificationConversation key={`${project.id}:${project.analysis.artifact_id}`}
              summary={project.analysis.summary} questions={project.analysis.missing_information} answers={project.answers}
              thinking={!!busy && operationTiming?.kind === "analyze"} confirmationKey={decisionKey} idea={project.idea} constraints={project.constraints} hasDraft={!!project.draft}
              retained={saved?.author_context?.clarifications.filter(item => item.input_index === null) ?? []}
              onAskMore={() => action("analyze")} onConfirm={() => action("plan", decisionKey)}
              onChange={(index, value) => setProject(current => {
                if (!current) return current;
                const answers = Array.from({ length: Math.max(current.answers.length, index + 1) },
                  (_, i) => i === index ? value : current.answers[i] ?? "");
                return { ...current, answers };
              })} />
            </div>
          </WorkspaceStage>}
          {project.draft && <section className="panel form-stack working-draft" data-workspace-stage="workspace-draft">
            <h2 id="workspace-draft" data-tour="draft" tabIndex={-1}>3. Bản phát triển đang làm việc</h2>
            <h3 id="draft-editor-title" tabIndex={-1}>Đọc và sửa ngay tại card</h3>
            {operationTiming?.kind === "plan" && operationTiming.finishedAt !== null && <a className="storage-note" href="#workspace-operation">Xem lại tiến trình tạo bản này</a>}
            {selectedFeedback && !selectedCard && <aside className="revision-note" aria-labelledby="selected-feedback-title">
              <h4 id="selected-feedback-title" tabIndex={-1}>Góp ý bạn đang cân nhắc</h4>
              <p>{feedbackGuidance.vi}</p>
              <p className={currentFeedback ? "operation-status" : "form-message"} role="status">
                {currentFeedback ? "Góp ý đọc bản hiện tại. Bạn tự chọn phần muốn sửa bên dưới."
                  : "Góp ý này thuộc bản trước. Giữ làm tham khảo; chưa có đánh giá cho nội dung đang sửa."}</p>
              <p className="preserve-lines">{selectedFeedback.message}</p>
              <FeedbackIntent source={saved?.feedback_source} projectId={selectedFeedback.projectId} artifactId={selectedFeedback.artifactId} />
              <p>Sửa trực tiếp theo ý bạn, rồi lưu và nhận phản hồi trên bản mới.
                Khi đọc lại, hãy tự giải thích vì sao bạn sửa hoặc giữ cách kể của mình.</p>
              <button type="button" className="secondary" onClick={() => {
                setSelectedFeedback(null);
                document.getElementById("draft-editor-title")?.focus();
              }}>Bỏ chọn góp ý này</button>
            </aside>}
            <StoryPlanEditor key={`${project.id}:${draftEditorRevision}`} draft={project.draft}
              dirty={dirty} onChange={updateDraftField} selectedCardId={selectedCard?.id} onSelectCard={card => {
                const previous = selectedCard?.id;
                setSelectedCard(card);
                if (!card && previous) requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(`[data-card-id="${previous}"] .card-feedback-trigger`)?.focus({preventScroll: true}));
              }}
              inspector={selectedCard && <CardFeedback cardId={selectedCard.id} label={selectedCard.label}
                evaluation={project.feedback} source={saved?.feedback_source?.project_id === project.id
                  && saved.feedback_source.artifact_id === project.feedback?.artifact_id ? saved.feedback_source : null}
                current={!!currentFeedback} selected={selectedFeedback ? { message: selectedFeedback.message } : null}
                onClose={() => {
                  const id = selectedCard.id; setSelectedCard(null); setSelectedFeedback(null);
                  requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(`[data-card-id="${id}"] .card-feedback-trigger`)?.focus());
                }} onReview={() => action("review")} />} />
            {!selectedCard && <button data-tour-review onClick={() => action("review")}>Nhận phản hồi trên bản hiện tại</button>}
        {project.feedback && <details id="workspace-feedback" tabIndex={-1} className="feedback-section" aria-label="Phản hồi"><summary>Toàn bộ góp ý</summary>
          <p className={currentFeedback ? "operation-status" : "form-message"} role="status">
            {currentFeedback ? "Phản hồi cho đúng bản hiện tại."
              : "Nội dung đã thay đổi. Phản hồi dưới đây thuộc bản trước; hãy nhận phản hồi mới."}
          </p>
          <FeedbackIntent source={saved?.feedback_source} projectId={project.id} artifactId={project.feedback.artifact_id} />
          {!selectableFeedback && !busy && <p className="storage-note">Góp ý cũ hoặc chưa có đủ nguồn chỉ để tham khảo.
            Hãy nhận phản hồi cho đúng bản hiện tại trước khi chọn góp ý mới để tự sửa.</p>}
          <StoryFeedback evaluation={project.feedback} uiLanguage="vi" onChoose={chooseFeedback}
            onTarget={chooseTarget} source={saved?.feedback_source?.project_id === project.id ? saved.feedback_source : null}
            selectedCriterion={selectedFeedback?.criterionId} selectionDisabled={!selectableFeedback} />
        </details>}

          </section>}
          {saved && <SceneOutlineEditor key={project.id} project={project} saved={saved} dirty={dirty} error={error || saveError}
            onSketch={input => {
              setSteps([{stage:"prepare",status:"active",occurrence:1}]);setOperationFailed(false);
              setOperationTiming({kind:"scene-sketches",startedAt:performance.now(),finishedAt:null});
              return run("Đang phác một cảnh trên máy…",async()=>{
                try {
                  const next=await persist();if(!next)return;
                  setSteps(items=>applyProgress(items,{stage:"prepare",status:"completed"}));
                  accept(await streamProjectOperation(next,"scene-sketches",event=>setSteps(items=>applyProgress(items,event)),progressLanguage(next.response_language),input));
                  setNotice("Đã giữ ảnh xem trước riêng; chưa thay ảnh đã chọn. Hãy đối chiếu nguồn rồi chọn giữ hoặc bỏ.");
                } catch(caught){setOperationFailed(true);throw caught;}
                finally{setOperationTiming(t=>t?{...t,finishedAt:performance.now()}:t);}
              },true);
            }}
            onSketchDecision={(id,decision)=>void run("Đang lưu lựa chọn hình phác…",async()=>{
              const next=await projectRequest(`/${project.id}/scene-sketches/${id}/${decision}`,"POST",{revision:currentRevision()});
              setSaved(next);setProject(current=>current?{...current,revision:next.revision,scene_sketches:next.scene_sketches,
                selected_scene_sketches:next.selected_scene_sketches,applicable_sketch_ids:next.applicable_sketch_ids}:current);
            })}
            sourceCurrent={!feedbackChanged && !!project.scene_source_is_current}
            canUseProposal={!feedbackChanged && !project.pending_scene_proposal_id && !project.pending_staging_use && JSON.stringify(project.scene_outline) === JSON.stringify(saved.scene_outline)}
            onPreviewChange={(id: string, scenes: Scene[]) => setProject(current => current ? { ...current,
              pending_scene_previews: { ...current.pending_scene_previews, [id]: scenes } } : current)}
            onStagingEdit={(id, value) => setProject(current => current ? { ...current,
              pending_staging_edits: { ...current.pending_staging_edits, [id]: value } } : current)}
            onDiscardIdea={(proposalId, ideaId) => void run("Đang bỏ ý góp ý…", async () => {
              const next = await projectRequest(`/${project.id}/scene-proposals/${proposalId}/ideas/${ideaId}/discard`, "POST", { revision: currentRevision() });
              setSaved(next); setProject(current => {
                if (!current) return current;
                const edits = { ...current.pending_staging_edits }; delete edits[ideaId];
                return { ...current, revision: next.revision, scene_proposals: next.scene_proposals, staging_proposals: next.staging_proposals,
                  applicable_scene_proposal_ids: next.applicable_scene_proposal_ids, pending_staging_edits: edits };
              });
            })}
            onChange={(outline, proposalId, stagingUse) => setProject(current => {
              if (!current) return current;
              const use = stagingUse === undefined ? current.pending_staging_use : stagingUse ?? undefined;
              const owner = use && current.staging_proposals?.find(p => p.id === use.proposal_id);
              const idea = owner?.staging_ideas?.find(i => i.id === use?.idea_id);
              const value = idea && outline.scenes.find(s => s.id === owner?.target_scene_id)?.staging_choices[idea.field];
              return { ...current, scene_outline: outline,
                ...(proposalId !== undefined ? { pending_scene_proposal_id: proposalId ?? undefined } : {}),
                pending_staging_use: use ? { ...use, value: value ?? use.value } : undefined };
            })}
            onSuggest={(input: SceneSuggestionInput) => {
              setSteps([{ stage: "prepare", status: "active", occurrence: 1 }]); setOperationFailed(false);
              setOperationTiming({ kind: "scene-suggestions", startedAt: performance.now(), finishedAt: null });
              return run("Đang gợi ý cảnh từ nguồn đã chọn…", async () => {
                try {
                  const next = await persist(); if (!next) return;
                  setSteps(items => applyProgress(items, { stage: "prepare", status: "completed" }));
                  const result = await streamProjectOperation(next, "scene-suggestions",
                    event => setSteps(items => applyProgress(items, event)), progressLanguage(next.response_language), input);
                  accept(result); setNotice("Đã giữ đề xuất riêng. Hãy đọc, tự chỉnh rồi chọn dùng; cảnh đang viết chưa đổi.");
                } catch (caught) {
                  setOperationFailed(true); setSteps(items => items.map(s => s.status === "active" ? { ...s, status: "failed" } : s));
                  throw caught;
                } finally { setOperationTiming(t => t ? { ...t, finishedAt: performance.now() } : t); }
              }, true);
            }}
            onInspect={async()=>{let checked=false;await run("Đang kiểm tra đề xuất đã lưu…",async()=>{
              await inspectProject(false);checked=true;
            });return checked;}}
            onDiscard={proposalId => void run("Đang bỏ đề xuất cảnh…", async () => {
              const next = await persist(); if (!next) return;
              accept(await projectRequest(`/${next.id}/scene-proposals/${proposalId}/discard`, "POST", { revision: next.revision }));
            })}
            onStart={versionId => void run("Đang giữ nguồn và mở dàn cảnh…", async () => {
              const next = await persist(); if (!next) return;
              accept(await projectRequest(`/${next.id}/scene-outline`, "POST", {
                revision: next.revision, source_version_id: versionId,
              })); setNotice("Đã giữ nguồn story plan. Bạn có thể tự thêm cảnh; không gọi AI.");
            })}
            onSave={() => void run("Đang lưu dàn cảnh…", async () => {
              await persist(); setNotice("Đã lưu thay đổi dàn cảnh và mọi sửa đang chờ trong dự án.");
            })}
            onPrepare={() => void run("Đang lưu bản nguồn viết tiếp…", async () => {
              const next = await persist();
              if (!next?.scene_handoff) throw new Error("Cần tên và diễn tiến cho từng cảnh trước khi chuẩn bị bản viết tiếp.");
              setNotice(`Đã lưu bản dàn cảnh phiên bản ${next.scene_handoff.version}. Có thể bắt đầu soạn thủ công tại phần Kịch bản; chưa tự tạo nội dung kịch bản.`);
              const target=document.getElementById("workspace-script");revealWorkspaceTarget(target);target?.scrollIntoView({block:"start"});target?.focus({preventScroll:true});
            })} />}
          {saved && <ScreenplayEditor key={`script:${project.id}`} project={project} savedProject={saved} dirty={dirty}
            onSelectSource={input=>run("Đang giữ bản đã lưu làm nguồn xuất kịch bản…",async()=>{
              const source=await persist();if(!source)return;
              const next=await projectRequest(`/${source.id}/screenplay-selections`,"POST",{revision:source.revision,...input});
              setSaved(next);setProject(current=>current?{...current,revision:next.revision,screenplay_selections:next.screenplay_selections,screenplay_handoff:next.screenplay_handoff}:current);
              setNotice("Đã lưu thay đổi và giữ bản nguồn để xuất kịch bản; chưa xuất bản.");
            })}
            onSourceInspect={async()=>{let checked=false;await run("Đang kiểm tra nguồn xuất kịch bản đã lưu…",async()=>{
              await inspectProject(true);checked=true;
            });return checked;}}
            sourceDirty={feedbackChanged || JSON.stringify(project.scene_outline)!==JSON.stringify(saved.scene_outline)}
            onChange={(screenplay,proposalId)=>setProject(current=>current?{...current,screenplay,pending_screenplay_proposal_id:proposalId}:current)}
            canUse={!feedbackChanged&&!project.pending_screenplay_proposal_id&&!project.pending_scene_proposal_id&&!project.pending_staging_use
              &&JSON.stringify(project.screenplay)===JSON.stringify(saved.screenplay)&&JSON.stringify(project.scene_outline)===JSON.stringify(saved.scene_outline)}
            onPreview={(id,scene)=>setProject(current=>current?{...current,pending_screenplay_previews:{...current.pending_screenplay_previews,[id]:scene}}:current)}
            canNavigateReview={!feedbackChanged&&JSON.stringify(project.screenplay)===JSON.stringify(saved.screenplay)&&JSON.stringify(project.scene_outline)===JSON.stringify(saved.scene_outline)}
            onReview={input=>{
              setSteps([{stage:"prepare",status:"active",occurrence:1}]);setOperationFailed(false);
              setOperationTiming({kind:"screenplay-reviews",startedAt:performance.now(),finishedAt:null});
              return run("Đang đọc cảnh đã lưu để góp ý…",async()=>{
                try{const next=await persist();if(!next)return;
                  setSteps(items=>applyProgress(items,{stage:"prepare",status:"completed"}));
                  accept(await streamProjectOperation(next,"screenplay-reviews",event=>setSteps(items=>applyProgress(items,event)),progressLanguage(next.response_language),input));
                  setNotice("Đã lưu góp ý riêng. Trích dẫn khớp nguồn không xác nhận nhận xét đúng; bạn tự cân nhắc và sửa.");
                }catch(caught){setOperationFailed(true);throw caught;}
                finally{setOperationTiming(t=>t?{...t,finishedAt:performance.now()}:t);}
              },true);
            }}
            onReviewInspect={async()=>{let checked=false;await run("Đang kiểm tra góp ý đã lưu…",async()=>{
              await inspectProject(false);checked=true;
            });return checked;}}
            onReviewDiscard={id=>void run("Đang lưu và bỏ lượt góp ý…",async()=>{
              const next=await persist();if(!next)return;
              accept(await projectRequest(`/${next.id}/screenplay-reviews/${id}/discard`,"POST",{revision:next.revision}));
            })}
            onReviewAssess={(reviewId,noteId,assessment)=>void run("Đang lưu ghi nhận về góp ý…",async()=>{
              const next=await projectRequest(`/${project.id}/screenplay-reviews/${reviewId}/notes/${noteId}/assessment`,"POST",{revision:currentRevision(),assessment});
              setSaved(next);setProject(current=>current?{...current,revision:next.revision,screenplay_reviews:next.screenplay_reviews,current_screenplay_review_ids:next.current_screenplay_review_ids}:current);
              setNotice("Đã lưu ghi nhận về góp ý; không sửa hoặc tự lưu kịch bản đang viết.");
            })}
            onWrite={input=>{
              setSteps([{stage:"prepare",status:"active",occurrence:1}]);setOperationFailed(false);
              setOperationTiming({kind:"screenplay-proposals",startedAt:performance.now(),finishedAt:null});
              return run("Đang viết thử một cảnh…",async()=>{
                try{const next=await persist();if(!next)return;
                  setSteps(items=>applyProgress(items,{stage:"prepare",status:"completed"}));
                  accept(await streamProjectOperation(next,"screenplay-proposals",event=>setSteps(items=>applyProgress(items,event)),progressLanguage(next.response_language),input));
                  setNotice("Đã giữ phương án riêng; bản tác giả chưa thay. Đọc, chỉnh rồi tự chọn dùng hoặc bỏ.");
                }catch(caught){setOperationFailed(true);throw caught;}
                finally{setOperationTiming(t=>t?{...t,finishedAt:performance.now()}:t);}
              },true);
            }}
            onProposalInspect={async()=>{let checked=false;await run("Đang kiểm tra phương án đã lưu…",async()=>{
              await inspectProject(false);checked=true;
            });return checked;}}
            onDiscard={id=>void run("Đang lưu và bỏ phương án…",async()=>{
              const next=await persist();if(!next)return;
              accept(await projectRequest(`/${next.id}/screenplay-proposals/${id}/discard`,"POST",{revision:next.revision}));
            })}
            onSave={()=>void run("Đang lưu kịch bản…",async()=>{await persist();setNotice("Đã lưu kịch bản và mọi sửa đang chờ.");})}
            onStart={request_id=>run("Đang giữ nguồn dàn cảnh cho kịch bản…",async()=>{
              const next=await persist();if(!next)return;
              accept(await projectRequest(`/${next.id}/screenplay`,"POST",{revision:next.revision,request_id}));
              setNotice("Đã giữ nguồn và khung cảnh kịch bản. Chưa tạo nội dung hoặc gọi AI.");
            })}
            onInspect={async()=>{let checked=false;await run("Đang kiểm tra kịch bản đã lưu…",async()=>{
              await inspectProject(false);checked=true;
            });return checked;}}
          />}
        </fieldset>}
        {library && <SavedLibrary key={project.id} project={saved ?? project} busy={!!busy}
          onRestoreScreenplay={id => run("Đang khôi phục kịch bản…", async () => {
            const next = await persist(); if (!next) return;
            accept(await projectRequest(`/${next.id}/screenplay-versions/${id}/restore`, "POST", {revision: next.revision}));
          })}
          outline={<>
            <section className="panel"><h3>Dàn cảnh đang lưu</h3>
              {project.scene_outline ? <SavedOutline outline={project.scene_outline} /> : <p>Chưa có dàn cảnh đã lưu.</p>}
            </section>
        <SceneHistory project={project} onRestore={id => void run("Đang khôi phục dàn cảnh…", async () => {
          const next = await persist(); if (!next) return;
          accept(await projectRequest(`/${next.id}/scene-versions/${id}/restore`, "POST", {revision: next.revision}));
        })} />
          </>}
          storyPlan={<>
            <section className="panel"><h3>Story plan đang lưu</h3>
              {project.draft ? <><h4>{project.draft.title}</h4><p className="preserve-lines">{project.draft.logline}</p>
                {project.draft.sections.map((section, i) => <div key={i}><h4>{sectionLabels[section.title] ?? section.title}</h4><p className="preserve-lines">{section.content}</p></div>)}
              </> : <p>Chưa có Story plan đã lưu.</p>}
            </section>
        {proposals}
        {!!project.clarification_history.length && <section className="panel version-history">
          <h2>Các lựa chọn trước đây</h2>
          <p>Bạn có thể tham khảo và chép lại câu trả lời phù hợp. Các lựa chọn này không tự áp dụng cho ý tưởng mới.</p>
          {[...project.clarification_history].reverse().map((version) => <details key={version.id}>
            <summary>{new Date(version.created_at).toLocaleString("vi-VN")} · {version.idea}</summary>
            <PastAnswers questions={version.questions} answers={version.answers} />
          </details>)}
        </section>}
        {!!project.versions.length && <section className="panel version-history">
          <h2>Các phiên bản đã giữ</h2>
          <p>Khôi phục chỉ thay bản phát triển; ý tưởng và câu trả lời hiện tại được giữ.
            Nhận phản hồi mới sau khi khôi phục.</p>
          {[...project.versions].reverse().map((version, index) => <details key={version.id}>
            <summary>Bản {project.versions.length - index} · {new Date(version.created_at).toLocaleString("vi-VN")}
              {version.feedback ? " · Có phản hồi" : " · Bản lưu trước khi tạo lại"}</summary>
            <p className="preserve-lines">{version.draft.title}{"\n"}{version.draft.logline}</p>
            <p className="preserve-lines">Ý tưởng của bản này: {version.idea}</p>
            <p>Ngôn ngữ đầu ra: {responseLanguageLabels[version.response_language ?? "auto"]}</p>
            <PastAnswers questions={version.questions} answers={version.answers} />
            {version.draft.sections.map((section, i) => <div key={i}>
              <h3>{sectionLabels[section.title] ?? section.title}</h3>
              <p className="preserve-lines">{section.content}</p>
            </div>)}
            {version.feedback && <>
              <FeedbackIntent source={version.feedback_source} projectId={project.id} artifactId={version.feedback.artifact_id} />
              <StoryFeedback evaluation={version.feedback} uiLanguage="vi" source={version.feedback_source} />
            </>}
            <button disabled={!!busy} onClick={() => void run("Đang giữ bản hiện tại và khôi phục…", async () => {
              const next = await persist();
              if (!next) return;
              accept(await projectRequest(`/${next.id}`, "PUT", {
                ...editableProject(next), draft: version.draft, restore_draft_id: version.id,
              }));
              setSelectedFeedback(null);
              setNotice("Đã dùng lại nội dung bản phát triển. Các phiên bản trước vẫn được giữ.");
            })}>Dùng lại bản phát triển này</button>
          </details>)}
        </section>}
          </>}
        />}
      </>}
    </div></div></div></main>
  );
}

function WorkspaceNavigation({ project, briefChanged, creatingPlan, analyzing, tourStep }: { project: Project | null; briefChanged: boolean; creatingPlan: boolean; analyzing: boolean; tourStep?: TourStep }) {
  const [active, setActive] = useState("workspace-idea");
  const [desktop, setDesktop] = useState(false);
  useEffect(() => {
    let frame = 0;
    const stages = [...document.querySelectorAll<HTMLElement>("[data-workspace-stage]")];
    const workspace = document.querySelector<HTMLElement>("[data-desktop-stage]");
    const selected = (event: Event) => setActive((event as CustomEvent<string>).detail);
    workspace?.addEventListener("workspace-stage-change", selected);
    const measure = () => {
      setDesktop(window.innerWidth > 760);
      if (window.innerWidth > 760) {
        setActive(workspace?.dataset.desktopStage ?? "workspace-idea");
        return;
      }
      const line = window.innerWidth <= 760 ? 190 : 130;
      const focused = document.activeElement as HTMLElement | null;
      const bounds = focused?.getBoundingClientRect();
      // A short final draft cannot always scroll to the rail's tracking line.
      const focusedStage = bounds && bounds.bottom > line && bounds.top < window.innerHeight
        ? focused?.closest<HTMLElement>("[data-workspace-stage]") : null;
      const current = focusedStage ?? stages.filter(stage => stage.getBoundingClientRect().top <= line).at(-1) ?? stages[0];
      if (current) setActive(current.dataset.workspaceStage!);
    };
    const scroll = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(measure); };
    const focus = (event: FocusEvent) => {
      const stage = (event.target as HTMLElement)?.closest<HTMLElement>("[data-workspace-stage]");
      if (stage) setActive(stage.dataset.workspaceStage!);
    };
    const resize = new ResizeObserver(scroll); stages.forEach(stage => resize.observe(stage));
    window.addEventListener("scroll", scroll, { passive: true }); window.addEventListener("resize", scroll);
    document.addEventListener("focusin", focus); measure();
    return () => { workspace?.removeEventListener("workspace-stage-change", selected); cancelAnimationFrame(frame); resize.disconnect(); window.removeEventListener("scroll", scroll);
      window.removeEventListener("resize", scroll); document.removeEventListener("focusin", focus); };
  }, [project?.id, !!project?.analysis, !!project?.draft, briefChanged]);
  useEffect(() => {
    if (window.innerWidth > 760) revealWorkspaceTarget(document.getElementById("workspace-idea"));
  }, [project?.id]);
  useEffect(() => {
    if (window.innerWidth <= 760) return;
    if ((active === "workspace-choices" && !analyzing && (!project?.analysis || briefChanged))
      || (active === "workspace-draft" && !project?.draft && !creatingPlan)) {
      revealWorkspaceTarget(document.getElementById("workspace-idea"));
    }
  }, [active, !!project?.analysis, !!project?.draft, briefChanged, creatingPlan, analyzing]);
  const items = [
    { id: "workspace-idea", label: "Ý tưởng", available: !!project },
    { id: "workspace-choices", label: "Làm rõ", available: analyzing || (!!project?.analysis && !briefChanged) },
    { id: "workspace-draft", label: "Story plan", available: !!project?.draft || creatingPlan },
    { id: "workspace-outline", label: "Dàn cảnh", available: !!project },
    { id: "workspace-script", label: "Kịch bản", available: !!project },
  ];
  const currentStage = !desktop && creatingPlan ? "workspace-draft"
    : items.some(item => item.id === `workspace-${tourStep}`) ? `workspace-${tourStep}` : active;
  return <aside className="workspace-rail"><p className="eyebrow">Câu chuyện của bạn</p>
    <nav className="workspace-stage-nav" aria-label="Hành trình câu chuyện">
      {items.map((item, index) => <button key={item.id} type="button" disabled={!item.available}
        aria-controls={item.id} aria-current={item.available && item.id === currentStage ? "step" : undefined}
        onClick={() => {
          const target = document.getElementById((creatingPlan && item.id === "workspace-draft") || (analyzing && item.id === "workspace-choices") ? "workspace-operation" : item.id);
          revealWorkspaceTarget(target); setActive(item.id);
          target?.scrollIntoView({ block: "start" }); target?.focus({ preventScroll: true });
        }}>
        <span className="workspace-stage-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
        <span>{item.label}<small>{!item.available && index > 2 ? "Chưa hỗ trợ" : item.available ? (item.id === currentStage ? (creatingPlan && item.id === "workspace-draft" ? "Đang tạo" : "Đang làm việc") : "Xem lại") : "Chưa có nội dung"}</small></span>
      </button>)}
    </nav>
    <p className="workspace-rail-note">Câu chuyện và lựa chọn của bạn làm chủ đạo.<br />Các bước sau mở khi sản phẩm hỗ trợ.</p>
  </aside>;
}

function message(error: unknown) {
  return error instanceof Error ? error.message : "Có lỗi xảy ra. Hãy thử lại.";
}

function PastAnswers({ questions, answers }: { questions: string[]; answers: string[] }) {
  return <dl>{questions.map((question, index) => <div key={index}>
    <dt>{question}</dt>
    <dd className="preserve-lines">{answers[index] || "Chưa trả lời"}</dd>
  </div>)}</dl>;
}
