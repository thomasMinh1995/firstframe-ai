"use client";

import { useEffect, useState } from "react";
import { diffOutputs, getOutputHistory, type OutputDiff, type OutputHistory, type OutputVersion, type SampleDetail } from "../datasetApi";

const label = (version: OutputVersion) => version.version === 0 ? "Bản gốc · model"
  : `Bản ${version.version} · ${version.action === "restore" ? `Khôi phục từ ${version.restored_from === 0 ? "bản gốc" : `bản ${version.restored_from}`}`
    : version.action === "imported" ? "Bản sửa có trước lịch sử" : "Biên tập"}`;
const display = (exists: boolean, value: unknown) => exists ? JSON.stringify(value, null, 2) : "(không có trường này)";
const message = (error: unknown) => error instanceof Error ? error.message : "Không đọc được lịch sử output.";

export default function OutputHistoryPanel({sample, disabled, onRestore}: {
  sample: SampleDetail; disabled: boolean; onRestore: (version: number) => Promise<void>;
}) {
  const [history, setHistory] = useState<OutputHistory | null>(null);
  const [from, setFrom] = useState(0);
  const [to, setTo] = useState(0);
  const [diff, setDiff] = useState<OutputDiff | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setHistory(null); setDiff(null); setError(""); setLoading(true);
    getOutputHistory(sample.run_id).then((next) => {
      if (cancelled) return;
      if (next.fingerprint !== sample.fingerprint) throw new Error("Dataset gốc đã thay đổi. Hãy tải lại mẫu.");
      setHistory(next); setTo(next.current_version);
      setFrom(next.versions.length > 1 ? next.versions[next.versions.length - 2].version : 0);
    }).catch((error) => { if (!cancelled) setError(message(error)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sample.run_id, sample.fingerprint, sample.review.revision, refresh]);
  useEffect(() => {
    if (!history) return;
    let cancelled = false;
    setDiff(null); setError("");
    diffOutputs(sample.run_id, from, to).then((next) => {
      if (cancelled) return;
      if (next.fingerprint !== sample.fingerprint) throw new Error("Dataset gốc đã thay đổi. Hãy tải lại mẫu.");
      setDiff(next);
    }).catch((error) => { if (!cancelled) setError(message(error)); });
    return () => { cancelled = true; };
  }, [history, sample.run_id, sample.fingerprint, from, to]);

  const comparison = diff && diff.from_version === from && diff.to_version === to ? diff : null;

  return <section className="panel form-stack" aria-label="Lịch sử output">
    <h2>Lịch sử chỉnh sửa output</h2>
    <p>Mỗi lần lưu thay đổi tạo một phiên bản. Bản gốc luôn có thể xem lại.
      Khôi phục tạo bản mới, bỏ duyệt và bỏ chọn demo/train; các phiên bản cũ vẫn được giữ.</p>
    {loading && <p role="status">Đang đọc lịch sử…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <button className="secondary" disabled={disabled || loading} onClick={() => setRefresh((n) => n + 1)}>Tải lại lịch sử</button>
    {history && <>
      <p>Đang sử dụng: {label(history.versions[history.versions.length - 1])}.</p>
      <ol className="output-version-list">{history.versions.map((version) => <li key={version.version}>
        <strong>{label(version)}</strong>{version.version === history.current_version && " · Hiện tại"}
        {version.created_at && <span> · {new Date(version.created_at).toLocaleString("vi-VN")}</span>}
      </li>)}</ol>
      <div className="output-compare-selectors">
        <label>So sánh từ phiên bản<select value={from} onChange={(event) => setFrom(Number(event.target.value))}>
          {history.versions.map((version) => <option key={version.version} value={version.version}>{label(version)}</option>)}
        </select></label>
        <label>Đến phiên bản<select value={to} onChange={(event) => setTo(Number(event.target.value))}>
          {history.versions.map((version) => <option key={version.version} value={version.version}>{label(version)}</option>)}
        </select></label>
      </div>
      {!comparison && !error && <p role="status">Đang so sánh…</p>}
      {comparison && <>
        <p role="status">{comparison.changes.length ? `${comparison.changes.length} trường khác biệt.` : "Hai phiên bản có cùng output."}</p>
        {comparison.changes.map((change) => <article className="output-change" key={change.path}>
          <h3>{change.path.replace(/^steps\[(\d+)\]\.output/, (_, index) => `Bước ${Number(index) + 1}`)}</h3>
          <div className="output-compare-selectors">
            <div><strong>Trước · {from === 0 ? "Bản gốc" : `Bản ${from}`}</strong><pre className="dataset-json">{display(change.before_exists, change.before)}</pre></div>
            <div><strong>Sau · {to === 0 ? "Bản gốc" : `Bản ${to}`}</strong><pre className="dataset-json">{display(change.after_exists, change.after)}</pre></div>
          </div>
        </article>)}
      </>}
      <button disabled={disabled || !sample.eligible || !comparison || to === history.current_version}
        onClick={() => onRestore(to)}>Khôi phục {to === 0 ? "bản gốc" : `bản ${to}`} thành phiên bản mới</button>
      {disabled && <p>Lưu hoặc bỏ thay đổi đang sửa trước khi khôi phục.</p>}
    </>}
  </section>;
}
