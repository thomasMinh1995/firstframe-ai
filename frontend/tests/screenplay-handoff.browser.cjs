// Complete M3 UI regression on a disposable backend, synthetic material and fake providers.
const {chromium,firefox,webkit}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path'),{randomUUID:uuid}=require('node:crypto');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const engine=process.env.FIRSTFRAME_QA_BROWSER||'chrome';assert.ok(['chrome','firefox','webkit'].includes(engine));
 const type={chrome:chromium,firefox,webkit}[engine];
 const browser=await type.launch({headless:true,...(engine==='chrome'?{channel:'chrome'}:{}),...(process.env.FIRSTFRAME_QA_EXECUTABLE?{executablePath:process.env.FIRSTFRAME_QA_EXECUTABLE}:{})});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 try {
 const tour={version:1,status:'completed',stepId:'save',projectId:seed.id};
 await context.addInitScript(value=>{if(!localStorage.getItem('firstframe:onboarding'))localStorage.setItem('firstframe:onboarding',JSON.stringify(value))},tour);
 const api='http://127.0.0.1:8034',url='/api/projects/'+seed.id;
 const req=async(route,method='GET',data)=>{const r=await context.request.fetch(api+route,{method,data});assert.equal(r.status(),200,await r.text());return r.json()};
 const read=()=>req(url),state=()=>req('/__test/state'),payload=p=>Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(k=>[k,p[k]]));
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:3034');
 const area=page.getByRole('region',{name:'Kịch bản',exact:true}),nav=area.locator('.screenplay-scene-list'),editor=area.getByLabel('Editor liền mạch',{exact:true}),comparison=area.locator('.screenplay-saved');
 const select=async i=>{const button=nav.getByRole('button').nth(i),id=await button.getAttribute('data-script-scene');await page.waitForFunction(id=>{const e=document.querySelector(`[data-script-scene="${id}"]`);return e&&!e.matches(':disabled')},id);await button.focus();await button.press('Enter');await page.waitForFunction(id=>document.querySelector('.screenplay-scene-list button[aria-pressed="true"]')?.getAttribute('data-script-scene')===id,id);await editor.waitFor()};
 const save=async()=>{const response=page.waitForResponse(r=>r.url()===api+url&&r.request().method()==='PUT');await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();assert.equal((await response).status(),200);await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.',{exact:true}).waitFor()};
 const open=async cls=>{const details=area.locator('.'+cls);if(!await details.evaluate(e=>e.open)){await details.locator(':scope > summary').focus();await page.keyboard.press('Enter')}return details};
 await area.waitFor();assert.equal(await editor.count(),0);assert.ok(!(await read()).screenplay,'old project without M3 remains unchanged on open');
 let p=await req(url+'/scene-outline','POST',{revision:seed.revision,source_version_id:'current'});
 p=await req(url,'PUT',{...payload(p),scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes:[0,1].map((_,i)=>({id:uuid(),title:'Hai cảnh trùng tên',action:`Nguồn ${i+1}: lá thư còn kín, nhân vật tự quyết định.`}))}});
 const m1=structuredClone(p.draft),m2=structuredClone(p.scene_outline);
 await page.reload();await area.getByRole('button',{name:'Bắt đầu viết từ bản dàn cảnh này',exact:true}).focus();await page.keyboard.press('Enter');await nav.waitFor();
 assert.equal(await editor.count(),0);await select(0);await page.waitForFunction(()=>document.activeElement?.closest('.screenplay-author-fields')&&document.activeElement.tagName==='INPUT');
 const text='  Con ga\u0301i nhìn 🙂.\n\n<img src=x onerror="window.qaUnsafe=1">  ';
 await editor.locator('textarea').fill(text);assert.ok(!(await comparison.innerText()).includes('onerror'));
 await editor.locator('textarea').press('End');await editor.locator('textarea').press('Enter');
 await editor.getByLabel('Đang viết',{exact:true}).selectOption('character');
 await editor.locator('[data-script-field="speaker"]').fill('Con gái');await editor.locator('[data-script-field="speaker"]').press('Enter');
 await editor.locator('textarea').nth(1).fill('  Cha cứ để đó…  ');await editor.locator('textarea').nth(1).press('End');await editor.locator('textarea').nth(1).press('Enter');
 await editor.locator('textarea').nth(2).fill('Con kéo ghế, ngồi xuống.');await save();
 p=await read();assert.deepEqual(p.screenplay.scenes[0].blocks.map(b=>b.kind),['action','dialogue','action']);assert.equal(p.screenplay.scenes[0].blocks[0].text,text);assert.equal(p.screenplay.scenes[0].blocks[1].speaker,'Con gái');assert.equal(await page.evaluate(()=>window.qaUnsafe),undefined);
 await select(1);await editor.locator('textarea').fill('Cha đứng lại trước cửa.');await save();p=await read();const manual=structuredClone(p.screenplay);
 await select(0);await open('screenplay-writing-tools');const proposals=area.locator('.screenplay-proposals');
 await proposals.getByRole('button',{name:'Nhờ FirstFrame viết thử cảnh này',exact:true}).click();const proposal=proposals.locator(':scope > .screenplay-proposal').first();
 await proposal.getByRole('button',{name:'Chỉnh phương án',exact:true}).click();await proposal.locator('.screenplay-proposal-edit').getByLabel('Nội dung hành động',{exact:true}).fill('Phương án riêng: giữ phong thư kín.');
 assert.equal(await editor.locator('textarea').first().inputValue(),text);assert.deepEqual((await read()).screenplay,manual);
 await proposal.getByRole('checkbox').check();await proposal.getByRole('button',{name:'Dùng phương án cho cảnh này',exact:true}).click();assert.equal(await editor.locator('textarea').first().inputValue(),'Phương án riêng: giữ phong thư kín.');assert.deepEqual((await read()).screenplay,manual);
 await area.getByRole('button',{name:'Hoàn tác dùng phương án',exact:true}).click();assert.equal(await editor.locator('textarea').first().inputValue(),text);
 await proposal.getByRole('button',{name:'Lưu sửa và bỏ phương án này',exact:true}).click();await proposal.getByText(/đã bỏ/).waitFor();assert.deepEqual((await read()).screenplay,manual);
 await req('/__test/control','POST',{review_all_fields:true});await open('screenplay-feedback-tools');const feedback=area.locator('.screenplay-feedback');
 await feedback.getByRole('button',{name:'Nhận góp ý cảnh này',exact:true}).click();const latest=()=>feedback.locator(':scope > .script-review').first();await latest().getByRole('group',{name:'Ghi nhận của tác giả'}).waitFor();
 p=await read();const review=structuredClone(p.screenplay_reviews.at(-1)),beforeLinks=await state();
 for(let i=0;i<3;i++){
  const source=review.sources.find(s=>s.id===review.notes[0].evidence[i].source_id);
  await latest().getByRole('button',{name:'Đọc nguồn đã giữ',exact:true}).nth(i).click();assert.equal(await latest().getByRole('region',{name:'Nguồn góp ý đã giữ'}).locator('p.preserve-lines').textContent(),source.text);
  await latest().getByRole('button',{name:'Đến phần đang viết',exact:true}).nth(i).click();
  await page.waitForFunction(s=>{const e=document.activeElement;return e?.closest('.screenplay-author-fields')&&e.value===s.text&&(s.field==='heading'?e.tagName==='INPUT':e.closest('[data-script-block]')?.dataset.scriptBlock===s.block_id&&e.getAttribute('data-script-field')===(s.field==='speaker'?'speaker':'text'))},source);
 }
 assert.equal((await state()).calls.filter(c=>c.method!=='GET').length,beforeLinks.calls.filter(c=>c.method!=='GET').length);
 await editor.locator('textarea').first().fill('Con đặt tay cạnh thư, chưa mở.');assert.equal(await latest().getByRole('button',{name:'Đến phần đang viết',exact:true}).count(),0);await save();
 await feedback.getByRole('button',{name:'Nhận góp ý cảnh này',exact:true}).click();await latest().getByRole('group',{name:'Ghi nhận của tác giả'}).waitFor();p=await read();assert.deepEqual(p.screenplay_reviews[0],review);const reviewed=structuredClone(p.screenplay);
 const reader=area.locator('.screenplay-reading');await select(1);await editor.locator('textarea').fill('Buffer khác bản đã đọc.');
 await reader.getByRole('button',{name:'Chọn bản đã đọc để xuất',exact:true}).click();await reader.getByRole('button',{name:'Đã chọn bản này để xuất',exact:true}).waitFor();p=await read();const handoff=structuredClone(p.screenplay_handoff);assert.deepEqual(handoff.screenplay,reviewed);assert.equal(await editor.locator('textarea').inputValue(),'Buffer khác bản đã đọc.');await save();assert.deepEqual((await read()).screenplay_handoff,handoff);
 // Restore an older saved script through the UI. The selected M4 snapshot must stay immutable.
 p=await read();const versions=[...p.screenplay_versions].reverse(),index=versions.findIndex(v=>JSON.stringify(v.screenplay)===JSON.stringify(manual));assert.ok(index>=0);
 await open('screenplay-history');await area.locator('.screenplay-history > div').nth(index).getByRole('button',{name:'Khôi phục kịch bản này',exact:true}).click();await page.getByText('Đã khôi phục kịch bản; Story plan và Dàn cảnh và bản trước vẫn giữ.',{exact:true}).waitFor();p=await read();assert.deepEqual(p.screenplay.scenes,manual.scenes);assert.deepEqual(p.screenplay_handoff,handoff);
 // A pre-M3 client omits every M2/M3 field. Saving it must preserve all newer artifacts.
 const preserved=Object.fromEntries(['scene_outline','screenplay','screenplay_reviews','screenplay_proposals','screenplay_handoff'].map(k=>[k,structuredClone(p[k])]));
 p=await req(url,'PUT',{...payload(p),title:'Tên từ client cũ'});for(const [key,value]of Object.entries(preserved))assert.deepEqual(p[key],value);
 await page.reload();assert.equal(await editor.count(),0);await select(0);assert.equal(await editor.locator('textarea').first().inputValue(),text);
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1000});await select(0);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const [a,b]=await area.locator('.screenplay-columns').evaluate(e=>[e.firstElementChild,e.querySelector('.screenplay-saved')].map(n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}}));assert.ok(width<700?b.y>=a.y+a.height-1:a.x+a.width<=b.x+1,JSON.stringify({width,a,b}));
  await editor.locator('textarea').first().focus();await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.tagName),'SUMMARY');await page.keyboard.press('Shift+Tab');assert.equal(await page.evaluate(()=>document.activeElement.tagName),'TEXTAREA');
  await area.screenshot({path:path.join(directory,`handoff-${engine}-${width}.png`)});
 }
 p=await read();assert.deepEqual(p.draft,m1);assert.deepEqual(p.scene_outline,m2);assert.deepEqual(p.screenplay.source_outline,manual.source_outline);assert.deepEqual(p.screenplay_handoff,handoff);assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem('firstframe:onboarding'))),tour);
 const end=await state();assert.equal(end.writing_requests,1);assert.equal(end.review_requests,2);assert.equal(end.image_requests,0);assert.deepEqual(end.provider_stages,[]);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(directory,`handoff-${engine}.json`),JSON.stringify({engine,version:browser.version(),viewportWidths:[1440,390,320],sourceSceneIds:p.screenplay.scenes.map(s=>s.source_scene_id),feedbackFields:review.notes[0].evidence.map(e=>review.sources.find(s=>s.id===e.source_id).field),writingRequests:end.writing_requests,reviewRequests:end.review_requests,imageRequests:end.image_requests,providerStages:end.provider_stages,pageErrors:errors,legacyClientPreserved:true,m4SnapshotPreserved:true},null,2));
 console.log(`PASS integrated M3 ${engine} ${browser.version()}: keyboard/manual writing, separate AI preview/use/undo/drop, exact action/heading/speaker evidence, manual re-review, immutable saved selection/history restore, legacy client, tour, 3 widths`);
 }finally{await context.close();await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
