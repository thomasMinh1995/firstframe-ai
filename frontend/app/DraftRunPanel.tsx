"use client";
import {useEffect,useRef,useState,useSyncExternalStore} from 'react';
import type {Project} from './projectsApi';
import {CandidateAutosave} from './candidateAutosave';
import {candidateRequest,listRuns,runPath,runRequest,statusLabels,stepLabels,type DraftRun} from './draftRunsApi';
import {revealWorkspaceTarget} from './WorkspaceStage';
import {ClarificationConversation} from './ClarificationConversation';
import {sameReviewScript} from './screenplayReviewTypes';
import {provenanceLabel} from './provenance';

type Props={project:Project;opened:DraftRun|null;onStart:()=>Promise<void>;onAdopt:(run:DraftRun,revision:number)=>Promise<void>;registerFlush:(flush:()=>Promise<void>)=>()=>void};
export function DraftRunPanel(props:Props){
 const [runs,setRuns]=useState<DraftRun[]>([]),[active,setActive]=useState<string|null>(null),[error,setError]=useState('');
 const flush=useRef<()=>Promise<void>>(async()=>{});
 useEffect(()=>{let cancelled=false;listRuns(props.project.id).then(rows=>{if(!cancelled){setRuns(current=>[...current,...rows.filter(r=>!current.some(c=>c.id===r.id))]);setActive(current=>current??rows[0]?.id??null)}}).catch(e=>{if(!cancelled)setError(String(e))});return()=>{cancelled=true}},[props.project.id]);
 useEffect(()=>{if(props.opened){setRuns(rows=>[props.opened!,...rows.filter(r=>r.id!==props.opened!.id)]);setActive(props.opened.id)}},[props.opened]);
 const register=(fn:()=>Promise<void>)=>{flush.current=fn;const remove=props.registerFlush(fn);return()=>{flush.current=async()=>{};remove()}};
 return <section id="draft-run" data-tour="draft-run" className="panel draft-run-panel" data-workspace-stage="draft-run" tabIndex={-1}>
   <h2>Tạo bản nháp</h2>
   <p>Một lượt tạo story plan, dàn cảnh và nội dung từng cảnh. Bản nháp AI được giữ riêng để bạn đọc, sửa và chọn dùng. Phạm vi hiện tại tối đa 6 cảnh.</p>
   <button type="button" disabled={!props.project.idea.trim()} onClick={()=>void props.onStart()}>Tạo bản nháp mới</button>
   {!!runs.length&&<label>Lượt tạo đã lưu<select value={active??''} onChange={e=>{const id=e.target.value;void flush.current().then(()=>setActive(id)).catch(e=>setError(String(e)))}}>{runs.map(r=><option key={r.id} value={r.id}>{statusLabels[r.status]} · {r.created_at?new Date(r.created_at).toLocaleString('vi-VN'):'Lượt đã lưu'}</option>)}</select></label>}
   {error&&<p role="alert" className="error">{error}</p>}
   {active&&<RunCandidate key={active} {...props} id={active} onStatus={r=>setRuns(rows=>rows.map(row=>row.id===r.id?r:row))} registerFlush={register}/>}
 </section>;
}
function RunCandidate({id,onStatus,...props}:Props&{id:string;onStatus:(run:DraftRun)=>void}){
 const path=runPath(props.project.id,id);
 const [queue]=useState(()=>new CandidateAutosave(body=>candidateRequest(path+'/candidate','PUT',body),()=>candidateRequest(path+'/candidate')));
 const state=useSyncExternalStore(queue.subscribe,queue.getSnapshot,queue.getSnapshot);
 const [run,setRun]=useState<DraftRun|null>(null),[error,setError]=useState(''),[working,setWorking]=useState(false);
 const edited=state.local?.project,dirty=queue.dirty;
 async function inspect(){const r=await runRequest(path);setRun(r);onStatus(r);const c=await candidateRequest(path+'/candidate');queue.accept(c);return r;}
 useEffect(()=>{
   let stopped=false,timer:ReturnType<typeof setTimeout>,delay=1500,lastRevision=-1;
   const poll=async()=>{try{const r=await runRequest(path);if(stopped)return;setRun(r);onStatus(r);if(r.candidate_revision!==lastRevision){const c=await candidateRequest(path+'/candidate');if(stopped)return;queue.accept(c);lastRevision=r.candidate_revision;delay=1500}else delay=Math.min(8000,delay*1.5);if(r.status==='running')timer=setTimeout(poll,delay)}catch(e){if(!stopped)setError(String(e))}};
   void poll();return()=>{stopped=true;clearTimeout(timer);queue.stop()};
 },[path,queue,run?.status]);
 useEffect(()=>props.registerFlush(()=>queue.flush()),[queue]);
 useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(dirty||state.saving||state.error){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[dirty,state.saving,state.error]);
 async function action(fn:()=>Promise<void>){if(working)return;setWorking(true);setError('');try{await queue.flush();await fn()}catch(e){setError(String(e))}finally{setWorking(false)}}
 const editable=run&&run.status!=='running'&&run.status!=='needs_input'&&run.adopted_revision===null;
 return <div onCompositionStartCapture={()=>queue.composition(true)} onCompositionEndCapture={()=>queue.composition(false)}>
   {run&&<>
     <p role="status"><strong>{statusLabels[run.status]}</strong> · {stepLabels[run.step]??run.step} · Đã lưu {run.completed_scenes}/{run.total_scenes||'…'} cảnh</p>
     {run.total_scenes>0&&<progress aria-label="Số cảnh đã lưu" max={run.total_scenes} value={run.completed_scenes}/>}
     {run.revision_instructions&&<p className="preserve-lines">Yêu cầu thay đổi cấu trúc: {run.revision_instructions} · {run.affected_scene_ids?.length??0} cảnh nguồn có thể bị ảnh hưởng. Bản đang viết được giữ nguyên cho đến khi bạn nhận bản nháp mới.</p>}
     <p>Tiến độ được giữ trên máy chủ. Mở lại trang không gọi AI lần nữa.</p>
     {run.error&&<p role="alert" className="error">{run.error}</p>}
     {run.review_error&&<p className="form-message">Bản nháp vẫn đọc được. Góp ý chưa hoàn tất: {run.review_error}</p>}
     {run.adopted_revision===null&&run.source_revision!==props.project.revision&&<p className="storage-note">Bản nguồn đã thay đổi từ khi khởi động. Khi nhận, hệ thống sẽ đối chiếu lại nội dung; phần bản nháp riêng vẫn giữ.</p>}
     <div className="draft-run-actions">
       <button type="button" disabled={working} className="secondary" onClick={()=>void action(async()=>{await inspect()})}>Kiểm tra tiến độ</button>
       {(run.status==='running'||run.status==='needs_input')&&<button type="button" className="secondary" disabled={working||run.cancel_requested} onClick={()=>void action(async()=>{setRun(await runRequest(path+'/cancel','POST'))})}>{run.cancel_requested?'Đang dừng sau bước hiện tại…':'Hủy các bước tiếp theo'}</button>}
       {['partial','failed','interrupted'].includes(run.status)&&<button type="button" disabled={working} onClick={()=>void action(async()=>{const c=queue.getSnapshot().saved!;setRun(await runRequest(path+'/continue','POST',{candidate_revision:c.revision}));await inspect()})}>Tiếp tục bước chưa gửi</button>}
       {['partial','failed','interrupted'].includes(run.status)&&<button type="button" className="secondary" disabled={working} onClick={()=>void action(async()=>{setRun(await runRequest(path+'/cancel','POST'))})}>Kết thúc lượt này</button>}
       {(run.status==='ready'||run.status==='partial')&&edited?.screenplay?.scenes.some(s=>s.blocks.length)&&run.adopted_revision===null&&<button type="button" disabled={working||state.saving||!!state.error} onClick={()=>void action(async()=>{await props.onAdopt(run,queue.getSnapshot().saved!.revision);await inspect()})}>Dùng bản nháp này</button>}
       {run.adopted_revision!==null&&<p>Đã nhận vào không gian viết. Các sửa tiếp theo lưu tại bản đang viết.</p>}
     </div>
   </>}
   {error&&<p role="alert" className="error">{error}</p>}
   {state.local&&<p role="status">{state.saving?'Đang lưu bản nháp riêng…':state.error?'Chưa xác nhận lưu bản nháp riêng':dirty?'Chờ tự lưu bản nháp riêng':'Bản nháp riêng đã lưu'}</p>}
   {state.error&&<div role="alert"><p>{state.error}</p><button type="button" onClick={()=>void queue.flush(true).catch(e=>setError(String(e)))}>Thử lưu lại bản nháp</button><button type="button" disabled={state.saving} onClick={()=>{if(window.confirm('Mở lại sẽ bỏ phần candidate chưa xác nhận lưu. Hãy tải bản sao trước nếu cần giữ.'))void queue.reopen().then(()=>setError('')).catch(e=>setError(String(e)))}}>Mở lại bản nháp đã lưu</button><button type="button" onClick={()=>{const blob=new Blob([JSON.stringify(state.local,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`draft-${id}.json`;a.click();URL.revokeObjectURL(url)}}>Tải bản sao bản nháp</button></div>}
   {run?.status==='needs_input'&&edited?.analysis&&<ClarificationConversation idPrefix={`run-${id}-`} creatingScreenplay summary={edited.analysis.summary} questions={edited.analysis.missing_information} answers={edited.answers}
      onEditBrief={()=>void action(async()=>{setRun(await runRequest(path+'/cancel','POST'));const input=document.getElementById('idea');revealWorkspaceTarget(input);input?.focus();input?.scrollIntoView({block:'center'})})}
      aiSuggestions={edited.analysis.ai_suggestions} idea={edited.idea} constraints={edited.constraints}
      onChange={(i,v)=>{const p={...edited,answers:edited.answers.map((a,j)=>j===i?v:a)};queue.edit(p)}}
      onConfirm={()=>void action(async()=>{const c=queue.getSnapshot().local!;setRun(await runRequest(path+'/continue','POST',{candidate_revision:c.revision,answers:c.project.answers}));await inspect()})}/>}
   {edited?.draft&&<details><summary>Story plan · {edited.draft.title}</summary><p className="preserve-lines">{edited.draft.logline}</p>{edited.draft.sections.map((s,i)=><p key={i} className="preserve-lines"><strong>{s.title}</strong><br/>{s.content}</p>)}</details>}
   {edited?.scene_outline&&<details><summary>Dàn cảnh · {edited.scene_outline.scenes.length} cảnh</summary><ol>{edited.scene_outline.scenes.map(s=><li key={s.id}><strong>{s.title}</strong><p className="preserve-lines">{s.action}</p></li>)}</ol></details>}
   {edited?.screenplay&&<div className="candidate-scenes"><h3>Kịch bản đang hình thành</h3>{edited.screenplay.scenes.map((scene,index)=><section key={scene.id} className="candidate-scene">
     <h4>{index+1}. {scene.heading}</h4>{!scene.blocks.length&&<p>Chưa có nội dung cảnh này.</p>}
     {scene.blocks.map((block,blockIndex)=><div key={block.id}>
       {block.speaker&&<strong>{block.speaker}</strong>}
       {editable?<label>Cảnh {index+1} · {block.kind==='dialogue'?'Lời thoại':'Hành động'} · đoạn {blockIndex+1}<small className="candidate-origin">{provenanceLabel(edited.screenplay?.provenance?.[`block:${block.id}:text`])}</small><textarea rows={3} maxLength={10000} value={block.text} onChange={e=>queue.edit({...edited,screenplay:{...edited.screenplay!,scenes:edited.screenplay!.scenes.map(s=>s.id===scene.id?{...s,blocks:s.blocks.map(b=>b.id===block.id?{...b,text:e.target.value}:b)}:s)}})}/></label>:<p className="preserve-lines">{block.text}</p>}
     </div>)}
   </section>)}</div>}
   {!!edited?.screenplay_reviews?.length&&<details><summary>Góp ý AI · để bạn cân nhắc</summary>{edited.screenplay_reviews.map(r=><div key={r.id}><p className="storage-note">{edited.screenplay&&sameReviewScript(edited.screenplay,r.source_screenplay)&&JSON.stringify(edited.draft)===JSON.stringify(r.source_screenplay.source_outline.source.draft)?'Góp ý đọc bản này. Bạn tự cân nhắc.':'Góp ý thuộc bản trước khi sửa; chỉ dùng tham khảo.'}</p>{r.notes.map(n=><p key={n.id}>{n.observation} {n.suggestion}</p>)}</div>)}</details>}
 </div>;
}
