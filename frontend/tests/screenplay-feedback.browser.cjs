// Disposable API/SQLite and fake reviewer; no real model requests.
const {openScriptScene}=require('./screenplay-browser-helpers.cjs');
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const {randomUUID:uuid}=require('node:crypto');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'}),context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 await context.addInitScript(()=>localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'save',projectId:null})));
 const api='http://127.0.0.1:8034',url=`/api/projects/${seed.id}`;
 const req=async(route,method='GET',data)=>{const r=await context.request.fetch(api+route,{method,data});assert.equal(r.status(),200,await r.text());return r.json()};
 const read=()=>req(url),payload=p=>Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(k=>[k,p[k]]));
 let p=await req(url+'/scene-outline','POST',{revision:seed.revision,source_version_id:'current'});
 p=await req(url,'PUT',{...payload(p),scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes:[0,1].map(()=>({id:uuid(),title:'Cảnh trùng tên',action:'Cha đặt thư. Con gái chưa mở.'}))}});
 p=await req(url+'/screenplay','POST',{revision:p.revision,request_id:uuid()});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:3034');
 const area=page.locator('.screenplay'),main=area.locator('.screenplay-author-fields'),panel=area.locator('.screenplay-feedback');
 const latest=()=>panel.locator(':scope > .script-review').first(),text=()=>main.getByLabel('Nội dung hành động',{exact:true});
 const save=async()=>{await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.',{exact:true}).waitFor()};
 const generate=async()=>{await panel.getByRole('button',{name:'Nhận góp ý cảnh này',exact:true}).click();await latest().getByRole('group',{name:'Ghi nhận của tác giả'}).waitFor()};
 const inspect=()=>panel.getByRole('button',{name:'Kiểm tra góp ý đã lưu',exact:true}).click();
 const writes=s=>s.calls.filter(c=>c.method!=='GET').length;
 await openScriptScene(area,0,{legacy:true});await main.getByRole('button',{name:'Thêm hành động',exact:true}).click();await text().fill('Con gái nhìn thư, chưa mở.');await generate();
 p=await read();const original=structuredClone(p.screenplay),first=structuredClone(p.screenplay_reviews[0]);
 assert.equal(first.source_screenplay.scenes[0].blocks[0].text,'Con gái nhìn thư, chưa mở.');assert.deepEqual(p.screenplay,original);
 let before=await req('/__test/state');
 await latest().getByRole('button',{name:'Đọc nguồn đã giữ',exact:true}).first().click();
 await latest().getByRole('region',{name:'Nguồn góp ý đã giữ'}).getByText('Con gái nhìn thư, chưa mở.',{exact:true}).waitFor();
 await latest().getByRole('button',{name:'Đến phần đang viết',exact:true}).first().click();await page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='Nội dung hành động'||document.activeElement?.closest('[data-script-block]')!==null);
 assert.equal(writes(await req('/__test/state')),writes(before));
 // Dirty edits stay in the buffer even when recording an assessment or inspecting sources.
 await text().fill('Con gái kéo ghế, để thư còn kín.');assert.equal(await latest().getByRole('button',{name:'Đến phần đang viết',exact:true}).count(),0);
 await latest().getByRole('button',{name:'Dẫn sai',exact:true}).click();await page.getByText('Đã lưu ghi nhận về góp ý; không sửa hoặc tự lưu kịch bản đang viết.',{exact:true}).waitFor();
 assert.equal(await text().inputValue(),'Con gái kéo ghế, để thư còn kín.');assert.deepEqual((await read()).screenplay,original);
 await inspect();assert.equal(await text().inputValue(),'Con gái kéo ghế, để thư còn kín.');
 await save();await generate();p=await read();assert.equal(p.screenplay_reviews[1].source_screenplay.scenes[0].blocks[0].text,'Con gái kéo ghế, để thư còn kín.');
 assert.deepEqual(p.screenplay_reviews[0].source_screenplay,first.source_screenplay);assert.equal(p.screenplay_reviews[0].notes[0].assessment,'misleading');
 // A neighboring edit invalidates the reference without redirecting to new text.
 const nav=area.getByRole('navigation',{name:'Các cảnh kịch bản'});await nav.getByRole('button').nth(1).click();
 await main.getByRole('button',{name:'Thêm hành động',exact:true}).click();await text().fill('Cha đứng ngoài cửa.');await save();await nav.getByRole('button').first().click();
 assert.equal(await latest().getByRole('button',{name:'Đến phần đang viết',exact:true}).count(),0);await latest().getByText(/Góp ý thuộc nguồn trước/).waitFor();
 await req('/__test/control','POST',{lose_response_suffix:url+'/screenplay-reviews/stream'});
 await panel.getByRole('button',{name:'Nhận góp ý cảnh này',exact:true}).click();await page.locator('.save-toolbar .error').waitFor();
 await area.locator('.screenplay-feedback-tools > summary').click();await area.locator('.screenplay-feedback-tools > summary').click();
 assert.ok(await panel.getByRole('button',{name:'Nhận góp ý cảnh này',exact:true}).isDisabled());await inspect();
 await latest().getByRole('group',{name:'Ghi nhận của tác giả'}).waitFor();assert.equal((await req('/__test/state')).review_requests,3);
 // Invalid evidence and timeout are retained failures, never rendered as verified notes.
 for(const [control,error] of [[{bad_review:true},'MalformedProviderResponseError'],[{bad_review:false,fail_review:true},'ProviderTimeoutError']]){
  await req('/__test/control','POST',control);await panel.getByRole('button',{name:'Nhận góp ý cảnh này',exact:true}).click();await page.locator('.save-toolbar .error').waitFor();await inspect();
  await latest().getByText(new RegExp(error)).waitFor({state:'attached'});if(!await latest().evaluate(e=>e.open))await latest().locator(':scope > summary').click();await latest().getByText(new RegExp(error)).waitFor();
  assert.equal(await latest().locator('.script-review-note').count(),0);
 }
 await text().fill('Tác giả vẫn tự sửa sau lỗi.');await save();
 await req('/__test/control','POST',{fail_review:false,empty_review:true});await panel.getByRole('button',{name:'Nhận góp ý cảnh này',exact:true}).click();
 await latest().getByText(/Điều đó không chứng minh cảnh đúng ý hoặc hay/).waitFor();await page.reload();await openScriptScene(area,0,{legacy:true});await text().waitFor();assert.equal(await text().inputValue(),'Tác giả vẫn tự sửa sau lỗi.');
 p=await read();assert.equal(p.screenplay_reviews.length,6);assert.equal(p.screenplay_reviews[0].notes[0].assessment,'misleading');assert.deepEqual(p.feedback_source,seed.feedback_source);
 const state=await req('/__test/state');assert.equal(state.review_requests,6);assert.equal(state.writing_requests,0);assert.equal(state.image_requests,0);assert.deepEqual(state.provider_stages,[]);
 for(const width of [1280,390,320]){await page.setViewportSize({width,height:900});await panel.scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`/tmp/firstframe-m3-feedback-${width}.png`});}
 assert.deepEqual(errors,[]);console.log('PASS M3 feedback: save-before-review, exact source/focus, no writes while reading, dirty-buffer assessment/inspect, manual save/re-review, neighbor stale, lost-response no retry, bad evidence, timeout, empty output caution, reload, 3 widths');
 await context.close();await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
