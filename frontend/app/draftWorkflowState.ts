import type {DraftRun, Candidate} from './draftRunsApi';
export type WorkflowStatus='pending'|'running'|'needs_input'|'completed'|'warning'|'failed'|'interrupted'|'cancelled'|'skipped'|'unknown';
export type WorkflowKind='analysis'|'intent'|'plan'|'plan_review'|'outline'|'write'|'review'|'review_scene'|'draft';
export type WorkflowItem={id:string;kind:WorkflowKind;scene_id:string|null;status:WorkflowStatus;started_at:string|null;finished_at:string|null;result:{kind:WorkflowKind;id:string|null;candidate_revision:number}|null;error_code:string|null;children:WorkflowItem[]};
const statuses=['pending','running','needs_input','completed','warning','failed','interrupted','cancelled','skipped','unknown'];
const kinds=['analysis','intent','plan','plan_review','outline','write','review','review_scene','draft'];
const integer=(v:unknown)=>Number.isSafeInteger(v)&&Number(v)>=0;
const nullableText=(v:unknown)=>v===null||typeof v==='string';
export function validProgress(r:Record<string,unknown>):boolean{
 if(!('progress_version' in r))return !('workflow_items' in r||'progress_revision' in r);
 if(![0,1].includes(Number(r.progress_version))||typeof r.progress_version!=='number'||!integer(r.progress_revision)||!Array.isArray(r.workflow_items)||r.workflow_items.length>13)return false;
 if(typeof r.can_continue!=='boolean'||!nullableText(r.continue_block_reason)||!nullableText(r.continue_block_message))return false;
 const ids=new Set<string>();
 function valid(v:unknown,child=false):boolean{
  if(!v||typeof v!=='object')return false;const i=v as Record<string,unknown>;
  if(typeof i.id!=='string'||!i.id||ids.has(i.id)||typeof i.kind!=='string'||!kinds.includes(i.kind)||typeof i.status!=='string'||!statuses.includes(i.status)||!['scene_id','started_at','finished_at','error_code'].every(k=>nullableText(i[k]))||!Array.isArray(i.children)||i.children.length>6||child&&i.children.length>0)return false;
  ids.add(i.id);
  if(i.result!==null){if(!i.result||typeof i.result!=='object')return false;const a=i.result as Record<string,unknown>;if(typeof a.kind!=='string'||!kinds.includes(a.kind)||!nullableText(a.id)||!integer(a.candidate_revision))return false;}
  else if(i.status==='completed')return false;
  return i.children.every(c=>valid(c,true));
 }
 return r.workflow_items.every(i=>valid(i));
}
export function newerRun(current:DraftRun|null,next:DraftRun):DraftRun{
 if(current&&current.id===next.id&&(next.candidate_revision<current.candidate_revision||(next.progress_revision??0)<(current.progress_revision??0)))return current;
 return next;
}
export const workflowLabels:Record<WorkflowKind,string>={analysis:'Đọc ý tưởng',intent:'Ý đồ và điểm còn mở',plan:'Story plan',plan_review:'Đối chiếu story plan',outline:'Dàn cảnh',write:'Viết nội dung cảnh',review:'Review kịch bản',review_scene:'Góp ý cảnh',draft:'Bản nháp để review'};
export const workflowStatusLabels:Record<WorkflowStatus,string>={pending:'Chờ bước trước',running:'Đang xử lý',needs_input:'Cần bạn xem',completed:'Đã có kết quả',warning:'Cần kiểm tra góp ý',failed:'Chưa hoàn tất',interrupted:'Bị gián đoạn',cancelled:'Đã hủy',skipped:'Chưa thực hiện',unknown:'Không có trạng thái chi tiết'};
export function nextDraftFollow(current:{enabled:boolean;manual:boolean},enabled:boolean,manual=true){
 return {enabled,manual:!enabled&&(manual||current.manual)};
}
export function draftReaderHeading(run:DraftRun,candidate:Candidate|null,target?:string|null,editing=false):string{
 const current=!!candidate&&candidate.revision>=run.candidate_revision;
 const heading=run.adopted_revision!=null?'Nháp đã nhận':run.status==='running'?'Nháp đang hình thành':run.status==='ready'?(current?'Nháp sẵn sàng':'Đang tải nháp đã lưu'):run.status==='partial'?'Nháp đã lưu một phần':'Phần nháp đã lưu';
 const scenes=candidate?.project.screenplay?.scenes??[];
 const index=target?.startsWith('scene:')?scenes.findIndex(scene=>scene.id===target.slice(6)):-1;
 return heading+(index>=0?` · Đang ${editing?'sửa':'đọc'} cảnh ${index+1}/${scenes.length} · ${scenes[index].heading||'Cảnh chưa đặt tên'}`:'');
}
export function draftRunSummary(run:DraftRun):string{
 const scenes=`Đã viết ${run.completed_scenes}/${run.total_scenes||'…'} cảnh`;
 if(run.adopted_revision!=null)return `Đã nhận vào workspace · ${scenes}`;
 if(run.cancel_requested&&run.status==='running')return `Đang kết thúc lượt · ${scenes} đã được giữ`;
 if(run.status==='running')return run.step==='review'?`${scenes} · Đang góp ý kịch bản`:`Đang tạo nháp · ${scenes}`;
 if(run.status==='ready')return `Sẵn sàng nhận nháp · ${scenes}${run.review_error?' · Góp ý chưa hoàn tất':''}`;
 if(run.status==='partial')return `Nháp đã lưu một phần · ${scenes}${run.review_error?' · Góp ý chưa hoàn tất':''}`;
 return `${run.status==='needs_input'?'Cần bạn làm rõ':run.status==='cancelled'?'Lượt đã kết thúc':'Lượt chưa hoàn tất'} · ${scenes}`;
}
// These labels describe the view; stored workflow states remain untouched.
export function workflowItemDisplay(item:WorkflowItem,run:DraftRun):{label:string;complete:boolean}{
 if(item.kind==='draft'&&item.result){
  if(run.adopted_revision!=null)return {label:'Đã nhận vào workspace',complete:true};
  if(run.status==='running')return {label:run.step==='review'?'Đã viết xong · Đang chờ góp ý':'Nháp đang hình thành',complete:false};
  if(run.status==='ready')return {label:'Sẵn sàng nhận nháp',complete:true};
  return {label:run.status==='partial'?'Nháp đã lưu một phần':'Phần nháp đã được giữ',complete:false};
 }
 return {label:workflowStatusLabels[item.status],complete:item.status==='completed'};
}
export function parentWorkflowItems(source:WorkflowItem[]):WorkflowItem[]{
 if(!source.length)return [];
 const children=source.filter(i=>i.kind==='write');
 const status=children.find(i=>i.status==='running')?.status
   ??children.find(i=>i.status==='needs_input')?.status
   ??children.find(i=>['failed','interrupted','warning','unknown','cancelled','skipped'].includes(i.status))?.status
   ??(children.length&&children.every(i=>i.status==='completed')?'completed':'pending');
 const results=children.flatMap(i=>i.result?[i.result]:[]);
 const result=results.sort((a,b)=>b.candidate_revision-a.candidate_revision)[0]??null;
 const write:WorkflowItem={id:'write',kind:'write',scene_id:null,status,children,
   started_at:children.find(i=>i.started_at)?.started_at??null,
   finished_at:status==='completed'?children[children.length-1].finished_at:null,
   result,error_code:null};
 return ['analysis','intent','plan','plan_review','outline','write','review','draft'].flatMap(id=>{
   const item=id==='write'?write:source.find(i=>i.id===id);
   return item?[item]:[];
 });
}
export function currentWorkflowItem(items:WorkflowItem[]):WorkflowItem|undefined{
 const all=items.flatMap(i=>i.children.length?i.children:[i]);
 return all.find(i=>i.status==='needs_input')??all.find(i=>i.status==='running');
}
export function workflowItemLabel(item:WorkflowItem,candidate:Candidate|null):string{
 if(item.kind==='write'&&!item.scene_id)return 'Viết kịch bản';
 if(item.scene_id){
   const scenes=candidate?.project.screenplay?.scenes??[];
   const index=scenes.findIndex(s=>s.id===item.scene_id);
   return `${workflowLabels[item.kind]}${index>=0?` ${index+1}/${scenes.length} · ${scenes[index].heading}`:''}`;
 }
 return workflowLabels[item.kind];
}
export function cardResult(item:WorkflowItem,candidate:Candidate|null):{text:string;target:string}|null{
 if(!item.result){if(item.kind==='review'&&candidate?.project.screenplay_reviews?.length)return {text:'Một phần góp ý đã lưu; xem đúng nguồn trước khi sửa.',target:'reviews'};return null;}
 if(!candidate||candidate.revision<item.result.candidate_revision)return {text:'Đang tải kết quả đã lưu…',target:''};
 const p=candidate.project;
 switch(item.kind){
 case 'analysis':return p.analysis?{text:p.analysis.summary,target:'understanding'}:null;
 case 'intent':return {text:'Ý đồ đã được giữ cùng bản nháp. Các phần để mở vẫn do bạn quyết định.',target:'understanding'};
 case 'plan':return p.draft?{text:p.draft.title+' · '+p.draft.logline,target:'plan'}:null;
 case 'plan_review':return candidate.plan_review?{text:'Góp ý story plan đã lưu riêng; bạn tự cân nhắc.',target:'plan-review'}:null;
 case 'outline':return p.scene_outline?{text:`${p.scene_outline.scenes.length} cảnh đã lưu.`,target:'outline'}:null;
 case 'write':{if(!item.scene_id)return {text:`${item.children.filter(i=>i.status==='completed').length}/${item.children.length} cảnh đã lưu.`,target:'script'};const scene=p.screenplay?.scenes.find(s=>s.id===item.scene_id);return scene?{text:scene.heading+(scene.blocks[0]?' · '+scene.blocks[0].text:''),target:'scene:'+scene.id}:null;}
 case 'review':return {text:'Góp ý theo nguồn đã lưu, không tự áp dụng sửa đổi.',target:'reviews'};
 case 'draft':return p.screenplay?{text:`${p.screenplay.scenes.length} cảnh trong bản nháp. Bạn đọc và chọn dùng.`,target:'script'}:null;
 default:return null;
 }
}
