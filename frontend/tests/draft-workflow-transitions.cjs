const assert=require('node:assert/strict');
const {WorkflowReveals}=require(process.argv[2]+'/draftWorkflowReveal.js');
const {DraftRunPoller}=require(process.argv[2]+'/draftRunPolling.js');
const {newerRun}=require(process.argv[2]+'/draftWorkflowState.js');
const item=(id,status='pending',revision=null)=>({id,kind:'analysis',status,result:revision===null?null:{candidate_revision:revision},children:[]});
const run=(items,revision=0,status='running')=>({id:'r',status,candidate_revision:revision,progress_revision:revision,workflow_items:items});
const candidate=revision=>({revision,project:{analysis:{summary:'Đã lưu'},screenplay_reviews:[]}});
const tracker=new WorkflowReveals();
const first=run([item('a','completed',1),item('b')],1);
assert.deepEqual(tracker.update(first,null),[],'opening saved history is not a new generation');
assert.deepEqual(tracker.update(first,candidate(1)),[],'hydrating initial candidate does not replay history');
const next=run([item('a','completed',1),item('b','completed',2),item('c','completed',2)],2);
assert.deepEqual(tracker.update(next,candidate(1)),[],'wait for the saved candidate checkpoint');
assert.deepEqual(tracker.update(next,candidate(2)),['b','c'],'a skipped poll reveals only actual new results together');
assert.deepEqual(tracker.update(next,candidate(2)),[],'poll and card remount do not replay a result');
assert.deepEqual(tracker.update(run([item('a','completed',3),...next.workflow_items.slice(1)],3),candidate(3)),['a'],'confirmed content revision can reveal again');
assert.deepEqual(new WorkflowReveals().update(next,candidate(2)),[],'reload treats existing results as history');
const legacy=new WorkflowReveals(),partial=run([{...item('review','unknown'),kind:'review'}]);
assert.deepEqual(legacy.update(partial,null),[]);
assert.deepEqual(legacy.update(partial,{revision:1,project:{screenplay_reviews:[{id:'old'}]}}),[],'legacy partial reviews do not replay after hydration');
assert.deepEqual(legacy.update(partial,{revision:2,project:{screenplay_reviews:[{id:'old'},{id:'new'}]}}),['review']);

(async()=>{
 let current=null,saved=null,error=null,reads=0,candidateReads=0,failRun=true,failCandidate=false,task,delay;
 let remote=run([item('a','running')]);
 const poller=new DraftRunPoller({
  readRun:async()=>{reads++;if(failRun)throw Error('offline');return remote},
  readCandidate:async()=>{candidateReads++;if(failCandidate)throw Error('candidate offline');return candidate(remote.candidate_revision)},
  current:()=>current,receive:r=>{current=newerRun(current,r)},candidateRevision:()=>saved?.revision??-1,
  accept:c=>{saved=c},onError:e=>{error=e}
 },(fn,ms)=>{task=fn;delay=ms;return()=>{task=null}});
 await poller.start();assert.equal(error,'offline');assert.ok(task);assert.ok(delay<=8000);
 failRun=false;await poller.start();assert.equal(error,null);assert.equal(saved.revision,0);
 remote=run([item('a','completed',1)],1,'ready');failCandidate=true;
 await poller.start();assert.equal(saved.revision,0,'retain loaded content when candidate GET fails');assert.equal(current.status,'ready');assert.equal(error,'candidate offline');assert.ok(task,'terminal progress retries its missing candidate');
 failCandidate=false;task=null;await poller.start();assert.equal(saved.revision,1);assert.equal(error,null);assert.equal(task,null,'stop after terminal run and matching candidate');
 const before=candidateReads;remote=run([item('a','running')],0);
 await poller.start();assert.equal(current.status,'ready','stale progress cannot regress terminal state');assert.equal(candidateReads,before);
 poller.stop();const calls=reads;await poller.start();assert.equal(reads,calls,'unmounted poller cannot continue reads');
 let resolve;const gate=new Promise(r=>{resolve=r});let accepted=false;
 const stopped=new DraftRunPoller({readRun:()=>gate,current:()=>null,receive:()=>{accepted=true},readCandidate:async()=>candidate(0),candidateRevision:()=>-1,accept:()=>{},onError:()=>{throw Error('late error')}},()=>()=>{});
 const pending=stopped.start();stopped.stop();resolve(remote);await pending;assert.equal(accepted,false,'late response from previous run/project is ignored');
 let resolveCandidate;const candidateGate=new Promise(r=>{resolveCandidate=r});let candidateAccepted=false;
 const lateCandidate=new DraftRunPoller({readRun:async()=>remote,current:()=>remote,receive:()=>{},readCandidate:()=>candidateGate,candidateRevision:()=>-1,accept:()=>{candidateAccepted=true},onError:()=>{}},()=>()=>{});
 const loading=lateCandidate.start();await Promise.resolve();lateCandidate.stop();resolveCandidate(candidate(0));await loading;assert.equal(candidateAccepted,false,'late candidate cannot enter another run');
 let maximumDelay=0;
 const offline=new DraftRunPoller({readRun:async()=>{throw Error('offline')},current:()=>null,receive:()=>{},readCandidate:async()=>candidate(0),candidateRevision:()=>-1,accept:()=>{},onError:()=>{}},(_,ms)=>{maximumDelay=ms;return()=>{}});
 for(let i=0;i<12;i++)await offline.start();assert.equal(maximumDelay,8000,'reconnect backoff is capped');offline.stop();
 console.log('PASS draft transitions: history, hydration, batch/revision reveal, reconnect, terminal candidate, stale and unmounted responses');
})().catch(e=>{console.error(e);process.exit(1)});
