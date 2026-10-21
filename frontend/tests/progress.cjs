// Run against TypeScript compiled to a temporary CommonJS directory.
const assert = require('node:assert/strict');
const { applyProgress, progressLanguage, progressCopy } = require(process.argv[2] + '/progressState.js');
const { streamProjectOperation } = require(process.argv[2] + '/projectsApi.js');
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
 console.log('Progress state, repeated/skipped stages, locale, UTF-8 stream, disconnect, conflict and immutable input checks passed');
})().catch(error=>{console.error(error);process.exitCode=1});
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { OperationProgress } = require(process.argv[2] + '/OperationProgress.js');
const timing = {kind:'review',startedAt:0,finishedAt:2000};
const render = (language, steps, failed) => renderToStaticMarkup(React.createElement(OperationProgress,{language,steps,failed,timing}));
const unsaved = render('en',[{stage:'prepare',occurrence:1,status:'failed'}],true);
assert.match(unsaved,/Changes could not be saved/);
assert.doesNotMatch(unsaved,/reopen the project before retrying/);
const saved = render('vi',[{stage:'prepare',occurrence:1,status:'completed'},{stage:'fidelity',occurrence:1,status:'failed'}],true);
assert.match(saved,/Nội dung đã lưu trước khi gọi AI/);
assert.doesNotMatch(saved,/Đã hoàn tất và lưu/);
assert.match(render('en',steps,false),/Completed and saved/);
assert.match(render('en',steps,false),/Check the evidence and proposed revision.*\(2\)/);
console.log('Rendered progress: unsaved/saved failures, success, repeated audit and bilingual labels passed');
