"use client";

import { useEffect, useState } from "react";
import { StoryFeedback } from "../StoryResultCards";
import { getDemoScenario, listDemoScenarios, type DemoScenario, type DemoStep, type DemoSummary } from "../demoApi";
import { sectionLabels } from "../storyLabels";

const reviewLabels: Record<string, string> = {
  approved: "Đã duyệt chất lượng", unreviewed: "Chưa duyệt chất lượng",
  needs_revision: "Cần chỉnh sửa", rejected: "Bản ghi bị loại",
};

export default function DemoPage() {
  const [curated, setCurated] = useState(false);
  useEffect(() => { setCurated(new URLSearchParams(window.location.search).get("curated") === "true"); }, []);
  const [items, setItems] = useState<DemoSummary[]>([]);
  const [selected, setSelected] = useState("");
  const [scenario, setScenario] = useState<DemoScenario | null>(null);
  const [index, setIndex] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [listing, setListing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setListing(true); setError(null);
    listDemoScenarios(curated).then((next) => {
      if (cancelled) return;
      setItems(next);
      setSelected((current) => next.some((item) => item.id === current) ? current : next[0]?.id ?? "");
    }).catch((caught) => {
      if (!cancelled) { setError(message(caught)); setItems([]); setSelected(""); }
    }).finally(() => { if (!cancelled) setListing(false); });
    return () => { cancelled = true; };
  }, [refresh, curated]);

  useEffect(() => {
    let cancelled = false;
    setScenario(null); setIndex(0);
    if (!selected) { setLoading(false); return; }
    setLoading(true); setError(null);
    getDemoScenario(selected, curated).then((next) => {
      if (!cancelled) setScenario(next);
    }).catch((caught) => {
      if (!cancelled) setError(message(caught));
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selected, refresh, curated]);

  const step = scenario?.steps[index];
  const busy = listing || loading;

  return <main className="page-shell"><div className="workspace demo-workspace">
    <header className="intro">
      <p className="eyebrow">FirstFrame · Demo local</p>
      <h1>Một ý tưởng, từng bước thành câu chuyện.</h1>
      <p className="summary">Chọn một kịch bản có sẵn rồi đi qua những lựa chọn và bản sửa đã ghi.
        Demo phát lại dữ liệu trên máy, không gọi OpenAI hay Ollama.</p>
      <a className="demo-entry secondary" href="/">Về không gian viết</a>
    </header>

    <section className="panel form-stack" aria-label="Chọn kịch bản demo">
      <a href="/datasets">Đánh giá và chọn mẫu dataset</a>
      <label className="review-choice"><input type="checkbox" checked={curated}
        onChange={(event) => setCurated(event.target.checked)} />Chỉ dùng mẫu tốt đã chọn cho demo</label>
      <label htmlFor="demo-picker">Kịch bản có sẵn</label>
      <div className="demo-picker-row">
        <select id="demo-picker" value={selected} disabled={listing || !items.length}
          onChange={(event) => setSelected(event.target.value)}>
          {!items.length && <option value="">Chưa có kịch bản</option>}
          {items.map((item) => <option key={item.id} value={item.id}>
            {item.title} · {item.step_count} bước
          </option>)}
        </select>
        <button className="secondary" disabled={busy} onClick={() => setRefresh((value) => value + 1)}>
          Tải lại danh sách
        </button>
      </div>
      <p>Đây là bản phát lại. Câu trả lời và nội dung sửa đã được ghi sẵn;
        demo không tạo phản hồi mới cho ý tưởng hoặc chỉnh sửa tùy ý.</p>
    </section>

    {busy && <p className="operation-status" role="status">Đang đọc kịch bản local…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!busy && !error && !items.length && <section className="panel empty-project">
      <h2>Chưa có workflow hoàn chỉnh để phát lại</h2>
      <p>Hãy xuất một lượt tạo bản phát triển thành công rồi tải lại danh sách.
        Các bản ghi lỗi hoặc chưa hoàn tất không xuất hiện ở đây.
        Khi lọc demo đã duyệt, hãy chọn các mẫu phân tích và tạo bản phát triển liên quan trong trang đánh giá dataset.</p>
    </section>}

    {!busy && scenario && step && <>
      <section className="panel demo-overview">
        <div className="demo-badges">
          <span className="result-pill">Đang phát lại · không gọi AI</span>
          <span>{reviewLabels[scenario.review_status] ?? "Chưa duyệt chất lượng"}</span>
        </div>
        <h2>{scenario.title}</h2>
        <p>{scenario.description}</p>
        <p className="demo-source">Nguồn bản ghi: {scenario.models_used.map((model) =>
          `${providerLabel(model.provider)} · ${model.model}`).join("; ") || "Chưa có thông tin model"}.</p>
        <progress value={index + 1} max={scenario.steps.length}
          aria-label={`Đang xem bước ${index + 1} trên ${scenario.steps.length}`} />
      </section>

      <nav className="demo-steps" aria-label="Các bước của kịch bản">
        <ol>{scenario.steps.map((item, position) => <li key={position}>
          <button className={position === index ? "demo-step is-current" : "demo-step secondary"}
            aria-current={position === index ? "step" : undefined} onClick={() => setIndex(position)}>
            <span>{position + 1}</span>{item.title}
          </button>
        </li>)}</ol>
      </nav>

      <div className="demo-controls">
        <button className="secondary" disabled={index === 0} onClick={() => setIndex(index - 1)}>Bước trước</button>
        <p role="status">Bước {index + 1} / {scenario.steps.length}</p>
        {index < scenario.steps.length - 1
          ? <button onClick={() => setIndex(index + 1)}>Tiếp: {scenario.steps[index + 1].title}</button>
          : <button onClick={() => setIndex(0)}>Xem lại từ đầu</button>}
      </div>

      <section className="panel form-stack demo-content" aria-labelledby="demo-step-title">
        <h2 id="demo-step-title">{step.title}</h2>
        {step.description && <p>{step.description}</p>}
        {!!step.models_used.length && <p className="demo-source">Kết quả đã ghi từ {step.models_used.map((model) =>
          `${providerLabel(model.provider)} · ${model.model}`).join("; ")}.</p>}
        <StepContent step={step} />
      </section>
      {step.feedback && <div className="feedback-section">
        <StoryFeedback evaluation={step.feedback} uiLanguage="vi" />
      </div>}
      {index === scenario.steps.length - 1 && <p className="operation-status" role="status">
        Đã xem hết kịch bản. Bạn có thể xem lại hoặc chọn một câu chuyện khác.
      </p>}
    </>}
  </div></main>;
}

function StepContent({ step }: { step: DemoStep }) {
  return <>
    {step.idea && <p className="preserve-lines">{step.idea}</p>}
    {!!step.constraints.length && <div><h3>Điều tác giả muốn giữ</h3>
      <ul>{step.constraints.map((constraint, i) => <li key={i}>{constraint}</li>)}</ul>
    </div>}
    {step.analysis && <>
      <p className="preserve-lines">{step.analysis.summary}</p>
      {!!step.analysis.notes.length && <details><summary>Những ghi nhận đã có</summary>
        {step.analysis.notes.map((note, i) => <p className="preserve-lines" key={i}>
          <strong>{note.label}: </strong>{note.content}
        </p>)}
      </details>}
      {!!step.analysis.missing_information.length ? <div><h3>Câu hỏi cần làm rõ</h3>
        <ol>{step.analysis.missing_information.map((question, i) => <li key={i}>{question}</li>)}</ol>
      </div> : <p>Brief đã đủ rõ trong lượt phân tích này; không có câu hỏi bổ sung.</p>}
    </>}
    {!!step.answers.length && <div className="demo-answers">
      {step.answers.map((answer, i) => <article className="question-block" key={i}>
        <h3>{answer.question}</h3><p className="preserve-lines">{answer.answer}</p>
      </article>)}
    </div>}
    {step.draft && <>
      <h3 className="story-title">{step.draft.title}</h3>
      <p className="logline preserve-lines">{step.draft.logline}</p>
      {step.draft.sections.map((section, i) => <article className="story-section" key={i}>
        <h3>{sectionLabels[section.title] ?? section.title}</h3>
        <p className="preserve-lines">{section.content}</p>
      </article>)}
    </>}
  </>;
}

function providerLabel(provider: string) {
  return ({ openai: "OpenAI", ollama: "Ollama" } as Record<string, string>)[provider] ?? provider;
}
function message(error: unknown) {
  return error instanceof Error ? error.message : "Không đọc được dữ liệu demo.";
}
