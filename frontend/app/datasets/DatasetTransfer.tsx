"use client";

import { useRef, useState } from "react";
import { compareBundle, downloadBundle, importBundle, previewBundle, type BundleReport, type ConflictChoices, type StateComparison } from "../datasetApi";

import JsonChanges from "./JsonChanges";

const message = (error: unknown) => error instanceof Error ? error.message : "Không chuyển được dataset.";

export default function DatasetTransfer({disabled, onBusy, onImported}: {
  disabled: boolean; onBusy: (busy: boolean) => void; onImported: () => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [content, setContent] = useState("");
  const [filename, setFilename] = useState("");
  const [preview, setPreview] = useState<BundleReport | null>(null);
  const [choices, setChoices] = useState<ConflictChoices>({});
  const [comparisons, setComparisons] = useState<Record<string, StateComparison>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const lock = (next: boolean) => { setBusy(next); onBusy(next); };
  async function exportFile() {
    lock(true); setError(""); setNotice("");
    try { await downloadBundle(); setNotice("Đã tải gói dataset đã duyệt. Chép file này sang máy khác rồi nhập tại trang Dataset."); }
    catch (error) { setError(message(error)); }
    finally { lock(false); }
  }
  async function selectFile(file: File | undefined) {
    setChoices({}); setComparisons({});
    setPreview(null); setContent(""); setFilename(file?.name ?? ""); setError(""); setNotice("");
    if (!file) return;
    if (file.size > 25 * 1024 * 1024) { setError("Gói vượt giới hạn 25 MiB."); return; }
    lock(true);
    try {
      const text = await file.text();
      const report = await previewBundle(text);
      setContent(text); setPreview(report);
    } catch (error) { setError(message(error)); }
    finally { lock(false); }
  }
  async function importFile() {
    if (!preview || !content || preview.conflicts.some((item) => !choices[item.run_id])) return;
    lock(true); setError(""); setNotice("");
    try {
      const result = await importBundle(content, choices);
      setContent(""); setPreview(null);
      if (fileInput.current) fileInput.current.value = "";
      setNotice(`Đã nhập ${result.new_count} mẫu mới; giữ local ${result.kept_local_count ?? 0}, dùng bản nhập ${result.used_incoming_count ?? 0}, bỏ qua ${result.unchanged_count} mẫu trùng. Hai phía xung đột đã được lưu thành nhánh riêng.`);
      onImported();
    } catch (error) {
      setError(message(error));
      try { setPreview(await previewBundle(content)); setChoices({}); setComparisons({}); } catch { /* Keep the import error visible. */ }
    }
    finally { lock(false); }
  }
  async function compare(id: string) {
    lock(true); setError("");
    try {
      const diff = await compareBundle(content, id);
      if (diff.local_token !== preview?.conflicts.find((item) => item.run_id === id)?.local_token) {
        setPreview(await previewBundle(content)); setChoices({}); setComparisons({});
        setError("Local đã thay đổi. Hãy so sánh và chọn lại các mẫu xung đột.");
      } else setComparisons((items) => ({...items, [id]: diff}));
    } catch (error) { setError(message(error)); }
    finally { lock(false); }
  }
  const unresolved = preview?.conflicts.some((item) => !choices[item.run_id]);
  return <section className="panel form-stack" aria-label="Chuyển dataset sang máy khác">
    <h2>Xuất / nhập dataset đã duyệt</h2>
    <p>Gói gồm bản ghi gốc, provider/model, góp ý, bản sửa, toàn bộ lịch sử và lựa chọn demo/train.
      Máy nhận nhập file rồi chạy demo local, không gọi OpenAI hay Ollama.</p>
    <button className="secondary" disabled={disabled || busy} onClick={exportFile}>Xuất gói dataset đã duyệt</button>
    <p>Chỉ xuất mẫu tốt đã duyệt. Để phát lại demo đủ ngữ cảnh, duyệt và chọn cả mẫu phân tích, tạo bản phát triển và các lượt sửa muốn dùng.</p>
    <label htmlFor="dataset-bundle-file">Nhập gói từ máy khác (.json, tối đa 25 MiB)</label>
    <input ref={fileInput} id="dataset-bundle-file" type="file" accept=".json,application/json" disabled={disabled || busy}
      onChange={(event) => selectFile(event.target.files?.[0])} />
    {busy && <p role="status">Đang xử lý gói dataset…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="operation-status" role="status">{notice}</p>}
    {preview && <div className="form-stack">
      <h3>Xem trước: {filename}</h3>
      <p>{preview.sample_count} mẫu đã duyệt · {preview.correction_count} mẫu có bản sửa · {preview.history_count} phiên bản lịch sử.</p>
      <p>{preview.new_count} mẫu cần nhập · {preview.unchanged_count} mẫu trùng hoàn toàn · {preview.conflicts.length} xung đột.</p>
      <p>{preview.demo_count} kịch bản đã chọn đủ chuỗi để demo.</p>
      {preview.demo_count === 0 && <p>Gói chưa có kịch bản được chọn đủ chuỗi. Sau khi nhập, kiểm tra lựa chọn demo ở các mẫu liên quan.</p>}
      {preview.branch_add_count > 0 && <p>{preview.branch_add_count} nhánh lưu trữ được chuyển kèm theo gói.</p>}
      {!!preview.conflicts.length && <>
        <p>Chọn rõ từng mẫu trước khi nhập. Cả local và bản nhập được giữ thành nhánh riêng, gồm bản gốc và toàn bộ lịch sử.</p>
        <p>Số kịch bản ở trên tính theo gói nhập. Khi giữ local ở một phần chuỗi, hãy kiểm tra lại demo sau khi nhập.</p>
        {preview.conflicts.map((item) => <article className="form-stack output-change" key={item.run_id}>
          <h3>Mẫu {item.run_id}</h3><p>{item.reason}</p>
          {item.originals_differ && <p>Hai bản gốc khác nhau. Dùng bản nhập sẽ đổi nhánh đang xem; bản gốc local vẫn được lưu nguyên.</p>}
          <button className="secondary" disabled={disabled || busy} onClick={() => compare(item.run_id)}>So sánh mẫu {item.run_id.slice(0, 8)}</button>
          {comparisons[item.run_id] && <JsonChanges changes={comparisons[item.run_id].changes} />}
          <fieldset disabled={disabled || busy} className="form-stack"><legend>Chọn bản đang dùng cho mẫu này</legend>
            <label className="review-choice"><input type="radio" name={`conflict-${item.run_id}`} checked={choices[item.run_id]?.choice === "local"}
              onChange={() => setChoices({...choices, [item.run_id]: {choice: "local", local_token: item.local_token}})} />Giữ bản local · lưu bản nhập vào nhánh</label>
            <label className="review-choice"><input type="radio" name={`conflict-${item.run_id}`} disabled={!item.incoming_allowed}
              checked={choices[item.run_id]?.choice === "incoming"}
              onChange={() => setChoices({...choices, [item.run_id]: {choice: "incoming", local_token: item.local_token}})} />Dùng bản nhập · lưu bản local vào nhánh</label>
          </fieldset>
          {!item.incoming_allowed && <p>Local đang thiếu hoặc hỏng dữ liệu cần thiết để bảo toàn nhánh; hãy giữ local và kiểm tra dữ liệu.</p>}
        </article>)}
      </>}
      <button disabled={disabled || busy || unresolved || (preview.new_count === 0 && !preview.conflicts.length && !preview.branch_add_count)} onClick={importFile}>
        Áp dụng nhập gói · {preview.new_count} mẫu mới · {preview.conflicts.length} xung đột
      </button>
      {preview.unchanged_count === preview.sample_count && !preview.branch_add_count && <p>Máy này đã có đầy đủ gói này; không cần nhập lại.</p>}
    </div>}
  </section>;
}
