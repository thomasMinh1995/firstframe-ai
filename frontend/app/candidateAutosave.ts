import type {Candidate} from './draftRunsApi';
import type {Project} from './projectsApi';
const editable=(p:Project)=>({draft:p.draft,answers:p.answers,screenplay:p.screenplay?{id:p.screenplay.id,version:p.screenplay.version,scenes:p.screenplay.scenes}:null});
const text=(p:Project)=>JSON.stringify({draft:p.draft,answers:p.answers,scenes:p.screenplay?.scenes});
export class CandidateAutosave {
 private state:{local:Candidate|null;saved:Candidate|null;saving:boolean;error:string|null}={local:null,saved:null,saving:false,error:null};
 private listeners=new Set<()=>void>();
 private timer:ReturnType<typeof setTimeout>|undefined;
 private flight:Promise<void>|null=null;
 private composing=false;
 private uncertain:{sent:Candidate;body:unknown;id:string}|null=null;
 constructor(private write:(body:unknown)=>Promise<Candidate>,private read:()=>Promise<Candidate>,private delay=1000){}
 getSnapshot=()=>this.state;
 subscribe=(fn:()=>void)=>{this.listeners.add(fn);return()=>{this.listeners.delete(fn)}};
 private update(patch:Partial<typeof this.state>){this.state={...this.state,...patch};this.listeners.forEach(f=>f());}
 get dirty(){return !!this.state.local&&!!this.state.saved&&text(this.state.local.project)!==text(this.state.saved.project);}
 accept=(c:Candidate)=>{if(this.dirty||this.state.error||this.flight)return;this.update({local:c,saved:c});};
 edit=(project:Project)=>{if(!this.state.local)return;this.update({local:{...this.state.local,project}});this.schedule();};
 composition=(active:boolean)=>{this.composing=active;this.schedule();};
 stop=()=>{clearTimeout(this.timer);};
 reopen=async()=>{this.stop();if(this.flight)await this.flight.catch(()=>{});const next=await this.read();this.uncertain=null;this.update({local:next,saved:next,error:null});};
 private schedule(){this.stop();if(this.dirty&&!this.composing&&!this.state.error&&!this.flight)this.timer=setTimeout(()=>void this.flush().catch(()=>{}),this.delay);}
 private ack(sent:Candidate,next:Candidate){
   const local=this.state.local!;
   const project=local===sent?next.project:{...next.project,draft:local.project.draft,answers:local.project.answers,
     screenplay:next.project.screenplay&&local.project.screenplay?{...next.project.screenplay,scenes:local.project.screenplay.scenes}:local.project.screenplay};
   this.uncertain=null;this.update({local:{...next,project},saved:next,error:null});
 }
 flush=async(retry=false):Promise<void>=>{
   this.stop();if(this.flight){await this.flight;return this.flush(retry)}
   if(this.composing)throw Error('Hãy hoàn tất ký tự đang nhập.');
   if(this.state.error&&!retry)throw Error(this.state.error);
   const send=async(sent:Candidate,body:unknown,id:string)=>{
     let next:Candidate;
     try{next=await this.write(body)}catch(error){
       if(error instanceof Error&&"status" in error&&error.status===422){this.uncertain=null;throw error;}
       const remote=await this.read().catch(()=>null);
       if(!remote||remote.save_id!==id||remote.revision!==sent.revision+1)throw error;
       next=remote;
     }
     if(next.save_id!==id||next.revision!==sent.revision+1)throw Error('Candidate đã đổi ở cửa sổ khác. Bản đang sửa vẫn giữ.');
     this.ack(sent,next);
   };
   const work=async()=>{
     if(this.uncertain){const {sent,body,id}=this.uncertain;try{await send(sent,body,id)}catch(error){
       if(!(error instanceof Error&&"status" in error&&error.status===422&&this.state.local&&text(this.state.local.project)!==text(sent.project)))throw error;
     }}
     this.update({error:null});
     while(this.dirty){
       const sent=this.state.local!,id=crypto.randomUUID();
       const body={revision:sent.revision,save_id:id,...editable(sent.project)};
       this.uncertain={sent,body,id};await send(sent,body,id);
     }
   };
   this.update({saving:true});this.flight=work();
   try{await this.flight}catch(error){this.update({error:error instanceof Error?error.message:'Chưa xác nhận được lần lưu candidate.'});throw error}
   finally{this.flight=null;this.update({saving:false});this.schedule()}
 };
}
