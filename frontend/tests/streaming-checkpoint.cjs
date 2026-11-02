const assert=require('node:assert/strict');
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const {streamProjectOperation}=require(process.argv[2]+'/projectsApi.js');
const {PlanCheckpointReader}=require(process.argv[2]+'/PlanCheckpointReader.js');
const {draftRunSummary}=require(process.argv[2]+'/draftWorkflowState.js');
const context={idea:'Ý tưởng của tác giả',constraints:[],clarifications:[],pending_questions:[]};
const project={id:'p',title:'Tên dự án',updated_at:'now',revision:4,response_language:'vi',idea:context.idea,constraints:[],answers:[],analysis:null,draft:null,feedback:null,feedback_is_current:false,versions:[],clarification_history:[],author_context:context,plan_generations:[]};
const draft={title:'Cánh cửa',logline:'Linh đặt lại chiếc ghế.',sections:[{title:'Ending',purpose:'End',content:'Cửa vẫn mở.'}]};
const source={idea:project.idea,response_language:'vi',constraints:[],answers:[],questions:[],clarifications:{},draft:null};
const generation={id:'g',created_at:'now',source_revision:4,source_content:JSON.stringify(source),context,draft,critic_status:'pending',applied_revision:5,feedback:null,feedback_source:null};
const checkpoint={type:'checkpoint',stage:'plan_checkpoint',generation_id:'g',project:{...project,revision:5,draft,plan_generations:[generation]}};
const final={...checkpoint.project,revision:6,plan_generations:[{...generation,critic_status:'failed'}]};
const encode=e=>new TextEncoder().encode(JSON.stringify(e)+'\n');
const clone=x=>JSON.parse(JSON.stringify(x));
function response(events){return new Response(new ReadableStream({start(c){for(const e of events){const bytes=encode(e);for(let i=0;i<bytes.length;i+=3)c.enqueue(bytes.slice(i,i+3));}c.close();}}));}
(async()=>{
 const original=JSON.stringify(project);let body,url,calls=0,received=[],settled=false;
 global.fetch=async(u)=>{url=u;calls++;return new Response(new ReadableStream({start(c){body=c;}}));};
 const task=streamProjectOperation(project,'plan',()=>{},'vi',undefined,e=>received.push(e));
 task.then(()=>{settled=true;});
 for(let i=0;i<5;i++)await Promise.resolve();
 body.enqueue(encode(checkpoint));
 for(let i=0;i<15;i++)await Promise.resolve();
 assert.equal(received.length,1);assert.equal(settled,false,'checkpoint must arrive before terminal');
 assert.match(url,/plan\/stream\?checkpoints=true$/);
 body.enqueue(encode(checkpoint));body.enqueue(encode({type:'result',project:final}));body.close();
 assert.deepEqual(await task,final);assert.equal(received.length,1);assert.equal(calls,1);
 assert.equal(JSON.stringify(project),original,'preview never mutates input');
 for(const mutate of [e=>e.project.id='other',e=>e.generation_id='other',e=>e.project.revision=4,e=>e.project.plan_generations[0].source_revision=3,e=>e.project.plan_generations[0].critic_status='reviewed',e=>e.project.plan_generations[0].source_content='{}',e=>e.project.plan_generations[0].context.idea='AI choice',e=>e.project.draft={...draft,title:'Wrong draft'}]){
  const bad=clone(checkpoint);mutate(bad);global.fetch=async()=>response([bad]);
  await assert.rejects(()=>streamProjectOperation(project,'plan',()=>{},'en',undefined,()=>{}),/Invalid response/);
 }
 const other=clone(checkpoint);other.generation_id='g2';other.project.plan_generations[0].id='g2';
 global.fetch=async()=>response([checkpoint,other]);
 await assert.rejects(()=>streamProjectOperation(project,'plan',()=>{},'en',undefined,()=>{}),/Invalid response/);
 global.fetch=async()=>response([checkpoint,{type:'result',project:{...final,plan_generations:[]}}]);
 await assert.rejects(()=>streamProjectOperation(project,'plan',()=>{},'en',undefined,()=>{}),/Invalid response/);
 received=[];global.fetch=async()=>response([checkpoint]);
 await assert.rejects(()=>streamProjectOperation(project,'plan',()=>{},'en',undefined,e=>received.push(e)),/Connection interrupted/);
 assert.equal(received.length,1,'lost terminal preserves last checkpoint for recovery');
 global.fetch=async()=>response([{type:'result',project:final}]);
 assert.deepEqual(await streamProjectOperation(project,'plan',()=>{},'vi',undefined,()=>assert.fail('old backend sends no checkpoint')),final);
 global.fetch=async()=>response([checkpoint]);
 await assert.rejects(()=>streamProjectOperation(project,'review',()=>{},'en'),/Invalid response/);
 const feedback={artifact_id:'f',passed:null,rubric_scores:{},findings:[]};
 const reviewed={...generation,critic_status:'reviewed',feedback,feedback_source:{project_id:'p',artifact_id:'f',revision:5,content_key:'source',context,draft}};
 for(const status of ['pending','reviewed','failed','unknown']){
  const markup=renderToStaticMarkup(React.createElement(PlanCheckpointReader,{reading:{projectId:'p',generation:status==='reviewed'?reviewed:generation,status},onClose(){}}));
  assert.match(markup,/Cửa vẫn mở/);assert.match(markup,/aria-live="polite"/);assert.doesNotMatch(markup,/<fieldset|<input|<textarea|autofocus/i);
  assert.match(markup,status==='pending'?/Đang góp ý/:status==='reviewed'?/Góp ý đã lưu/:status==='failed'?/Chưa có góp ý hợp lệ/:/Chưa rõ kết quả góp ý/);
 }
 const run={status:'running',step:'plan_review',completed_scenes:0,total_scenes:3,adopted_revision:null,candidate_revision:3};
 assert.equal(draftRunSummary(run),'Story plan đã lưu · Đang góp ý');
 assert.match(draftRunSummary({...run,step:'write',completed_scenes:1}),/1 cảnh đã lưu · Đang viết cảnh 2/);
 assert.doesNotMatch(draftRunSummary({...run,status:'ready'},null),/sẵn sàng/);
 assert.match(draftRunSummary({...run,status:'ready'},{revision:3}),/Toàn bộ nháp sẵn sàng/);
 console.log('Streaming checkpoint: incremental delivery, immutable input, protocol guards, compatibility, retained preview and reader states passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
