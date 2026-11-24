"use client";

import { useId, useState } from "react";
import { SceneHint } from "./SceneHint";
import type { Project } from "./projectsApi";
import type { Scene, SceneProposal, SceneSuggestionInput } from "./sceneTypes";

export function SceneSuggestions({ project, dirty, onSuggest, onInspect, onDiscard, onUse, onPreviewChange, canUse, onKeepManual }: {
  project: Project; dirty: boolean; canUse: boolean; onKeepManual: () => void; onPreviewChange: (id: string, scenes: Scene[]) => void; onSuggest: (input: SceneSuggestionInput) => Promise<void>;
  onInspect: () => Promise<boolean>; onDiscard: (id: string) => void;
  onUse: (scenes: Scene[], proposalId: string) => void;
}) {
  const id = useId();
  const [mode, setMode] = useState<"append" | "develop">("append");
  const [target, setTarget] = useState("");
  const [instructions, setInstructions] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const outline = project.scene_outline!;
  const proposals = project.scene_proposals ?? [];
  const allProposals = [...proposals, ...(project.staging_proposals ?? [])];
  const uncertain = sent !== null && !proposals.some(p => p.id === sent);
  const pending = allProposals.some(p => p.status === "pending");
  const targetExists = outline.scenes.some(s => s.id === target);
  const chosenTarget = targetExists ? target : "";
  return <section className="scene-suggestions" aria-label="FirstFrame gợi ý cảnh">
    <SceneHint title="FirstFrame gợi ý cảnh" heading="h3"><p>Lưu mọi sửa đang chờ, rồi dùng story plan và ý đồ nguồn ở trên để gợi ý.
      Đề xuất được giữ riêng; bạn tự đọc, chỉnh, bỏ hoặc chọn dùng. Không có điểm chứng nhận chất lượng.</p></SceneHint>
    {!!outline.scenes.length && <div className="scene-pair">
      <div><label htmlFor={`${id}-mode`}>Loại gợi ý</label><select id={`${id}-mode`} value={mode} onChange={e => setMode(e.target.value as typeof mode)}>
        <option value="append">Thêm một cảnh</option><option value="develop">Phát triển một cảnh</option></select></div>
      <div><label htmlFor={`${id}-target`}>{mode === "append" ? "Thêm sau cảnh" : "Cảnh cần phát triển"}</label>
        <select id={`${id}-target`} value={chosenTarget} onChange={e => setTarget(e.target.value)}>
          <option value="">{mode === "append" ? "Cuối danh sách" : "Chọn một cảnh"}</option>
          {outline.scenes.map((s, i) => <option key={s.id} value={s.id}>{i + 1}. {s.title || "Chưa đặt tên"}</option>)}
        </select></div>
    </div>}
    <label htmlFor={`${id}-request`}>Bạn muốn gợi ý thêm điều gì? · tùy chọn</label>
    <textarea id={`${id}-request`} rows={2} maxLength={2000} value={instructions} onChange={e => setInstructions(e.target.value)} />
    <div className="scene-heading"><button type="button" disabled={uncertain || pending ||
      (!!outline.scenes.length && (mode === "develop" ? !chosenTarget : outline.scenes.length >= 60))}
      onClick={() => { const request_id = crypto.randomUUID(); setSent(request_id);
        void onSuggest({ request_id, mode: outline.scenes.length ? mode : "list", target_scene_id: chosenTarget || null, instructions });
      }}>{outline.scenes.length ? mode === "append" ? "Gợi ý thêm một cảnh" : "Gợi ý phát triển cảnh" : "Gợi ý danh sách cảnh ban đầu"}</button>
      <button type="button" className="secondary" onClick={async () => { if (await onInspect()) setSent(null); }}>Kiểm tra đề xuất đã lưu</button>
    </div>
    {(uncertain || pending) && <p role="status">Yêu cầu đã gửi hoặc chưa rõ kết quả. Không tự chạy lại.
      Kiểm tra đề xuất đã lưu; nếu còn đang xử lý, bạn vẫn có thể tự viết và lưu cảnh.</p>}
    {dirty && <p className="storage-note">Có sửa chưa lưu, gồm cả chỉnh trong bản xem trước. Nút Lưu thay đổi giữ bản xem trước riêng; chỉ Dùng mới đưa vào dàn cảnh.</p>}
    {(project.pending_scene_proposal_id || project.pending_staging_use) && <div><p className="storage-note">Đề xuất đang nằm trong bản sửa, chưa đánh dấu đã dùng cho tới khi lưu.
      Nếu muốn tiếp tục tự chỉnh cả story plan/ý đồ, có thể giữ cảnh như bản tự sửa; nguồn cũ và đề xuất gốc vẫn được giữ.</p>
      <button type="button" className="secondary" onClick={onKeepManual}>Giữ cảnh đang sửa như bản tự chỉnh</button></div>}
    {[...proposals].reverse().map(p => <details key={p.id} className="scene-proposal" open={p.status === "ready"}>
      <summary>Đề xuất {p.mode === "list" ? "danh sách" : p.mode === "append" ? "thêm cảnh" : "phát triển cảnh"} · {statusLabels[p.status]} · {new Date(p.created_at).toLocaleString("vi-VN")}</summary>
      <p className="storage-note">Nguồn dàn cảnh phiên bản {p.source_outline.version} · {p.model ?? "chưa gọi được model"} · {p.prompt_version}.</p>
      {p.status === "failed" && <p role="status">Lượt này lỗi ({p.error}). Cảnh đang viết vẫn được giữ. Không tự retry.</p>}
      {p.status === "pending" && <p role="status">Chưa có kết quả được lưu. Không coi đây là thất bại hay tự gọi lại model.</p>}
      <details><summary>Đối chiếu story plan và ý đồ đã dùng</summary>
        <p className="preserve-lines">{p.source_outline.source.draft.title}{"\n"}{p.source_outline.source.draft.logline}</p>
        <p className="preserve-lines">{p.source_outline.source.context.idea}{"\n"}{p.source_outline.source.context.constraints.join("\n")}</p>
        {p.source_outline.source.context.clarifications.map((a, i) => <p key={i} className="preserve-lines">{a.question}: {a.answer}</p>)}
        {p.source_outline.source.draft.sections.map((s, i) => <p key={i} className="preserve-lines">{s.title}{"\n"}{s.content}</p>)}
        {p.source_outline.scenes.map((s, i) => <p key={s.id} className="preserve-lines">Cảnh {i + 1}: {s.title}{"\n"}{s.action}</p>)}
        <p className="preserve-lines">Yêu cầu thêm: {p.instructions || "Không có"}</p>
      </details>
      {!!p.scenes.length && <SceneProposalPreview proposal={p} outline={outline.scenes} onUse={onUse}
        scenes={project.pending_scene_previews?.[p.id] ?? p.preview_scenes ?? p.scenes}
        onEdit={scenes => onPreviewChange(p.id, scenes)} eligible={canUse && (project.applicable_scene_proposal_ids ?? []).includes(p.id)} />}
      {!dirty && p.status === "ready" && !(project.applicable_scene_proposal_ids ?? []).includes(p.id) && <p role="status">Nguồn đã đổi; chỉ đọc để tham khảo, không tự gắn lại nguồn hoặc áp dụng.</p>}
      {p.status === "pending" && <p className="storage-note">Bỏ yêu cầu chỉ dừng chờ và không dùng kết quả; model trên máy chủ có thể vẫn chạy. Không tự gọi lại.</p>}
      {p.status !== "applied" && p.status !== "discarded" && <button type="button" className="secondary" onClick={() => onDiscard(p.id)}>{p.status === "pending" ? "Lưu sửa và bỏ yêu cầu đang chờ" : "Lưu sửa đang chờ và bỏ đề xuất"}</button>}
    </details>)}
  </section>;
}
const statusLabels = { pending: "chờ kết quả", ready: "chờ tác giả chọn", failed: "lỗi", applied: "đã dùng và lưu", discarded: "đã bỏ" };

