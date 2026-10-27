// Disposable SQLite/API with fake providers: manual and AI-choice paths, no real model.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const {randomUUID:uuid}=require('node:crypto');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'}),context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 await context.addInitScript(()=>localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'completed',stepId:'save',projectId:null})));
 const api='http://127.0.0.1:8034',url=`/api/projects/${seed.id}`;
 const req=async(route,method='GET',data)=>{const r=await context.request.fetch(api+route,{method,data});assert.equal(r.status(),200,await r.text());return r.json()};
 const read=()=>req(url),payload=p=>Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(k=>[k,p[k]]));
 let p=await req(url+'/scene-outline','POST',{revision:seed.revision,source_version_id:'current'});
 p=await req(url,'PUT',{...payload(p),scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes:[0,1].map(()=>({id:uuid(),title:'Cảnh trùng tên',action:'Cha đặt thư. Con gái tự quyết định.'}))}});
 p=await req(url+'/screenplay','POST',{revision:p.revision,request_id:uuid()});
 const script=structuredClone(p.screenplay);script.scenes[0].blocks=[{id:uuid(),kind:'action',speaker:'',text:'Bản lưu ban đầu: thư còn kín.'}];
 p=await req(url,'PUT',{...payload(p),screenplay:{id:script.id,version:script.version,scenes:script.scenes}});
 const savedOutline=structuredClone(p.scene_outline);
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:3034');
 const area=page.locator('.screenplay'),main=area.locator('.screenplay-columns > .screenplay-scene'),reader=area.locator('.screenplay-reading');
 const full=reader.locator(':scope > .screenplay-full-text'),nav=area.getByRole('navigation',{name:'Các cảnh kịch bản'});
 const action=()=>main.getByLabel('Nội dung hành động',{exact:true}),choose=()=>reader.getByRole('button',{name:'Chọn bản đã đọc cho M4',exact:true});
 const save=async()=>{await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.',{exact:true}).waitFor()};
 const select=async()=>{await choose().click();await page.getByText('Đã giữ snapshot nguồn M4; chưa xuất bản và không tự lưu phần đang sửa.',{exact:true}).waitFor()};
 assert.equal(await full.locator('article').count(),2);await full.getByText('Cảnh chưa viết.',{exact:true}).waitFor();assert.ok(await choose().isDisabled());
 assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('firstframe:onboarding')).status),'completed','M3 must not reset an old completed tour');
 await action().fill('  Cha đặt thư.\n\nCon gái nhìn, chưa mở.  ');assert.match(await full.innerText(),/Bản lưu ban đầu/);assert.ok(!(await full.innerText()).includes('Con gái nhìn, chưa mở'));
 await reader.getByRole('button',{name:'Quay lại sửa cảnh 2',exact:true}).click();await main.getByRole('button',{name:'Thêm lời thoại',exact:true}).click();
 await main.getByLabel('Người nói',{exact:true}).fill('Con gái');await main.getByLabel('Nội dung lời thoại',{exact:true}).fill('  Không sao đâu cha ạ…\n  ');await save();
 p=await read();const manual=structuredClone(p.screenplay);await full.getByText('Không sao đâu cha ạ…',{exact:false}).waitFor();
 await nav.getByRole('button').first().click();await action().fill('Buffer chưa chọn, không tự lưu.');
 let before=await req('/__test/state');await select();p=await read();const first=structuredClone(p.screenplay_handoff);
 assert.deepEqual(first.screenplay,manual);assert.deepEqual(p.screenplay,manual);assert.equal(await action().inputValue(),'Buffer chưa chọn, không tự lưu.');
 let writes=(await req('/__test/state')).calls.slice(before.calls.length).filter(c=>c.method!=='GET');assert.deepEqual(writes.map(c=>c.path),[url+'/screenplay-selections']);
 await save();p=await read();assert.deepEqual(p.screenplay_handoff,first);
 // Lost response recovers only metadata, without resending or saving a dirty buffer.
 await action().fill('Buffer vẫn giữ khi kiểm tra nguồn.');await req('/__test/control','POST',{lose_response_suffix:url+'/screenplay-selections'});
 await choose().click();await page.locator('.save-toolbar .error').waitFor();assert.ok(await choose().isDisabled());
 await reader.getByRole('button',{name:'Kiểm tra nguồn M4 đã lưu',exact:true}).click();await reader.getByRole('button',{name:'Đã chọn nguồn này cho M4',exact:true}).waitFor();
 assert.equal(await action().inputValue(),'Buffer vẫn giữ khi kiểm tra nguồn.');p=await read();assert.equal(p.screenplay_selections.length,2);
 assert.equal(p.screenplay_handoff.screenplay.scenes[0].blocks[0].text,'Buffer chưa chọn, không tự lưu.');
 // Choose complete history without restoring current text or losing pending edits.
 const history=p.screenplay_versions.find(v=>JSON.stringify(v.screenplay)===JSON.stringify(manual));assert.ok(history);
 await reader.getByLabel('Bản để đọc và đối chiếu',{exact:true}).selectOption(history.id);before=await req('/__test/state');await select();
 let after=await read();assert.deepEqual(after.screenplay,p.screenplay);assert.deepEqual(after.screenplay_handoff.screenplay,manual);assert.equal(await action().inputValue(),'Buffer vẫn giữ khi kiểm tra nguồn.');
 writes=(await req('/__test/state')).calls.slice(before.calls.length).filter(c=>c.method!=='GET');assert.deepEqual(writes.map(c=>c.path),[url+'/screenplay-selections']);await save();
 await reader.getByLabel('Bản để đọc và đối chiếu',{exact:true}).selectOption('current');
 // AI proposal is separate: selection before explicit save must use the saved manual version.
 await nav.getByRole('button').nth(1).click();const panel=area.locator('.screenplay-proposals');
 await panel.getByRole('button',{name:'Nhờ FirstFrame viết thử cảnh này',exact:true}).click();const proposal=panel.locator(':scope > .screenplay-proposal').first();
 await proposal.getByRole('button',{name:'Chỉnh phương án',exact:true}).waitFor();await proposal.getByRole('checkbox').check();await proposal.getByRole('button',{name:'Dùng phương án cho cảnh này',exact:true}).click();
 const pendingSaved=(await read()).screenplay;await select();p=await read();assert.deepEqual(p.screenplay_handoff.screenplay,pendingSaved);assert.equal(p.screenplay_proposals.at(-1).status,'ready');
 const beforeAiSave=structuredClone(p.screenplay_handoff);await save();assert.deepEqual((await read()).screenplay_handoff,beforeAiSave);await select();
 p=await read();assert.equal(p.screenplay_proposals.at(-1).status,'applied');assert.deepEqual(p.screenplay_handoff.screenplay,p.screenplay);assert.equal(p.screenplay_selections.length,5);
 assert.deepEqual(p.screenplay_selections[0].screenplay,manual);await page.reload();await reader.getByRole('button',{name:'Đã chọn nguồn này cho M4',exact:true}).waitFor();
 const handoff=reader.locator('.screenplay-handoff');await handoff.locator(':scope > summary').click();assert.equal(await handoff.locator('[data-reading-scene]').count(),2);
 const state=await req('/__test/state');assert.equal(state.writing_requests,1);assert.equal(state.review_requests,0);assert.equal(state.image_requests,0);assert.deepEqual(state.provider_stages,[]);
 before=await req('/__test/state');const provenance=handoff.getByText('Nguồn M2 và ý đồ đi cùng bản này',{exact:true});await provenance.click();
 await handoff.getByText('Cha đặt thư. Con gái tự quyết định.',{exact:true}).first().waitFor();await provenance.click();
 assert.equal((await req('/__test/state')).calls.filter(c=>c.method!=='GET').length,before.calls.filter(c=>c.method!=='GET').length);
 assert.deepEqual(p.feedback_source,seed.feedback_source);assert.deepEqual(p.scene_outline,savedOutline);
 // Cross-window revision changes leave the author's buffer and old selected source intact.
 await nav.getByRole('button').first().click();await action().fill('Buffer giữ sau 409.');await reader.getByLabel('Bản để đọc và đối chiếu',{exact:true}).selectOption(history.id);
 const fresh=await read();await req(url,'PUT',{...payload(fresh),title:'Tên đổi từ cửa sổ khác'});await choose().click();await page.locator('.save-toolbar .error').waitFor();
 assert.equal(await action().inputValue(),'Buffer giữ sau 409.');assert.deepEqual((await read()).screenplay_handoff,p.screenplay_handoff);
 for(const width of [1280,390,320]){await page.setViewportSize({width,height:900});await reader.scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`/tmp/firstframe-m3-g4-${width}.png`});}
 assert.deepEqual(errors,[]);console.log('PASS M3 G4: saved full reading/order/missing scene, preserved tour, manual+AI choice, buffer isolation, immutable/history source, lost response no retry, reload, 409, 3 widths');
 await context.close();await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
