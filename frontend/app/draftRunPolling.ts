import type {Candidate,DraftRun} from './draftRunsApi';

type Ports={
 readRun:()=>Promise<DraftRun>;readCandidate:()=>Promise<Candidate>;
 current:()=>DraftRun|null;receive:(run:DraftRun)=>void;
 candidateRevision:()=>number;accept:(candidate:Candidate)=>void;
 onError:(error:string|null)=>void;
};
type Schedule=(task:()=>void,delay:number)=>()=>void;
const schedule:Schedule=(task,delay)=>{const timer=setTimeout(task,delay);return()=>clearTimeout(timer)};

// Retries are reads only. A lost response must never resend model work.
export class DraftRunPoller {
 private stopped=false;
 private cancel:(()=>void)|undefined;
 private delay=1500;
 constructor(private ports:Ports,private later:Schedule=schedule){}
 stop=()=>{this.stopped=true;this.cancel?.()};
 start=async()=>{
  if(this.stopped)return;
  const p=this.ports,previous=p.current()?.progress_revision;
  let retry=false;
  try{
   const received=await p.readRun();if(this.stopped)return;
   p.receive(received);
   const run=p.current()!;
   if(p.candidateRevision()<run.candidate_revision){
    const candidate=await p.readCandidate();if(this.stopped)return;
    p.accept(candidate);
   }
   p.onError(null);
   retry=run.status==='running'||p.candidateRevision()<run.candidate_revision;
   this.delay=previous!==run.progress_revision?1500:Math.min(8000,this.delay*1.5);
  }catch(error){
   if(this.stopped)return;
   p.onError(error instanceof Error?error.message:'Chưa cập nhật được tiến độ.');
   retry=true;this.delay=Math.min(8000,this.delay*1.5);
  }
  if(retry&&!this.stopped)this.cancel=this.later(()=>void this.start(),this.delay);
 };
}
