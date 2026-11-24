const assert=require('node:assert/strict');
const {workspaceGroup,workspaceJourney,workspaceNextStep,workspaceFallbackStage,workspaceToolSteps,toolOperations}=require(process.argv[2]+'/workspaceToolState.js');
const saved={idea:'Ý tưởng đã lưu',revision:13,versions:[],draft:null,screenplay:null};
const original=JSON.stringify(saved);
assert.equal(workspaceGroup('workspace-choices'),'idea');
assert.equal(workspaceGroup('workspace-history'),'draft');
assert.equal(workspaceGroup('workspace-export'),'finish');
for(const tool of ['plan','outline','write','review','history']){
  const steps=workspaceToolSteps(tool,saved,true);
  assert.equal(steps.at(-1).status,'unsaved');
  assert.equal(steps.some(s=>s.label==='Story plan'&&s.status==='available'),false);
}
const partiallyWritten={...saved,screenplay:{scenes:[{blocks:[]},{blocks:[{text:'Đã viết'}]}]}};
assert.match(workspaceToolSteps('write',partiallyWritten,false)[1].detail,/^1\/2/);
assert.deepEqual(toolOperations.review,['review','screenplay-reviews']);
assert.equal(JSON.stringify(saved),original);
console.log('workspace tools: saved evidence, unsaved edits, grouping and source preservation passed');

const journey=p=>workspaceJourney(p,false).map(s=>s.available);
assert.deepEqual(journey(null),[false,false,false,false,false,false]);
assert.deepEqual(journey(saved),[true,false,false,false,false,false]);
const clarified={...saved,analysis:{artifact_id:'a1'}};
const planned={...clarified,draft:{title:'Plan'}};
const outlined={...planned,scene_outline:{scenes:[]}};
assert.deepEqual(journey(clarified),[true,true,false,false,false,false]);
assert.deepEqual(journey(planned),[true,true,true,true,false,false]);
assert.deepEqual(journey(outlined),[true,true,true,true,true,false]);
assert.deepEqual(journey({...outlined,screenplay:{scenes:[]}}),[true,true,true,true,true,true]);
assert.equal(workspaceJourney(planned,true)[1].available,false,'changed source hides obsolete clarification');
const next=(stage,p=planned,changed=false,blocking=false)=>workspaceNextStep('workspace-'+stage,p,changed,blocking).target;
assert.equal(next('idea',saved),'analyze');
assert.equal(next('idea',clarified),'workspace-choices');
assert.equal(next('idea',planned,true),'analyze','old draft does not bypass reclarification');
assert.equal(next('idea',saved,false,true),'draft-run','open existing run, do not request another');
assert.equal(next('choices',clarified),'clarification-complete','navigation does not create a plan');
assert.equal(next('choices'),'workspace-draft');
assert.equal(next('draft'),'workspace-outline');
assert.equal(next('outline',outlined),'workspace-script');
assert.equal(next('script',outlined),'workspace-script-start','navigation focuses explicit start');
assert.equal(next('script',{...outlined,screenplay:{}}),'workspace-export');
assert.equal(next('export'),'workspace-export-choice');
assert.equal(workspaceFallbackStage('workspace-choices',true),'workspace-idea');
assert.equal(workspaceFallbackStage('workspace-choices',false),'workspace-choices');
assert.equal(JSON.stringify(saved),original);
console.log('PASS author-led journey: artifact availability, changed source, explicit AI entry, existing automatic run and navigation-only next steps');

require.extensions['.css']=()=>{};
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const {WorkspaceNavigation,WorkspaceTools}=require(process.argv[2]+'/WorkspaceTools.js');
for(const [project,briefChanged,label] of [[saved,true,'Chưa có nội dung'],[clarified,false,'Xem lại'],[clarified,true,'Nguồn đã thay đổi · cần làm rõ lại']]){
  const navigation=renderToStaticMarkup(React.createElement(WorkspaceNavigation,{project,briefChanged}));
  const button=navigation.match(/<button[^>]*aria-controls="workspace-choices"[^>]*>.*?<\/button>/)[0];
  assert.ok(button.includes(`<small>${label}</small>`),'clarification navigation distinguishes missing, existing and changed source');
  assert.equal(button.includes('disabled=""'),!project.analysis||briefChanged);
  const tools=renderToStaticMarkup(React.createElement(WorkspaceTools,{project,saved:project,dirty:briefChanged,busy:false,run:null,steps:[],timing:null,briefChanged,onAnalyze(){throw Error('Rendering must not call AI')}}));
  const option=tools.match(/<option[^>]*value="clarify"[^>]*>.*?<\/option>/)[0];
  assert.ok(option.includes(briefChanged?label:'Làm rõ</option>'),'tool picker uses the same source status');
}
