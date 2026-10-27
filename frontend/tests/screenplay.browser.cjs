// Disposable SQLite/API, no model calls. Run against a fresh ui_workspace_fixture.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
const fs=require('node:fs/promises');const path=require('node:path');const {randomUUID:uuid}=require('node:crypto');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 await context.addInitScript(()=>{try{localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'save',projectId:null}));}catch{}});
 const api='http://127.0.0.1:8034',base='http://127.0.0.1:3034',url=`/api/projects/${seed.id}`;
 const request=async(route,method='GET',data)=>{const r=await context.request.fetch(api+route,{method,data});assert.equal(r.status(),200,await r.text());return r.json()};
 const read=()=>request(url);const payload=p=>Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(k=>[k,p[k]]));
 let p=await request(url+'/scene-outline','POST',{revision:seed.revision,source_version_id:'current'});
 const scenes=[0,1].map(()=>({id:uuid(),title:'Lá thư',action:'Cha đặt thư. Con gái chưa mở.',staging_choices:{blocking:'Chừa lối đi.'}}));
 p=await request(url,'PUT',{...payload(p),scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes}});
 const before=await request('/__test/state');
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);const area=page.getByRole('region',{name:'M3 Kịch bản',exact:true});await area.waitFor();
 await page.getByRole('navigation',{name:'Hành trình câu chuyện'}).getByRole('button',{name:/Kịch bản/}).click();assert.equal(await page.evaluate(()=>document.activeElement.id),'workspace-script');
 const save=async()=>{await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.',{exact:true}).waitFor()};
 const nav=area.getByRole('navigation',{name:'Các cảnh kịch bản'});
 await area.getByRole('button',{name:'Bắt đầu viết từ bản dàn cảnh này',exact:true}).click();
 await area.getByLabel('Tiêu đề cảnh',{exact:true}).waitFor();p=await read();const original=structuredClone(p.screenplay.source_outline);
 assert.deepEqual(p.screenplay.scenes.map(s=>s.source_scene_id),scenes.map(s=>s.id));
 assert.equal(await area.locator('.script-block').count(),0);
 await area.getByRole('button',{name:'Thêm hành động',exact:true}).click();
 const action='  Cha đặt lá thư.\n\nCon gái đặt tay cạnh phong thư, chưa mở.  ';
 await area.getByLabel('Nội dung hành động',{exact:true}).fill(action);
 await area.getByRole('button',{name:'Thêm lời thoại',exact:true}).click();
 await area.getByLabel('Người nói',{exact:true}).fill('Con gái');await area.getByLabel('Nội dung lời thoại',{exact:true}).fill('Không sao đâu cha ạ…');
 const blocks=area.locator('.script-block');const initialIds=await blocks.evaluateAll(xs=>xs.map(x=>x.dataset.scriptBlock));
 await blocks.last().getByRole('button',{name:'Đưa khối lên',exact:true}).click();
 assert.deepEqual(await blocks.evaluateAll(xs=>xs.map(x=>x.dataset.scriptBlock)),[initialIds[1],initialIds[0]]);
 await blocks.last().getByRole('button',{name:'Xóa khối',exact:true}).click();
 await area.getByRole('button',{name:'Hoàn tác xóa khối',exact:true}).click();assert.equal(await area.getByLabel('Nội dung hành động',{exact:true}).inputValue(),action);
 await nav.getByRole('button').nth(1).click();assert.equal(await blocks.count(),0);
 await nav.getByRole('button').first().click();assert.equal(await area.getByLabel('Nội dung hành động',{exact:true}).inputValue(),action);
 assert.equal((await read()).screenplay.scenes[0].blocks.length,0);
 await area.getByLabel('Nội dung hành động',{exact:true}).press('Tab');assert.equal(await page.evaluate(()=>document.activeElement?.tagName),'BUTTON');
 await save();p=await read();const savedScript=structuredClone(p.screenplay);
 assert.equal(p.screenplay.scenes[0].blocks[1].text,action);assert.deepEqual(p.screenplay.source_outline,original);
 // Backups include current unsaved screenplay text and immutable source.
 await area.getByLabel('Nội dung hành động',{exact:true}).fill('Bản chưa lưu cần giữ.');
 const more=page.locator('.save-more');await more.locator('summary').click();const downloadPromise=page.waitForEvent('download');
 await more.getByRole('button',{name:'Tải bản sao JSON',exact:true}).click();const download=await downloadPromise;
 const backup=JSON.parse(await fs.readFile(await download.path(),'utf8'));assert.equal(backup.screenplay.scenes[0].blocks[1].text,'Bản chưa lưu cần giữ.');
 await more.locator('summary').click();
 // Failed save and project switch retain the local buffer and last saved script.
 const route=`**${url}`;const offline=r=>r.request().method()==='PUT'?r.abort('failed'):r.continue();await page.route(route,offline);
 await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.locator('.save-toolbar .error').waitFor();
 assert.deepEqual((await read()).screenplay,savedScript);
 await page.getByRole('button',{name:'Dự án mới',exact:true}).click();await page.locator('.save-toolbar .error').waitFor();
 assert.equal(await area.getByLabel('Nội dung hành động',{exact:true}).inputValue(),'Bản chưa lưu cần giữ.');
 await page.unroute(route,offline);
 // A concurrent writer advances revision. Inspect must not rebase the local edit over it.
 p=await read();await request(url,'PUT',{...payload(p),title:'Tên từ cửa sổ khác'});
 await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.locator('.save-toolbar .error').filter({hasText:'cửa sổ khác'}).waitFor();
 await area.getByRole('button',{name:'Kiểm tra kịch bản đã lưu',exact:true}).click();await page.locator('.save-toolbar .error').filter({hasText:'cửa sổ khác'}).waitFor();
 assert.equal(await area.getByLabel('Nội dung hành động',{exact:true}).inputValue(),'Bản chưa lưu cần giữ.');
 // Reload only the disposable buffer after verifying backup/rejection.
 await page.reload();await area.getByLabel('Tiêu đề cảnh',{exact:true}).waitFor();
 assert.equal(await area.getByLabel('Nội dung hành động',{exact:true}).inputValue(),action);
 // Changed M2 text and current M1 do not replace the captured source or screenplay.
 p=await read();const changed=structuredClone(p.scene_outline);changed.scenes[0].action='Diễn tiến M2 mới.';
 await request(url,'PUT',{...payload(p),scene_outline:{id:changed.id,version:changed.version,scenes:changed.scenes}});
 await page.reload();await area.getByText(/Dàn cảnh hoặc ý đồ hiện tại khác nguồn/).waitFor();
 assert.match(await area.locator('.screenplay-source').innerText(),/Cha đặt thư. Con gái chưa mở/);assert.doesNotMatch(await area.locator('.screenplay-source').innerText(),/Diễn tiến M2 mới/);
 assert.deepEqual((await read()).screenplay,savedScript);
 // Starting a new draft after editing checkpoints that work. Lost response is inspected, never retried.
 await area.getByLabel('Nội dung hành động',{exact:true}).fill('Sửa trước khi bắt đầu bản khác.');
 await area.getByRole('checkbox').check();await request('/__test/control','POST',{lose_response_suffix:url+'/screenplay'});
 await area.getByRole('button',{name:'Bắt đầu bản kịch bản khác',exact:true}).click();await page.locator('.save-toolbar .error').waitFor();
 await area.getByText(/Chưa rõ kết quả bắt đầu bản mới/).waitFor();
 await area.getByRole('button',{name:'Kiểm tra kịch bản đã lưu',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.screenplay .script-block').length===0);
 p=await read();const newScript=structuredClone(p.screenplay);const latest=p.screenplay_versions.at(-1);
 assert.equal(latest.screenplay.scenes[0].blocks[1].text,'Sửa trước khi bắt đầu bản khác.');
 assert.equal(p.screenplay.source_outline.scenes[0].action,'Diễn tiến M2 mới.');
 const state=await request('/__test/state');assert.equal(state.calls.filter(c=>c.method==='POST'&&c.path===url+'/screenplay').length,2);
 // Read history without writes, then restore; current blank draft remains archived.
 const history=area.locator('.screenplay-history');await history.locator(':scope > summary').click();
 const previous=history.locator(':scope > div').first();await previous.getByText('Đọc phiên bản này',{exact:true}).click();
 assert.match(await previous.innerText(),/Sửa trước khi bắt đầu bản khác/);
 await previous.getByRole('button',{name:'Khôi phục kịch bản này',exact:true}).click();
 await page.getByText('Đã khôi phục kịch bản; M1/M2 và bản trước vẫn giữ.',{exact:true}).waitFor();
 assert.equal(await area.getByLabel('Nội dung hành động',{exact:true}).inputValue(),'Sửa trước khi bắt đầu bản khác.');
 p=await read();assert.deepEqual(p.screenplay_versions.at(-1).screenplay,newScript);
 assert.deepEqual(p.screenplay.source_outline,original);assert.equal(p.scene_outline.scenes[0].action,'Diễn tiến M2 mới.');
 for(const width of [1280,390,320]){
   await page.setViewportSize({width,height:900});await area.scrollIntoViewIfNeeded();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:`/tmp/firstframe-m3-manual-${width}.png`});
 }
 // Successful project switching saves the buffer before leaving and recovers it when reopened.
 await area.getByLabel('Nội dung hành động',{exact:true}).fill('Lưu trước khi đổi dự án.');
 await page.getByRole('button',{name:'Dự án mới',exact:true}).click();await page.waitForFunction(id=>document.querySelector('#project-picker')?.value!==id,seed.id);
 await page.locator('#project-picker').selectOption(seed.id);await area.getByLabel('Tiêu đề cảnh',{exact:true}).waitFor();
 assert.equal(await area.getByLabel('Nội dung hành động',{exact:true}).inputValue(),'Lưu trước khi đổi dự án.');
 const after=await request('/__test/state');assert.deepEqual(after.provider_stages,before.provider_stages);assert.equal(after.image_requests,before.image_requests);assert.equal(after.writing_requests,before.writing_requests);
 assert.deepEqual(errors,[]);
 console.log('PASS M3 manual: source snapshot, Vietnamese/whitespace, blocks/reorder/delete/undo, scene buffer, save/reload/backup, network/409, project switch, M2 divergence, start lost-response inspect no retry, history/restore, 3 widths, zero model calls');
 await context.close();await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