function SceneProposalPreview({ proposal, outline, eligible, onUse, scenes, onEdit }: {
  proposal: SceneProposal; outline: Scene[]; eligible: boolean; scenes: Scene[]; onEdit: (scenes: Scene[]) => void;
  onUse: (scenes: Scene[], proposalId: string) => void;
}) {
  const id = useId();
  const [localError, setLocalError] = useState("");
  const editable = proposal.status === "ready";
  function useProposal() {
    if (!eligible || !scenes.length || scenes.some(s => !s.title.trim() || !s.action.trim())) return;
    let next: Scene[];
    if (proposal.mode === "list") next = scenes;
    else if (proposal.mode === "develop") next = outline.map(s => s.id === proposal.target_scene_id ? scenes[0] : s);
    else {
      const after = proposal.target_scene_id ? outline.findIndex(s => s.id === proposal.target_scene_id) + 1 : outline.length;
      next = [...outline.slice(0, after), ...scenes, ...outline.slice(after)];
    }
    if (next.length > 60) { setLocalError("Tối đa 60 cảnh. Hãy bớt cảnh trong bản xem trước."); return; }
    onUse(next, proposal.id);
  }
  return <div className="scene-proposal-preview">
    <p>{proposal.mode === "list" ? "Dùng sẽ đưa danh sách xem trước vào dàn cảnh rỗng." : proposal.mode === "develop"
      ? "Dùng sẽ thay nội dung cảnh được chọn; giữ ID, ghi chú tác giả và các lựa chọn dàn cảnh."
      : proposal.target_scene_id ? "Dùng sẽ thêm sau cảnh đã chọn; giữ mọi cảnh đang có." : "Dùng sẽ thêm ở cuối; giữ mọi cảnh đang có."} Chưa lưu cho tới khi bạn bấm Lưu thay đổi.</p>
    <ol>{scenes.map((scene, i) => <li key={scene.id}>
      <h4>Cảnh đề xuất {i + 1}</h4>
      {([ ["title", "Tên cảnh", 200], ["action", "Diễn tiến cảnh", 10000], ["location", "Địa điểm", 500],
        ["time", "Thời điểm", 200], ["characters", "Nhân vật", 2000], ["goal", "Nhân vật muốn gì?", 2000], ["purpose", "Mục đích cảnh", 2000] ] as const).map(([field, label, maxLength]) =>
        <div key={field}><label htmlFor={`${id}-${scene.id}-${field}`}>{label}</label><textarea id={`${id}-${scene.id}-${field}`} rows={field === "action" ? 4 : 2} maxLength={maxLength} value={scene[field]}
          readOnly={!editable} onChange={e => onEdit(scenes.map(s => s.id === scene.id ? { ...s, [field]: e.target.value } : s))} /></div>)}
      <p className="preserve-lines">Nhịp nối đề xuất: {proposal.transitions[scene.id] || "Chưa quyết định"}</p>
      {editable && <button type="button" className="secondary" onClick={() => onEdit(scenes.filter(s => s.id !== scene.id))}>Bỏ cảnh đề xuất {i + 1}</button>}
    </li>)}</ol>
    {editable && <button type="button" disabled={!eligible || !scenes.length || scenes.some(s => !s.title.trim() || !s.action.trim())} onClick={useProposal}>
      {proposal.mode === "list" ? "Dùng danh sách này" : "Dùng cảnh đề xuất này"}</button>}
    {localError && <p role="alert">{localError}</p>}
  </div>;
}
