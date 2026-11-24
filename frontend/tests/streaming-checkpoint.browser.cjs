// Focused HTTP/browser check. Start backend/tests/streaming_checkpoint_fixture.py
// and a frontend built with NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8055 on port 3055.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const api='http://127.0.0.1:8055',url='http://127.0.0.1:3055';
async function state(){const s=await(await fetch(api+'/_fixture/state')).json();assert.equal(s.fixture,true,'only the isolated fake-provider fixture is allowed');return s;}
(async()=>{
 const initial=await state();const browser=await chromium.launch({channel:'chrome',headless:true});
 const output=process.env.SI_SCREENSHOTS||'/private/tmp/si91-browser';await fs.mkdir(output,{recursive:true});
 try{
  for(const [width,failed] of [[1280,false],[390,true]]){
   await fetch(api+'/_fixture/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({failed})});
   const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
   context.setDefaultTimeout(10000);
   await context.addInitScript(()=>localStorage.setItem('firstframe:onboarding:v2',JSON.stringify({version:3,status:'dismissed',stepId:'new-project',projectId:null})));
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto(url+'/?project='+initial.project.id);
   await page.locator('.workspace-tools-at-hand select').selectOption('clarify');
   await page.getByRole('button',{name:'Mở Làm rõ',exact:true}).click();
   await page.locator('[data-tour-action="plan"]').click();
   const reader=page.locator('.plan-checkpoint-reader');await reader.waitFor();
   await reader.getByRole('heading',{name:'Story plan đọc sớm',exact:true}).waitFor();
   const waiting=await state();assert.equal(waiting.critic_waiting,true);assert.deepEqual(waiting.calls,['planning','evaluation']);
   assert.equal(await reader.evaluate(el=>!!el.closest('[inert]')),false);
   assert.equal(await page.locator('.project-fields').evaluate(el=>el.inert),true);
   const node=await reader.elementHandle();const close=reader.getByRole('button');await close.focus();
   await page.evaluate(()=>window.scrollBy(0,80));const scroll=await page.evaluate(()=>window.scrollY);
   const anchor=reader.locator('p.preserve-lines').first();const beforeTop=await anchor.evaluate(el=>el.getBoundingClientRect().top);
   await page.screenshot({path:`${output}/${width}-before-terminal.png`});
   await fetch(api+'/_fixture/release',{method:'POST'});
   await reader.getByRole('status').filter({hasText:failed?'Chưa có góp ý hợp lệ':'Góp ý đã lưu'}).waitFor();
   assert.equal(await node.evaluate(el=>el.isConnected),true,'terminal preserves the reader DOM node');
   assert.equal(await close.evaluate(el=>el===document.activeElement),true,'terminal preserves keyboard focus');
   const afterScroll=await page.evaluate(()=>window.scrollY);
   const afterTop=await anchor.evaluate(el=>el.getBoundingClientRect().top);
   // Scroll anchoring can adjust scrollY when progress above the reader changes height.
   assert.ok(Math.abs(afterTop-beforeTop)<=2,`terminal preserves the visible text position (${beforeTop} -> ${afterTop}; scroll ${scroll} -> ${afterScroll})`);
   const final=await state();assert.deepEqual(final.calls,['planning','evaluation']);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.deepEqual(errors,[]);await page.screenshot({path:`${output}/${width}-after-terminal.png`});
   await close.click();await reader.waitFor({state:'detached'});
   await context.close();console.log(`PASS ${width}px: checkpoint before critic release, stable reader/focus/scroll, ${failed?'failure':'success'}, one planning and one evaluation request on fake provider`);
  }
 }finally{await fetch(api+'/_fixture/release',{method:'POST'});await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
