"use client";

import {ReviewPanel} from "./ReviewPanel";
import {useEffect,useId,useMemo,useRef,useState} from "react";
import type {Project} from "./projectsApi";
import type {Screenplay, ScriptScene, SceneWritingInput, ScreenplaySelectionInput} from "./screenplayTypes";
import {ScreenplayReading, SavedScript} from "./ScreenplayReading";
import {stagingLabels, type StagingKey} from "./sceneTypes";
import {screenplaySketches} from "./screenplaySketches";
import {SketchImage} from "./SceneSketchPanel";
import {ScriptSceneFields} from "./ScriptSceneFields";
import {ContinuousSceneEditor} from "./ContinuousSceneEditor";
import {ScreenplayProposals} from "./ScreenplayProposals";
import {ScreenplayFeedback} from "./ScreenplayFeedback";
import type {ReviewAssessment,ReviewSource} from "./screenplayReviewTypes";
import {SceneHint} from "./SceneHint";
import "./screenplay.css";

const undoContent = (script: Screenplay) => JSON.stringify({id:script.id, scenes:script.scenes, source:script.source_outline.id});

export function ScreenplayEditor({project, savedProject, onSelectSource, onDownloadPdf, onSourceInspect, dirty, sourceDirty, onChange, onStart, onSave, onInspect, onWrite, onProposalInspect, onPreview, onDiscard, canUse, onReview, onReviewInspect, onReviewDiscard, onReviewAssess, canNavigateReview,onApply,onUndoProposal,onStructural,busy=false}: {
  busy?:boolean;onApply?:(id:string,scene:ScriptScene)=>void;onUndoProposal?:(id:string)=>void;onStructural?:(instructions:string)=>void;
  savedProject:Project;onSelectSource:(input:ScreenplaySelectionInput,read:Screenplay)=>Promise<void>;onDownloadPdf?:(selectionId:string)=>Promise<void>;onSourceInspect:()=>Promise<boolean>;
  onReview:(input:SceneWritingInput)=>Promise<void>;onReviewInspect:()=>Promise<boolean>;onReviewDiscard:(id:string)=>void;
  onReviewAssess:(reviewId:string,noteId:string,value:ReviewAssessment)=>void;canNavigateReview:boolean;
  project: Project; dirty: boolean; sourceDirty: boolean;
  onChange: (script: Screenplay, proposalId?: string) => void;
  onWrite:(input:SceneWritingInput)=>Promise<void>;onProposalInspect:()=>Promise<boolean>;
  onPreview:(id:string,scene:ScriptScene)=>void;onDiscard:(id:string)=>void;canUse:boolean; onStart: (requestId: string) => Promise<void>;
  onSave: () => void; onInspect: () => Promise<boolean>;
}) {
  const editorId=useId();
  const [toolsOpen,setToolsOpen]=useState(false);
  const toolsOpener=useRef<HTMLElement|null>(null);
  useEffect(()=>{if(window.innerWidth>1000)setToolsOpen(true)},[]);
  function closeTools(){setToolsOpen(false);requestAnimationFrame(()=>toolsOpener.current?.focus({preventScroll:true}))}

  const editOrigin=useRef<Element|null>(null);
  const [pendingReference,setPendingReference]=useState<ReviewSource|null>(null);
  const [pendingEdit,setPendingEdit]=useState<string|null>(null);
  const [selected, setSelected] = useState<{scriptId:string;sceneId:string} | null>(null);
  const [useBlockEditor, setUseBlockEditor] = useState(false);
  const [replace, setReplace] = useState(false);
  const [undo, setUndo] = useState<{before: Screenplay; after: string; label:string} | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const script = project.screenplay;
  const uncertain = sent !== null && script?.id !== sent && !project.screenplay_versions?.some(v=>v.screenplay.id===sent);
  const scene = selected?.scriptId===script?.id ? script?.scenes.find(s=>s.id===selected?.sceneId) : undefined;
  const sketches = useMemo(()=>savedProject.id===project.id && script ? screenplaySketches(savedProject,script.source_outline) : {},[savedProject,project.id,script?.source_outline]);
  const sketch = scene ? sketches[scene.source_scene_id] : undefined;
  const source = script?.source_outline.scenes.find(s=>s.id===scene?.source_scene_id);
  const edit = (next: ScriptScene) => script && onChange({...script,scenes:script.scenes.map(s=>s.id===next.id?next:s)});
  useEffect(()=>{setSelected(null);setUseBlockEditor(false);setPendingReference(null);setPendingEdit(null);},[script?.id]);
  function chooseScene(id:string, focus=true) {
    if(!script?.scenes.some(s=>s.id===id))return;
    setSelected({scriptId:script.id,sceneId:id});
    if(focus){editOrigin.current=document.activeElement;setPendingEdit(id);}
  }
  useEffect(()=>{
    if(!pendingEdit||scene?.id!==pendingEdit)return;
    const frame=requestAnimationFrame(()=>{
      const host=document.getElementById(editorId)?.querySelector('.screenplay-author-fields');
      // Focus only while the author has not moved elsewhere since requesting navigation.
      if(host&&document.activeElement===editOrigin.current&&!host.contains(document.activeElement)){const node=host.querySelector<HTMLInputElement>('input');node?.scrollIntoView({block:'center'});node?.focus({preventScroll:true});}
      setPendingEdit(null);
    });
    return()=>cancelAnimationFrame(frame);
  },[pendingEdit,scene?.id,editorId]);
  useEffect(()=>{document.querySelectorAll(".review-highlight").forEach(node=>node.classList.remove("review-highlight"));},[script,canNavigateReview]);
  useEffect(()=>{
    if(!pendingReference||!canNavigateReview)return;
    const frame=requestAnimationFrame(()=>{
      const ref=pendingReference;
      const owner=script?.scenes.find(s=>s.id===ref.scene_id),block=owner?.blocks.find(b=>b.id===ref.block_id);
      const text=ref.field==='heading'?owner?.heading:ref.field==='speaker'?block?.speaker:block?.text;
      if(text===ref.text){
        const node=ref.block_id?document.querySelector<HTMLElement>(`.screenplay-author-fields [data-script-block="${ref.block_id}"] ${ref.field==='speaker'?'input':'textarea'}`)
          :document.querySelector<HTMLElement>('.screenplay-author-fields input');
        node?.closest('[data-script-block]')?.classList.add('review-highlight');
        node?.scrollIntoView({block:'center'});node?.focus({preventScroll:true});
      }
      setPendingReference(null);
    });return()=>cancelAnimationFrame(frame);
  },[pendingReference,scene?.id,script,canNavigateReview]);
  function remove(id: string) {
    if (!scene || !script) return;
    const next={...script,scenes:script.scenes.map(s=>s.id===scene.id?{...s,blocks:s.blocks.filter(b=>b.id!==id)}:s)};
    setUndo({before:structuredClone(script),after:undoContent(next),label:"Hoàn tác xóa khối"});onChange(next);
  }
  return <section className="panel screenplay" data-workspace-stage="workspace-script" aria-label="Kịch bản">
    <header className="screenplay-heading"><div><p className="eyebrow">Kịch bản</p><h2 id="workspace-script" data-tour="script" tabIndex={-1}>Viết kịch bản</h2></div>
      <div className="screenplay-actions">
        <button ref={node=>{toolsOpener.current=node}} type="button" className="secondary" disabled={!scene} aria-controls={scene?`${editorId}-support`:undefined} onClick={e=>{
          toolsOpener.current=e.currentTarget;setToolsOpen(true);
          const host=e.currentTarget.closest('.screenplay')?.querySelector<HTMLElement>('.screenplay-tools');
          host?.querySelectorAll<HTMLDetailsElement>('.screenplay-source, .screenplay-feedback-tools').forEach(node=>{node.open=true;});
          host?.scrollIntoView({block:'start'});host?.querySelector<HTMLElement>('summary')?.focus({preventScroll:true});
        }}>Dàn cảnh &amp; góp ý</button>
        <button type="button" className="secondary" disabled={savedProject.id!==project.id||!savedProject.screenplay} onClick={e=>{
          const reader=e.currentTarget.closest('.screenplay')?.querySelector<HTMLElement>('.screenplay-reading');
          const details=reader?.closest('details');if(details)details.open=true;
          reader?.scrollIntoView({block:'start'});reader?.focus({preventScroll:true});
        }}>Đọc &amp; xuất PDF</button>
      </div>
    </header>
    <SceneHint title="Bắt đầu viết từ đâu?">Chọn cảnh → viết và sửa → lưu để cập nhật kịch bản bên cạnh.
      Không bắt buộc có lời thoại hoặc hình phác. Mở nguồn, ảnh và góp ý khi cần; bạn có thể tự viết hoặc nhờ AI viết thử một cảnh. Quyết định vẫn thuộc về bạn.</SceneHint>
    <details className="screenplay-start"><summary>Bắt đầu từ dàn cảnh nào?</summary>
      <p>Lưu mọi sửa đang chờ trước khi bắt đầu. Nguồn dàn cảnh được giữ riêng; sửa dàn cảnh sau đó không tự thay kịch bản. Muốn đổi cấu trúc cảnh, sửa dàn cảnh rồi chủ động bắt đầu bản khác.</p>
      {project.scene_handoff ? <p>Dàn cảnh phiên bản {project.scene_handoff.version} · {project.scene_handoff.scenes.length} cảnh · {project.scene_outline?.source.draft.title}</p>
        : <p>Cần lưu tên và diễn tiến cho mọi cảnh trong dàn cảnh trước khi bắt đầu. Bạn vẫn lưu nháp dàn cảnh được.</p>}
      {project.scene_outline?.scenes.map((s,i)=><p key={s.id} className="preserve-lines">{i+1}. {s.title}: {s.action}</p>)}
    </details>
    {script && <label><input type="checkbox" checked={replace} onChange={e=>setReplace(e.target.checked)} />Tôi muốn bắt đầu bản khác từ dàn cảnh đã lưu; bản kịch bản hiện tại sẽ giữ trong lịch sử.</label>}
    <button type="button" disabled={uncertain || (!!script&&!replace) || !project.scene_outline?.scenes.length || project.scene_outline.scenes.some(s=>!s.title.trim()||!s.action.trim())}
      onClick={()=>{const id=crypto.randomUUID();setSent(id);setReplace(false);void onStart(id);}}>{script?"Bắt đầu bản kịch bản khác":"Bắt đầu viết từ bản dàn cảnh này"}</button>
    <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra kịch bản đã lưu</button>
    {uncertain && <p role="status">Chưa rõ kết quả bắt đầu bản mới. Kiểm tra bản đã lưu trước; không tự gửi lại.</p>}
    {script && <>
      <p role="status">Bản kịch bản phiên bản {script.version} · {dirty?"Có sửa chưa lưu trong dự án":"Đang xem bản đã lưu"}.</p>
      {(!project.screenplay_source_is_current || sourceDirty) && <p role="status">Dàn cảnh hoặc ý đồ hiện tại khác nguồn kịch bản. Giữ bản nguồn trước; không tự đồng bộ.</p>}
      <nav className="screenplay-scene-list" aria-label="Các cảnh kịch bản"><ol>{script.scenes.map((s,i)=><li key={s.id}>
        {i>0&&<span className="screenplay-scene-arrow" aria-hidden="true">→</span>}
        <button type="button" aria-pressed={s.id===scene?.id} aria-controls={editorId} data-script-scene={s.id}
          onFocus={e=>e.currentTarget.scrollIntoView({block:'nearest',inline:'nearest'})} onClick={()=>chooseScene(s.id)}>
          <span>Cảnh {i+1}</span>
          {sketches[s.source_scene_id]?.matches ? <SketchImage key={sketches[s.source_scene_id].sketch.id} projectId={project.id} sketchId={sketches[s.source_scene_id].sketch.id} alt={`Phác họa dàn cảnh tham khảo cho cảnh ${i+1}`}/> : <span className="screenplay-sketch-placeholder">{sketches[s.source_scene_id] ? "Ảnh dàn cảnh khác nguồn" : "Chưa có ảnh phù hợp"}</span>}
          <strong>{s.heading || "Cảnh chưa đặt tiêu đề"}</strong>
          <span>{s.blocks.some(b=>b.text.trim())?'Đang viết':'Chưa viết'}</span>
        </button>
      </li>)}</ol></nav>
      <div className="screenplay-columns screenplay-layout">
        <div className="screenplay-scene" id={editorId}>
          {scene ? <>
            <div className="screenplay-writing-heading"><h3>Viết và sửa cảnh</h3><span>Cảnh {script.scenes.indexOf(scene)+1} / {script.scenes.length}</span></div>
            <div className="screenplay-author-fields">
            <button type="button" aria-pressed={useBlockEditor} onClick={()=>setUseBlockEditor(!useBlockEditor)}>
              {useBlockEditor?'Dùng editor liền mạch':'Dùng editor dạng khối'}
            </button>
            {useBlockEditor
              ? <ScriptSceneFields key={`${script.id}:${scene.id}`} scene={scene} onChange={edit} onDelete={remove}/>
              : <ContinuousSceneEditor key={`${script.id}:${scene.id}`} scene={scene} scope={script.id}
                  blockLimit={Math.min(200,1000-script.scenes.filter(s=>s.id!==scene.id).reduce((total,s)=>total+s.blocks.length,0))} onChange={edit}/>}
            </div>
            <button type="button" onClick={onSave}>Lưu kịch bản</button>
            <p>Chuyển cảnh giữ phần đang viết. Thay đổi tự lưu khi dừng gõ; bản nháp không cần đủ mọi cảnh.</p>
            <ReviewPanel disabled={busy} open={toolsOpen} onClose={closeTools} label="Góp ý và phương án sửa"><div className="screenplay-tools" id={`${editorId}-support`} aria-label="Hỗ trợ cảnh đang viết">
              <details className="screenplay-source"><summary>Nguồn dàn cảnh của cảnh đang viết</summary>
                <p>Đây là nguồn được giữ lúc bắt đầu, không phải bản soạn.</p>
                {source && <><h3>{source.title}</h3><p className="preserve-lines">{source.action}</p>
                  {(["location","time","characters","goal","purpose","viewer_intent","keep_or_avoid"] as const).map((key,i)=>source[key]&&<p key={key} className="preserve-lines"><strong>{["Địa điểm","Thời điểm","Nhân vật","Mục tiêu","Đóng góp","Cảm nhận","Giữ/tránh"][i]}: </strong>{source[key]}</p>)}
                  {Object.entries(source.staging_choices).map(([key,value])=><p key={key} className="preserve-lines"><strong>{stagingLabels[key as StagingKey]}: </strong>{value}</p>)}
                </>}
                <p>Ảnh tham khảo theo lựa chọn dàn cảnh đang lưu, có thể đổi khi bạn chọn ảnh khác. Ảnh không được giữ riêng cùng phiên bản kịch bản và có thể sai chi tiết.</p>
                {sketch ? sketch.matches ? <figure className="screenplay-sketch">
                  <SketchImage key={`${project.id}:${sketch.sketch.id}:${sketch.sketch.asset_id}`} projectId={project.id} sketchId={sketch.sketch.id} alt="Phác họa dàn cảnh khớp nguồn kịch bản"/>
                  <figcaption>Ảnh dàn cảnh đang giữ · nguồn dàn cảnh bản {sketch.sketch.source_outline.version} · {sketch.sketch.model}</figcaption>
                </figure> : <details className="screenplay-sketch-other"><summary>Đối chiếu ảnh dàn cảnh khác nguồn</summary>
                  <p role="status">Ảnh này không khớp nguồn kịch bản. Không dùng làm minh họa xác nhận cho cảnh đang viết.</p>
                  <SketchImage key={`${project.id}:${sketch.sketch.id}:${sketch.sketch.asset_id}`} projectId={project.id} sketchId={sketch.sketch.id} alt="Ảnh dàn cảnh khác nguồn, chỉ để đối chiếu"/>
                  <p>Nguồn ảnh: dàn cảnh bản {sketch.sketch.source_outline.version} · {sketch.sketch.source_outline.scenes.find(s=>s.id===sketch.sketch.scene_id)?.action}</p>
                </details> : <p>Chưa có ảnh phù hợp. Bạn vẫn viết và lưu bình thường.</p>}
                <details><summary>Story plan và ý đồ đi cùng nguồn</summary>
                  <h4>{script.source_outline.source.draft.title}</h4><p className="preserve-lines">{script.source_outline.source.draft.logline}</p>
                  {script.source_outline.source.draft.sections.map((s,i)=><p key={i} className="preserve-lines">{s.title}: {s.content}</p>)}
                  <p className="preserve-lines">{script.source_outline.source.context.idea}</p>
                  {script.source_outline.source.context.constraints.map((c,i)=><p key={i} className="preserve-lines">{c}</p>)}
                  {script.source_outline.source.context.pending_questions.map((q,i)=><p key={i}>Chưa quyết định: {q.question}</p>)}
                  {script.source_outline.source.context.clarifications.map((c,i)=><p key={i} className="preserve-lines">{c.question} — {c.answer}</p>)}
                </details>
              </details>
            {undo && undoContent(script)===undo.after && <button type="button" onClick={()=>{onChange({...script,scenes:undo.before.scenes});setUndo(null);}}>{undo.label}</button>}
            <details className="screenplay-writing-tools"><summary>Nhờ FirstFrame viết thử một cảnh</summary>
            <ScreenplayProposals key={`${script.id}:${scene.id}`} project={project} scene={scene} canUse={canUse}
              onChooseScene={id=>chooseScene(id)} onWrite={onWrite} onUndo={onUndoProposal} onStructural={onStructural} onInspect={onProposalInspect} onPreview={onPreview} onDiscard={onDiscard}
              onUse={(id,replacement)=>{
                if(onApply){onApply(id,replacement);return;}
                const next={...script,scenes:script.scenes.map(s=>s.id===replacement.id?replacement:s)};
                setUndo({before:structuredClone(script),after:undoContent(next),label:"Hoàn tác dùng phương án"});onChange(next,id);
              }}/>
            </details>
            <details className="screenplay-feedback-tools"><summary>Góp ý có bằng chứng để tự sửa</summary>
            <ScreenplayFeedback key={`review:${script.id}:${scene.id}`} project={project} scene={scene} canNavigate={canNavigateReview}
              onRevise={async input=>{await onWrite(input);setToolsOpen(true);requestAnimationFrame(()=>document.querySelectorAll<HTMLDetailsElement>(".screenplay-writing-tools").forEach(d=>d.open=true))}} onReview={onReview} onInspect={onReviewInspect} onDiscard={onReviewDiscard} onAssess={onReviewAssess}
              onNavigate={source=>{if(canNavigateReview&&source.scene_id){chooseScene(source.scene_id,false);setUseBlockEditor(true);setToolsOpen(false);setPendingReference(source);}}}/>
            </details>
            </div></ReviewPanel>
          </> : <div className="screenplay-empty" role="status"><h3>Chọn một cảnh để viết</h3><p>Chọn cảnh phía trên để mở form. Kịch bản đã lưu ở bên cạnh không bao gồm các sửa chưa lưu.</p></div>}
        </div>
        <details className="screenplay-saved" aria-label="Kịch bản đã lưu để đối chiếu"><summary>Đối chiếu bản đã lưu khi cần</summary>
          <h3>Kịch bản đã lưu</h3>
          {savedProject.id===project.id&&savedProject.screenplay?.id===script.id ? <>
            <p>Phiên bản {savedProject.screenplay.version} · {savedProject.screenplay.scenes.length} cảnh.</p>
            {dirty&&<p role="status">Có sửa chưa lưu trong dự án. Cột này vẫn giữ bản server đã xác nhận.</p>}
            <SavedScript script={savedProject.screenplay} activeSceneId={scene?.id}/>
          </> : <p>Chưa có bản đã lưu tương ứng để đối chiếu. Phần đang viết vẫn được giữ.</p>}
        </details>
      </div>

    </>}
    <details className="screenplay-reader-toggle"><summary>Hoàn tất · đọc và xuất PDF kịch bản</summary><ScreenplayReading saved={savedProject} dirty={dirty} onSelect={onSelectSource} onDownload={onDownloadPdf} onInspect={onSourceInspect}
      onEdit={id=>chooseScene(id)}/></details>

  </section>;
}

export function ScreenplayHistory({ project, onRestore }: {project: Project; onRestore: (id: string) => void}) {
  return <>
    {project.screenplay_versions?.length ? <details open className="screenplay-history"><summary>Lịch sử kịch bản ({project.screenplay_versions.length})</summary>
      <p>Khôi phục sẽ lưu mọi sửa đang chờ trước, giữ bản hiện tại trong lịch sử; không thay Story plan và Dàn cảnh.</p>
      {[...project.screenplay_versions].reverse().map(v=><div key={v.id}><span>Bản {v.screenplay.version} · {v.created_at} · nguồn dàn cảnh {v.screenplay.source_outline.version}</span>
        <details><summary>Đọc phiên bản này</summary>{v.screenplay.scenes.map(s=><div key={s.id}><h4>{s.heading}</h4>{s.blocks.map(b=><p key={b.id} className="preserve-lines">{b.kind==="dialogue"&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</div>)}</details>
        <button type="button" onClick={()=>onRestore(v.id)}>Khôi phục kịch bản này</button></div>)}
    </details> : <p>Chưa có bản lịch sử kịch bản.</p>}
  </>;
}
