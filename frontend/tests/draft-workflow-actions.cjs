const assert=require('node:assert/strict');
const {runCapabilities,continuationBody}=require(process.argv[2]+'/draftWorkflowActions.js');
const candidate={revision:3,project:{answers:['Tôi chọn.',''],draft:{title:'Saved'},screenplay:{scenes:[{blocks:[{text:'Bản đã đọc'}]}]}}};
const run={status:'needs_input',adopted_revision:null,cancel_requested:false,candidate_revision:3,can_continue:true,continue_block_message:null};
assert.equal(runCapabilities(run,candidate).canContinue,true);
assert.deepEqual(continuationBody(run,candidate),{candidate_revision:3,answers:['Tôi chọn.','']},'blank answers remain open decisions');
for(const reason of ['unknown_result','configuration_changed','candidate_edited','provider_unavailable']){
 const blocked={...run,status:'interrupted',can_continue:false,continue_block_message:reason};
 assert.equal(runCapabilities(blocked,candidate).canContinue,false);assert.throws(()=>continuationBody(blocked,candidate),new RegExp(reason));
}
assert.equal(runCapabilities({...run,can_continue:undefined},candidate).canContinue,false,'legacy data cannot invent a continuation capability');
assert.equal(runCapabilities(run,{...candidate,revision:2}).canContinue,false,'wait for candidate checkpoint');
assert.throws(()=>continuationBody(run,{...candidate,revision:4}),/đã đổi/,'newer unseen candidate requires refreshing run');
assert.equal(runCapabilities({...run,cancel_requested:true},candidate).canContinue,false);
assert.equal(runCapabilities({...run,status:'running'},candidate).canCancel,true);
assert.equal(runCapabilities({...run,status:'running',cancel_requested:true},candidate).canCancel,false);
for(const status of ['ready','partial'])assert.equal(runCapabilities({...run,status},candidate).canAdopt,true);
for(const status of ['running','needs_input','cancelled','failed','interrupted'])assert.equal(runCapabilities({...run,status},candidate).canAdopt,false);
assert.equal(runCapabilities({...run,status:'partial',cancel_requested:true},candidate).canAdopt,false);
assert.equal(runCapabilities({...run,status:'ready'},null).canAdopt,false);
assert.equal(runCapabilities({...run,status:'ready'},{...candidate,project:{...candidate.project,screenplay:{scenes:[{blocks:[]}]}}}).canAdopt,false);
assert.equal(runCapabilities({...run,status:'ready'},candidate).canEdit,true);
assert.equal(runCapabilities(run,candidate).canEdit,false);
for(const capability of ['canEdit','canAdopt','canContinue','canCancel'])assert.equal(runCapabilities({...run,status:'ready',adopted_revision:7},candidate)[capability],false,'adopted candidate stays read-only');
assert.deepEqual(continuationBody({...run,status:'partial'},candidate),{candidate_revision:3},'retry does not resubmit clarification answers');
console.log('PASS workflow actions: authoritative capabilities, open answers, unknown calls, stale revisions, cancellation, adoption and read-only adopted candidate');

(async()=>{
 const {confirmedAdoption}=require(process.argv[2]+'/draftWorkflowActions.js');
 let writes=0,reads=0,projects=0;const result={id:'p',revision:9};
 const lost=async()=>{writes++;throw Error('lost response')};
 assert.equal(await confirmedAdoption(lost,async()=>{reads++;return {...run,candidate_revision:3,adopted_revision:9}},async()=>{projects++;return result},3),result);
 assert.deepEqual([writes,reads,projects],[1,1,1],'lost adoption acknowledgement is recovered with GETs, never another POST');
 for(const checked of [{...run,adopted_revision:null},{...run,candidate_revision:4,adopted_revision:9}])await assert.rejects(confirmedAdoption(lost,async()=>checked,async()=>{throw Error('must not accept another version')},3),/lost response/);
 await assert.rejects(confirmedAdoption(lost,async()=>{throw Error('offline')},async()=>result,3),/lost response/);
 console.log('PASS adoption acknowledgement: confirmed exact revision only, no POST retry, conflicts/unknown remain errors');
})().catch(e=>{console.error(e);process.exit(1)});
