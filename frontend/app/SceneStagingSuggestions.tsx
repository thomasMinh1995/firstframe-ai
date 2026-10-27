"use client";

import { useId, useState } from "react";
import type { Project } from "./projectsApi";
import { stagingGroups, stagingLabels, type Scene, type SceneSuggestionInput, type StagingIdea, type StagingUse } from "./sceneTypes";

export function SceneStagingSuggestions({ project, scene, canUse, onSuggest, onInspect, onEdit, onUse, onDiscard, onDiscardBatch }: {
  project: Project; scene: Scene; canUse: boolean;
  onSuggest: (input: SceneSuggestionInput) => Promise<void>; onInspect: () => Promise<boolean>;
  onEdit: (id: string, text: string) => void; onUse: (use: StagingUse, field: StagingIdea["field"]) => void;
  onDiscard: (proposalId: string, ideaId: string) => void; onDiscardBatch: (id: string) => void;
}) {
  const [sent, setSent] = useState<string | null>(null);
  const all = [...(project.scene_proposals ?? []), ...(project.staging_proposals ?? [])];
  const batches = (project.staging_proposals ?? []).filter(p => p.mode === "staging" && p.target_scene_id === scene.id);
  const uncertain = sent !== null && !all.some(p => p.id === sent);
  return <section className="staging-feedback" aria-label="Góp ý dàn cảnh có căn cứ">
    <h4>Thử cách thể hiện bằng hình ảnh</h4>
    <p className="storage-note">FirstFrame đưa phương án để bạn cân nhắc. Trích đoạn khớp nguồn không chứng minh cách diễn giải hoặc phương án là đúng.
      Chỉ dùng điều có ích; bạn vẫn tự viết và lưu được khi AI lỗi.</p>
    <div className="scene-heading"><button type="button" disabled={uncertain || all.some(p => p.status === "pending")}
      onClick={() => { const request_id = crypto.randomUUID(); setSent(request_id);
        void onSuggest({ request_id, mode: "staging", target_scene_id: scene.id, instructions: "" }); }}>Gợi ý cách dàn cảnh</button>
      <button type="button" className="secondary" onClick={async () => { if (await onInspect()) setSent(null); }}>Kiểm tra góp ý đã lưu</button></div>
    {uncertain && <p role="status">Chưa rõ kết quả yêu cầu. Kiểm tra góp ý đã lưu; không tự gọi AI lại.</p>}
    {[...batches].reverse().map(p => <details key={p.id} className="scene-proposal" open={p.status === "ready"}>
      <summary>Góp ý cảnh · nguồn M2 phiên bản {p.source_outline.version} · {p.status === "pending" ? "đang chờ" : p.status === "failed" ? "lỗi" : p.status === "discarded" ? "đã bỏ" : "đã giữ kết quả"}</summary>
      <p className="storage-note">Các phương án được giữ riêng, chưa tự thay cảnh.</p>
      {p.status === "pending" && <div><p role="status">Chưa rõ kết quả. Bỏ yêu cầu chỉ dừng chờ; model có thể vẫn chạy, kết quả đến sau sẽ không được dùng.</p>
        <button type="button" className="secondary" onClick={() => onDiscardBatch(p.id)}>Lưu sửa và bỏ yêu cầu dàn cảnh đang chờ</button></div>}
      {p.status === "failed" && <p role="status">Chưa có góp ý có nguồn hợp lệ ({p.error}). Bản đang viết vẫn được giữ.</p>}
      {p.staging_question && <p className="preserve-lines">Câu hỏi tham khảo: {p.staging_question}</p>}
      {p.status === "ready" && !p.staging_ideas?.length && <p role="status">Chưa có ý góp ý có căn cứ để chọn dùng. Bạn có thể bổ sung điều muốn giữ/tránh và yêu cầu lại khi cần.</p>}
      {p.status === "ready" && !(project.applicable_scene_proposal_ids ?? []).includes(p.id) && <p role="status">Nguồn đã đổi. Giữ góp ý để đọc; cần yêu cầu mới nếu muốn dùng theo nguồn hiện tại.</p>}
      {stagingGroups.map(group => {
        const ideas = (p.staging_ideas ?? []).filter(i => group.keys.includes(i.field));
        return ideas.length ? <section key={group.title}><h4>{group.title}</h4>{ideas.map(idea => <StagingIdeaCard key={idea.id}
          idea={idea} scene={scene} sources={p.staging_sources ?? []}
          text={project.pending_staging_edits?.[idea.id] ?? idea.preview_text ?? idea.suggestion}
          editable={p.status === "ready" && idea.status === "available"}
          eligible={canUse && (project.applicable_scene_proposal_ids ?? []).includes(p.id)}
          onEdit={text => onEdit(idea.id, text)} onUse={value => onUse({ proposal_id: p.id, idea_id: idea.id, value }, idea.field)}
          onDiscard={() => onDiscard(p.id, idea.id)} />)}</section> : null;
      })}
    </details>)}
  </section>;
}

function StagingIdeaCard({ idea, scene, text, sources, editable, eligible, onEdit, onUse, onDiscard }: {
  idea: StagingIdea; scene: Scene; text: string; sources: { id: string; label: string; text: string }[];
  editable: boolean; eligible: boolean; onEdit: (text: string) => void; onUse: (text: string) => void; onDiscard: () => void;
}) {
  const [editing, setEditing] = useState(false); const id = useId();
  return <article className="staging-idea" aria-label={`Ý góp ý: ${stagingLabels[idea.field]}`}>
    <h5>{stagingLabels[idea.field]}{idea.status === "applied" ? " · đã dùng và lưu" : idea.status === "discarded" ? " · đã bỏ" : ""}</h5>
    <div>{idea.evidence.map((e, i) => <blockquote key={i}><p className="preserve-lines">“{e.quote}”</p>
      <cite>{sources.find(s => s.id === e.source_id)?.label ?? "Nguồn đã lưu"}</cite></blockquote>)}</div>
    <p className="preserve-lines"><strong>Vì sao gợi ý: </strong>{idea.reason}</p>
    <p className="preserve-lines"><strong>Tác động dự kiến: </strong>{idea.purpose}</p>
    {editing && editable ? <div><label htmlFor={id}>Phương án tự chỉnh: {stagingLabels[idea.field]}</label>
      <textarea id={id} rows={3} maxLength={2000} value={text} onChange={e => onEdit(e.target.value)} /></div>
      : <p className="preserve-lines"><strong>Phương án: </strong>{idea.status === "applied" ? idea.applied_text ?? text : text}</p>}
    {editable && <><p className="storage-note">Dùng ý chỉ thay mục “{stagingLabels[idea.field]}”; diễn tiến và story plan được giữ.
      {scene.staging_choices[idea.field] ? ` Mục này đang có nội dung: ${scene.staging_choices[idea.field]}. Dùng ý sẽ thay nội dung đó; bạn có thể hoàn tác trước khi sửa tiếp.` : " Chọn dùng chưa đồng nghĩa đã lưu."}</p>
      <div className="scene-order"><button type="button" disabled={!eligible || !text.trim()} onClick={() => onUse(text)}>Dùng ý: {stagingLabels[idea.field]}</button>
        <button type="button" className="secondary" onClick={() => { setEditing(!editing); if (!editing) requestAnimationFrame(() => document.getElementById(id)?.focus()); }}>{editing ? "Xong" : "Chỉnh ý"}</button>
        <button type="button" className="secondary" onClick={onDiscard}>Bỏ ý: {stagingLabels[idea.field]}</button></div></>}
  </article>;
}
