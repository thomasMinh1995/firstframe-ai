// Run against TypeScript compiled to a temporary CommonJS directory.
const assert = require('node:assert/strict');
const { applyProgress, progressLanguage, progressCopy } = require(process.argv[2] + '/progressState.js');
const { streamProjectOperation, projectRequest, editableProject } = require(process.argv[2] + '/projectsApi.js');
const project = { id:'p1', title:'lab coach', updated_at:'now', revision:1, response_language:'en', idea:'untouched', constraints:[], answers:[], analysis:null, draft:null, feedback:null, feedback_is_current:false, versions:[], clarification_history:[] };
let steps = [];
for (const stage of ['prepare','fidelity','fidelity_audit','fidelity_audit','saving']) {
  steps = applyProgress(steps, {stage,status:'active'});
  steps = applyProgress(steps, {stage,status:'completed'});
}
assert.deepEqual(steps.map(s=>[s.stage,s.occurrence]), [['prepare',1],['fidelity',1],['fidelity_audit',1],['fidelity_audit',2],['saving',1]]);
assert.equal(steps.some(s=>s.stage==='evaluation'),false); // Skipped critic never shown as waiting/completed.
assert.equal(steps.every(s=>s.status==='completed'),true);
assert.equal(progressLanguage('en'),'en');
assert.equal(progressLanguage('auto'),'vi');
assert.notEqual(progressCopy.vi.stages.fidelity, progressCopy.en.stages.fidelity);
const snapshot = JSON.stringify(project);
function stream(text, chunkSize=7) {
 const bytes = new TextEncoder().encode(text);
 return new Response(new ReadableStream({start(controller) {
   for(let i=0;i<bytes.length;i+=chunkSize) controller.enqueue(bytes.slice(i,i+chunkSize));
   controller.close();
 }}));
}
(async()=>{
 let received=[];
 global.fetch=async()=>stream('\n'+JSON.stringify({type:'progress',stage:'fidelity',status:'active'})+'\n'+JSON.stringify({type:'result',project:{...project,title:'Tiếng Việt – lab coach'}}));
 const result=await streamProjectOperation(project,'review',e=>received.push(e),'en');
 assert.equal(result.title,'Tiếng Việt – lab coach');
 assert.equal(received[0].stage,'fidelity');
 assert.equal(JSON.stringify(project),snapshot);
 global.fetch=async()=>stream(JSON.stringify({type:'progress',stage:'fidelity',status:'completed'})+'\n');
 await assert.rejects(()=>streamProjectOperation(project,'review',()=>{},'en'),/Connection interrupted/);
 global.fetch=async()=>stream(JSON.stringify({type:'error',detail:'Revision conflict'})+'\n');
 await assert.rejects(()=>streamProjectOperation(project,'review',()=>{}),/Revision conflict/);
 global.fetch=async()=>stream(JSON.stringify({type:'result',project:{...project,id:'other'}})+'\n');
 await assert.rejects(()=>streamProjectOperation(project,'review',()=>{},'en'),/Invalid response/);
 global.fetch=async()=>{throw new Error('offline')};
 await assert.rejects(()=>streamProjectOperation(project,'review',()=>{},'en'),/Your edits are preserved/);
 assert.equal(JSON.stringify(project),snapshot);
 for (const invalid of ['null', '{bad json', '[]']) {
   global.fetch=async()=>stream(invalid+'\n');
   await assert.rejects(()=>streamProjectOperation(project,'review',()=>{},'en'),/Invalid response/);
 }
 // Deterministic timer: advance only the 45-second inactivity deadline, no real waiting.
 const realSetTimeout = global.setTimeout;
 const realClearTimeout = global.clearTimeout;
 let deadline, cleared=0, cancellations=0;
 global.setTimeout = (callback, ms) => { assert.equal(ms,45000); deadline=callback; return 1; };
 global.clearTimeout = () => { cleared++; };
 try {
   global.fetch=(_url,{signal})=>new Promise((_resolve,reject)=>{
     signal.addEventListener('abort',()=>reject(new Error('aborted')));
   });
   let run=streamProjectOperation(project,'review',()=>{},'en');
   deadline();
   await assert.rejects(()=>run,/Connection interrupted/);
   let body;
   global.fetch=async(_url,{signal})=>{
     const response=new Response(new ReadableStream({
       start(controller){body=controller;signal.addEventListener('abort',()=>{cancellations++;controller.error(new Error('aborted'));});}
     }));
     return response;
   };
   run=streamProjectOperation(project,'review',()=>{},'en');
   await Promise.resolve(); await Promise.resolve();
   const beforeHeartbeat=deadline;
   body.enqueue(new TextEncoder().encode('\n'));
   for(let i=0;i<5;i++) await Promise.resolve();
   assert.notEqual(deadline,beforeHeartbeat,'heartbeat resets inactivity deadline');
   deadline();
   await assert.rejects(()=>run,/Connection interrupted/);
   assert.equal(cancellations,1);
   assert.ok(cleared>=3);
 } finally { global.setTimeout=realSetTimeout; global.clearTimeout=realClearTimeout; }
 const contextProject = { ...project, author_context: { idea: project.idea, constraints: [],
   clarifications: [{ question: 'Saved question', answer: 'Chưa quyết định', input_index: null }], pending_questions: [] },
   feedback_source: null };
 global.fetch=async()=>Response.json(contextProject);
 assert.deepEqual(await projectRequest('/p1'), contextProject);
 assert.equal('author_context' in editableProject(contextProject), false, 'read projection is never submitted as an edit');
 assert.equal('feedback_source' in editableProject(contextProject), false, 'feedback source cannot be rebound by an edit');
 global.fetch=async()=>Response.json({ ...contextProject, author_context: { ...contextProject.author_context,
   pending_questions: [{ question: 'Cannot navigate here', input_index: -1 }] } });
 await assert.rejects(()=>projectRequest('/p1'), /Nội dung đang sửa được giữ nguyên/);
 global.fetch=async()=>Response.json({ ...contextProject, feedback_source: { artifact_id: 'missing snapshot' } });
 await assert.rejects(()=>projectRequest('/p1'), /Nội dung đang sửa được giữ nguyên/);
 const generation = { id: 'g1', created_at: 'now', source_revision: 1, source_content: 'saved source',
   context: contextProject.author_context, draft: { title: 'Recovered plan', logline: '',
     sections: [{ title: 'Ending', purpose: '', content: 'The fan stops.' }] },
   critic_status: 'failed', applied_revision: null, feedback: null, feedback_source: null };
 const recovered = { ...contextProject, plan_generations: [generation], applicable_plan_ids: ['g1'] };
 global.fetch=async()=>Response.json(recovered);
 assert.deepEqual(await projectRequest('/p1'), recovered);
 assert.equal('plan_generations' in editableProject(recovered), false);
 assert.equal('applicable_plan_ids' in editableProject(recovered), false);
 for (const patch of [{ critic_status: 'passed' }, { source_revision: -1 }, { applied_revision: -1 },
   { draft: null }, { context: null }, { feedback: { passed: true } }]) {
   global.fetch=async()=>Response.json({ ...recovered, plan_generations: [{ ...generation, ...patch }] });
   await assert.rejects(()=>projectRequest('/p1'), /Nội dung đang sửa được giữ nguyên/);
 }
 assert.equal(generation.critic_status, 'failed', 'validation never changes recovery data');
 const originalTimeout=AbortSignal.timeout;
 const saveController=new AbortController();
 AbortSignal.timeout=(ms)=>{assert.equal(ms,45000);return saveController.signal;};
 try {
   global.fetch=(_url,{signal})=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted'))));
   const save=projectRequest('/p1','PUT',project);
   saveController.abort();
   await assert.rejects(()=>save,/Bản đang sửa vẫn được giữ/);
   assert.equal(JSON.stringify(project),snapshot);
 } finally { AbortSignal.timeout=originalTimeout; }
 console.log('Progress state, repeated/skipped stages, locale, UTF-8 stream, disconnect, conflict and immutable input checks passed');
})().catch(error=>{console.error(error);process.exitCode=1});
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { OperationProgress } = require(process.argv[2] + '/OperationProgress.js');
const timing = {kind:'review',startedAt:0,finishedAt:2000};
const render = (language, steps, failed, dirty = false) => renderToStaticMarkup(React.createElement(OperationProgress,{language,steps,failed,timing,dirty}));
const unsaved = render('en',[{stage:'prepare',occurrence:1,status:'failed'}],true);
assert.match(unsaved,/Changes could not be saved/);
assert.doesNotMatch(unsaved,/reopen the project before retrying/);
const saved = render('vi',[{stage:'prepare',occurrence:1,status:'completed'},{stage:'fidelity',occurrence:1,status:'failed'}],true);
assert.match(saved,/Nội dung đã lưu trước khi gọi AI/);
assert.doesNotMatch(saved,/Đã hoàn tất và lưu/);
assert.match(render('en',steps,false),/Completed and saved/);
assert.match(render('en',steps,false),/Check the evidence and proposed revision.*\(2\)/);
console.log('Rendered progress: unsaved/saved failures, success, repeated audit and bilingual labels passed');

const dirtyFailure = render('en',[{stage:'prepare',occurrence:1,status:'completed'}],true,true);
assert.match(dirtyFailure,/You have unsaved edits/);
assert.match(dirtyFailure,/Save or download a JSON backup before reloading/);
assert.doesNotMatch(dirtyFailure,/Content saved before the AI request/);
assert.match(render('vi',steps,false,true),/Các thay đổi mới trên màn hình chưa được lưu/);
