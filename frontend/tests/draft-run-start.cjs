const assert=require('node:assert/strict');
const {blockingDraftRun,draftRunActionLabel,startOrOpenDraftRun}=require(process.argv[2]+'/draftRunsApi.js');
const {ProjectRequestError}=require(process.argv[2]+'/projectsApi.js');
const run={id:'existing',project_id:'p',source_revision:1,status:'running',step:'write',sending:true,
 cancel_requested:false,candidate_revision:3,completed_scenes:1,total_scenes:3,error:null,review_error:null,adopted_revision:null};
const body={revision:1,request_id:'new'};
for(const status of ['running','needs_input','partial','failed','interrupted']){
 const existing={...run,status};
 assert.equal(blockingDraftRun([{...run,status:'ready'},existing]),existing);
 assert.ok(draftRunActionLabel(existing));
 assert.equal(blockingDraftRun([{...existing,adopted_revision:8}]),null);
}
for(const status of ['ready','cancelled'])assert.equal(blockingDraftRun([{...run,status}]),null);
assert.equal(draftRunActionLabel(null),null);
assert.equal(draftRunActionLabel(run),'Xem tiến độ');
assert.equal(draftRunActionLabel({...run,cancel_requested:true}),'Xem tiến độ dừng');
assert.equal(draftRunActionLabel({...run,status:'needs_input'}),'Tiếp tục làm rõ');

async function scenario(responses,check){
 const calls=[];const original=global.fetch;
 global.fetch=async(url,options)=>{
  calls.push({url,method:options.method,body:options.body});
  const response=responses.shift();assert.ok(response,'Unexpected extra request');
  if(response instanceof Error)throw response;
  return new Response(JSON.stringify(response.body),{status:response.status??200});
 };
 try{await check(calls);assert.equal(responses.length,0)}finally{global.fetch=original}
}
(async()=>{
 await scenario([{body:[run]}],async calls=>{
  assert.deepEqual(await startOrOpenDraftRun('p',body),run);
  assert.deepEqual(calls.map(c=>c.method),['GET'],'existing work opens without POST');
 });
 await scenario([{body:[]},{body:run}],async calls=>{
  await startOrOpenDraftRun('p',body);
  assert.deepEqual(calls.map(c=>c.method),['GET','POST']);
  assert.deepEqual(JSON.parse(calls[1].body),body,'keep the original idempotency key');
 });
 await scenario([{body:[]},{status:409,body:{detail:{code:'active_draft_run',message:'Mở lượt đã có',run}}}],async calls=>{
  assert.deepEqual(await startOrOpenDraftRun('p',body),run);
  assert.deepEqual(calls.map(c=>c.method),['GET','POST'],'409 opens the server-selected run without another POST');
 });
 await scenario([{body:[]},{status:409,body:{detail:'legacy conflict'}},{body:[run]}],async calls=>{
  assert.deepEqual(await startOrOpenDraftRun('p',body),run);
  assert.deepEqual(calls.map(c=>c.method),['GET','POST','GET']);
 });
 for(const detail of ['revision conflict',{code:'active_draft_run',run:{...run,project_id:'other'}},{code:'active_draft_run',run:{id:'invalid'}}]){
  await scenario([{body:[]},{status:409,body:{detail}},{body:[]}],async calls=>{
   await assert.rejects(startOrOpenDraftRun('p',body),e=>e instanceof ProjectRequestError&&e.status===409);
   assert.deepEqual(calls.map(c=>c.method),['GET','POST','GET'],'never open another project or retry a failed start');
  });
 }
 await scenario([{body:[]},Error('lost acknowledgement')],async calls=>{
  await assert.rejects(startOrOpenDraftRun('p',body));
  assert.deepEqual(calls.map(c=>c.method),['GET','POST'],'unknown outcomes must not be retried');
 });
 await scenario([Error('offline')],async calls=>{
  await assert.rejects(startOrOpenDraftRun('p',body));assert.equal(calls.length,1);
 });
 await scenario([{body:[{...run,project_id:'other'}]}],async calls=>{
  await assert.rejects(startOrOpenDraftRun('p',body),/Danh sách lượt tạo không hợp lệ/);
  assert.deepEqual(calls.map(c=>c.method),['GET']);
 });
 console.log('PASS draft start: state labels, preflight, structured/legacy 409, source isolation and no POST retries');
})().catch(error=>{console.error(error);process.exit(1)});
