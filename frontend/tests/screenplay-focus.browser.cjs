// Reproduce navigation focus landing between Playwright focus and text insertion.
// A fresh disposable fixture and fake providers are required; no real model calls.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path'),{randomUUID:uuid}=require('node:crypto');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'}),context=await browser.newContext({viewport:{width:1280,height:900}});
 try {
 await context.addInitScript(()=>localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'save',projectId:null})));
 const api='http://127.0.0.1:8034',url='/api/projects/'+seed.id;
 const req=async(route,method='GET',data)=>{const r=await context.request.fetch(api+route,{method,data});assert.equal(r.status(),200,await r.text());return r.json()};
 let p=await req(url+'/scene-outline','POST',{revision:seed.revision,source_version_id:'current'});
 const payload=Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(k=>[k,p[k]]));
 p=await req(url,'PUT',{...payload,scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes:[{id:uuid(),title:'Lá thư',action:'Cha đặt thư. Con gái chưa mở.'}]}});
 p=await req(url+'/screenplay','POST',{revision:p.revision,request_id:uuid()});
 const heading=p.screenplay.scenes[0].heading,source=structuredClone(p.screenplay.source_outline),page=await context.newPage(),puts=[];
 page.on('request',r=>{if(r.method()==='PUT'&&r.url()===api+url)puts.push(r.postDataJSON())});
 await page.goto('http://127.0.0.1:3034');const area=page.locator('.screenplay'),editor=area.getByLabel('Editor liền mạch',{exact:true});
 await area.locator('.screenplay-scene-list button').waitFor();
 await page.evaluate(()=>{window.qaRaf=requestAnimationFrame;window.qaCancel=cancelAnimationFrame;window.qaFrames=new Map();let id=0;
  window.requestAnimationFrame=fn=>{window.qaFrames.set(--id,fn);return id};window.cancelAnimationFrame=id=>id<0?window.qaFrames.delete(id):window.qaCancel(id)});
 await area.locator('.screenplay-scene-list button').evaluate(e=>e.click());
 // Reproduce the interval between focusing the action and the browser inserting text.
 // Drain the actual component callback here; old navigation redirects insertion to the heading.
 await page.waitForFunction(()=>[...window.qaFrames.values()].some(fn=>fn.toString().includes('screenplay-author-fields')),null,{polling:10});
 await editor.locator('textarea').focus();
 await page.evaluate(()=>{requestAnimationFrame=window.qaRaf;cancelAnimationFrame=window.qaCancel;
  const frames=[...window.qaFrames.values()];window.qaFrames.clear();window.qaTrace={callbacks:frames.map(fn=>fn.toString()),before:document.activeElement?.tagName,host:document.querySelector('.screenplay-author-fields')?.parentElement?.id};for(const fn of frames)fn(performance.now());window.qaTrace.after=document.activeElement?.tagName;});
 const text='  Cha đặt thư.\n\nCon ga\u0301i nhìn 🙂.  ';
 await page.keyboard.insertText(text);
 const ui={heading:await editor.locator('input').inputValue(),action:await editor.locator('textarea').inputValue()};
 const response=page.waitForResponse(r=>r.url()===api+url&&r.request().method()==='PUT');
 await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();assert.equal((await response).status(),200);
 p=await req(url);const state=await req('/__test/state');
 const evidence={focus:await page.evaluate(()=>window.qaTrace),expected:{heading,text},ui,putScene:puts.at(-1)?.screenplay?.scenes[0],savedScene:p.screenplay.scenes[0],sourceUnchanged:JSON.stringify(p.screenplay.source_outline)===JSON.stringify(source),requests:{writing:state.writing_requests,review:state.review_requests,image:state.image_requests}};
 await fs.writeFile(path.join(directory,'navigation-focus-trace.json'),JSON.stringify(evidence,null,2));
 assert.equal(ui.heading,heading,'navigation must not redirect insertion into heading');assert.equal(ui.action,text);
 assert.equal(p.screenplay.scenes[0].heading,heading);assert.equal(p.screenplay.scenes[0].blocks[0]?.text,text);
 assert.equal(puts.at(-1).screenplay.scenes[0].blocks[0]?.text,text);assert.deepEqual(p.screenplay.source_outline,source);
 await page.reload();await area.locator('.screenplay-scene-list button').click();assert.equal(await editor.locator('textarea').inputValue(),text);
 // An author may instead start entering an AI request before the navigation frame runs.
 await page.reload();
 await page.evaluate(()=>{window.qaRaf=requestAnimationFrame;window.qaCancel=cancelAnimationFrame;window.qaFrames=new Map();let id=0;
  window.requestAnimationFrame=fn=>{window.qaFrames.set(--id,fn);return id};window.cancelAnimationFrame=id=>id<0?window.qaFrames.delete(id):window.qaCancel(id)});
 await area.locator('.screenplay-scene-list button').evaluate(e=>e.click());
 await page.waitForFunction(()=>[...window.qaFrames.values()].some(fn=>fn.toString().includes('screenplay-author-fields')),null,{polling:10});
 await area.locator('.screenplay-writing-tools > summary').evaluate(e=>e.click());
 const instructions=area.getByLabel('Bạn muốn viết thử theo hướng nào? · tùy chọn',{exact:true});await instructions.focus();
 await page.evaluate(()=>{requestAnimationFrame=window.qaRaf;cancelAnimationFrame=window.qaCancel;const frames=[...window.qaFrames.values()];window.qaFrames.clear();for(const fn of frames)fn(performance.now())});
 await page.keyboard.insertText('Giữ khoảng lặng.');
 evidence.support={heading:await editor.locator('input').inputValue(),instructions:await instructions.inputValue()};
 await fs.writeFile(path.join(directory,'navigation-focus-trace.json'),JSON.stringify(evidence,null,2));
 assert.equal(await instructions.inputValue(),'Giữ khoảng lặng.','navigation must not steal focus from the support form either');
 assert.equal(await editor.locator('input').inputValue(),heading);assert.equal(await editor.locator('textarea').inputValue(),text);
 assert.deepEqual((await req(url)).screenplay,p.screenplay,'typing optional instructions does not save or change screenplay');
 const end=await req('/__test/state');assert.equal(end.writing_requests+end.review_requests+end.image_requests,0);assert.equal(puts.length,1,'support input never saves automatically');
 console.log('PASS navigation focus: original text stays in action at input, PUT, server and reload; heading/source and support form preserved, no model');
 } finally {await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
