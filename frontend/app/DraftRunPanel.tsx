"use client";
import {useEffect,useRef,useState,useSyncExternalStore} from 'react';
import type {Project} from './projectsApi';
import {DraftWorkflow,WorkflowSkeleton} from './DraftWorkflow';
import {newerRun,type WorkflowItem} from './draftWorkflowState';
import {runCapabilities,continuationBody} from './draftWorkflowActions';
import {DraftRunPoller} from './draftRunPolling';
import {WorkflowReveals} from './draftWorkflowReveal';
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
 useEffect(()=>{let cancelled=false;listRuns(props.project.id).then(rows=>{if(!cancelled){let remembered:string|null=null;try{remembered=sessionStorage.getItem(`firstframe-draft-run:${props.project.id}`)}catch{}setRuns(current=>[...current,...rows.filter(r=>!current.some(c=>c.id===r.id))]);setActive(current=>current??rows.find(r=>r.id===remembered)?.id??rows[0]?.id??null)}}).catch(e=>{if(!cancelled)setError(e instanceof Error?e.message:String(e))});return()=>{cancelled=true}},[props.project.id]);
 useEffect(()=>{if(active)try{sessionStorage.setItem(`firstframe-draft-run:${props.project.id}`,active)}catch{}},[active,props.project.id]);
 useEffect(()=>{if(props.opened){setRuns(rows=>[props.opened!,...rows.filter(r=>r.id!==props.opened!.id)]);setActive(props.opened.id)}},[props.opened]);
 const register=(fn:()=>Promise<void>)=>{flush.current=fn;const remove=props.registerFlush(fn);return()=>{flush.current=async()=>{};remove()}};
 const activeRun=runs.find(r=>r.id===active);
 return <section id="draft-run" data-tour="draft-run" className="panel draft-run-panel" data-workspace-stage="draft-run" tabIndex={-1}>
   <h2>Tạo bản nháp</h2>
   <p>Một lượt tạo story plan, dàn cảnh và nội dung từng cảnh. Bản nháp AI được giữ riêng để bạn đọc, sửa và chọn dùng. Phạm vi hiện tại tối đa 6 cảnh.</p>
   <button type="button" disabled={!props.project.idea.trim()} onClick={()=>void props.onStart()}>Tạo bản nháp mới</button>
   {!!runs.length&&<label>Lượt tạo đã lưu<select value={active??''} onChange={e=>{const id=e.target.value;void flush.current().then(()=>setActive(id)).catch(e=>setError(e instanceof Error?e.message:String(e)))}}>{runs.map(r=><option key={r.id} value={r.id}>{statusLabels[r.status]} · {r.created_at?new Date(r.created_at).toLocaleString('vi-VN'):'Lượt đã lưu'}</option>)}</select></label>}
   {activeRun?.created_at&&<p className="draft-run-created-at">Lượt đang xem được tạo lúc {new Date(activeRun.created_at).toLocaleString('vi-VN')}.</p>}
   {error&&<p role="alert" className="error">{error}</p>}
   {active&&<RunCandidate key={active} {...props} id={active} onStatus={r=>setRuns(rows=>rows.map(row=>row.id===r.id?r:row))} registerFlush={register}/>}
 </section>;
}
function RunCandidate({id,onStatus,...props}:Props&{id:string;onStatus:(run:DraftRun)=>void}){
 const path=runPath(props.project.id,id);
 const [queue]=useState(()=>new CandidateAutosave(body=>candidateRequest(path+'/candidate','PUT',body),()=>candidateRequest(path+'/candidate')));
 const state=useSyncExternalStore(queue.subscribe,queue.getSnapshot,queue.getSnapshot);
 const [run,setRun]=useState<DraftRun|null>(null),[error,setError]=useState(''),[working,setWorking]=useState(false);
 const [cardsPreference,setCards]=useState(false);
 const cards=cardsPreference&&!!run?.workflow_items?.length;
 const [reveals,setReveals]=useState<string[]>([]),[revealHistory]=useState(()=>new WorkflowReveals());
 const [syncError,setSyncError]=useState<string|null>(null);
 const latest=useRef<DraftRun|null>(null);
 const lastRead=useRef<string|null>(null),pendingRead=useRef<string|null>(null),restoreRead=useRef<string|null>(null);
 const readTrigger=useRef<HTMLButtonElement|null>(null),workingNow=useRef(false);
 const [selectedTarget,setSelectedTarget]=useState<string|null>(null),[editing,setEditing]=useState(false);
 useEffect(()=>{try{setCards(sessionStorage.getItem(`firstframe-draft-cards:${id}`)==='1');lastRead.current=sessionStorage.getItem(`firstframe-draft-read:${id}`)}catch{}},[id]);
 function receive(next:DraftRun){const accepted=newerRun(latest.current,next);latest.current=accepted;setRun(accepted);onStatus(accepted)}
 function focusRead(target:string,focus=true){const el=document.getElementById(`run-${id}-${target}`);if(!el)return;if(el instanceof HTMLDetailsElement)el.open=true;if(focus)el.focus({preventScroll:true});if(el.getClientRects().length)(cards?el.closest('.draft-candidate-reader')??el:el).scrollIntoView({block:'start',behavior:'auto'})}
 function readCard(target:string,trigger:HTMLButtonElement){readTrigger.current=trigger;try{sessionStorage.setItem(`firstframe-draft-read:${id}`,target)}catch{}setEditing(false);if(selectedTarget===target)focusRead(target);else{pendingRead.current=target;setSelectedTarget(target)}}
 useEffect(()=>{if(selectedTarget===pendingRead.current&&selectedTarget){focusRead(selectedTarget);pendingRead.current=null}else if(selectedTarget===restoreRead.current&&selectedTarget){focusRead(selectedTarget,false);restoreRead.current=null}},[selectedTarget]);
 const edited=state.local?.project,dirty=queue.dirty;
 async function inspect(){const r=await runRequest(path);receive(r);const c=await candidateRequest(path+'/candidate');queue.accept(c);return latest.current!;}
 useEffect(()=>{
   const poller=new DraftRunPoller({readRun:()=>runRequest(path),readCandidate:()=>candidateRequest(path+'/candidate'),
     current:()=>latest.current,receive,candidateRevision:()=>queue.getSnapshot().saved?.revision??-1,accept:queue.accept,onError:setSyncError});
   void poller.start();return poller.stop;
 },[path,queue,run?.status]);
 useEffect(()=>()=>queue.stop(),[queue]);
 useEffect(()=>{if(run){const changed=revealHistory.update(run,state.saved);setReveals(cards?changed.slice(0,3):[])}},[run,state.saved,revealHistory]);
 useEffect(()=>{if(state.saved&&lastRead.current){const target=lastRead.current;lastRead.current=null;if(cards){restoreRead.current=target;setSelectedTarget(target)}else focusRead(target,false)}},[state.saved,id,cards]);
 useEffect(()=>props.registerFlush(()=>queue.flush()),[queue]);
 useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(dirty||state.saving||state.error){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[dirty,state.saving,state.error]);
 async function action(fn:()=>Promise<void>){if(workingNow.current)return;workingNow.current=true;setWorking(true);setError('');try{await queue.flush();await fn()}catch(e){setError(e instanceof Error?e.message:String(e))}finally{workingNow.current=false;setWorking(false)}}
 const capabilities=run?runCapabilities(run,state.saved):null;
 const editable=!!capabilities?.canEdit&&(!cards||editing);
 const show=(target:string)=>!cards||selectedTarget===target;
 const showScript=!cards||selectedTarget==='script'||!!selectedTarget?.startsWith('scene:');
 async function continueRun(){await action(async()=>{const fresh=await inspect();const body=continuationBody(fresh,queue.getSnapshot().saved);receive(await runRequest(path+'/continue','POST',body));await inspect()})}
 const cancelRun=()=>action(async()=>{receive(await runRequest(path+'/cancel','POST'))});
 const adoptRun=()=>action(async()=>{const c=queue.getSnapshot().saved;const fresh=await runRequest(path);receive(fresh);if(!c||c.revision!==fresh.candidate_revision||!runCapabilities(fresh,c).canAdopt)throw Error('Bản nháp đã đổi hoặc chưa thể nhận. Hãy kiểm tra và đọc lại bản đã lưu.');await props.onAdopt(fresh,c.revision);const checked=await inspect();if(checked.adopted_revision===null)throw Error('Chưa xác nhận nhận bản nháp. Phần đang sửa vẫn được giữ.');setEditing(false)});
 const closeReader=()=>action(async()=>{setSelectedTarget(null);setEditing(false);try{sessionStorage.removeItem(`firstframe-draft-read:${id}`)}catch{}const button=readTrigger.current?.isConnected?readTrigger.current:[...document.querySelectorAll<HTMLButtonElement>('#draft-run [data-read-target]')].find(b=>b.dataset.readTarget===selectedTarget);button?.focus();button?.scrollIntoView({block:'nearest',behavior:'auto'})});
 const cancelButton=run&&capabilities?.canCancel&&<button type="button" className="secondary" disabled={working} onClick={()=>void cancelRun()}>{run.status==='running'?'Hủy các bước tiếp theo':'Kết thúc lượt này'}</button>;
 const controls=run&&<div className="draft-run-actions">
  {['partial','failed','interrupted'].includes(run.status)&&<><button type="button" disabled={working||!capabilities?.canContinue||!!state.error} onClick={()=>void continueRun()}>Tiếp tục bước chưa gửi</button>{capabilities?.continueReason&&<p>{capabilities.continueReason}</p>}</>}
  {run.status!=='running'&&run.status!=='needs_input'&&cancelButton}
  {capabilities?.canAdopt&&<button type="button" disabled={working||state.saving||!!state.error} onClick={()=>void adoptRun()}>Dùng bản nháp này</button>}
  {run.cancel_requested&&<p>{run.status==='running'?'Đang dừng sau bước hiện tại; lần gọi đã gửi có thể vẫn trả kết quả.':'Lượt này đã được kết thúc. Phần đã lưu vẫn đọc được.'}</p>}
  {run.adopted_revision!==null&&<p>Đã nhận vào không gian viết. Các sửa tiếp theo lưu tại bản đang viết.</p>}
 </div>;
 const clarification=run?.status==='needs_input'&&edited?.analysis&&<ClarificationConversation idPrefix={`run-${id}-`} creatingScreenplay thinking={working} summary={edited.analysis.summary} questions={edited.analysis.missing_information} answers={edited.answers}
  onEditBrief={()=>void action(async()=>{receive(await runRequest(path+'/cancel','POST'));const input=document.getElementById('idea');revealWorkspaceTarget(input);input?.focus();input?.scrollIntoView({block:'center'})})}
  aiSuggestions={edited.analysis.ai_suggestions} idea={edited.idea} constraints={edited.constraints}
  onChange={(i,v)=>queue.edit({...edited,answers:edited.answers.map((a,j)=>j===i?v:a)})}
  onConfirm={capabilities?.canContinue&&!state.error?()=>void continueRun():undefined}/>;
 const intentActions=run?.status==='needs_input'&&<div className="draft-workflow-decisions">{clarification}{!edited?.analysis&&<p>Đang tải câu hỏi đã lưu…</p>}{capabilities?.continueReason&&<p>{capabilities.continueReason}</p>}{cancelButton}</div>;
 function cardActions(item:WorkflowItem){
  if(item.kind==='intent'&&run?.status==='needs_input')return intentActions;
  if(item.id===run?.workflow_items?.find(i=>i.status==='running')?.id)return <div className="draft-workflow-decisions">{cancelButton}{run?.cancel_requested&&<p>Đang dừng sau bước hiện tại; kết quả đã gửi vẫn có thể được giữ.</p>}</div>;
  if(item.kind==='draft'&&run?.status!=='running'&&run?.status!=='needs_input')return controls;
  return null;
 }
 return <div onPointerDownCapture={()=>{lastRead.current=null;restoreRead.current=null}} onKeyDownCapture={()=>{lastRead.current=null;restoreRead.current=null}} onCompositionStartCapture={()=>queue.composition(true)} onCompositionEndCapture={()=>queue.composition(false)}>
   {syncError&&<p role="status" className="draft-workflow-network">Chưa cập nhật được tiến độ. Bản đã tải vẫn được giữ; FirstFrame sẽ tự thử kết nối lại. {syncError}</p>}
   {!run&&!syncError&&<div role="status"><p>Đang tải lượt tạo đã lưu…</p><WorkflowSkeleton/></div>}
   {run&&<>
     <p role="status"><strong>{statusLabels[run.status]}</strong> · {stepLabels[run.step]??run.step} · Đã lưu {run.completed_scenes}/{run.total_scenes||'…'} cảnh</p>
     <label className="draft-workflow-toggle"><input type="checkbox" disabled={!run.workflow_items?.length} checked={cards} onChange={e=>{setReveals([]);setCards(e.target.checked);try{sessionStorage.setItem(`firstframe-draft-cards:${id}`,e.target.checked?'1':'0')}catch{}}}/>Xem thử tiến độ dạng card</label>
     {cards&&<DraftWorkflow run={run} candidate={state.saved} reveals={reveals} actions={cardActions} onRead={(target,trigger)=>void action(async()=>{readCard(target,trigger)})}/>}
     {run.total_scenes>0&&<progress aria-label="Số cảnh đã lưu" max={run.total_scenes} value={run.completed_scenes}/>}
     {run.revision_instructions&&<p className="preserve-lines">Yêu cầu thay đổi cấu trúc: {run.revision_instructions} · {run.affected_scene_ids?.length??0} cảnh nguồn có thể bị ảnh hưởng. Bản đang viết được giữ nguyên cho đến khi bạn nhận bản nháp mới.</p>}
     <p>Tiến độ được giữ trên máy chủ. Mở lại trang không gọi AI lần nữa.</p>
     {run.error&&<p role="alert" className="error">{run.error}</p>}
     {run.review_error&&<p className="form-message">Bản nháp vẫn đọc được. Góp ý chưa hoàn tất: {run.review_error}</p>}
     {run.adopted_revision===null&&run.source_revision!==props.project.revision&&<p className="storage-note">Bản nguồn đã thay đổi từ khi khởi động. Khi nhận, hệ thống sẽ đối chiếu lại nội dung; phần bản nháp riêng vẫn giữ.</p>}
     <button type="button" className="secondary" disabled={working} onClick={()=>void action(async()=>{await inspect()})}>Kiểm tra tiến độ</button>
     {!cards&&<>{controls}{run.status==='running'&&cancelButton}</>}
   </>}
   {error&&<p role="alert" className="error">{error}</p>}
   {state.local&&<p role="status">{state.saving?'Đang lưu bản nháp riêng…':state.error?'Chưa xác nhận lưu bản nháp riêng':dirty?'Chờ tự lưu bản nháp riêng':'Bản nháp riêng đã lưu'}</p>}
   {state.error&&<div role="alert"><p>{state.error}</p><button type="button" onClick={()=>void queue.flush(true).catch(e=>setError(e instanceof Error?e.message:String(e)))}>Thử lưu lại bản nháp</button><button type="button" disabled={state.saving} onClick={()=>{if(window.confirm('Mở lại sẽ bỏ phần candidate chưa xác nhận lưu. Hãy tải bản sao trước nếu cần giữ.'))void queue.reopen().then(()=>setError('')).catch(e=>setError(e instanceof Error?e.message:String(e)))}}>Mở lại bản nháp đã lưu</button><button type="button" onClick={()=>{const blob=new Blob([JSON.stringify(state.local,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`draft-${id}.json`;a.click();URL.revokeObjectURL(url)}}>Tải bản sao bản nháp</button></div>}
   {!cards&&intentActions}
   <div className={cards?'draft-candidate-reader':undefined} role={cards?'region':undefined} aria-label={cards?'Đọc và sửa bản nháp':undefined} hidden={cards&&!selectedTarget}>
   {cards&&selectedTarget&&<header className="draft-candidate-reader-header"><h3>Bản nháp đang xem</h3><p>{dirty?'Có thay đổi đang chờ lưu':`Bản đã lưu · mốc ${state.saved?.revision??'…'}`}</p><div className="draft-run-actions"><button type="button" className="secondary" disabled={working} onClick={()=>void closeReader()}>Quay lại card</button>{capabilities?.canEdit&&(selectedTarget==='plan'||showScript)&&<button type="button" disabled={working||!!state.error} onClick={()=>{if(editing)void action(async()=>setEditing(false));else setEditing(true)}}>{editing?'Lưu và đọc lại':'Chỉnh bản nháp'}</button>}</div></header>}
   {edited?.analysis&&<details hidden={!show('understanding')} open={cards?true:undefined} id={`run-${id}-understanding`} tabIndex={-1}><summary>Điều đã hiểu và ý đồ đã lưu</summary><p>{edited.analysis.summary}</p><p>{edited.constraints.join(' · ')}</p></details>}
   {!!state.saved?.plan_review&&<details hidden={!show('plan-review')} open={cards?true:undefined} id={`run-${id}-plan-review`} tabIndex={-1}><summary>Góp ý story plan đã lưu</summary><p>Góp ý thuộc nguồn lúc tạo story plan; chỉ dùng tham khảo nếu bạn đã sửa bản.</p>{typeof state.saved.plan_review==='object'&&state.saved.plan_review!==null&&'findings' in state.saved.plan_review&&Array.isArray(state.saved.plan_review.findings)&&state.saved.plan_review.findings.map((f:unknown,i:number)=>f&&typeof f==='object'&&'message' in f&&typeof f.message==='string'?<p key={i}>{f.message}</p>:null)}</details>}
   {edited?.draft&&<details hidden={!show('plan')} open={cards?true:undefined} id={`run-${id}-plan`} tabIndex={-1}><summary>Story plan · {edited.draft.title}</summary>{cards&&editable?<div className="draft-plan-fields"><label>Tên story plan<input disabled={working} maxLength={200} value={edited.draft.title} onChange={e=>queue.edit({...edited,draft:{...edited.draft!,title:e.target.value}})}/></label><label>Tóm tắt story plan<textarea disabled={working} rows={3} maxLength={2000} value={edited.draft.logline} onChange={e=>queue.edit({...edited,draft:{...edited.draft!,logline:e.target.value}})}/></label>{edited.draft.sections.map((section,i)=><label key={i}>{section.title}<textarea disabled={working} rows={4} maxLength={10000} value={section.content} onChange={e=>queue.edit({...edited,draft:{...edited.draft!,sections:edited.draft!.sections.map((s,j)=>j===i?{...s,content:e.target.value}:s)}})}/></label>)}</div>:<><p className="preserve-lines">{edited.draft.logline}</p>{edited.draft.sections.map((s,i)=><p key={i} className="preserve-lines"><strong>{s.title}</strong><br/>{s.content}</p>)}</>}</details>}
   {edited?.scene_outline&&<details hidden={!show('outline')} open={cards?true:undefined} id={`run-${id}-outline`} tabIndex={-1}><summary>Dàn cảnh · {edited.scene_outline.scenes.length} cảnh</summary><ol>{edited.scene_outline.scenes.map(s=><li key={s.id}><strong>{s.title}</strong><p className="preserve-lines">{s.action}</p></li>)}</ol></details>}
   {edited?.screenplay&&<div className="candidate-scenes" hidden={!showScript} id={`run-${id}-script`} tabIndex={-1}><h3>Kịch bản đang hình thành</h3>{edited.screenplay.scenes.map((scene,index)=><section key={scene.id} hidden={cards&&selectedTarget!=='script'&&selectedTarget!==`scene:${scene.id}`} id={`run-${id}-scene:${scene.id}`} tabIndex={-1} className="candidate-scene">
     <h4>{index+1}. {scene.heading}</h4>{!scene.blocks.length&&<p>Chưa có nội dung cảnh này.</p>}
     {scene.blocks.map((block,blockIndex)=><div key={block.id}>
       {block.speaker&&<strong>{block.speaker}</strong>}
       {editable?<label>Cảnh {index+1} · {block.kind==='dialogue'?'Lời thoại':'Hành động'} · đoạn {blockIndex+1}<small className="candidate-origin">{provenanceLabel(edited.screenplay?.provenance?.[`block:${block.id}:text`])}</small><textarea disabled={working} rows={3} maxLength={10000} value={block.text} onChange={e=>queue.edit({...edited,screenplay:{...edited.screenplay!,scenes:edited.screenplay!.scenes.map(s=>s.id===scene.id?{...s,blocks:s.blocks.map(b=>b.id===block.id?{...b,text:e.target.value}:b)}:s)}})}/></label>:<p className="preserve-lines">{block.text}</p>}
     </div>)}
   </section>)}</div>}
   {!!edited?.screenplay_reviews?.length&&<details hidden={!show('reviews')} open={cards?true:undefined} id={`run-${id}-reviews`} tabIndex={-1}><summary>Góp ý AI · để bạn cân nhắc</summary>{edited.screenplay_reviews.map(r=><div key={r.id}><p className="storage-note">{edited.screenplay&&sameReviewScript(edited.screenplay,r.source_screenplay)&&JSON.stringify(edited.draft)===JSON.stringify(r.source_screenplay.source_outline.source.draft)?'Góp ý đọc bản này. Bạn tự cân nhắc.':'Góp ý thuộc bản trước khi sửa; chỉ dùng tham khảo.'}</p>{r.notes.map(n=><div key={n.id}><p>{n.observation} {n.suggestion}</p>{n.evidence.map((e,i)=><blockquote key={i}>{e.quote}</blockquote>)}</div>)}<details><summary>Đọc bản nguồn của góp ý</summary>{r.source_screenplay.scenes.filter(scene=>scene.id===r.target_scene_id).map(scene=><section key={scene.id}><h4>{scene.heading}</h4>{scene.blocks.map(block=><p className="preserve-lines" key={block.id}>{block.speaker&&<strong>{block.speaker}<br/></strong>}{block.text}</p>)}</section>)}</details></div>)}</details>}
   </div>
 </div>;
}
