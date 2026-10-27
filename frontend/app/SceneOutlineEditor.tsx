"use client";

import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from "react";
import type { Project } from "./projectsApi";
import { emptyScene, stagingLabels, type Scene, type SceneOutline, type StagingKey, type SceneSuggestionInput, type StagingUse, stagingGroups } from "./sceneTypes";
import { StoryPath } from "./StoryPlanEditor";
import { SceneStagingSuggestions } from "./SceneStagingSuggestions";
import { SceneSuggestions } from "./SceneSuggestions";
import {SceneSketchPanel, SketchImage, type SketchInput} from "./SceneSketchPanel";
import { IntentDetails } from "./AuthorIntentCard";
import "./sceneOutline.css";

type Tab = "content" | "staging" | "sketch";
const tabs: [Tab, string][] = [["content", "Nội dung"], ["staging", "Dàn cảnh"], ["sketch", "Phác hình"]];
const groups = stagingGroups;

export function SceneOutlineEditor({ project, saved, dirty, sourceCurrent, error, onChange, onStart, onRestore, onPrepare, onSave, onSuggest, onInspect, onDiscard, onPreviewChange, canUseProposal, onStagingEdit, onDiscardIdea, onSketch, onSketchDecision }: {
  project: Project; saved: Project; dirty: boolean; sourceCurrent: boolean;
  onChange: (outline: SceneOutline, proposalId?: string | null, stagingUse?: StagingUse | null) => void; onStart: (versionId: string) => void;
  onRestore: (versionId: string) => void; onPrepare: () => void;
  onSave: () => void;
  onStagingEdit: (id: string, text: string) => void; onDiscardIdea: (proposalId: string, ideaId: string) => void;
  onSketch: (input: SketchInput) => Promise<void>; onSketchDecision: (id: string, action: "keep" | "discard") => void;
  error: string | null; canUseProposal: boolean; onPreviewChange: (id: string, scenes: Scene[]) => void;
  onSuggest: (input: SceneSuggestionInput) => Promise<void>; onInspect: () => Promise<boolean>; onDiscard: (id: string) => void;
}) {
  const outline = project.scene_outline;
  const [source, setSource] = useState("current");
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("content");
  const [editingChoice, setEditingChoice] = useState<StagingKey | null>(null);
  const [notice, setNotice] = useState("");
  const [undo, setUndo] = useState<{ before: Scene[]; after: string; proposalId?: string; stagingUse?: StagingUse } | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLOListElement>(null);
  const id = useId();
  const selectedScene = outline?.scenes.find(s => s.id === selected);
  useEffect(() => {
    const node = dialog.current;
    if (node && selectedScene && !node.matches(":popover-open")) {
      node.showPopover(); node.querySelector<HTMLButtonElement>("[data-close-scene]")?.focus();
    }
    if (selected && !selectedScene) setSelected(null);
  }, [selected, selectedScene]);
  function close() {
    dialog.current?.hidePopover();
    setSelected(null); setEditingChoice(null);
    requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(`[data-select-scene="${selected}"]`)?.focus());
  }
  function choose(sceneId: string) { setTab("content"); setEditingChoice(null); setSelected(sceneId); }
  function changeScene(patch: Partial<Scene>) {
    if (outline && selected) onChange({ ...outline, scenes: outline.scenes.map(s => s.id === selected ? { ...s, ...patch } : s) });
  }
  function replace(scenes: Scene[], message: string) {
    if (!outline) return;
    setUndo({ before: structuredClone(outline.scenes), after: JSON.stringify(scenes), proposalId: project.pending_scene_proposal_id, stagingUse: project.pending_staging_use });
    onChange({ ...outline, scenes }); setNotice(message);
  }
  function add() {
    if (!outline || outline.scenes.length >= 60) return;
    const scene = emptyScene(); replace([...outline.scenes, scene], "Đã thêm cảnh trong bản chưa lưu."); choose(scene.id);
  }
  function remove(sceneId: string) {
    if (!outline) return;
    replace(outline.scenes.filter(s => s.id !== sceneId), "Đã bỏ cảnh trong bản chưa lưu. Có thể hoàn tác nếu chưa sửa tiếp.");
    if (selected === sceneId) close();
  }
  function move(delta: number) {
    if (!outline) return;
    const scenes = [...outline.scenes], from = scenes.findIndex(s => s.id === selected), to = from + delta;
    if (from < 0 || to < 0 || to >= scenes.length) return;
    [scenes[from], scenes[to]] = [scenes[to], scenes[from]];
    replace(scenes, "Đã đổi thứ tự cảnh; ID và nội dung được giữ nguyên.");
  }
  function undoChange() {
    if (!outline || !undo) return;
    if (JSON.stringify(outline.scenes) !== undo.after) {
      setNotice("Bạn đã sửa tiếp. Không tự ghi đè phần mới để hoàn tác."); return;
    }
    onChange({ ...outline, scenes: structuredClone(undo.before) }, undo.proposalId ?? null, undo.stagingUse ?? null); setUndo(null); setNotice("Đã hoàn tác trong bản chưa lưu.");
  }
  const fields = (key: keyof Omit<Scene, "id" | "staging_choices">, label: string, maxLength = 2000, rows = 2) => selectedScene &&
    <div className="scene-field" key={key}><label htmlFor={`${id}-${key}`}>{label}</label>
      {key === "title" ? <input id={`${id}-${key}`} value={selectedScene[key]} maxLength={maxLength}
        onChange={e => changeScene({ [key]: e.target.value })} />
        : <textarea id={`${id}-${key}`} value={selectedScene[key]} rows={rows} maxLength={maxLength}
          onChange={e => changeScene({ [key]: e.target.value })} />}</div>;

  return <section className="scene-outline panel" data-workspace-stage="workspace-outline" aria-labelledby="workspace-outline">
    <header className="scene-heading"><div><p className="eyebrow">M2 · Dàn cảnh</p>
      <h2 id="workspace-outline" tabIndex={-1}>Kể câu chuyện qua từng cảnh</h2></div>
      {outline && <button type="button" onClick={add} disabled={outline.scenes.length >= 60}>Tự thêm cảnh</button>}</header>
    <SceneHint title="Bắt đầu từ đâu?">
      <ol aria-label="Ba bước dàn cảnh">
        <li>Chọn một story plan đã lưu. Tự thêm cảnh, hoặc nhờ FirstFrame gợi ý danh sách khi chưa có cảnh.</li>
        <li>Mở card để viết diễn tiến ở Nội dung. Sang Dàn cảnh nếu muốn cân nhắc cách thể hiện; hai câu hỏi đều tùy chọn.
          Đọc nguồn và lý do trước khi dùng, chỉnh hoặc bỏ từng góp ý. Góp ý có thể sai; bạn tự quyết định.</li>
        <li>Lưu thay đổi rồi đối chiếu bản đã lưu để viết tiếp. Đóng card hoặc Xong giữ phần đang viết, chưa lưu.
          Bạn không cần dùng AI hoặc có ảnh để hoàn tất dàn cảnh.</li>
      </ol>
      <p>Gợi ý AI sẽ lưu các sửa đang chờ trước khi gửi yêu cầu. Nếu lỗi, kiểm tra góp ý đã lưu; không tự chạy lại.</p>
    </SceneHint>
    {!outline ? <div className="scene-start">
      <label htmlFor={`${id}-source`}>Story plan nguồn</label>
      <select id={`${id}-source`} value={source} onChange={e => setSource(e.target.value)}>
        <option value="current" disabled={!saved.draft}>Bản story plan hiện tại đã lưu</option>
        {[...saved.versions].reverse().map((v, i) => <option key={v.id} value={v.id}>
          Bản lịch sử {saved.versions.length - i} · {v.draft.title || "Chưa đặt tên"}</option>)}
      </select>
      {!saved.draft && !saved.versions.length && <p>Chưa có story plan đã lưu để chọn làm nguồn.</p>}
      <button type="button" disabled={source === "current" && !saved.draft} onClick={() => onStart(source)}>
        {dirty ? "Lưu thay đổi và bắt đầu dàn cảnh" : "Bắt đầu dàn cảnh từ bản đã chọn"}</button>
      <p className="storage-note">Tạo bản dàn cảnh rỗng và giữ nguồn trên máy; không tự tạo cảnh hoặc gọi AI.</p>
    </div> : <>
      <details className="scene-source"><summary>Story plan và ý đồ nguồn · M2 phiên bản {outline.version}</summary>
        <p>Nguồn {outline.source.version_id === "current" ? "bản hiện tại khi bắt đầu" : "bản lịch sử đã chọn"}, revision dự án {outline.source.project_revision}.</p>
        <p className="preserve-lines">{outline.source.draft.title}{"\n"}{outline.source.draft.logline}</p>
        <IntentDetails context={outline.source.context} />
        {outline.source.draft.sections.map((s, i) => <div key={i}><h4>{s.title}</h4><p className="preserve-lines">{s.content}</p></div>)}
      </details>
      {!sourceCurrent && <p className="form-message" role="status">Story plan hoặc ý đồ hiện tại khác nguồn đã chọn.
        Dàn cảnh vẫn giữ nguồn riêng; không tự cập nhật hoặc ghi đè.</p>}
      <SceneSuggestions project={project} dirty={dirty} onSuggest={onSuggest} onInspect={onInspect} onDiscard={onDiscard}
        onPreviewChange={onPreviewChange} canUse={canUseProposal}
        onKeepManual={() => { onChange(outline, null, null); setUndo(null);
          setNotice("Đã giữ nội dung để tự chỉnh; chưa lưu và không đánh dấu đề xuất đã dùng. Nguồn dàn cảnh vẫn giữ nguyên."); }}
        onUse={(scenes, proposalId) => { setUndo({ before: structuredClone(outline.scenes), after: JSON.stringify(scenes), proposalId: project.pending_scene_proposal_id, stagingUse: project.pending_staging_use });
          onChange({ ...outline, scenes }, proposalId, null);
          setNotice("Đã đưa đề xuất vào bản đang sửa. Bạn tự chỉnh và lưu; AI chưa xác nhận chất lượng."); }} />
      <div className="scene-heading"><span>TRÌNH TỰ CẢNH · đọc theo mũi tên</span><span>{outline.scenes.length} cảnh</span></div>
      <div className="scene-canvas"><StoryPath list={list} count={outline.scenes.length} orderKey={outline.scenes.map(s => s.id).join()} />
        <ol ref={list} className="scene-path" aria-label="Danh sách cảnh">
          {outline.scenes.map((s, i) => <li key={s.id} data-scene-id={s.id} style={{
            "--wide-row": Math.floor(i / 3) + 1, "--wide-column": Math.floor(i / 3) % 2 ? 3 - i % 3 : i % 3 + 1,
            "--row": Math.floor(i / 2) + 1, "--column": Math.floor(i / 2) % 2 ? 2 - i % 2 : i % 2 + 1,
          } as CSSProperties}>
            <button type="button" className="scene-select" data-select-scene={s.id} aria-haspopup="dialog"
              aria-expanded={selected === s.id} onClick={() => choose(s.id)}>
              <span className="eyebrow">Cảnh {i + 1}</span>{project.selected_scene_sketches?.[s.id]
                ? <><SketchImage key={project.selected_scene_sketches[s.id]} projectId={project.id} sketchId={project.selected_scene_sketches[s.id]} alt={`Hình phác đã giữ: ${s.title}`} />
                  {(dirty || !(project.applicable_sketch_ids??[]).includes(project.selected_scene_sketches[s.id])) && <span>Hình đã giữ thuộc bản nguồn trước; xem lại trong Phác hình.</span>}</>
                : <span className="scene-image-empty">Chưa có hình phác</span>}
              <strong>{s.title || "Cảnh chưa đặt tên"}</strong><span>{s.location || "Chưa chọn địa điểm"}</span>
              <span className="scene-excerpt">{s.action || "Chọn để viết diễn tiến cảnh."}</span>
            </button>
            <button type="button" className="secondary" onClick={() => remove(s.id)} aria-label={`Xóa cảnh ${i + 1}: ${s.title || "chưa đặt tên"}`}>Xóa cảnh</button>
          </li>)}
        </ol>
      </div>
      {!outline.scenes.length && <p className="storage-note">Chưa có cảnh nào. Chọn Tự thêm cảnh để bắt đầu; không cần đủ một số lượng cảnh cố định.</p>}
      <div className="scene-heading"><p role="status">{notice}</p>{undo && <button type="button" className="secondary" onClick={undoChange}>Hoàn tác thao tác cảnh</button>}</div>
      {selectedScene && <div ref={dialog} popover="auto" className="scene-popover" role="dialog" aria-labelledby={`${id}-dialog-title`}
        onToggle={e => { if (e.target === e.currentTarget && (e.nativeEvent as ToggleEvent).newState === "closed") { setSelected(null); setEditingChoice(null); } }}>
        <header className="scene-heading"><h3 id={`${id}-dialog-title`}>Chi tiết cảnh {outline.scenes.findIndex(s => s.id === selected) + 1}</h3>
          <button type="button" data-close-scene className="secondary" onClick={close}>Đóng</button></header>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="scene-heading"><span className="storage-note">Đóng hoặc Esc giữ phần đang sửa.</span><div className="scene-order">
          <button type="button" disabled={outline.scenes[0].id === selected} onClick={() => move(-1)}>Lên trước</button>
          <button type="button" disabled={outline.scenes.at(-1)?.id === selected} onClick={() => move(1)}>Xuống sau</button></div></div>
        {fields("title", "Tên cảnh", 200)}
        <div className="scene-tabs" role="tablist" aria-label="Các phần nội dung cảnh" onKeyDown={e => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
          e.preventDefault(); const index = tabs.findIndex(([key]) => key === tab);
          const next = e.key === "Home" ? 0 : e.key === "End" ? 2 : (index + (e.key === "ArrowRight" ? 1 : 2)) % 3;
          setTab(tabs[next][0]); document.getElementById(`${id}-tab-${tabs[next][0]}`)?.focus();
        }}>{tabs.map(([key, label]) => <button key={key} type="button" role="tab" id={`${id}-tab-${key}`}
          aria-controls={`${id}-panel-${key}`} aria-selected={tab === key} tabIndex={tab === key ? 0 : -1}
          onClick={() => setTab(key)}>{label}</button>)}</div>
        {tabs.map(([key]) => <div key={key} role="tabpanel" id={`${id}-panel-${key}`} aria-labelledby={`${id}-tab-${key}`} hidden={tab !== key}>
          {key === "content" && <>{fields("action", "Chuyện gì xảy ra trong cảnh này?", 10000, 5)}
            <div className="scene-pair">{fields("location", "Địa điểm", 500)}{fields("time", "Thời điểm", 200)}</div>
            {fields("characters", "Nhân vật xuất hiện")}{fields("goal", "Nhân vật muốn gì?")}{fields("purpose", "Cảnh đóng góp gì cho câu chuyện?")}</>}
          {key === "staging" && <><SceneHint title="Kể cảnh này bằng hình ảnh">Không cần điền thuật ngữ điện ảnh.
            Hai câu hỏi dưới đây đều tùy chọn; FirstFrame dựa vào cảnh và ý đồ đã lưu để gợi ý, bạn tự quyết định.</SceneHint>
            {fields("viewer_intent", "Bạn muốn người xem cảm nhận điều gì? · tùy chọn")}
            {fields("keep_or_avoid", "Có chi tiết nào muốn giữ hoặc tránh? · tùy chọn")}
            <SceneStagingSuggestions project={project} scene={selectedScene} canUse={canUseProposal}
              onSuggest={onSuggest} onInspect={onInspect} onEdit={onStagingEdit} onDiscard={onDiscardIdea} onDiscardBatch={onDiscard}
              onUse={(use, field) => {
                const scenes = outline.scenes.map(s => s.id === selected ? { ...s,
                  staging_choices: { ...s.staging_choices, [field]: use.value } } : s);
                setUndo({ before: structuredClone(outline.scenes), after: JSON.stringify(scenes),
                  proposalId: project.pending_scene_proposal_id, stagingUse: project.pending_staging_use });
                onChange({ ...outline, scenes }, null, use); setNotice("Đã dùng một ý trong bản chưa lưu; chỉ thay mục đã nêu.");
              }} />
            <details className="scene-choices"><summary>Các lựa chọn đang giữ · xem hoặc tự chỉnh</summary>
              {groups.map(group => <section key={group.title}><h4>{group.title}</h4>{group.keys.map(choice => <div className="scene-choice" key={choice}>
                <div className="scene-heading"><span>{stagingLabels[choice]}</span>
                  <button type="button" className="secondary" onClick={() => setEditingChoice(editingChoice === choice ? null : choice)}>{editingChoice === choice ? "Xong" : "Tự chỉnh"}</button></div>
                {editingChoice === choice ? <textarea aria-label={stagingLabels[choice]} maxLength={2000} rows={2}
                  value={selectedScene.staging_choices[choice] ?? ""} onChange={e => changeScene({ staging_choices: {
                    ...selectedScene.staging_choices, [choice]: e.target.value,
                  } })} /> : <p className="preserve-lines">{selectedScene.staging_choices[choice] || "Chưa quyết định"}</p>}
              </div>)}</section>)}
            </details></>}
          {key === "sketch" && <SceneSketchPanel key={selectedScene.id} project={project} scene={selectedScene} dirty={dirty}
            onGenerate={onSketch} onInspect={onInspect} onDecide={onSketchDecision} />}
        </div>)}
        <div className="scene-heading"><p className="storage-note">{dirty ? "Có thay đổi chưa lưu trong dự án." : "Đang xem bản đã lưu."}</p>
          <button type="button" onClick={onSave}>Lưu thay đổi dàn cảnh</button></div>
      </div>}
      <div className="scene-next"><button type="button" disabled={!outline.scenes.length || outline.scenes.some(s => !s.title.trim() || !s.action.trim())}
        onClick={onPrepare}>Lưu bản dàn cảnh để viết tiếp</button>
        <p className="storage-note">Thao tác này lưu bản nguồn để đối chiếu; bắt đầu soạn thủ công tại M3. Không tạo nội dung hoặc gọi AI.</p>
        {saved.scene_handoff && <details className="scene-handoff">
          <summary>Đối chiếu bản dàn cảnh đã lưu để viết tiếp</summary>
          <p className="storage-note">Bản nguồn đã lưu: M2 phiên bản {saved.scene_handoff.version}, revision dự án {saved.scene_handoff.project_revision} · {saved.scene_handoff.scenes.length} cảnh.</p>
          {dirty && <p role="status">Có sửa chưa lưu. Bản dưới đây chỉ gồm nội dung đã lưu, chưa nhận các sửa trên màn hình.</p>}
          <p className="preserve-lines">Story plan nguồn: {saved.scene_outline?.source.draft.title || "Chưa đặt tên"}</p>
          {!saved.scene_source_is_current && <p role="status">Story plan hoặc ý đồ hiện tại khác nguồn này; bản bàn giao vẫn giữ nguồn đã chọn, không tự đồng bộ.</p>}
          <ol aria-label="Các cảnh trong bản đã lưu">{saved.scene_handoff.scenes.map(s => <li key={s.id} data-handoff-scene={s.id}>
            <h4>{s.title}</h4><p className="preserve-lines">{s.action}</p>
            {(["location", "time", "characters", "goal", "purpose", "viewer_intent", "keep_or_avoid"] as const).map((key, i) => s[key] && <p key={key} className="preserve-lines">
              <strong>{["Địa điểm", "Thời điểm", "Nhân vật", "Nhân vật muốn gì", "Đóng góp của cảnh", "Cảm nhận người xem", "Điều muốn giữ/tránh"][i]}: </strong>{s[key]}</p>)}
            {Object.entries(s.staging_choices).map(([key, text]) => text && <p key={key} className="preserve-lines"><strong>{stagingLabels[key as StagingKey]}: </strong>{text}</p>)}
          </li>)}</ol>
          <p className="storage-note">Chỉ những lựa chọn đã đưa vào cảnh và lưu mới có trong bản này; các đề xuất riêng không được tự nhận. M3 hỗ trợ soạn thủ công từ bản này; AI viết thử chưa triển khai.</p>
        </details>}
      </div>
      {!!project.scene_versions?.length && <details className="scene-history"><summary>Lịch sử dàn cảnh ({project.scene_versions.length})</summary>
        <p className="storage-note">Khôi phục sẽ lưu mọi sửa đang chờ trước; chỉ thay dàn cảnh, giữ story plan hiện tại.</p>
        {[...project.scene_versions].reverse().map(v => <div key={v.id}><p>Phiên bản {v.outline.version} · {new Date(v.created_at).toLocaleString("vi-VN")} · {v.outline.scenes.length} cảnh</p>
          <button type="button" className="secondary" onClick={() => onRestore(v.id)}>Khôi phục dàn cảnh phiên bản {v.outline.version}</button></div>)}
      </details>}
    </>}
  </section>;
}

function SceneHint({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false); const id = useId();
  return <div className="scene-help"><div className="scene-help-heading"><h4>{title}</h4>
    <button type="button" className="scene-info" aria-label={`Thông tin: ${title}`} aria-expanded={open} aria-controls={id}
      onClick={() => setOpen(!open)}>ⓘ</button></div>
    <div className={`scene-help-content${open ? " is-open" : ""}`} id={id} aria-hidden={!open}><div><div className="storage-note">{children}</div></div></div>
  </div>;
}
