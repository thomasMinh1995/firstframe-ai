"use client";
import {useEffect,useRef,useState,useSyncExternalStore,useId} from 'react';
import type {Project} from './projectsApi';
import {DraftWorkflow,WorkflowSkeleton} from './DraftWorkflow';
import {newerRun,draftRunSummary,nextDraftFollow,draftReaderHeading,type WorkflowItem} from './draftWorkflowState';
import {runCapabilities,continuationBody,sceneAfterAdoption} from './draftWorkflowActions';
import {DraftRunPoller} from './draftRunPolling';
import {WorkflowReveals} from './draftWorkflowReveal';
import {CandidateAutosave} from './candidateAutosave';
import {blockingDraftRun,draftRunActionLabel,candidateRequest,listRuns,runPath,runRequest,statusLabels,type DraftRun} from './draftRunsApi';
import {revealWorkspaceTarget} from './WorkspaceStage';
import {ClarificationConversation} from './ClarificationConversation';
import {sameReviewScript} from './screenplayReviewTypes';
import {provenanceLabel} from './provenance';

type Props={project:Project;opened:DraftRun|null;onStart:(existing?:DraftRun|null)=>Promise<void>;onBlockingRun:(run:DraftRun|null)=>void;onViewedRun?:(run:DraftRun)=>void;onAdopt:(run:DraftRun,revision:number,sceneId?:string|null)=>Promise<void>;registerFlush:(flush:()=>Promise<void>)=>()=>void};
export function DraftRunPanel(props:Props){
 const [runs,setRuns]=useState<DraftRun[]>([]),[active,setActive]=useState<string|null>(null),[error,setError]=useState('');
 const flush=useRef<()=>Promise<void>>(async()=>{});
 const blocking=blockingDraftRun(runs);
 useEffect(()=>props.onBlockingRun(blocking),[blocking,props.onBlockingRun]);
 useEffect(()=>{let cancelled=false;listRuns(props.project.id).then(rows=>{if(!cancelled){let remembered:string|null=null;try{remembered=sessionStorage.getItem(`firstframe-draft-run:${props.project.id}`)}catch{}setRuns(current=>[...current,...rows.filter(r=>!current.some(c=>c.id===r.id))]);setActive(current=>current??rows.find(r=>r.id===remembered)?.id??rows[0]?.id??null)}}).catch(e=>{if(!cancelled)setError(e instanceof Error?e.message:String(e))});return()=>{cancelled=true}},[props.project.id]);
 useEffect(()=>{if(active)try{sessionStorage.setItem(`firstframe-draft-run:${props.project.id}`,active)}catch{}},[active,props.project.id]);
 useEffect(()=>{if(props.opened){setRuns(rows=>[props.opened!,...rows.filter(r=>r.id!==props.opened!.id)]);setActive(props.opened.id)}},[props.opened]);
 const register=(fn:()=>Promise<void>)=>{flush.current=fn;const remove=props.registerFlush(fn);return()=>{flush.current=async()=>{};remove()}};
 const activeRun=runs.find(r=>r.id===active);
 return <section id="draft-run" data-tour="draft-run" className="panel draft-run-panel" data-workspace-stage="draft-run" tabIndex={-1}>
   <h2>Tạo bản nháp</h2>
   <p>Một lượt tạo story plan, dàn cảnh và nội dung từng cảnh. Bản nháp AI được giữ riêng để bạn đọc, sửa và chọn dùng. Phạm vi hiện tại tối đa 6 cảnh.</p>
   <button type="button" disabled={!blocking&&!props.project.idea.trim()} onClick={()=>void props.onStart(blocking)}>{draftRunActionLabel(blocking)??'Tạo bản nháp mới'}</button>
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
 const [adopting,setAdopting]=useState(false);
 const followRef=useRef({enabled:true,manual:false}),[follow,setFollow]=useState(followRef.current);
 function changeFollowing(enabled:boolean,manual=true){const next=nextDraftFollow(followRef.current,enabled,manual);if(next.enabled===followRef.current.enabled&&next.manual===followRef.current.manual)return;followRef.current=next;setFollow(next)}
 const [cardsPreference,setCards]=useState(false);
 const cards=cardsPreference&&!!run?.workflow_items?.length;
 const [reveals,setReveals]=useState<string[]>([]),[revealHistory]=useState(()=>new WorkflowReveals());
 const [syncError,setSyncError]=useState<string|null>(null);
 const latest=useRef<DraftRun|null>(null);
 const lastRead=useRef<string|null>(null),pendingRead=useRef<string|null>(null),restoreRead=useRef<string|null>(null);
 const readTrigger=useRef<HTMLButtonElement|null>(null),workingNow=useRef(false),lastScene=useRef<string|null>(null);
 function rememberScene(sceneId:string){lastScene.current=sceneId;try{sessionStorage.setItem(`firstframe-draft-scene:${id}`,sceneId)}catch{}}
 const readerSelectId=useId();
 const [selectedTarget,setSelectedTarget]=useState<string|null>(null),[editing,setEditing]=useState(false);
 useEffect(()=>{try{setCards(sessionStorage.getItem(`firstframe-draft-cards:${id}`)==='1');lastRead.current=sessionStorage.getItem(`firstframe-draft-read:${id}`);lastScene.current=sessionStorage.getItem(`firstframe-draft-scene:${id}`)}catch{}},[id]);
 function receive(next:DraftRun){const accepted=newerRun(latest.current,next);latest.current=accepted;setRun(accepted);onStatus(accepted);props.onViewedRun?.(accepted)}
 function focusRead(target:string,focus=true){const el=document.getElementById(`run-${id}-${target}`);if(!el)return;if(el instanceof HTMLDetailsElement)el.open=true;if(focus)el.focus({preventScroll:true});if(el.getClientRects().length)(cards?el.closest('.draft-candidate-reader')??el:el).scrollIntoView({block:'start',behavior:'auto'})}
 function readCard(target:string,trigger?:HTMLButtonElement){if(target.startsWith('scene:'))rememberScene(target.slice(6));if(trigger)readTrigger.current=trigger;try{sessionStorage.setItem(`firstframe-draft-read:${id}`,target)}catch{}setEditing(false);if(selectedTarget===target)focusRead(target);else{pendingRead.current=target;setSelectedTarget(target)}}
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
 async function continueRun(){await action(async()=>{const fresh=await inspect();const body=continuationBody(fresh,queue.getSnapshot().saved);const next=await runRequest(path+'/continue','POST',body);receive(next);if(fresh.status==='needs_input'&&next.status==='running'&&!followRef.current.manual)changeFollowing(true,false);await inspect()})}
 const cancelRun=()=>action(async()=>{receive(await runRequest(path+'/cancel','POST'))});
 const adoptRun=(sceneId?:string|null)=>action(async()=>{setAdopting(true);try{const c=queue.getSnapshot().saved;const fresh=await runRequest(path);receive(fresh);if(!c||c.revision!==fresh.candidate_revision||!runCapabilities(fresh,c).canAdopt)throw Error('Bản nháp đã đổi hoặc chưa thể nhận. Hãy kiểm tra và đọc lại bản đã lưu.');await props.onAdopt(fresh,c.revision,sceneId??lastScene.current);const checked=await inspect();if(checked.adopted_revision===null)throw Error('Chưa xác nhận nhận bản nháp. Phần đang sửa vẫn được giữ.');setEditing(false)}finally{setAdopting(false)}});
 const readerScene=sceneAfterAdoption(state.saved?.project.screenplay,selectedTarget?.startsWith('scene:')?selectedTarget.slice(6):lastScene.current);
 const readerSceneNumber=state.saved?.project.screenplay?.scenes.findIndex(scene=>scene.id===readerScene?.sceneId)??-1;
 const readerOptions=[...(edited?.analysis?[{value:'understanding',label:'Ý tưởng và ý đồ đã lưu'}]:[]),...(state.saved?.plan_review?[{value:'plan-review',label:'Góp ý Story plan'}]:[]),...(edited?.draft?[{value:'plan',label:'Story plan'}]:[]),...(edited?.scene_outline?[{value:'outline',label:'Dàn cảnh'}]:[]),...(edited?.screenplay?[{value:'script',label:'Toàn bộ kịch bản'},...edited.screenplay.scenes.map((scene,index)=>({value:`scene:${scene.id}`,label:`Cảnh ${index+1} · ${scene.heading||'Cảnh chưa đặt tên'}`}))]:[]),...(edited?.screenplay_reviews?.length?[{value:'reviews',label:'Góp ý kịch bản'}]:[])];
 const adoptLabel=adopting?'Đang nhận toàn bộ nháp…':`Nhận toàn bộ nháp (${state.saved?.project.screenplay?.scenes.length??0} cảnh)`;
 const closeReader=()=>action(async()=>{setSelectedTarget(null);setEditing(false);try{sessionStorage.removeItem(`firstframe-draft-read:${id}`)}catch{}const button=readTrigger.current?.isConnected?readTrigger.current:[...document.querySelectorAll<HTMLButtonElement>('#draft-run [data-read-target]')].find(b=>b.dataset.readTarget===selectedTarget);const details=button?.closest('details');if(details)details.open=true;button?.focus();button?.scrollIntoView({block:'nearest',behavior:'auto'})});
 const cancelButton=run&&capabilities?.canCancel&&<button type="button" className="secondary" disabled={working} onClick={()=>void cancelRun()}>{run.status==='running'?'Hủy các bước tiếp theo':'Kết thúc lượt này'}</button>;
 const controls=run&&<div className="draft-run-actions">
  {['partial','failed','interrupted'].includes(run.status)&&<><button type="button" disabled={working||!capabilities?.canContinue||!!state.error} onClick={()=>void continueRun()}>Tiếp tục bước chưa gửi</button>{capabilities?.continueReason&&<p>{capabilities.continueReason}</p>}</>}
  {run.status!=='running'&&run.status!=='needs_input'&&cancelButton}
  {capabilities?.canAdopt&&<button type="button" disabled={working||state.saving||!!state.error} onClick={()=>void adoptRun()}>{adoptLabel}</button>}
  {run.cancel_requested&&<p>{run.status==='running'?'Đang dừng sau bước hiện tại; lần gọi đã gửi có thể vẫn trả kết quả.':'Lượt này đã được kết thúc. Phần đã lưu vẫn đọc được.'}</p>}
  {run.adopted_revision!==null&&<p>Đã nhận vào không gian viết. Các sửa tiếp theo lưu tại bản đang viết.</p>}
 </div>;
 const clarification=run?.status==='needs_input'&&edited?.analysis&&<ClarificationConversation idPrefix={`run-${id}-`} creatingScreenplay thinking={working} summary={edited.analysis.summary} questions={edited.analysis.missing_information} answers={edited.answers}
  onEditBrief={()=>void action(async()=>{receive(await runRequest(path+'/cancel','POST'));const input=document.getElementById('idea');revealWorkspaceTarget(input);input?.focus();input?.scrollIntoView({block:'center'})})}
  aiSuggestions={edited.analysis.ai_suggestions} idea={edited.idea} constraints={edited.constraints}
  onChange={(i,v)=>queue.edit({...edited,answers:edited.answers.map((a,j)=>j===i?v:a)})}
  confirmLabel={cards&&!follow.manual?'Tiếp tục và theo dõi':undefined}
  onConfirm={capabilities?.canContinue&&!state.error?()=>void continueRun():undefined}/>;
 const intentActions=run?.status==='needs_input'&&<div className="draft-workflow-decisions">{clarification}{!edited?.analysis&&<p>Đang tải câu hỏi đã lưu…</p>}{capabilities?.continueReason&&<p>{capabilities.continueReason}</p>}{cancelButton}</div>;
 function cardActions(item:WorkflowItem){
  if(item.kind==='intent'&&run?.status==='needs_input')return intentActions;
  if([item.id,...item.children.map(child=>child.id)].includes(run?.workflow_items?.find(i=>i.status==='running')?.id??''))return <div className="draft-workflow-decisions">{cancelButton}{run?.cancel_requested&&<p>Đang dừng sau bước hiện tại; kết quả đã gửi vẫn có thể được giữ.</p>}</div>;
  if(item.kind==='draft'&&run?.status!=='running'&&run?.status!=='needs_input')return controls;
  return null;
 }
 return <div onFocusCapture={e=>{const scene=(e.target as HTMLElement).closest<HTMLElement>('[data-candidate-scene]')?.dataset.candidateScene;if(scene)rememberScene(scene)}} onPointerDownCapture={()=>{lastRead.current=null;restoreRead.current=null}} onKeyDownCapture={()=>{lastRead.current=null;restoreRead.current=null}} onCompositionStartCapture={()=>queue.composition(true)} onCompositionEndCapture={()=>queue.composition(false)}>
   {syncError&&<p role="status" className="draft-workflow-network">Chưa cập nhật được tiến độ. Bản đã tải vẫn được giữ; FirstFrame sẽ tự thử kết nối lại. {syncError}</p>}
   {!run&&!syncError&&<div role="status"><p>Đang tải lượt tạo đã lưu…</p><WorkflowSkeleton/></div>}
   {run&&<>
     <p role="status"><strong>{draftRunSummary(run)}</strong></p>
     <label className="draft-workflow-toggle"><input type="checkbox" disabled={!run.workflow_items?.length} checked={cards} onChange={e=>{setReveals([]);setCards(e.target.checked);try{sessionStorage.setItem(`firstframe-draft-cards:${id}`,e.target.checked?'1':'0')}catch{}}}/>Xem thử tiến độ dạng card</label>
     {cards&&<DraftWorkflow run={run} candidate={state.saved} following={follow.enabled} onFollowingChange={changeFollowing} reading={!!selectedTarget} reveals={reveals} actions={cardActions} onRead={(target,trigger)=>void action(async()=>{readCard(target,trigger)})}/>}
     {run.total_scenes>0&&<progress aria-label="Số cảnh đã lưu" max={run.total_scenes} value={run.completed_scenes}/>}
     {run.revision_instructions&&<p className="preserve-lines">Yêu cầu thay đổi cấu trúc: {run.revision_instructions} · {run.affected_scene_ids?.length??0} cảnh nguồn có thể bị ảnh hưởng. Bản đang viết được giữ nguyên cho đến khi bạn nhận bản nháp mới.</p>}
     <p>Tiến độ được giữ trên máy chủ. Mở lại trang không gọi AI lần nữa.</p>
     {run.error&&<p role="alert" className="error">{run.error}</p>}
     {run.review_error&&<p className="form-message">{run.review_error}</p>}
     {run.adopted_revision===null&&run.source_revision!==props.project.revision&&<p className="storage-note">Bản nguồn đã thay đổi từ khi khởi động. Khi nhận, hệ thống sẽ đối chiếu lại nội dung; phần bản nháp riêng vẫn giữ.</p>}
     <button type="button" className="secondary" disabled={working} onClick={()=>void action(async()=>{await inspect()})}>Kiểm tra tiến độ</button>
     {!cards&&<>{controls}{run.status==='running'&&cancelButton}</>}
   </>}
   {error&&<p role="alert" className="error">{error}</p>}
   {state.local&&<p role="status">{state.saving?'Đang lưu bản nháp riêng…':state.error?'Chưa xác nhận lưu bản nháp riêng':dirty?'Chờ tự lưu bản nháp riêng':'Bản nháp riêng đã lưu'}</p>}
   {state.error&&<div role="alert"><p>{state.error}</p><button type="button" onClick={()=>void queue.flush(true).catch(e=>setError(e instanceof Error?e.message:String(e)))}>Thử lưu lại bản nháp</button><button type="button" disabled={state.saving} onClick={()=>{if(window.confirm('Mở lại sẽ bỏ phần candidate chưa xác nhận lưu. Hãy tải bản sao trước nếu cần giữ.'))void queue.reopen().then(()=>setError('')).catch(e=>setError(e instanceof Error?e.message:String(e)))}}>Mở lại bản nháp đã lưu</button><button type="button" onClick={()=>{const blob=new Blob([JSON.stringify(state.local,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`draft-${id}.json`;a.click();URL.revokeObjectURL(url)}}>Tải bản sao bản nháp</button></div>}
   {!cards&&intentActions}
   <div className={cards?'draft-candidate-reader':undefined} role={cards?'region':undefined} aria-label={cards?'Đọc và sửa bản nháp':undefined} hidden={cards&&!selectedTarget}>
   {cards&&selectedTarget&&<header className="draft-candidate-reader-header" aria-busy={adopting}><h3>{run?draftReaderHeading(run,state.saved,selectedTarget,editing):'Bản nháp đang xem'}</h3><p>{state.saving?'Đang lưu bản nháp riêng…':state.error?'Chưa xác nhận lưu bản nháp riêng':dirty?'Có thay đổi đang chờ lưu':'Bản nháp riêng đã lưu'}</p>{capabilities?.canAdopt&&readerScene&&<p className="storage-note">Nhận toàn bộ bản nháp vào workspace, sau đó mở cảnh “{state.saved?.project.screenplay?.scenes[readerSceneNumber]?.heading||`Cảnh ${readerSceneNumber+1}`}” để sửa.</p>}{adopting&&<p role="status">Đang nhận toàn bộ nháp…</p>}<div className="draft-reader-picker"><label htmlFor={readerSelectId}>Phần cần xem hoặc sửa</label><select id={readerSelectId} value={selectedTarget} disabled={working||state.saving} onChange={event=>{const target=event.target.value;void action(async()=>readCard(target))}}>{readerOptions.map(option=><option key={option.value} value={option.value}>{option.label}</option>)}</select></div><div className="draft-run-actions">{capabilities?.canAdopt&&readerScene&&<button type="button" disabled={working||state.saving||!!state.error} onClick={()=>void adoptRun(readerScene.sceneId)}>{adoptLabel}</button>}<button type="button" className="secondary" disabled={working} onClick={()=>void closeReader()}>Quay lại card</button>{capabilities?.canEdit&&(selectedTarget==='plan'||showScript)&&<button type="button" disabled={working||!!state.error} onClick={()=>{if(editing)void action(async()=>setEditing(false));else setEditing(true)}}>{editing?'Lưu và đọc lại':'Chỉnh bản nháp'}</button>}</div></header>}
   {edited?.analysis&&<details hidden={!show('understanding')} open={cards?true:undefined} id={`run-${id}-understanding`} tabIndex={-1}><summary>Điều đã hiểu và ý đồ đã lưu</summary><p>{edited.analysis.summary}</p><p>{edited.constraints.join(' · ')}</p></details>}
   {!!state.saved?.plan_review&&<details hidden={!show('plan-review')} open={cards?true:undefined} id={`run-${id}-plan-review`} tabIndex={-1}><summary>Góp ý story plan đã lưu</summary><p>Góp ý thuộc nguồn lúc tạo story plan; chỉ dùng tham khảo nếu bạn đã sửa bản.</p>{typeof state.saved.plan_review==='object'&&state.saved.plan_review!==null&&'findings' in state.saved.plan_review&&Array.isArray(state.saved.plan_review.findings)&&state.saved.plan_review.findings.map((f:unknown,i:number)=>f&&typeof f==='object'&&'message' in f&&typeof f.message==='string'?<p key={i}>{f.message}</p>:null)}</details>}
   {edited?.draft&&<details hidden={!show('plan')} open={cards?true:undefined} id={`run-${id}-plan`} tabIndex={-1}><summary>Story plan · {edited.draft.title}</summary>{cards&&editable?<div className="draft-plan-fields"><label>Tên story plan<input disabled={working} maxLength={200} value={edited.draft.title} onChange={e=>queue.edit({...edited,draft:{...edited.draft!,title:e.target.value}})}/></label><label>Tóm tắt story plan<textarea disabled={working} rows={3} maxLength={2000} value={edited.draft.logline} onChange={e=>queue.edit({...edited,draft:{...edited.draft!,logline:e.target.value}})}/></label>{edited.draft.sections.map((section,i)=><label key={i}>{section.title}<textarea disabled={working} rows={4} maxLength={10000} value={section.content} onChange={e=>queue.edit({...edited,draft:{...edited.draft!,sections:edited.draft!.sections.map((s,j)=>j===i?{...s,content:e.target.value}:s)}})}/></label>)}</div>:<><p className="preserve-lines">{edited.draft.logline}</p>{edited.draft.sections.map((s,i)=><p key={i} className="preserve-lines"><strong>{s.title}</strong><br/>{s.content}</p>)}</>}</details>}
   {edited?.scene_outline&&<details hidden={!show('outline')} open={cards?true:undefined} id={`run-${id}-outline`} tabIndex={-1}><summary>Dàn cảnh · {edited.scene_outline.scenes.length} cảnh</summary><ol>{edited.scene_outline.scenes.map(s=><li key={s.id}><strong>{s.title}</strong><p className="preserve-lines">{s.action}</p></li>)}</ol></details>}
   {edited?.screenplay&&<div className="candidate-scenes" hidden={!showScript} id={`run-${id}-script`} tabIndex={-1}><h3>{cards?'Nội dung kịch bản':run?draftReaderHeading(run,state.saved):'Kịch bản nháp'}</h3>{edited.screenplay.scenes.map((scene,index)=><section key={scene.id} hidden={cards&&selectedTarget!=='script'&&selectedTarget!==`scene:${scene.id}`} id={`run-${id}-scene:${scene.id}`} tabIndex={-1} className="candidate-scene" data-candidate-scene={scene.id}>
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
