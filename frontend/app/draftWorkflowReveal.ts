import type {Candidate,DraftRun} from './draftRunsApi';
import {cardResult,type WorkflowItem} from './draftWorkflowState';

function token(item:WorkflowItem,candidate:Candidate|null):string|null{
 if(item.result)return String(item.result.candidate_revision);
 if(item.kind==='review'&&candidate?.project.screenplay_reviews?.length)return JSON.stringify(candidate.project.screenplay_reviews);
 return null;
}

// Kept by the run panel, so toggling card view never replays saved results.
export class WorkflowReveals {
 private initialized=false;
 private seen=new Map<string,string>();
 private awaitingHistory=new Set<string>();
 update(run:DraftRun,candidate:Candidate|null):string[]{
  const changed:string[]=[];
  for(const item of run.workflow_items??[]){
   if(!this.initialized&&!candidate&&item.kind==='review')this.awaitingHistory.add(item.id);
   const historyLoaded=!!candidate&&this.awaitingHistory.delete(item.id);
   const value=token(item,candidate);
   if(value===null)continue;
   if(!this.initialized){this.seen.set(item.id,value);continue;}
   if(historyLoaded&&!item.result){this.seen.set(item.id,value);continue;}
   if(!cardResult(item,candidate)?.target)continue;
   if(this.seen.get(item.id)!==value){this.seen.set(item.id,value);changed.push(item.id);}
  }
  this.initialized=true;
  return changed;
 }
}
