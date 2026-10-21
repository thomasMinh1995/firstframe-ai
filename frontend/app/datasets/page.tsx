"use client";

import { useEffect, useState } from "react";
import { datasetBase, getSample, listSamples, restoreOutputs, restoreSavedBranch, saveOutputs, saveReview, type Review, type Sample, type SampleDetail } from "../datasetApi";

import SavedBranchesPanel from "./SavedBranches";
import DatasetTransfer from "./DatasetTransfer";
import OutputHistoryPanel from "./OutputHistory";
import OutputFields from "./OutputFields";

const effectiveOutputs = (sample: SampleDetail) => Object.fromEntries(sample.recording.steps.flatMap((step, index) =>
  step.output && typeof step.output === "object" && !Array.isArray(step.output)
    ? [[String(index), sample.corrected_outputs[String(index)] ?? step.output as Record<string, unknown>]] : []));

const labels = { unreviewed: "Chưa đánh giá", approved: "Tốt · đã duyệt", needs_revision: "Chưa phù hợp" };
const operations: Record<string, string> = {analyze: "Phân tích", plan: "Tạo plan", review: "Phản hồi bản sửa", generate: "Workflow đầy đủ"};
const pretty = (value: unknown) => JSON.stringify(value, null, 2);
const message = (error: unknown) => error instanceof Error ? error.message : "Không đọc được dataset.";

