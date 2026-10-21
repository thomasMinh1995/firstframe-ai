"use client";

import { useEffect, useState } from "react";
import { StoryFeedback } from "./StoryResultCards";
import { sectionLabels } from "./storyLabels";
import {
  editableProject, listProjects, projectRequest,
  type Project, type ProjectSummary, type StoryDraft,
} from "./projectsApi";

export default function Home() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [saved, setSaved] = useState<Project | null>(null);
  const [busy, setBusy] = useState<string | null>("Đang mở dự án…");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const dirty = project !== null && saved !== null
    && JSON.stringify(editableProject(project)) !== JSON.stringify(editableProject(saved));
  const briefChanged = project !== null && saved !== null && (project.idea !== saved.idea
    || JSON.stringify(project.constraints) !== JSON.stringify(saved.constraints));
  const feedbackChanged = project !== null && saved !== null && JSON.stringify({
    idea: project.idea, constraints: project.constraints, answers: project.answers, draft: project.draft,
    questions: project.analysis?.missing_information ?? [],
  }) !== JSON.stringify({
    idea: saved.idea, constraints: saved.constraints, answers: saved.answers, draft: saved.draft,
    questions: saved.analysis?.missing_information ?? [],
  });
  const currentFeedback = project?.feedback_is_current && !feedbackChanged;

  function accept(next: Project) {
    setProject(next); setSaved(next);
    setProjects((items) => [next, ...items.filter((item) => item.id !== next.id)]);
  }
  useEffect(() => {
    let cancelled = false;
    async function openLastProject() {
      try {
        const items = await listProjects();
        const last = items.length ? await projectRequest(`/${items[0].id}`) : null;
        if (!cancelled) { setProjects(items); setProject(last); setSaved(last); }
      } catch (caught) {
        if (!cancelled) setError(message(caught));
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

  async function run(label: string, action: () => Promise<void>) {
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
    const labels = { analyze: "Đang tìm câu hỏi cần làm rõ…", plan: "Đang phát triển câu chuyện…",
      review: "Đang đọc và góp ý bản đã sửa…" };
    void run(labels[kind], async () => {
      const next = await persist();
      if (!next) return;
      accept(await projectRequest(`/${next.id}/${kind}`, "POST", { revision: next.revision }));
      setNotice(kind === "analyze" ? "Hãy trả lời các câu hỏi trước khi tạo story plan."
        : kind === "plan" ? "Đã tạo và lưu bản phát triển. Bạn có thể sửa trực tiếp bên dưới."
          : "Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.");
    });
  }
  function updateDraft(next: StoryDraft) {
    if (project) setProject({ ...project, draft: next });
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
        <h1>FirstFrame</h1>
        <p className="tagline">Từng bước phát triển câu chuyện bạn muốn kể.</p>
        <p className="summary">Bắt đầu bằng ý tưởng, làm rõ những lựa chọn rồi cùng sửa bản phát triển.
          Phiên bản này hỗ trợ story plan; viết kịch bản theo cảnh sẽ đến sau.</p>
        <a className="demo-entry secondary" href="/demo">Xem demo local từ kịch bản có sẵn</a>
        <a className="demo-entry secondary" href="/datasets">Đánh giá chất lượng dataset</a>
      </header>
      <nav className="project-toolbar panel" aria-label="Dự án">
        <label htmlFor="project-picker">Dự án của bạn</label>
        <select id="project-picker" value={project?.id ?? ""} disabled={!!busy}
          onChange={(event) => {
            const id = event.target.value;
            void run("Đang lưu và mở dự án…", async () => {
              await persist(); accept(await projectRequest(`/${id}`));
            });
          }}>
          <option value="" disabled>Chọn dự án</option>
          {projects.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
        <button disabled={!!busy} onClick={() => void run("Đang tạo dự án…", async () => {
          await persist(); accept(await projectRequest("", "POST"));
        })}>Dự án mới</button>
        <p className="storage-note">Dự án được lưu cục bộ trên máy này. Chưa có đồng bộ tài khoản.</p>
      </nav>
      {busy && <p className="operation-status" role="status">{busy}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="operation-status" role="status">{notice}</p>}
      {!project && !busy && <section className="panel empty-project">
        <h2>Bắt đầu câu chuyện đầu tiên</h2>
        <p>Chọn “Dự án mới” để lưu ý tưởng và quay lại phát triển bất cứ lúc nào.</p>
        {error && <button onClick={() => window.location.reload()}>Thử kết nối lại</button>}
      </section>}
      {project && <>
        <div className="save-toolbar">
          <p role="status">{dirty ? "Có thay đổi chưa lưu" : "Đã lưu"}</p>
          <button disabled={!!busy || !dirty} onClick={() => void run("Đang lưu…", async () => {
            await persist(); setNotice("Đã lưu thay đổi.");
          })}>Lưu thay đổi</button>
          <button className="secondary" onClick={downloadBackup}>Tải bản sao JSON</button>
        </div>
        <fieldset disabled={!!busy} className="project-fields">
          <section className="panel form-stack">
            <h2>1. Câu chuyện bạn muốn kể</h2>
            <label htmlFor="project-title">Tên dự án</label>
            <input id="project-title" maxLength={200} value={project.title}
              onChange={(event) => setProject({ ...project, title: event.target.value })} />
            <label htmlFor="idea">Ý tưởng, kỷ niệm hoặc tình huống của bạn</label>
            <textarea id="idea" maxLength={5000} value={project.idea} rows={5}
              placeholder="Điều gì khiến bạn muốn kể câu chuyện này?"
              onChange={(event) => setProject({ ...project, idea: event.target.value })} />
            <label htmlFor="constraints">Điều bạn muốn giữ hoặc giới hạn thực hiện (tùy chọn)</label>
            <textarea id="constraints" className="short-textarea" rows={3}
              value={project.constraints.join("\n")}
              placeholder="Mỗi dòng một ý, ví dụ: kết thúc mở; hai nhân vật; chỉ một căn nhà."
              onChange={(event) => setProject({ ...project, constraints: event.target.value.split("\n") })} />
            {briefChanged && (project.analysis || project.draft) && <p className="form-message">Ý tưởng đã thay đổi. Làm rõ lại trước khi tạo
              plan mới; bản thảo và câu trả lời trước đó sẽ được giữ trong lịch sử.</p>}
            {(!project.analysis || briefChanged) && <button disabled={!project.idea.trim()}
              onClick={() => action("analyze")}>Cùng làm rõ ý tưởng</button>}
          </section>
          {project.analysis && !briefChanged && <section className="panel form-stack">
            <h2>2. Những lựa chọn của bạn</h2>
            <p className="preserve-lines">{project.analysis.summary}</p>
            {!project.analysis.missing_information.length && <p>Ý tưởng đã đủ rõ cho một bản phát triển.
              Bạn quyết định khi nào bắt đầu tạo plan.</p>}
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
            <button disabled={project.analysis.missing_information.some((_, i) => !project.answers[i]?.trim())}
              onClick={() => action("plan")}>
              {project.draft ? "Tạo lại story plan (giữ phiên bản cũ)" : "Phát triển story plan từ lựa chọn của tôi"}
            </button>
          </section>}
          {project.draft && <section className="panel form-stack">
            <h2>3. Bản phát triển đang làm việc</h2>
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
          <StoryFeedback evaluation={project.feedback} uiLanguage="vi" />
        </section>}
        {!!project.versions.length && <section className="panel version-history">
          <h2>Các phiên bản đã giữ</h2>
          <p>Dùng lại một bản chỉ thay nội dung story plan; ý tưởng và câu trả lời hiện tại được giữ.
            Nhận phản hồi mới sau khi khôi phục.</p>
          {[...project.versions].reverse().map((version, index) => <details key={version.id}>
            <summary>Bản {project.versions.length - index} · {new Date(version.created_at).toLocaleString("vi-VN")}
              {version.feedback ? " · Có phản hồi" : " · Bản lưu trước khi tạo lại"}</summary>
            <p className="preserve-lines">{version.draft.title}{"\n"}{version.draft.logline}</p>
            <p className="preserve-lines">Ý tưởng của bản này: {version.idea}</p>
            <PastAnswers questions={version.questions} answers={version.answers} />
            {version.draft.sections.map((section, i) => <div key={i}>
              <h3>{sectionLabels[section.title] ?? section.title}</h3>
              <p className="preserve-lines">{section.content}</p>
            </div>)}
            {version.feedback && <StoryFeedback evaluation={version.feedback} uiLanguage="vi" />}
            <button disabled={!!busy} onClick={() => void run("Đang giữ bản hiện tại và khôi phục…", async () => {
              const next = await persist();
              if (!next) return;
              accept(await projectRequest(`/${next.id}`, "PUT", {
                ...editableProject(next), draft: version.draft,
              }));
              setNotice("Đã dùng lại nội dung story plan. Các phiên bản trước vẫn được giữ.");
            })}>Dùng lại story plan này</button>
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
