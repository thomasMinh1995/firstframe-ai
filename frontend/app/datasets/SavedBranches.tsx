"use client";

import { useEffect, useState } from "react";
import { compareBranch, listBranches, type SampleDetail, type SavedBranches, type StateComparison } from "../datasetApi";
import JsonChanges from "./JsonChanges";

export default function SavedBranchesPanel({sample, disabled, onRestore}: {
  sample: SampleDetail; disabled: boolean; onRestore: (branch: string, token: string) => Promise<void>;
}) {
  const [saved, setSaved] = useState<SavedBranches | null>(null);
  const [selected, setSelected] = useState("");
  const [comparison, setComparison] = useState<StateComparison | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    setSaved(null); setSelected(""); setComparison(null); setError("");
    listBranches(sample.run_id).then((value) => { if (!cancelled) setSaved(value); })
      .catch(() => { if (!cancelled) setError("Không đọc được các nhánh xung đột đã lưu."); });
    return () => { cancelled = true; };
  }, [sample.run_id, sample.fingerprint, sample.review.revision]);
  useEffect(() => {
    let cancelled = false;
    setComparison(null);
    if (selected) compareBranch(sample.run_id, selected).then((value) => {
      if (!cancelled) setComparison(value);
    }).catch(() => { if (!cancelled) setError("Không so sánh được nhánh. Hãy tải lại mẫu."); });
    return () => { cancelled = true; };
  }, [selected, sample.run_id, sample.review.revision]);
  if (!saved?.branches.length && !error) return null;
  return <section className="panel form-stack" aria-label="Nhánh xung đột đã lưu">
    <h2>Nhánh xung đột đã lưu</h2>
    <p>Các nhánh giữ nguyên bản gốc, góp ý và lịch sử của mỗi phía. Dùng lại một nhánh sẽ lưu nhánh hiện tại trước,
      tạo lượt khôi phục mới và yêu cầu duyệt lại trước khi chọn demo/train.</p>
    {error && <p role="alert" className="error">{error}</p>}
    <label htmlFor="saved-branch">Chọn nhánh để đối chiếu</label>
    <select id="saved-branch" value={selected} disabled={disabled} onChange={(event) => setSelected(event.target.value)}>
      <option value="">Chọn nhánh đã lưu</option>{saved?.branches.map((branch) => <option key={branch.branch_id} value={branch.branch_id}>
        {branch.source === "local" ? "Local" : branch.source === "incoming" ? "Bản nhập" : "Khôi phục"} · {branch.history_count} phiên bản · {branch.branch_id.slice(0, 8)}
      </option>)}
    </select>
    {selected && !comparison && !error && <p role="status">Đang so sánh nhánh…</p>}
    {comparison && <JsonChanges changes={comparison.changes} left="Đang dùng" right="Nhánh đã lưu" />}
    <button disabled={disabled || !comparison || !selected} onClick={() => onRestore(selected, comparison!.local_token)}>Dùng lại nhánh đã chọn và duyệt lại</button>
  </section>;
}
