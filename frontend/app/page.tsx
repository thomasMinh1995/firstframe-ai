"use client";

import { useEffect, useState } from "react";
import { StoryFeedback } from "./StoryResultCards";
import { StoryPlanReading } from "./StoryPlanReading";
import { AuthorIntentCard, FeedbackIntent } from "./AuthorIntentCard";
import { OperationProgress } from "./OperationProgress";
import { OnboardingTour, useOnboarding } from "./OnboardingTour";
import { applyProgress, progressLanguage, type OperationStep } from "./progressState";
import { sectionLabels } from "./storyLabels";
import { responseLanguageLabels, type ResponseLanguage } from "./language";
import type { EvaluationFinding } from "./apiClient";
import {
  editableProject, listProjects, projectRequest, streamProjectOperation,
  type Project, type ProjectSummary, type StoryDraft,
} from "./projectsApi";

export default function Home() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [saved, setSaved] = useState<Project | null>(null);
  const [busy, setBusy] = useState<string | null>("Đang mở dự án…");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedFeedback, setSelectedFeedback] = useState<{
    projectId: string; artifactId: string; criterionId: string; message: string;
  } | null>(null);
  const [workspaceLoadState, setWorkspaceLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [projectsListed, setProjectsListed] = useState(false);
  const [steps, setSteps] = useState<OperationStep[]>([]);
  const [operationFailed, setOperationFailed] = useState(false);
  const [operationTiming, setOperationTiming] = useState<{
    kind: "analyze" | "plan" | "review"; startedAt: number; finishedAt: number | null;
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
  const currentFeedback = project?.feedback_is_current && !feedbackChanged;
  const selectableFeedback = currentFeedback && !busy && !!project?.draft && !!project.feedback?.artifact_id
    && saved?.feedback_source?.project_id === project.id
    && saved.feedback_source.artifact_id === project.feedback.artifact_id;
  const tourContext = { projectId: project?.id ?? null, hasAnalysis: !!project?.analysis,
    hasDraft: !!project?.draft, briefChanged };
  const tour = useOnboarding(tourContext, !!busy, error);
  useEffect(() => { if (dirty) setNotice(null); }, [dirty]);
  useEffect(() => {
    if (!selectedFeedback) return;
    const frame = requestAnimationFrame(() => {
      const note = document.getElementById("selected-feedback-title");
      note?.scrollIntoView({ block: "center" });
      note?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [selectedFeedback]);

  function accept(next: Project) {
    setSelectedFeedback(current => current?.projectId === next.id
      && current.artifactId === next.feedback?.artifact_id ? current : null);
    setProject(next); setSaved(next);
    setWorkspaceLoadState("ready");
    setProjects((items) => [next, ...items.filter((item) => item.id !== next.id)]);
  }
  useEffect(() => {
    let cancelled = false;
    async function openLastProject() {
      try {
        const items = await listProjects();
        const last = items.length ? await projectRequest(`/${items[0].id}`) : null;
        if (!cancelled) {
          setProjects(items); setProject(last); setSaved(last);
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
      if (dirty || busy) { event.preventDefault(); event.returnValue = ""; }
    }
    window.addEventListener("beforeunload", warnBeforeLeaving);
    return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
  }, [dirty, busy]);

  async function run(label: string, action: () => Promise<void>, showProgress = false) {
    if (!showProgress) { setSteps([]); setOperationFailed(false); setOperationTiming(null); }
    setBusy(label); setError(null); setNotice(null);
    try { await action(); } catch (caught) { setError(message(caught)); }
    finally { setBusy(null); }
  }
  async function persist() {
    if (!project) return null;
    if (!dirty) return project;
    const next = await projectRequest(`/${project.id}`, "PUT", editableProject(project));
    accept(next);
    return next;
  }
  function action(kind: "analyze" | "plan" | "review") {
    const tourRequest = kind === "review" ? null : tour.begin(kind);
    const labels = { analyze: "Đang tìm câu hỏi cần làm rõ…", plan: "Đang phát triển câu chuyện…",
      review: "Đang đọc và góp ý bản đã sửa…" };
    setOperationFailed(false);
    setOperationTiming({ kind, startedAt: performance.now(), finishedAt: null });
    setSteps([{ stage: "prepare", status: "active", occurrence: 1 }]);
    void run(labels[kind], async () => {
      try {
        const next = await persist();
        if (!next) throw new Error("Hãy mở dự án trước khi tiếp tục.");
        setSteps((items) => items.map((step) => step.stage === "prepare" ? { ...step, status: "completed" } : step));
        const result = await streamProjectOperation(next, kind, (event) => {
          setSteps((items) => applyProgress(items, event));
        }, progressLanguage(next.response_language));
        accept(result);
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
      setNotice(kind === "analyze" ? "Hãy trả lời các câu hỏi trước khi tạo bản phát triển."
        : kind === "plan" ? "Đã tạo và lưu bản phát triển. Bạn có thể sửa trực tiếp bên dưới."
          : "Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.");
    }, true);
  }
  function updateDraft(next: StoryDraft) {
    if (project) setProject({ ...project, draft: next });
  }
  function chooseFeedback(finding: EvaluationFinding) {
    if (!selectableFeedback || !project?.feedback?.artifact_id) return;
    setSelectedFeedback({ projectId: project.id, artifactId: project.feedback.artifact_id,
      criterionId: finding.criterion_id, message: finding.message });
  }
  function downloadBackup() {
    if (!project) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(project, null, 2)],
      { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = `firstframe-${project.id}.json`; link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="page-shell"><div className="workspace">
      <header className="intro">
        <p className="eyebrow">Câu chuyện của bạn. Kịch bản đầu tiên của bạn.</p>
        <h1 id="workspace-title" tabIndex={-1}>FirstFrame</h1>
        <p className="tagline">Một khoảnh khắc nhỏ cũng đủ để bắt đầu.</p>
        <p className="summary">Ghi lại điều bạn thấy, nghe hoặc nhớ. Cùng làm rõ điều muốn kể,
          đọc bản phác thảo câu chuyện rồi tự sửa theo ý bạn.</p>
        <details className="workspace-tools">
          <summary>Demo và công cụ đánh giá</summary>
          <a className="demo-entry secondary" href="/demo">Xem demo local từ kịch bản có sẵn</a>{" "}
          <a className="demo-entry secondary" href="/datasets">Đánh giá chất lượng dataset</a>
        </details>
      </header>
      <OnboardingTour tour={tour} context={tourContext} ready={workspaceLoadState === "ready"}
        empty={projectsListed && !projects.length} busy={!!busy} error={error}
        idea={project?.idea ?? ""} answers={project?.answers ?? []}
        questionCount={project?.analysis?.missing_information.length ?? 0} />
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
        <button data-tour="new-project" disabled={!!busy} onClick={() => {
          const ticket = tour.begin("create");
          void run("Đang tạo dự án…", async () => {
            try {
              await persist();
              const created = await projectRequest("", "POST");
              accept(created); tour.succeeded(ticket, created.id);
            } catch (caught) { tour.failed(ticket); throw caught; }
          });
        }}>Dự án mới</button>
        <p className="storage-note">Dự án được lưu cục bộ trên máy này. Chưa có đồng bộ tài khoản.</p>
      </nav>
      {!!steps.length && operationTiming && <OperationProgress steps={steps} failed={operationFailed}
        timing={operationTiming} dirty={dirty} language={progressLanguage(project?.response_language ?? "auto")} />}
      {busy && !steps.length && <p className="operation-status" role="status">{busy}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="operation-status" role="status">{notice}</p>}
      {!project && !busy && <section className="panel empty-project">
        <h2>Ghi lại khoảnh khắc của bạn</h2>
        <p>Chọn “Dự án mới”, kể một khoảnh khắc bạn nhớ rồi lưu để quay lại viết tiếp.
          Chưa cần biết toàn bộ câu chuyện sẽ đi tới đâu.</p>
        {error && <button onClick={() => window.location.reload()}>Thử kết nối lại</button>}
      </section>}
      {project && <>
        <div className="save-toolbar" data-tour="save" tabIndex={-1}>
          <p id="save-status" role="status" tabIndex={-1}>{dirty ? "Có thay đổi chưa lưu" : "Đã lưu"}</p>
          <button data-tour-action="save" disabled={!!busy || !dirty} onClick={() => void run("Đang lưu…", async () => {
            await persist(); setNotice("Đã lưu thay đổi.");
          })}>Lưu thay đổi</button>
          <button className="secondary" onClick={downloadBackup}>Tải bản sao JSON</button>
        </div>
        <fieldset disabled={!!busy} className="project-fields">
          <section className="panel form-stack">
            <h2>1. Khoảnh khắc bạn muốn kể</h2>
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
            <textarea id="idea" data-tour="idea" maxLength={5000} value={project.idea} rows={5}
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
          </section>
          {saved && <AuthorIntentCard context={saved.author_context} revision={saved.revision}
            dirty={dirty} canEditAnswers={!briefChanged} />}
          {project.analysis && !briefChanged && <section className="panel form-stack">
            <h2 data-tour="choices" tabIndex={-1}>2. Những lựa chọn của bạn</h2>
            <p className="preserve-lines">{project.analysis.summary}</p>
            {!project.analysis.missing_information.length && <p>Ý tưởng đã đủ rõ cho một bản phát triển.
              Bạn quyết định khi nào bắt đầu tạo bản phát triển.</p>}
            {project.analysis.missing_information.map((question, index) => (
              <div className="question-block" key={`${project.analysis?.artifact_id}-${index}`}>
                <label htmlFor={`answer-${index}`}>{question}</label>
                <textarea id={`answer-${index}`} className="short-textarea" rows={3} maxLength={2000}
                  value={project.answers[index] ?? ""} onChange={(event) => {
                    const answers = [...project.answers]; answers[index] = event.target.value;
                    setProject({ ...project, answers });
                  }} />
                <button className="secondary" onClick={() => {
                  const answers = [...project.answers];
                  answers[index] = "Chưa quyết định. Nếu đề xuất một lựa chọn, hãy ghi rõ đó là gợi ý của AI.";
                  setProject({ ...project, answers });
                }}>Để quyết định sau</button>
              </div>
            ))}
            <button data-tour-action="plan" disabled={project.analysis.missing_information.some((_, i) => !project.answers[i]?.trim())}
              onClick={() => action("plan")}>
              {project.draft ? "Tạo lại bản phát triển (giữ phiên bản cũ)" : "Tạo bản phát triển từ lựa chọn của tôi"}
            </button>
          </section>}
          {project.draft && <section className="panel form-stack">
            <h2 data-tour="draft" tabIndex={-1}>3. Bản phát triển đang làm việc</h2>
            <StoryPlanReading draft={project.draft} dirty={dirty} />
            <h3 id="draft-editor-title" tabIndex={-1}>Chỉnh sửa bản phác thảo</h3>
            {selectedFeedback && <aside className="revision-note" aria-labelledby="selected-feedback-title">
              <h4 id="selected-feedback-title" tabIndex={-1}>Góp ý bạn đang cân nhắc</h4>
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
            <p>Sửa trực tiếp nội dung của bạn. Nhận phản hồi sẽ lưu bản này trước khi gửi cho AI.</p>
            <label htmlFor="draft-title">Tên phim tạm thời</label>
            <input id="draft-title" maxLength={200} value={project.draft.title}
              onChange={(event) => updateDraft({ ...project.draft!, title: event.target.value })} />
            <label htmlFor="draft-logline">Tóm tắt câu chuyện trong một câu</label>
            <textarea id="draft-logline" className="short-textarea" rows={3} maxLength={2000}
              value={project.draft.logline}
              onChange={(event) => updateDraft({ ...project.draft!, logline: event.target.value })} />
            {project.draft.sections.map((section, index) => <div className="draft-section" key={index}>
              <label htmlFor={`section-${index}`}>{sectionLabels[section.title] ?? section.title}</label>
              <textarea id={`section-${index}`} rows={5} maxLength={10000} value={section.content}
                onChange={(event) => updateDraft({ ...project.draft!,
                  sections: project.draft!.sections.map((item, i) => i === index
                    ? { ...item, content: event.target.value } : item) })} />
            </div>)}
            <button onClick={() => action("review")}>Nhận phản hồi trên bản hiện tại</button>
          </section>}
        </fieldset>
        {!!project.clarification_history.length && <section className="panel version-history">
          <h2>Các lựa chọn trước đây</h2>
          <p>Bạn có thể tham khảo và chép lại câu trả lời phù hợp. Các lựa chọn này không tự áp dụng cho ý tưởng mới.</p>
          {[...project.clarification_history].reverse().map((version) => <details key={version.id}>
            <summary>{new Date(version.created_at).toLocaleString("vi-VN")} · {version.idea}</summary>
            <PastAnswers questions={version.questions} answers={version.answers} />
          </details>)}
        </section>}
        {project.feedback && <section className="feedback-section" aria-label="Phản hồi">
          <p className={currentFeedback ? "operation-status" : "form-message"} role="status">
            {currentFeedback ? "Phản hồi cho đúng bản hiện tại."
              : "Nội dung đã thay đổi. Phản hồi dưới đây thuộc bản trước; hãy nhận phản hồi mới."}
          </p>
          <FeedbackIntent source={saved?.feedback_source} projectId={project.id} artifactId={project.feedback.artifact_id} />
          {!selectableFeedback && !busy && <p className="storage-note">Góp ý cũ hoặc chưa có đủ nguồn chỉ để tham khảo.
            Hãy nhận phản hồi cho đúng bản hiện tại trước khi chọn góp ý mới để tự sửa.</p>}
          <StoryFeedback evaluation={project.feedback} uiLanguage="vi" onChoose={chooseFeedback}
            selectedCriterion={selectedFeedback?.criterionId} selectionDisabled={!selectableFeedback} />
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
              <StoryFeedback evaluation={version.feedback} uiLanguage="vi" />
            </>}
            <button disabled={!!busy} onClick={() => void run("Đang giữ bản hiện tại và khôi phục…", async () => {
              const next = await persist();
              if (!next) return;
              accept(await projectRequest(`/${next.id}`, "PUT", {
                ...editableProject(next), draft: version.draft,
              }));
              setSelectedFeedback(null);
              setNotice("Đã dùng lại nội dung bản phát triển. Các phiên bản trước vẫn được giữ.");
            })}>Dùng lại bản phát triển này</button>
          </details>)}
        </section>}
      </>}
    </div></main>
  );
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
