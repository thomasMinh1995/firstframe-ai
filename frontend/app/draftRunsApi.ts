import {request, isProject, type Project} from './projectsApi';
export type DraftRun = {revision_instructions?:string;affected_scene_ids?:string[];id:string;project_id:string;source_revision:number;status:'running'|'needs_input'|'ready'|'partial'|'failed'|'interrupted'|'cancelled';step:string;sending:boolean;cancel_requested:boolean;candidate_revision:number;completed_scenes:number;total_scenes:number;error:string|null;review_error:string|null;adopted_revision:number|null};
export type Candidate={revision:number;save_id?:string|null;project:Project};
export const runPath=(projectId:string,id?:string)=>`/${projectId}/draft-runs${id?`/${id}`:''}`;
export function isDraftRun(value:unknown):value is DraftRun {
  if(!value||typeof value!=='object')return false;
  const r=value as Record<string,unknown>;
  return typeof r.id==='string'&&typeof r.project_id==='string'&&['running','needs_input','ready','partial','failed','interrupted','cancelled'].includes(String(r.status))
    &&typeof r.step==='string'&&['candidate_revision','completed_scenes','total_scenes','source_revision'].every(k=>Number.isInteger(r[k])&&Number(r[k])>=0)
    &&typeof r.cancel_requested==='boolean'&&typeof r.sending==='boolean'
    &&['error','review_error'].every(k=>r[k]===null||typeof r[k]==='string')
    &&(r.adopted_revision===null||(Number.isInteger(r.adopted_revision)&&Number(r.adopted_revision)>=0));
}
export async function runRequest(path:string,method='GET',body?:unknown):Promise<DraftRun>{
  const r=await request(path,method,body);if(!isDraftRun(r))throw Error('Trạng thái tạo nháp không hợp lệ.');return r;
}
export async function listRuns(projectId:string):Promise<DraftRun[]>{
 const r=await request(runPath(projectId));if(!Array.isArray(r)||!r.every(isDraftRun))throw Error('Danh sách lượt tạo không hợp lệ.');return r;
}
export async function candidateRequest(path:string,method='GET',body?:unknown):Promise<Candidate>{
 const r=await request(path,method,body) as Candidate;
 if(!r||!Number.isInteger(r.revision)||!isProject(r.project)||r.project.id!==path.split('/')[1])throw Error('Bản nháp trả về không hợp lệ.');return r;
}
export const statusLabels={running:'Đang tạo',needs_input:'Cần bạn xem phần còn thiếu',ready:'Bản nháp đã sẵn sàng',partial:'Đã giữ một phần',failed:'Chưa tạo được bản nháp',interrupted:'Bị gián đoạn',cancelled:'Đã hủy'};
export const stepLabels:Record<string,string>={prepare:'Giữ nguồn ý tưởng',clarify:'Đọc ý tưởng',plan:'Tạo story plan',plan_review:'Đối chiếu story plan',outline:'Tạo dàn cảnh',write:'Viết nội dung cảnh',review:'Chuẩn bị góp ý',done:'Hoàn tất'};