export default function DatasetsPage() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [selected, setSelected] = useState("");
  const [sample, setSample] = useState<SampleDetail | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [outputs, setOutputs] = useState<Record<string, Record<string, unknown>>>({});
  const [filter, setFilter] = useState("all");
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const reviewDirty = sample !== null && pretty(review) !== pretty(sample.review);
  const outputsDirty = sample !== null && pretty(outputs) !== pretty(effectiveOutputs(sample));
  const dirty = reviewDirty || outputsDirty;

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError("");
    listSamples().then((items) => {
      if (cancelled) return;
      setSamples(items);
      setSelected((id) => items.some((item) => item.run_id === id) ? id : items[0]?.run_id ?? "");
    }).catch((error) => { if (!cancelled) setError(message(error)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [refresh]);
  useEffect(() => {
    let cancelled = false;
    setSample(null); setReview(null); setOutputs({}); setNotice(""); setError("");
    if (!selected) return;
    setLoading(true);
    getSample(selected).then((item) => {
      if (!cancelled) { setSample(item); setReview(item.review); setOutputs(effectiveOutputs(item)); }
    }).catch((error) => { if (!cancelled) setError(message(error)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selected, refresh]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function save() {
    if (!sample || !review) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const next = await saveReview(sample, review);
      setReview(next); setSample({...sample, review: next});
      setSamples((items) => items.map((item) => item.run_id === sample.run_id ? {...item, review: next} : item));
      setNotice("Đã lưu đánh giá trên máy. Dataset gốc được giữ nguyên.");
    } catch (error) { setError(message(error)); }
    finally { setSaving(false); }
  }
  async function saveOutputChanges() {
    if (!sample) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const next = await saveOutputs(sample, outputs);
      setSample(next); setOutputs(effectiveOutputs(next));
      setReview({...next.review, feedback: review?.feedback ?? next.review.feedback});
      setSamples((items) => items.map((item) => item.run_id === next.run_id ? next : item));
      setNotice("Đã lưu bản sửa riêng. Mẫu trở về chưa đánh giá; hãy đọc lại và duyệt bản mới.");
    } catch (error) { setError(message(error)); }
    finally { setSaving(false); }
  }
  async function restoreOutputVersion(version: number) {
    if (!sample || dirty || saving) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const next = await restoreOutputs(sample, version);
      setSample(next); setOutputs(effectiveOutputs(next)); setReview(next.review);
      setSamples((items) => items.map((item) => item.run_id === next.run_id ? next : item));
      setNotice("Đã khôi phục thành phiên bản mới. Hãy duyệt lại trước khi chọn demo/train.");
    } catch (error) { setError(message(error)); }
    finally { setSaving(false); }
  }
  async function useBranch(branch: string, token: string) {
    if (!sample || dirty || saving) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const next = await restoreSavedBranch(sample.run_id, branch, token);
      setSample(next); setOutputs(effectiveOutputs(next)); setReview(next.review);
      setSamples((items) => items.map((item) => item.run_id === next.run_id ? next : item));
      setNotice("Đã dùng lại nhánh đã lưu và giữ nhánh trước đó. Hãy duyệt lại mẫu.");
    } catch (error) { setError(message(error)); }
    finally { setSaving(false); }
  }
  const visible = samples.filter((item) => filter === "all" || item.review.status === filter);
  return <main className="page-shell"><div className="workspace demo-workspace">
    <header className="intro">
      <p className="eyebrow">FirstFrame · Chất lượng dataset</p>
      <h1>Duyệt mẫu trước khi dùng lại.</h1>
      <p className="summary">Đọc đầu vào, kết quả và model đã dùng; ghi nhận đánh giá của bạn.
        Điểm của AI trong workflow không tự quyết định chất lượng mẫu.</p>
      <div className="demo-controls"><a href="/">Về không gian viết</a><a href="/demo?curated=true">Mở demo đã duyệt</a></div>
    </header>
    <section className="panel form-stack">
      <p>{samples.length} mẫu · {samples.filter((item) => item.review.status === "approved").length} đã duyệt
        · {samples.filter((item) => item.review.use_for_training).length} được chọn train.</p>
      <label htmlFor="review-filter">Lọc chất lượng</label>
      <select id="review-filter" value={filter} disabled={saving} onChange={(event) => setFilter(event.target.value)}>
        <option value="all">Tất cả mẫu</option>{Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select>
      <label htmlFor="sample-picker">Mẫu workflow ({visible.length})</label>
      <select id="sample-picker" value={visible.some((item) => item.run_id === selected) ? selected : ""}
        disabled={saving || dirty} onChange={(event) => setSelected(event.target.value)}>
        <option value="" disabled>Chọn mẫu để đánh giá</option>
        {visible.map((item) => <option key={item.run_id} value={item.run_id}>
          {operations[item.operation]} · {item.title} · {labels[item.review.status]}{item.has_corrections ? " · Có bản sửa" : ""} · {item.run_id.slice(0, 8)}
        </option>)}
      </select>
      <div className="demo-controls">
        <button className="secondary" disabled={saving || loading || dirty} onClick={() => setRefresh((n) => n + 1)}>Tải lại mẫu</button>
        <a href={`${datasetBase}/training.jsonl`} download>Xuất JSONL đã chọn cho train</a>
      </div>
      <p>JSONL gồm các bước AI trong mẫu tốt đã chọn, kèm prompt, output và nguồn model.
        Đây là dữ liệu chuẩn bị; cần chia train/test theo dự án và chuyển sang định dạng provider trước khi train.</p>
    </section>
    <DatasetTransfer disabled={saving || dirty || loading} onBusy={setSaving} onImported={() => setRefresh((n) => n + 1)} />
    {loading && <p role="status">Đang đọc dataset…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="operation-status" role="status">{notice}</p>}
    {!loading && !samples.length && <p>Chưa có dataset. Hoàn tất một workflow hoặc thêm JSON/JSONL vào thư mục dataset.</p>}
    {sample && review && <>
      <section className="panel form-stack">
        <h2>{operations[sample.operation]} · {sample.title}</h2>
        <p className="preserve-lines">{sample.idea}</p>
        <p>Nguồn: {sample.models_used.map((model) => `${model.provider} · ${model.model}`).join("; ") || "Không có model hoàn tất"}
          {" · "}{sample.status} · {sample.started_at}</p>
        <p className="demo-source">ID: {sample.run_id}{sample.project_id && ` · Dự án: ${sample.project_id}`}</p>
        <details><summary>Đầu vào và ngữ cảnh tác giả</summary><pre className="dataset-json">{pretty(sample.recording.input)}</pre></details>
        {sample.recording.steps.map((step, i) => <article className="story-section" key={i}>
          <h3>{step.stage} · {step.provider} · {step.model ?? "Chưa có model trả kết quả"}</h3>
          <p>{step.status}{step.error_type ? ` · ${step.error_type}` : ""}</p>
          <p>{pretty(outputs[String(i)] ?? step.output) !== pretty(sample.corrected_outputs[String(i)] ?? step.output)
            ? "Bản đang sửa · chưa lưu"
            : sample.corrected_outputs[String(i)] ? "Có bản người biên tập sửa" : "Output gốc từ model"}</p>
          <pre className="dataset-json">{pretty(outputs[String(i)] ?? step.output)}</pre>
          <details><summary>Đối chiếu output gốc</summary><pre className="dataset-json">{pretty(step.output)}</pre></details>
          {sample.eligible && outputs[String(i)] && <details><summary>Chỉnh sửa output bước này</summary>
            <fieldset disabled={saving} className="form-stack"><legend>Bản biên tập · {step.stage}</legend>
              <OutputFields value={outputs[String(i)]} onChange={(next) => setOutputs({...outputs, [String(i)]: next as Record<string, unknown>})} />
              <button className="secondary" type="button" onClick={() => setOutputs({...outputs, [String(i)]: step.output as Record<string, unknown>})}>Khôi phục output gốc của bước</button>
            </fieldset>
          </details>}
          <details><summary>Prompt và schema đã dùng</summary><pre className="dataset-json">{pretty(step.request)}</pre></details>
        </article>)}
        <details><summary>Snapshot kết quả đã lưu</summary><pre className="dataset-json">{pretty(sample.recording.output)}</pre></details>
      </section>
      <section className="panel form-stack" aria-label="Lưu bản sửa output">
        <h2>Lưu bản sửa output</h2>
        <p>Bản gốc luôn được giữ nguyên. Lưu thay đổi sẽ bỏ duyệt và bỏ chọn demo/train để bạn duyệt lại.
          Không gọi AI; phản hồi cũ không tự đánh giá lại nội dung đã sửa.</p>
        <p>Khi sửa một bước, bản xuất train chỉ lấy đến bước đó trong mẫu này;
          các bước sau vẫn dùng ngữ cảnh gốc nên không được xuất cùng bản sửa.</p>
        <div className="demo-controls"><button disabled={saving || !outputsDirty} onClick={saveOutputChanges}>Lưu bản sửa output</button>
          <button className="secondary" disabled={saving || !outputsDirty} onClick={() => setOutputs(effectiveOutputs(sample))}>Bỏ thay đổi output</button></div>
        {outputsDirty && <p role="status">Có output chưa lưu. Lưu hoặc bỏ thay đổi trước khi duyệt.</p>}
      </section>
      <SavedBranchesPanel sample={sample} disabled={saving || dirty} onRestore={useBranch} />
      <OutputHistoryPanel sample={sample} disabled={saving || dirty} onRestore={restoreOutputVersion} />
      <section className="panel form-stack" aria-label="Đánh giá của bạn">
        <h2>Đánh giá của bạn</h2>
        {!sample.eligible && <p>Mẫu chưa hoàn tất hoặc không hợp lệ; chỉ ghi góp ý, không dùng cho demo/train.</p>}
        <fieldset disabled={saving || outputsDirty} className="form-stack"><legend>Chất lượng mẫu</legend>
          {Object.entries(labels).map(([status, label]) => <label key={status} className="review-choice">
            <input type="radio" name="quality" value={status} checked={review.status === status}
              disabled={status === "approved" && !sample.eligible}
              onChange={() => setReview({...review, status: status as Review["status"],
                use_for_demo: status === "approved" && review.use_for_demo,
                use_for_training: status === "approved" && review.use_for_training})} />{label}
          </label>)}
          <label htmlFor="human-feedback">Góp ý cho mẫu</label>
          <textarea id="human-feedback" rows={4} maxLength={10000} value={review.feedback}
            placeholder="Ví dụ: Giữ đúng ý tác giả; phần kết còn thiếu động cơ nhân vật…"
            onChange={(event) => setReview({...review, feedback: event.target.value})} />
          <label className="review-choice"><input type="checkbox" checked={review.use_for_demo}
            disabled={review.status !== "approved" || !sample.eligible}
            onChange={(event) => setReview({...review, use_for_demo: event.target.checked})} />Chọn cho demo đã duyệt</label>
          <label className="review-choice"><input type="checkbox" checked={review.use_for_training}
            disabled={review.status !== "approved" || !sample.eligible}
            onChange={(event) => setReview({...review, use_for_training: event.target.checked})} />Chọn để chuẩn bị train model</label>
        </fieldset>
        <p>Để demo phát lại đủ ngữ cảnh, chọn cả mẫu phân tích và tạo plan liên quan.
          Các lượt sửa chỉ xuất hiện khi được duyệt và chọn theo chuỗi.</p>
        <div className="demo-controls"><button disabled={saving || !reviewDirty || outputsDirty} onClick={save}>{saving ? "Đang lưu…" : "Lưu đánh giá"}</button>
          <button className="secondary" disabled={saving || !reviewDirty} onClick={() => setReview(sample.review)}>Bỏ thay đổi</button></div>
        {dirty && <p role="status">Có thay đổi chưa lưu. Lưu hoặc bỏ thay đổi để chuyển mẫu.</p>}
        {review.updated_at && <p>Lưu gần nhất: {review.updated_at}</p>}
      </section>
    </>}
  </div></main>;
}
