import {validProgress,type WorkflowItem} from './draftWorkflowState';
import {request, isProject, ProjectRequestError, type Project} from './projectsApi';
export type DraftRun = {progress_version?:0|1;progress_revision?:number;workflow_items?:WorkflowItem[];can_continue?:boolean;continue_block_reason?:string|null;continue_block_message?:string|null;created_at?:string|null;revision_instructions?:string;affected_scene_ids?:string[];id:string;project_id:string;source_revision:number;status:'running'|'needs_input'|'ready'|'partial'|'failed'|'interrupted'|'cancelled';step:string;sending:boolean;cancel_requested:boolean;candidate_revision:number;completed_scenes:number;total_scenes:number;error:string|null;review_error:string|null;adopted_revision:number|null};
export type Candidate={revision:number;save_id?:string|null;project:Project;plan_review?:unknown};
export const runPath=(projectId:string,id?:string)=>`/${projectId}/draft-runs${id?`/${id}`:''}`;
export function isDraftRun(value:unknown):value is DraftRun {
  if(!value||typeof value!=='object')return false;
  const r=value as Record<string,unknown>;
  return typeof r.id==='string'&&typeof r.project_id==='string'&&['running','needs_input','ready','partial','failed','interrupted','cancelled'].includes(String(r.status))
    &&validProgress(r)&&typeof r.step==='string'&&['candidate_revision','completed_scenes','total_scenes','source_revision'].every(k=>Number.isInteger(r[k])&&Number(r[k])>=0)
    &&typeof r.cancel_requested==='boolean'&&typeof r.sending==='boolean'
    &&['error','review_error'].every(k=>r[k]===null||typeof r[k]==='string')
    &&(r.adopted_revision===null||(Number.isInteger(r.adopted_revision)&&Number(r.adopted_revision)>=0));
}
export async function runRequest(path:string,method='GET',body?:unknown):Promise<DraftRun>{
  const r=await request(path,method,body);if(!isDraftRun(r))throw Error('Trạng thái tạo nháp không hợp lệ.');return r;
}
export async function listRuns(projectId:string):Promise<DraftRun[]>{
 const r=await request(runPath(projectId));if(!Array.isArray(r)||!r.every(isDraftRun)||r.some(run=>run.project_id!==projectId))throw Error('Danh sách lượt tạo không hợp lệ.');return r;
}
export function blockingDraftRun(runs:DraftRun[]):DraftRun|null {
 return runs.find(r=>r.adopted_revision===null&&['running','needs_input','partial','failed','interrupted'].includes(r.status))??null;
}
export function draftRunActionLabel(run:DraftRun|null):string|null {
 if(!run)return null;
 if(run.status==='running')return run.cancel_requested?'Xem tiến độ dừng':'Xem tiến độ';
 if(run.status==='needs_input')return 'Tiếp tục làm rõ';
 return 'Xem lượt tạo chưa hoàn tất';
}
export async function startOrOpenDraftRun(projectId:string,body:{revision:number;request_id:string;revision_instructions?:string}):Promise<DraftRun>{
 const existing=blockingDraftRun(await listRuns(projectId));
 if(existing)return existing;
 try{return await runRequest(runPath(projectId),'POST',body)}catch(error){
  if(!(error instanceof ProjectRequestError)||error.status!==409)throw error;
  const detail=error.detail;
  if(detail&&typeof detail==='object'&&'code' in detail&&detail.code==='active_draft_run'&&'run' in detail
    &&isDraftRun(detail.run)&&detail.run.project_id===projectId)return detail.run;
  // Older servers and a concurrent start are reconciled by GET, never another POST.
  const blocking=blockingDraftRun(await listRuns(projectId).catch(()=>[]));
  if(blocking)return blocking;
  throw error;
 }
}
export async function candidateRequest(path:string,method='GET',body?:unknown):Promise<Candidate>{
 const r=await request(path,method,body) as Candidate;
 if(!r||!Number.isInteger(r.revision)||!isProject(r.project)||r.project.id!==path.split('/')[1])throw Error('Bản nháp trả về không hợp lệ.');return r;
}
export const statusLabels={running:'Đang tạo',needs_input:'Cần bạn xem phần còn thiếu',ready:'Bản nháp đã sẵn sàng',partial:'Đã giữ một phần',failed:'Chưa tạo được bản nháp',interrupted:'Bị gián đoạn',cancelled:'Đã hủy'};
export const stepLabels:Record<string,string>={prepare:'Giữ nguồn ý tưởng',clarify:'Đọc ý tưởng',plan:'Tạo story plan',plan_review:'Đối chiếu story plan',outline:'Tạo dàn cảnh',write:'Viết nội dung cảnh',review:'Chuẩn bị góp ý',done:'Hoàn tất'};
