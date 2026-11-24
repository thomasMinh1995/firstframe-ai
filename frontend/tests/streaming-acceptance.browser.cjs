// SI-03 focused matrix. Only backend/tests/streaming_acceptance_fixture.py is allowed.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const api='http://127.0.0.1:8055',url='http://127.0.0.1:3055';
const output=process.env.SI_SCREENSHOTS||'/private/tmp/si03-browser';
const rows=[];let browser;
const selection=process.env.SI_CASES?.split(',');
const selected=name=>!selection||selection.includes(name);
async function json(path,body){const r=await fetch(api+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.equal(r.ok,true,await r.clone().text());return r.json();}
async function state(id){const s=await json('/_fixture/'+id);assert.equal(s.fixture,true);return s;}
async function until(read,accept){const end=Date.now()+20000;while(Date.now()<end){const s=await read();if(accept(s))return s;await new Promise(r=>setTimeout(r,80));}throw Error('fixture state deadline');}
const release=(id,gate)=>json('/_fixture/'+id+'/release',gate?{gate}:{all:true});
async function fresh(options){const c=await json('/_fixture/new',options);assert.equal(c.fixture,true);return c.project;}
async function open(project,width=1280,heartbeat=false){
 const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
 context.setDefaultTimeout(15000);
 await context.route('**/*',route=>{const u=new URL(route.request().url());return ['127.0.0.1','localhost'].includes(u.hostname)&&['3055','8055'].includes(u.port)?route.continue():route.abort();});
 await context.addInitScript(({heartbeat})=>{
  localStorage.setItem('firstframe:onboarding:v2',JSON.stringify({version:3,status:'dismissed',stepId:'new-project',projectId:null}));
  if(heartbeat){const timer=window.setTimeout;window.setTimeout=(fn,ms,...args)=>timer(fn,ms===45000?600:ms,...args);}
  const t=window.__si03={events:[]};const mark=(kind)=>t.events.push({kind,ms:performance.now()});
  const native=window.fetch.bind(window);
  window.fetch=async(...args)=>{
   if(!String(args[0]).includes('/plan/stream'))return native(...args);
   mark('request');const response=await native(...args);if(!response.body)return response;
   const reader=response.body.getReader(),decoder=new TextDecoder();let pending='';
   return new Response(new ReadableStream({async pull(controller){try{
    const {value,done}=await reader.read();if(done){mark('eof');controller.close();return;}
    pending+=decoder.decode(value,{stream:true});const lines=pending.split('\n');pending=lines.pop();
    for(const line of lines){if(!line.trim()){mark('heartbeat');continue;}try{const e=JSON.parse(line);mark('event:'+e.type);}catch{mark('invalid-json');}}
    controller.enqueue(value);
   }catch(error){controller.error(error);}},cancel(reason){return reader.cancel(reason);}}),{status:response.status,headers:response.headers});
  };
  let painted=false;
  new MutationObserver(()=>{
   const reader=document.querySelector('.plan-checkpoint-reader');
   if(reader&&!painted){painted=true;requestAnimationFrame(()=>mark('readable-frame'));}
  }).observe(document,{childList:true,subtree:true});
 },{heartbeat});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url+'/?project='+project.id);
 await page.locator('.workspace-tools-at-hand select').waitFor();
 return {page,context,errors};
}
async function startPlan(page){await page.locator('.workspace-tools-at-hand select').selectOption('clarify');await page.getByRole('button',{name:'Mở Làm rõ',exact:true}).click();await page.locator('[data-tour-action="plan"]').click();}
async function plan(name,options){
 const p=await fresh(options),{page,context,errors}=await open(p,options.width,options.transport==='heartbeat');
 const row={name,project_id:p.id,width:options.width,options};rows.push(row);
 try{
  if(options.transport==='legacy')await page.route('**/plan/stream?checkpoints=true',route=>route.continue({url:route.request().url().split('?')[0]}));
  await startPlan(page);const reader=page.locator('.plan-checkpoint-reader');
  if(options.fault?.startsWith('planner_')){
   await page.locator('.error').first().waitFor();assert.equal(await reader.count(),0);
   const s=await state(p.id);assert.equal(s.project.plan_generations.length,p.plan_generations.length);assert.deepEqual(s.project.draft,p.draft);
   row.trace=await page.evaluate(()=>window.__si03);row.calls=s.calls;row.result='passed';return;
  }
  if(options.transport==='legacy'){
   await until(()=>state(p.id),s=>s.waiting==='critic');assert.equal(await reader.count(),0);
   await release(p.id,'critic');await page.locator('.working-draft').waitFor();
   const s=await state(p.id);assert.deepEqual(s.calls.map(c=>c.stage),['planning','evaluation']);
   row.calls=s.calls;row.trace=await page.evaluate(()=>window.__si03);row.result='passed';return;
  }
  await reader.waitFor();await reader.getByRole('heading',{name:'Story plan SI-03',exact:true}).waitFor();
  assert.equal((await state(p.id)).waiting,'critic');
  assert.equal(await reader.evaluate(el=>!!el.closest('[inert]')),false);
  if(options.transport==='heartbeat'){
   await until(()=>page.evaluate(()=>window.__si03.events.filter(e=>e.kind==='heartbeat').length),n=>n>=8);
   assert.match(await reader.getByRole('status').innerText(),/Đang góp ý/);
  }
  const handle=await reader.elementHandle(),close=reader.getByRole('button');await close.focus();
  if(name==='initial-success'){
   const before=await page.evaluate(()=>scrollY);await page.keyboard.press('PageDown');
   await until(()=>page.evaluate(()=>scrollY),y=>y>before);
   await page.evaluate(()=>new Promise(resolve=>{let last=scrollY,stable=0;function frame(){stable=scrollY===last?stable+1:0;last=scrollY;if(stable>=5)resolve();else requestAnimationFrame(frame);}requestAnimationFrame(frame);}));
   await close.focus();row.keyboard_scroll_when_busy=true;
  }
  const anchor=reader.locator('p.preserve-lines').first(),top=await anchor.evaluate(el=>el.getBoundingClientRect().top);
  await page.screenshot({path:`${output}/${name}-before.png`});
  if(options.transport==='truncate'){
   await reader.getByRole('status').filter({hasText:'Chưa rõ kết quả góp ý'}).waitFor();
   row.trace_before_recovery=await page.evaluate(()=>window.__si03);
   assert.equal(await handle.evaluate(el=>el.isConnected),true);await release(p.id);
   await until(()=>state(p.id),s=>s.project.plan_generations.at(-1).critic_status==='reviewed');
   await page.reload();await page.locator('.workspace-tools-at-hand select').waitFor();
  }else{
   await release(p.id,'critic');
   await reader.getByRole('status').filter({hasText:options.fault?'Chưa có góp ý hợp lệ':'Góp ý đã lưu'}).waitFor();
   assert.equal(await handle.evaluate(el=>el.isConnected),true);
   assert.equal(await close.evaluate(el=>el===document.activeElement),true);
   const finalTop=await anchor.evaluate(el=>el.getBoundingClientRect().top);
   assert.ok(Math.abs(finalTop-top)<3,`preserve visible reading position (${top} -> ${finalTop})`);
  }
  const s=await state(p.id);assert.deepEqual(s.calls.map(c=>c.stage),['planning','evaluation']);
  assert.deepEqual(s.project.screenplay_selections,p.screenplay_selections,'preview never selects an export');
  if(options.existing!==false){assert.deepEqual(s.project.draft,p.draft);assert.deepEqual(s.project.feedback_source,p.feedback_source);}
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual(errors,[]);
  row.trace=row.trace_before_recovery??await page.evaluate(()=>window.__si03);row.server=s.events;row.calls=s.calls;row.result='passed';
  const events=row.trace.events,at=kind=>events.find(e=>e.kind===kind)?.ms;
  row.timing={time_to_readable_ms:at('readable-frame')-at('request'),checkpoint_arrival_to_frame_ms:at('readable-frame')-at('event:checkpoint'),terminal_received_ms:at('event:result')-at('request')};
  await page.screenshot({path:`${output}/${name}-after.png`});
 }catch(e){row.result='failed';row.error=String(e);await page.screenshot({path:`${output}/${name}-failure.png`});throw e;}
 finally{await release(p.id);await context.close();}
}
async function concurrent(late=false){
 const p=await fresh({existing:true}),a=await open(p),row={name:late?'late-unmounted':'two-tabs'};rows.push(row);
 try{
  await startPlan(a.page);await a.page.locator('.plan-checkpoint-reader').waitFor();
  if(late){
   const q=await fresh({existing:false});await a.page.goto(url+'/?project='+q.id);await a.page.locator('.workspace-tools-at-hand select').waitFor();
   await release(p.id);await until(()=>state(p.id),s=>s.project.plan_generations.at(-1).critic_status==='reviewed');
   assert.equal(await a.page.locator('#project-picker').inputValue(),q.id);assert.equal(await a.page.locator('.plan-checkpoint-reader').count(),0);
   assert.equal((await state(q.id)).calls.length,0);
  }else{
   const b=await open(p);
   try{
    await b.page.locator('#idea').fill(p.idea+' Chất liệu mới của tác giả ở tab B.');
    await until(()=>state(p.id),s=>s.project.idea!==p.idea);
    await release(p.id);await a.page.locator('.plan-checkpoint-reader [role="status"]').filter({hasText:'Chưa rõ kết quả góp ý'}).waitFor();
    assert.match((await state(p.id)).project.idea,/Chất liệu mới/);assert.match(await b.page.locator('#idea').inputValue(),/Chất liệu mới/);
    assert.equal((await state(p.id)).project.plan_generations.at(-1).critic_status,'pending');
   }finally{await b.context.close();}
  }
  row.calls=(await state(p.id)).calls;assert.deepEqual(row.calls.map(c=>c.stage),['planning','evaluation']);row.result='passed';
 }catch(e){row.result='failed';row.error=String(e);throw e;}finally{await release(p.id);await a.context.close();}
}
async function draft(count,fault=''){
 const p=await fresh({mode:'draft',scenes:count,fault}),{page,context,errors}=await open(p);
 const row={name:`draft-${count}${fault?'-'+fault:''}`,project_id:p.id,timings:[]};rows.push(row);
 try{
  await page.locator('[data-workspace-stage="workspace-idea"]').getByRole('button',{name:'Tạo bản nháp',exact:true}).click();
  await until(()=>state(p.id),s=>s.waiting==='critic');
  await page.locator('.draft-workflow-toggle input').check();
  await page.locator('[data-read-target="plan"]').click();
  const picker=page.locator('.draft-reader-picker select');assert.equal(await picker.inputValue(),'plan');
  await release(p.id,'critic');await until(()=>state(p.id),s=>s.waiting==='outline');
  assert.equal(await picker.inputValue(),'plan');
  await release(p.id,'outline');let s=await until(()=>state(p.id),s=>s.waiting==='scene:0');
  await until(()=>picker.locator('option[value="outline"]').count(),n=>n===1);await picker.selectOption('outline');
  await page.getByText(`Dàn cảnh · ${count} cảnh`,{exact:true}).waitFor();
  for(let i=0;i<count;i++){
   const before=await page.evaluate(()=>performance.now());await release(p.id,`scene:${i}`);
   s=await until(()=>state(p.id),s=>fault&&i===1?s.run.status==='interrupted':s.run.completed_scenes>=i+1);
   const confirmed=await page.evaluate(()=>performance.now());
   if(fault&&i===1)break;
   const first=s.candidate.project.screenplay.scenes[0];
   if(i===0){await until(()=>picker.locator(`option[value="scene:${first.id}"]`).count(),n=>n===1);await picker.selectOption('scene:'+first.id);}
   await page.locator(`[data-candidate-scene="${first.id}"]`).getByText('Cha đặt phong thư kín lên bàn rồi lùi lại.',{exact:true}).waitFor();
   const completedScene=s.candidate.project.screenplay.scenes[i];
   await page.locator(`[data-workflow-id="write:${completedScene.id}"] [data-read-target="scene:${completedScene.id}"]`).waitFor({state:'attached'});
   await until(()=>page.locator('#draft-run > div').innerText(),text=>text.includes(`${i+1} cảnh đã lưu`)||text.includes(`Đã viết ${i+1}/${count}`));
   const rendered=await page.evaluate(()=>performance.now());row.timings.push({scene:i+1,scene_id:completedScene.id,
    saved_result_revision:s.run.workflow_items.find(item=>item.id===`write:${completedScene.id}`)?.result?.candidate_revision,
    poll_commit_to_readable_bound_ms:[Math.max(0,rendered-confirmed),rendered-before]});
   assert.equal(await picker.inputValue(),'scene:'+first.id,'new checkpoints keep the selected scene');
   assert.equal((await page.locator('#draft-run').innerText()).includes('Toàn bộ nháp sẵn sàng'),false);
  }
  if(fault){
   await until(()=>state(p.id),s=>s.run.status==='interrupted');
   assert.equal(s.candidate.project.screenplay.scenes.filter(s=>s.blocks.length).length,1);
   assert.equal(s.calls.filter(c=>c.kind==='writer').length,2);
  }else{
   await until(()=>state(p.id),s=>s.waiting==='review');await release(p.id,'review');
   s=await until(()=>state(p.id),s=>s.run.status==='ready');
   await page.locator('#draft-run > div > p[role="status"]').filter({hasText:'Toàn bộ nháp sẵn sàng'}).waitFor();
   const selected=s.candidate.project.screenplay.scenes[1].id;await picker.selectOption('scene:'+selected);
   await page.locator('.draft-candidate-reader').getByRole('button',{name:`Nhận toàn bộ nháp (${count} cảnh)`,exact:true}).click();
   await page.locator(`[data-script-scene="${selected}"][aria-pressed="true"]`).waitFor();
   assert.equal((await state(p.id)).project.screenplay.scenes.length,count);
  }
  const final=await state(p.id);row.calls=final.calls;row.review_error=final.run.review_error;row.saved_reviews=final.candidate.project.screenplay_reviews.length;
  if(!fault){assert.equal(row.review_error,null);assert.equal(row.saved_reviews,count);}
  assert.equal(new Set(row.calls.map(c=>c.key)).size,row.calls.length,'no duplicate fake provider request');
  assert.deepEqual(errors,[]);row.result='passed';await page.screenshot({path:`${output}/${row.name}.png`});
 }catch(e){row.result='failed';row.error=String(e);await page.screenshot({path:`${output}/${row.name}-failure.png`});throw e;}finally{await release(p.id);await context.close();}
}
(async()=>{
 await fs.mkdir(output,{recursive:true});browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  for(const [name,options] of [
   ['initial-success',{existing:false,width:1280}],['regeneration-heartbeat',{existing:true,width:390,transport:'heartbeat'}],
   ['critic-timeout',{existing:true,width:1280,fault:'critic_timeout'}],['critic-json',{existing:true,width:390,fault:'critic_json'}],
   ['planner-timeout',{existing:false,width:1280,fault:'planner_timeout'}],['planner-json',{existing:false,width:390,fault:'planner_json'}],
   ['truncated-stream',{existing:true,width:1280,transport:'truncate'}],
   ['legacy-stream',{existing:false,width:1280,transport:'legacy'}],
  ]){if(selected(name)){await plan(name,options);console.log('PASS '+name);}}
  if(selected('two-tabs')){await concurrent();console.log('PASS two tabs preserve newer source');}
  if(selected('late-unmounted')){await concurrent(true);console.log('PASS late unmounted response');}
  if(selected('draft-2')){await draft(2);console.log('PASS draft 2');}
  if(selected('draft-6')){await draft(6);console.log('PASS draft 6');}
  if(selected('draft-2-scene_unknown')){await draft(2,'scene_unknown');console.log('PASS saved first scene after unknown outcome');}
 }finally{
  await fs.writeFile(`${output}/results-${Date.now()}.json`,JSON.stringify({base:process.env.SI_BASE_HEAD,selection,rows},null,2));await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
