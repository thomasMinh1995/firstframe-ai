import type {Candidate,DraftRun} from './draftRunsApi';
import type {Project} from './projectsApi';

export function runCapabilities(run:DraftRun,candidate:Candidate|null){
 const current=!!candidate&&candidate.revision>=run.candidate_revision;
 const owned=run.adopted_revision===null;
 const resumable=['needs_input','partial','failed','interrupted'].includes(run.status);
 return {
  canContinue:owned&&!run.cancel_requested&&resumable&&current&&run.can_continue===true,
  continueReason:resumable&&run.can_continue!==true?(run.continue_block_message??'Máy chủ chưa xác nhận có thể tiếp tục. Hãy kiểm tra tiến độ; phần đã có vẫn được giữ.'):null,
  canCancel:owned&&!run.cancel_requested&&['running','needs_input','partial','failed','interrupted'].includes(run.status),
  canAdopt:owned&&!run.cancel_requested&&current&&['ready','partial'].includes(run.status)&&!!candidate?.project.screenplay?.scenes.some(s=>s.blocks.length),
  canEdit:owned&&current&&run.status!=='running'&&run.status!=='needs_input'&&!!candidate?.project.draft,
 };
}

export function continuationBody(run:DraftRun,candidate:Candidate|null){
 if(!runCapabilities(run,candidate).canContinue)throw Error(run.continue_block_message??'Lượt này chưa được xác nhận có thể tiếp tục. Hãy kiểm tra tiến độ.');
 if(!candidate||candidate.revision!==run.candidate_revision)throw Error('Bản nháp đã đổi. Hãy kiểm tra tiến độ trước khi tiếp tục.');
 return {candidate_revision:candidate.revision,...(run.status==='needs_input'?{answers:candidate.project.answers}:{})};
}

export async function confirmedAdoption(write:()=>Promise<Project>,readRun:()=>Promise<DraftRun>,readProject:()=>Promise<Project>,revision:number):Promise<Project>{
 try{return await write()}catch(error){
  const checked=await readRun().catch(()=>null);
  if(!checked||checked.adopted_revision===null||checked.candidate_revision!==revision)throw error;
  return readProject();
 }
}
