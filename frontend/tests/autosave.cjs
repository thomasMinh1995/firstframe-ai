const assert = require('node:assert/strict');
const {randomUUID} = require('node:crypto');
const {ProjectAutosave, acknowledgeSave} = require(process.argv[2] + '/projectAutosave.js');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const deferred = () => {let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b;});return {promise,resolve,reject};};
const project = () => ({id:randomUUID(),revision:1,title:'Tên phim',idea:'Một chiếc túi.',response_language:'vi',
 constraints:[],answers:[],analysis:null,draft:null,feedback:null,feedback_is_current:false,versions:[],clarification_history:[],updated_at:'now'});
const acknowledge = (sent,body) => ({...structuredClone(sent),revision:sent.revision+1,last_save_id:body.save_id,last_save_revision:sent.revision+1});

(async()=>{
 // One in-flight write, with new text queued while its acknowledgement is delayed.
 const first=deferred(),writes=[];let remote=project(),active=0,maxActive=0;
 const saver=new ProjectAutosave(async(sent,body)=>{
   active++;maxActive=Math.max(active,maxActive);writes.push({sent:structuredClone(sent),body});
   if(writes.length===1)await first.promise;
   remote=acknowledge(sent,body);active--;return remote;
 },async()=>remote,5,randomUUID);
 saver.accept(remote);saver.setProject(p=>({...p,title:'Lần một'}));
 const flushing=saver.flush();saver.setProject(p=>({...p,title:'Lần hai'}));
 const alsoFlushing=saver.flush();first.resolve();await Promise.all([flushing,alsoFlushing]);
 assert.equal(writes.length,2);assert.equal(maxActive,1);assert.equal(writes[1].sent.revision,2);
 assert.equal(saver.getSnapshot().project.title,'Lần hai');assert.equal(saver.getSnapshot().saved.title,'Lần hai');assert.equal(saver.dirty,false);
 assert.equal(writes[0].body.edit_session_id,writes[1].body.edit_session_id);

 // A lost acknowledgement is recovered by reading the exact save ID, without replay.
 let lost=project(),calls=0;
 const recovered=new ProjectAutosave(async(sent,body)=>{calls++;lost=acknowledge(sent,body);throw Error('Mất phản hồi');},async()=>lost,5,randomUUID);
 recovered.accept(lost);recovered.setProject(p=>({...p,idea:'Đã lưu nhưng mất phản hồi'}));await recovered.flush();
 assert.equal(calls,1);assert.equal(recovered.dirty,false);assert.equal(recovered.getSnapshot().error,null);

 // Failed writes stop. Retry checks the server first and retains the same save ID.
 let retryRemote=project(),fail=true;const attempts=[];
 const retrying=new ProjectAutosave(async(sent,body)=>{attempts.push(body.save_id);if(fail)throw Error('Ngoại tuyến');return retryRemote=acknowledge(sent,body);},async()=>retryRemote,5,randomUUID);
 retrying.accept(retryRemote);retrying.setProject(p=>({...p,title:'Chưa gửi được'}));retrying.setEnabled(true);
 await sleep(20);assert.equal(attempts.length,1);assert.ok(retrying.getSnapshot().error);
 retrying.setProject(p=>({...p,title:'Tiếp tục gõ khi lỗi'}));await sleep(20);assert.equal(attempts.length,1);
 fail=false;await retrying.flush('autosave',true);
 assert.equal(attempts.length,3);assert.equal(attempts[0],attempts[1]);assert.notEqual(attempts[1],attempts[2]);
 assert.equal(retrying.getSnapshot().saved.title,'Tiếp tục gõ khi lỗi');retrying.setEnabled(false);

 // Another tab's changes cannot be rebased by silently increasing the revision.
 let conflictRemote=project(),conflictCalls=0;
 const conflict=new ProjectAutosave(async()=>{conflictCalls++;conflictRemote={...conflictRemote,revision:10,title:'Cửa sổ khác'};throw Error('409');},async()=>conflictRemote,5,randomUUID);
 conflict.accept(conflictRemote);conflict.setProject(p=>({...p,title:'Buffer của tôi'}));await assert.rejects(conflict.flush(),/409/);
 await assert.rejects(conflict.flush('autosave',true),/cửa sổ khác/);assert.equal(conflictCalls,1);assert.equal(conflict.getSnapshot().project.title,'Buffer của tôi');

 // A later server mutation after our save is not a safe lost-response recovery.
 let laterRemote=project();const later=new ProjectAutosave(async(sent,body)=>{
   laterRemote={...acknowledge(sent,body),revision:sent.revision+2,title:'Nguồn đã thay'};throw Error('Mất phản hồi');
 },async()=>laterRemote,5,randomUUID);
 later.accept(laterRemote);later.setProject(p=>({...p,title:'Chữ mới'}));await assert.rejects(later.flush());
 assert.equal(later.getSnapshot().project.title,'Chữ mới');await assert.rejects(later.flush('autosave',true),/cửa sổ khác/);

 // A rejected validation request is not replayed after the user fixes the input.
 let validRemote=project();const valid=new ProjectAutosave(async(sent,body)=>{
   if(!sent.title)throw Object.assign(Error('Tên trống'),{status:422});return validRemote=acknowledge(sent,body);
 },async()=>validRemote,5,randomUUID);
 valid.accept(validRemote);valid.setProject(p=>({...p,title:''}));await assert.rejects(valid.flush(),/Tên trống/);
 valid.setProject(p=>({...p,title:'Tên đã sửa'}));await valid.flush('autosave',true);assert.equal(valid.getSnapshot().saved.title,'Tên đã sửa');

 // An offline invalid request can be rejected on retry; then save the corrected current input.
 let invalidRemote=project(),offline=true;const retryValidationCalls=[];
 const retryValidation=new ProjectAutosave(async(sent,body)=>{
   retryValidationCalls.push(sent.title);if(offline)throw Error('Ngoại tuyến');
   if(!sent.title)throw Object.assign(Error('Tên trống'),{status:422});
   return invalidRemote=acknowledge(sent,body);
 },async()=>invalidRemote,5,randomUUID);
 retryValidation.accept(invalidRemote);retryValidation.setProject(p=>({...p,title:''}));await assert.rejects(retryValidation.flush());
 retryValidation.setProject(p=>({...p,title:'Đã sửa khi ngoại tuyến'}));offline=false;
 await retryValidation.flush('autosave',true);
 assert.equal(retryValidation.getSnapshot().saved.title,'Đã sửa khi ngoại tuyến');
 assert.equal(retryValidation.dirty,false);assert.deepEqual(retryValidationCalls,['','','Đã sửa khi ngoại tuyến']);

 // An idempotent replay may return a later server state; never adopt those foreign edits.
 let replayRemote=project(),replayCalls=0;
 const replay=new ProjectAutosave(async(sent,body)=>{
   if(++replayCalls===1)throw Error('Mất kết nối');
   return {...acknowledge(sent,body),revision:sent.revision+2,title:'Thay đổi từ cửa sổ khác'};
 },async()=>replayRemote,5,randomUUID);
 replay.accept(replayRemote);replay.setProject(p=>({...p,title:'Buffer của tôi'}));await assert.rejects(replay.flush());
 await assert.rejects(replay.flush('autosave',true));
 assert.equal(replay.getSnapshot().project.title,'Buffer của tôi');assert.equal(replay.dirty,true);

 // Inspecting while a save is finishing uses its acknowledged baseline, not the old render.
 const inspectGate=deferred();let inspectRemote=project();
 const inspecting=new ProjectAutosave(async(sent,body)=>{await inspectGate.promise;return inspectRemote=acknowledge(sent,body);},async()=>({...inspectRemote,revision:inspectRemote.revision+1}),5,randomUUID);
 inspecting.accept(inspectRemote);inspecting.setProject(p=>({...p,title:'Đang tự lưu'}));
 const inspectSave=inspecting.flush(),inspection=inspecting.inspect();inspectGate.resolve();await Promise.all([inspectSave,inspection]);
 assert.equal(inspecting.getSnapshot().project.title,'Đang tự lưu');assert.equal(inspecting.dirty,false);

 // Equal answer strings are not interchangeable when their questions changed remotely.
 let questionRemote={...project(),analysis:{artifact_id:'old',missing_information:['Kết thúc ở đâu?']},answers:['']};
 const questionSaver=new ProjectAutosave(async(sent,body)=>acknowledge(sent,body),async()=>questionRemote,5,randomUUID);
 questionSaver.accept(questionRemote);questionSaver.setProject(p=>({...p,answers:['Dừng khi khâu xong.']}));
 questionRemote={...questionRemote,revision:2,analysis:{artifact_id:'new',missing_information:['Ai xuất hiện?']}};
 await assert.rejects(questionSaver.inspect(),/cửa sổ khác/);
 assert.equal(questionSaver.getSnapshot().project.analysis.missing_information[0],'Kết thúc ở đâu?');
 assert.equal(questionSaver.getSnapshot().project.answers[0],'Dừng khi khâu xong.');

 // Vietnamese IME composition delays autosave, then resumes after compositionend.
 let imeCalls=0,imeRemote=project();const ime=new ProjectAutosave(async(sent,body)=>{imeCalls++;return imeRemote=acknowledge(sent,body);},async()=>imeRemote,5,randomUUID);
 ime.accept(imeRemote);ime.setEnabled(true);ime.setComposing(true);ime.setProject(p=>({...p,idea:'Con ga\u0301i'}));
 await sleep(20);assert.equal(imeCalls,0);await assert.rejects(ime.flush(),/ký tự/);
 ime.setComposing(false);await sleep(20);assert.equal(imeCalls,1);assert.equal(ime.getSnapshot().saved.idea,'Con ga\u0301i');ime.setEnabled(false);

 // Scene acknowledgements refresh server versions without resetting newer local fields.
 const sent={...project(),screenplay:{id:'script',version:1,scenes:[{id:'s',blocks:[{id:'b',text:'Cũ'}]}]}};
 const current=structuredClone(sent);current.screenplay.scenes[0].blocks[0].text='Mới';
 const next=structuredClone(sent);next.revision=2;next.screenplay.version=2;next.screenplay.provenance={'block:b:text':{origin:'author_input',author_confirmed:false}};
 const merged=acknowledgeSave(current,sent,next);assert.equal(merged.screenplay.version,2);assert.equal(merged.screenplay.scenes[0].blocks[0].text,'Mới');assert.deepEqual(merged.screenplay.provenance,next.screenplay.provenance);
 // Accepting a proposal starts its own write before later typing; it is not applied twice.
 const acceptGate=deferred(),proposalBase=project(),proposalWrites=[];let proposalRemote=proposalBase;
 const adopting=new ProjectAutosave(async(sent,body)=>{
   proposalWrites.push(body);if(proposalWrites.length===1)await acceptGate.promise;
   proposalRemote=acknowledge(sent,body);delete proposalRemote.pending_screenplay_proposal_id;return proposalRemote;
 },async()=>proposalRemote,5,randomUUID);
 adopting.accept(proposalBase);adopting.setEnabled(true);
 adopting.setProject(p=>({...p,pending_screenplay_proposal_id:'proposal'}));
 assert.equal(proposalWrites.length,1,'explicit adoption is saved immediately');
 adopting.setProject(p=>({...p,title:'Gõ tiếp sau khi nhận'}));acceptGate.resolve();await adopting.idle();
 assert.equal(proposalWrites.length,2);assert.equal(proposalWrites[1].screenplay_proposal_id,undefined);
 assert.equal(adopting.getSnapshot().saved.title,'Gõ tiếp sau khi nhận');adopting.setEnabled(false);
 // A response for an old project must never replace the newly opened project.
 const gate=deferred(),old=project(),other=project();const switched=new ProjectAutosave(async(sent,body)=>{await gate.promise;return acknowledge(sent,body);},async()=>old,5,randomUUID);
 switched.accept(old);switched.setProject(p=>({...p,title:'Đang lưu'}));const pending=switched.flush();switched.accept(other);gate.resolve();await assert.rejects(pending,/không khớp/);assert.equal(switched.getSnapshot().project.id,other.id);
 console.log('PASS autosave: serialization, newer input, exact acknowledgement recovery, explicit retry, conflict, IME, server versions and project isolation');
})().catch(error=>{console.error(error);process.exit(1);});
