const assert=require('node:assert/strict');
const {initialTour,reduceTour:reduce,parseTour,entryStep,nextStep,previousStep,continuation,tourSteps}=require(process.argv[2]+'/onboardingState.js');
const empty={projectId:null,hasAnalysis:false,hasDraft:false,hasScreenplay:false,briefChanged:false};
const idea={...empty,projectId:'p1'},legacy={...idea,hasDraft:true},script={...legacy,hasScreenplay:true};
const record=(status,stepId='idea',version=3)=>JSON.stringify({version,status,stepId,projectId:'p1'});
const load=raw=>reduce(initialTour,{type:'load',raw});
const open=(context,step)=>{const s=reduce(load(null),{type:'open',resume:false,context});return step?reduce(s,{type:'navigate',step,context}):s};
assert.deepEqual(tourSteps,['new-project','idea','draft-run','script','export','save']);
assert.equal(load(null).offerAllowed,true);assert.equal(load(undefined).offerAllowed,false);
for(const raw of ['{','{}',record('unknown'),'null',record('paused','choices',3),record('paused','idea','3')])assert.equal(parseTour(raw),null);
for(const [old,mapped] of [['choices','draft-run'],['draft','script'],['outline','script'],['script','script'],['save','save']]){
 const r=parseTour(record('paused',old,2));assert.equal(r.stepId,mapped);assert.equal(r.version,3);
}
for(const status of ['completed','dismissed']){
 const s=load(record(status,'outline',2));assert.equal(s.record.status,status);assert.equal(s.offerAllowed,false);
 assert.equal(reduce(s,{type:'pause'}),s);
}
assert.equal(entryStep(empty),'new-project');assert.equal(entryStep(idea),'idea');assert.equal(entryStep(legacy),'draft-run');assert.equal(entryStep(script),'script');
assert.equal(continuation(load(record('paused','draft',2)),legacy),'draft-run','legacy plan cannot pretend a screenplay exists');
assert.equal(continuation(load(record('paused','outline',2)),script),'script');
assert.equal(nextStep('draft-run',idea),null);assert.equal(nextStep('draft-run',script),'script');assert.equal(nextStep('script',script),'export');assert.equal(nextStep('export',script),'save');assert.equal(previousStep('export',script),'script');
let s=reduce(open(idea,'draft-run'),{type:'practice',context:idea});
assert.equal(continuation(s,idea),null);assert.equal(continuation(s,script),'script','adopted screenplay unlocks review, no extra AI request');
s=reduce(open(empty),{type:'practice',context:empty});s=reduce(s,{type:'begin',kind:'create',context:empty});const ticket=s.request;
assert.ok(ticket);assert.equal(reduce(s,{type:'success',ticket:{...ticket,serial:ticket.serial+1},resultId:'p1'}),s);
const success=reduce(s,{type:'success',ticket,resultId:'p1'});assert.equal(continuation(success,idea),'idea');assert.equal(reduce(success,{type:'success',ticket,resultId:'p1'}),success);
assert.equal(reduce(s,{type:'failed',ticket}).record.status,'paused');
const dismissed=reduce(s,{type:'dismiss',context:empty});assert.equal(reduce(dismissed,{type:'success',ticket,resultId:'p1'}),dismissed);
assert.equal(continuation(load(record('paused','export')),{...script,projectId:'other'}),'script');
const paused=load(record('active','script'));assert.equal(paused.record.status,'paused');
assert.equal(reduce(open(script,'save'),{type:'complete',context:script}).record.status,'completed');
assert.equal(reduce(open(idea,'idea'),{type:'complete',context:idea}).record.status,'active');
assert.equal(reduce(open(script,'script'),{type:'external',raw:record('dismissed')}).record.status,'dismissed');
assert.equal(reduce(load(record('completed')),{type:'open',resume:false,context:script}).record.stepId,'new-project','replay is explicit');
console.log('PASS tour v3: six-step AI-first flow, v2 migration, skip/replay, real artifacts, request isolation and cross-tab dismissal');
