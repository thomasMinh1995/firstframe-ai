// Disposable fixture, synthetic author data, fake image provider only.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path'),{randomUUID:uuid}=require('node:crypto');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'}),context=await browser.newContext({viewport:{width:1440,height:1000}});
 await context.addInitScript(()=>localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'save',projectId:null})));
 const api='http://127.0.0.1:8034',url='/api/projects/'+seed.id;
 const req=async(route,method='GET',data)=>{const r=await context.request.fetch(api+route,{method,data});assert.equal(r.status(),200,await r.text());return r.json()};
 const read=()=>req(url),state=()=>req('/__test/state'),writes=s=>s.calls.filter(c=>c.method!=='GET').length;
 const payload=p=>Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(k=>[k,p[k]]));
 let p=await req(url+'/scene-outline','POST',{revision:seed.revision,source_version_id:'current'});
 p=await req(url,'PUT',{...payload(p),scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes:[0,1].map((_,i)=>({id:uuid(),title:'Cùng tên',action:'Nguồn '+i+': đặt thư còn kín.'}))}});
 const source=structuredClone(p.scene_outline),first=source.scenes[0].id,second=source.scenes[1].id;
 const sketchId=uuid();p=await req(url+'/scene-sketches','POST',{revision:p.revision,request_id:sketchId,scene_id:first,instructions:''});
 p=await req(url+'/scene-sketches/'+sketchId+'/keep','POST',{revision:p.revision});
 p=await req(url+'/screenplay','POST',{revision:p.revision,request_id:uuid()});
 const frozen=structuredClone(p.screenplay.source_outline),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const area=page.locator('.screenplay'),nav=area.locator('.screenplay-scene-list'),editor=area.getByLabel('Editor liền mạch',{exact:true}),sourcePanel=area.locator('.screenplay-source');
 await page.goto('http://127.0.0.1:3034');await nav.getByRole('button').first().waitFor();
 assert.equal(await nav.locator('img').count(),1);assert.ok((await nav.locator('img').getAttribute('src')).includes(sketchId));
 const before=await state();
 // Hold the navigation frame so fast typing precedes its delayed heading focus.
 await page.evaluate(()=>{window.qaRaf=requestAnimationFrame;window.qaCancel=cancelAnimationFrame;window.qaFrames=new Map();let id=0;window.requestAnimationFrame=fn=>{window.qaFrames.set(--id,fn);return id};window.cancelAnimationFrame=id=>id<0?window.qaFrames.delete(id):window.qaCancel(id)});
 await nav.getByRole('button').first().click();
 for(const cls of ['screenplay-source','screenplay-writing-tools','screenplay-feedback-tools'])assert.equal(await area.locator('.'+cls).evaluate(e=>e.open),false);
 await editor.locator('textarea').fill('Tác giả đang viết, chưa lưu.');
 await page.evaluate(()=>{requestAnimationFrame=window.qaRaf;cancelAnimationFrame=window.qaCancel;for(const fn of window.qaFrames.values())fn(performance.now());window.qaFrames.clear()});
 assert.ok(await editor.locator('textarea').evaluate(e=>e===document.activeElement),'delayed navigation must not steal typing focus');
 for(const cls of ['screenplay-source','screenplay-writing-tools','screenplay-feedback-tools']){
  const panel=area.locator('.'+cls);await panel.locator(':scope > summary').click();await panel.locator(':scope > summary').click();
 }
 const writing=area.locator('.screenplay-writing-tools');await writing.locator(':scope > summary').click();
 const request=writing.getByLabel('Bạn muốn viết thử theo hướng nào? · tùy chọn',{exact:true});await request.fill('Giữ khoảng lặng.');
 await writing.locator(':scope > summary').click();await writing.locator(':scope > summary').click();assert.equal(await request.inputValue(),'Giữ khoảng lặng.');await writing.locator(':scope > summary').click();
 assert.equal(await editor.locator('textarea').inputValue(),'Tác giả đang viết, chưa lưu.');
 assert.equal(writes(await state()),writes(before));assert.equal((await state()).image_requests,1);
 await sourcePanel.locator(':scope > summary').click();await sourcePanel.getByText(source.scenes[0].action,{exact:true}).waitFor();
 await page.waitForFunction(()=>document.querySelector('.screenplay-source img')?.naturalWidth===768);await sourcePanel.getByText(/Ảnh không được giữ riêng cùng phiên bản kịch bản/).waitFor();
 await area.screenshot({path:path.join(directory,'context-support-desktop.png')});
 // Same title, different ID: no image moves to scene 2.
 await nav.getByRole('button').nth(1).click();assert.equal(await sourcePanel.locator('img').count(),0);await sourcePanel.getByText(source.scenes[1].action,{exact:true}).waitFor();
 await nav.getByRole('button').first().click();assert.equal(await editor.locator('textarea').inputValue(),'Tác giả đang viết, chưa lưu.');
 await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.',{exact:true}).waitFor();
 assert.equal((await read()).screenplay.scenes[0].blocks[0].text,'Tác giả đang viết, chưa lưu.','fast typing before delayed navigation focus survives save');
 // Change/reorder current M2: old kept image still matches the frozen M3 source.
 p=await read();p=await req(url,'PUT',{...payload(p),scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes:[{...p.scene_outline.scenes[1]},{...p.scene_outline.scenes[0],action:'M2 mới: mở thư.'}]}});
 await page.reload();await nav.getByRole('button').first().click();await sourcePanel.locator(':scope > summary').click();
 assert.equal(await nav.locator('img').count(),1);await sourcePanel.getByText(source.scenes[0].action,{exact:true}).waitFor();
 // Keeping a new image from the new M2 does not silently reuse the old unselected image.
 const other=uuid();p=await req(url+'/scene-sketches','POST',{revision:p.revision,request_id:other,scene_id:first,instructions:''});p=await req(url+'/scene-sketches/'+other+'/keep','POST',{revision:p.revision});
 await page.reload();await nav.getByRole('button').first().click();await sourcePanel.locator(':scope > summary').click();
 assert.equal(await nav.locator('img').count(),0);await nav.getByText('Ảnh dàn cảnh khác nguồn',{exact:true}).waitFor();
 await sourcePanel.locator('.screenplay-sketch-other > summary').click();await sourcePanel.getByText(/Ảnh này không khớp nguồn kịch bản/).waitFor();
 assert.ok((await sourcePanel.locator('img').getAttribute('src')).includes(other));
 // A missing asset is a neutral fallback; writing and saving remain available.
 await page.route('**/scene-sketches/*/image',r=>r.fulfill({status:404,body:'missing'}));await page.reload();await nav.getByRole('button').first().click();await sourcePanel.locator(':scope > summary').click();await sourcePanel.locator('.screenplay-sketch-other > summary').click();
 await sourcePanel.getByText(/Tệp ảnh thiếu hoặc lỗi/).waitFor();await editor.locator('textarea').fill('Vẫn lưu được khi ảnh thiếu.');await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.',{exact:true}).waitFor();
 p=await read();assert.equal(p.screenplay.scenes[0].blocks[0].text,'Vẫn lưu được khi ảnh thiếu.');assert.deepEqual(p.screenplay.source_outline,frozen);assert.equal(p.scene_outline.scenes[0].id,second);
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await area.screenshot({path:path.join(directory,`context-${width}.png`)});}
 const end=await state();assert.equal(end.image_requests,2);assert.equal(end.writing_requests,0);assert.equal(end.review_requests,0);assert.deepEqual(end.provider_stages,[]);assert.deepEqual(errors,[]);
 console.log('PASS M3 context: closed support, no writes/AI on toggles/navigation, exact frozen source, duplicate titles/reordered M2, current kept choice, stale warning, missing asset, save without image, 3 widths');
 await context.close();await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
