"use client";

import {useEffect,useState} from "react";
import type {Project} from "./projectsApi";
import type {Screenplay, ScriptScene, SceneWritingInput} from "./screenplayTypes";
import {stagingLabels, type StagingKey} from "./sceneTypes";
import {ScriptSceneFields} from "./ScriptSceneFields";
import {ScreenplayProposals} from "./ScreenplayProposals";
import {ScreenplayFeedback} from "./ScreenplayFeedback";
import type {ReviewAssessment,ReviewSource} from "./screenplayReviewTypes";
import "./screenplay.css";

export function ScreenplayEditor({project, dirty, sourceDirty, onChange, onStart, onRestore, onSave, onInspect, onWrite, onProposalInspect, onPreview, onDiscard, canUse, onReview, onReviewInspect, onReviewDiscard, onReviewAssess, canNavigateReview}: {
  onReview:(input:SceneWritingInput)=>Promise<void>;onReviewInspect:()=>Promise<boolean>;onReviewDiscard:(id:string)=>void;
  onReviewAssess:(reviewId:string,noteId:string,value:ReviewAssessment)=>void;canNavigateReview:boolean;
  project: Project; dirty: boolean; sourceDirty: boolean;
  onChange: (script: Screenplay, proposalId?: string) => void;
  onWrite:(input:SceneWritingInput)=>Promise<void>;onProposalInspect:()=>Promise<boolean>;
  onPreview:(id:string,scene:ScriptScene)=>void;onDiscard:(id:string)=>void;canUse:boolean; onStart: (requestId: string) => Promise<void>;
  onRestore: (id: string) => void; onSave: () => void; onInspect: () => Promise<boolean>;
}) {
  const [pendingReference,setPendingReference]=useState<ReviewSource|null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [replace, setReplace] = useState(false);
  const [undo, setUndo] = useState<{before: Screenplay; after: string; label:string} | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const script = project.screenplay;
  const uncertain = sent !== null && script?.id !== sent && !project.screenplay_versions?.some(v=>v.screenplay.id===sent);
  const scene = script?.scenes.find(s=>s.id===selected) ?? script?.scenes[0];
  const source = script?.source_outline.scenes.find(s=>s.id===scene?.source_scene_id);
  const edit = (next: ScriptScene) => script && onChange({...script,scenes:script.scenes.map(s=>s.id===next.id?next:s)});
  useEffect(()=>{
    if(!pendingReference||!canNavigateReview)return;
    const frame=requestAnimationFrame(()=>{
      const ref=pendingReference;
      const owner=script?.scenes.find(s=>s.id===ref.scene_id),block=owner?.blocks.find(b=>b.id===ref.block_id);
      const text=ref.field==='heading'?owner?.heading:ref.field==='speaker'?block?.speaker:block?.text;
      if(text===ref.text){
        const node=ref.block_id?document.querySelector<HTMLElement>(`.screenplay-columns [data-script-block="${ref.block_id}"] ${ref.field==='speaker'?'input':'textarea'}`)
          :document.querySelector<HTMLElement>('.screenplay-columns .screenplay-scene input');
        node?.scrollIntoView({block:'center'});node?.focus({preventScroll:true});
      }
      setPendingReference(null);
    });return()=>cancelAnimationFrame(frame);
  },[pendingReference,scene?.id,script,canNavigateReview]);
  function remove(id: string) {
    if (!scene || !script) return;
    const next={...script,scenes:script.scenes.map(s=>s.id===scene.id?{...s,blocks:s.blocks.filter(b=>b.id!==id)}:s)};
    setUndo({before:structuredClone(script),after:JSON.stringify(next),label:"Hoàn tác xóa khối"});onChange(next);
  }
  return <section className="panel screenplay" data-workspace-stage="workspace-script" aria-label="M3 Kịch bản">
    <h2 id="workspace-script" tabIndex={-1}>M3 · Viết kịch bản</h2>
    <p>Viết bằng hành động và lời thoại theo từng cảnh. Không bắt buộc có lời thoại hoặc hình phác. Bạn có thể tự viết, nhờ AI viết thử một cảnh hoặc nhận góp ý để tự sửa. Quyết định vẫn thuộc về bạn.</p>
    <details><summary>Bắt đầu từ dàn cảnh nào?</summary>
      <p>Lưu mọi sửa đang chờ trước khi bắt đầu. Nguồn M2 được giữ riêng; sửa dàn cảnh sau đó không tự thay kịch bản. Muốn đổi cấu trúc cảnh, sửa M2 rồi chủ động bắt đầu bản khác.</p>
      {project.scene_handoff ? <p>M2 phiên bản {project.scene_handoff.version} · {project.scene_handoff.scenes.length} cảnh · {project.scene_outline?.source.draft.title}</p>
        : <p>Cần lưu tên và diễn tiến cho mọi cảnh M2 trước khi bắt đầu. Bạn vẫn lưu nháp M2 được.</p>}
      {project.scene_outline?.scenes.map((s,i)=><p key={s.id} className="preserve-lines">{i+1}. {s.title}: {s.action}</p>)}
    </details>
    {script && <label><input type="checkbox" checked={replace} onChange={e=>setReplace(e.target.checked)} />Tôi muốn bắt đầu bản khác từ M2 đã lưu; bản kịch bản hiện tại sẽ giữ trong lịch sử.</label>}
    <button type="button" disabled={uncertain || (!!script&&!replace) || !project.scene_outline?.scenes.length || project.scene_outline.scenes.some(s=>!s.title.trim()||!s.action.trim())}
      onClick={()=>{const id=crypto.randomUUID();setSent(id);setReplace(false);void onStart(id);}}>{script?"Bắt đầu bản kịch bản khác":"Bắt đầu viết từ bản dàn cảnh này"}</button>
    <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra kịch bản đã lưu</button>
    {uncertain && <p role="status">Chưa rõ kết quả bắt đầu bản mới. Kiểm tra bản đã lưu trước; không tự gửi lại.</p>}
    {script && scene && <>
      <p role="status">Bản kịch bản phiên bản {script.version} · {dirty?"Có sửa chưa lưu trong dự án":"Đang xem bản đã lưu"}.</p>
      {(!project.screenplay_source_is_current || sourceDirty) && <p role="status">Dàn cảnh hoặc ý đồ hiện tại khác nguồn kịch bản. Giữ bản nguồn trước; không tự đồng bộ.</p>}
      <nav aria-label="Các cảnh kịch bản">{script.scenes.map((s,i)=><button key={s.id} type="button" aria-pressed={s.id===scene.id}
        onClick={()=>setSelected(s.id)}>{i+1}. {s.heading || "Cảnh chưa đặt tiêu đề"}{!s.blocks.some(b=>b.text.trim())?" · chưa viết":""}</button>)}</nav>
      <div className="screenplay-columns">
        <details className="screenplay-source" open><summary>Nguồn M2 của cảnh đang viết</summary>
          <p>Đây là nguồn được giữ lúc bắt đầu, không phải bản soạn.</p>
          {source && <><h3>{source.title}</h3><p className="preserve-lines">{source.action}</p>
            {(["location","time","characters","goal","purpose","viewer_intent","keep_or_avoid"] as const).map((key,i)=>source[key]&&<p key={key} className="preserve-lines"><strong>{["Địa điểm","Thời điểm","Nhân vật","Mục tiêu","Đóng góp","Cảm nhận","Giữ/tránh"][i]}: </strong>{source[key]}</p>)}
            {Object.entries(source.staging_choices).map(([key,value])=><p key={key} className="preserve-lines"><strong>{stagingLabels[key as StagingKey]}: </strong>{value}</p>)}
          </>}
          <details><summary>Story plan và ý đồ đi cùng nguồn</summary>
            <h4>{script.source_outline.source.draft.title}</h4><p className="preserve-lines">{script.source_outline.source.draft.logline}</p>
            {script.source_outline.source.draft.sections.map((s,i)=><p key={i} className="preserve-lines">{s.title}: {s.content}</p>)}
            <p className="preserve-lines">{script.source_outline.source.context.idea}</p>
            {script.source_outline.source.context.constraints.map((c,i)=><p key={i} className="preserve-lines">{c}</p>)}
            {script.source_outline.source.context.pending_questions.map((q,i)=><p key={i}>Chưa quyết định: {q.question}</p>)}
            {script.source_outline.source.context.clarifications.map((c,i)=><p key={i} className="preserve-lines">{c.question} — {c.answer}</p>)}
          </details>
        </details>
        <ScriptSceneFields key={scene.id} scene={scene} onChange={edit} onDelete={remove}/>
      </div>
      {undo && JSON.stringify(script)===undo.after && <button type="button" onClick={()=>{onChange(undo.before);setUndo(null);}}>{undo.label}</button>}
      <ScreenplayProposals key={`${script.id}:${scene.id}`} project={project} scene={scene} canUse={canUse}
        onWrite={onWrite} onInspect={onProposalInspect} onPreview={onPreview} onDiscard={onDiscard}
        onUse={(id,replacement)=>{
          const next={...script,scenes:script.scenes.map(s=>s.id===replacement.id?replacement:s)};
          setUndo({before:structuredClone(script),after:JSON.stringify(next),label:"Hoàn tác dùng phương án"});onChange(next,id);
        }}/>
      <ScreenplayFeedback key={`review:${script.id}:${scene.id}`} project={project} scene={scene} canNavigate={canNavigateReview}
        onReview={onReview} onInspect={onReviewInspect} onDiscard={onReviewDiscard} onAssess={onReviewAssess}
        onNavigate={source=>{if(canNavigateReview&&source.scene_id){setSelected(source.scene_id);setPendingReference(source);}}}/>
      <button type="button" onClick={onSave}>Lưu kịch bản</button>
      <p>Chuyển cảnh chỉ giữ phần đang viết trên màn hình. Lưu để mở lại; bản nháp không cần đủ mọi cảnh. M4 xuất bản chưa triển khai.</p>
    </>}
    {!!project.screenplay_versions?.length && <details className="screenplay-history"><summary>Lịch sử kịch bản ({project.screenplay_versions.length})</summary>
      <p>Khôi phục sẽ lưu mọi sửa đang chờ trước, giữ bản hiện tại trong lịch sử; không thay M1/M2.</p>
      {[...project.screenplay_versions].reverse().map(v=><div key={v.id}><span>Bản {v.screenplay.version} · {v.created_at} · nguồn M2 {v.screenplay.source_outline.version}</span>
        <details><summary>Đọc phiên bản này</summary>{v.screenplay.scenes.map(s=><div key={s.id}><h4>{s.heading}</h4>{s.blocks.map(b=><p key={b.id} className="preserve-lines">{b.kind==="dialogue"&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</div>)}</details>
        <button type="button" onClick={()=>onRestore(v.id)}>Khôi phục kịch bản này</button></div>)}
    </details>}
  </section>;
}
