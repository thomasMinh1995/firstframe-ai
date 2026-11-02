const assert=require('node:assert/strict');
const {workspaceGroup,workspaceToolSteps,toolOperations}=require(process.argv[2]+'/workspaceToolState.js');
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
