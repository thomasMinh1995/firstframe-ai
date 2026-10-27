// Disposable API/SQLite + fake image provider. Never generates real images.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
const fs=require('node:fs/promises');const path=require('node:path');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 await context.addInitScript(()=>{try{localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'save',projectId:null}));}catch{}});
 const api='http://127.0.0.1:8034',base='http://127.0.0.1:3034';
 const read=async()=>{const r=await context.request.get(`${api}/api/projects/${seed.id}`);assert.equal(r.status(),200);return r.json()};
 const controls=async data=>{const r=await context.request.post(api+'/__test/control',{data});assert.equal(r.status(),200)};
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.locator('#workspace-outline').waitFor();
 await page.getByRole('button',{name:'Bắt đầu dàn cảnh từ bản đã chọn',exact:true}).click();
 const area=page.locator('.scene-outline'),pop=page.locator('.scene-popover:popover-open');
 for(const title of ['Lá thư','Cửa']){
   await area.getByRole('button',{name:'Tự thêm cảnh',exact:true}).click();
   await pop.getByLabel('Tên cảnh',{exact:true}).fill(title);
   await pop.getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).fill('Cha đặt thư. Con gái nhìn, chưa mở.');
   await pop.getByRole('button',{name:'Đóng',exact:true}).click();
 }
 await page.getByRole('button',{name:'Lưu thay đổi',exact:true}).click();await page.getByText('Đã lưu thay đổi.',{exact:true}).waitFor();
 const initial=(await read()).scene_outline;
 await area.locator('[data-select-scene]').first().click();await pop.getByRole('tab',{name:'Phác hình',exact:true}).click();
 const panel=pop.locator('.scene-sketches'),latest=()=>panel.locator(':scope > details').first();
 const generate=async()=>{await panel.getByRole('button',{name:'Tạo một hình phác',exact:true}).click();await latest().getByRole('button',{name:'Giữ hình phác này',exact:true}).waitFor()};
 await generate();await page.waitForFunction(()=>document.querySelector('.scene-sketches img')?.naturalWidth===768);
 let project=await read();const first=project.scene_sketches.at(-1);assert.deepEqual(project.selected_scene_sketches,{});
 assert.equal(first.prompt_version,'scene-sketch-direct-v3');
 assert.ok(first.prompt.includes(initial.scenes[0].action));assert.ok(!first.prompt.includes('"scene":'));
 assert.ok(!first.prompt.includes('Quoted passages'));assert.ok(!first.prompt.includes('Show the visible action described here'));
 assert.ok(!first.prompt.includes('“')&&!first.prompt.includes('”'));
 const sourceDetails=latest().locator('details');await sourceDetails.locator('summary').click();
 assert.equal(await sourceDetails.locator('p').innerText(),first.prompt);
 await sourceDetails.locator('summary').click();assert.equal(await pop.count(),1);
 await latest().getByRole('button',{name:'Giữ hình phác này',exact:true}).click();
 await latest().getByRole('button',{name:'Bỏ hình đang giữ',exact:true}).waitFor();
 assert.equal((await read()).selected_scene_sketches[initial.scenes[0].id],first.id);
 await generate();project=await read();assert.equal(project.selected_scene_sketches[initial.scenes[0].id],first.id);
 await latest().getByRole('button',{name:'Bỏ hình phác này',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.scene-sketches > details > summary')?.textContent?.includes('đã bỏ')); assert.equal((await read()).selected_scene_sketches[initial.scenes[0].id],first.id);
 // Lose a response after generation: inspect retrieves the same request; no automatic extra image.
 await controls({lose_response_suffix:`/api/projects/${seed.id}/scene-sketches/stream`});
 await panel.getByRole('button',{name:'Tạo một hình phác',exact:true}).click();await pop.locator('.error').waitFor();
 await panel.getByRole('button',{name:'Kiểm tra ảnh đã lưu',exact:true}).click();
 await latest().getByRole('button',{name:'Giữ hình phác này',exact:true}).waitFor();
 project=await read();assert.equal(project.scene_sketches.length,3);
 assert.equal((await (await context.request.get(api+'/__test/state')).json()).image_requests,3);
 await latest().getByRole('button',{name:'Giữ hình phác này',exact:true}).click();
 await latest().getByRole('button',{name:'Bỏ hình đang giữ',exact:true}).waitFor();
 const selected=(await read()).scene_sketches.at(-1);
 await pop.getByRole('button',{name:'Đóng',exact:true}).click();
 assert.equal(await area.locator('.scene-select img').count(),1);
 await page.reload();await area.locator('.scene-select img').waitFor();
 assert.equal((await read()).selected_scene_sketches[initial.scenes[0].id],selected.id);
 // Reorder text: the kept image remains attached to its ID, is marked stale, and cannot be selected anew.
 await area.locator('[data-select-scene]').first().click();await pop.getByRole('button',{name:'Xuống sau',exact:true}).click();
 await pop.getByRole('button',{name:'Lưu thay đổi dàn cảnh',exact:true}).click();await page.getByText('Đã lưu thay đổi dàn cảnh và mọi sửa đang chờ trong dự án.',{exact:true}).waitFor();
 await pop.getByRole('tab',{name:'Phác hình',exact:true}).click();assert.match(await panel.innerText(),/Nguồn đã đổi/);
 assert.ok(await latest().getByRole('button',{name:'Giữ hình phác này',exact:true}).isDisabled());
 assert.equal((await read()).scene_outline.scenes[1].id,initial.scenes[0].id);
 // Timeout and a new successful preview do not replace the stale-but-kept image.
 await controls({fail_sketch:true});await panel.getByRole('button',{name:'Tạo một hình phác',exact:true}).click();await pop.locator('.error').waitFor();
 await panel.getByRole('button',{name:'Kiểm tra ảnh đã lưu',exact:true}).click();
 assert.equal((await read()).selected_scene_sketches[initial.scenes[0].id],selected.id);
 await controls({fail_sketch:false});await generate();
 await pop.getByRole('tab',{name:'Dàn cảnh',exact:true}).click();
 await pop.getByLabel('Bạn muốn người xem cảm nhận điều gì? · tùy chọn',{exact:true}).fill('Ghi chú chưa lưu.');
 await pop.getByRole('tab',{name:'Phác hình',exact:true}).click();
 assert.ok(await latest().getByRole('button',{name:'Giữ hình phác này',exact:true}).isDisabled());
 await latest().getByRole('button',{name:'Bỏ hình phác này',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.scene-sketches > details > summary')?.textContent?.includes('đã bỏ'));
 await pop.getByRole('tab',{name:'Dàn cảnh',exact:true}).click();
 assert.equal(await pop.getByLabel('Bạn muốn người xem cảm nhận điều gì? · tùy chọn',{exact:true}).inputValue(),'Ghi chú chưa lưu.');
 assert.equal((await read()).scene_outline.scenes[1].viewer_intent,'');
 await pop.getByRole('button',{name:'Lưu thay đổi dàn cảnh',exact:true}).click();await page.getByText('Đã lưu thay đổi dàn cảnh và mọi sửa đang chờ trong dự án.',{exact:true}).waitFor();
 await pop.getByRole('button',{name:'Đóng',exact:true}).click();
 // Missing image leaves text/references readable and never blocks the text handoff.
 await fs.unlink(path.join(directory,'scene-images',seed.id,selected.asset_id+'.png'));
 await page.reload();await area.locator('.scene-select').last().getByText(/Tệp ảnh thiếu hoặc lỗi/).waitFor();
 await area.getByRole('button',{name:'Lưu bản dàn cảnh để viết tiếp',exact:true}).click();await page.getByText(/Đã lưu bản nguồn M2 phiên bản/).waitFor();
 assert.ok((await read()).scene_handoff);assert.equal((await read()).feedback_source.content_key,seed.feedback_source.content_key);
 for(const width of [1280,390,320]){
   await page.setViewportSize({width,height:900});await area.locator('[data-select-scene]').last().click();
   await pop.getByRole('tab',{name:'Phác hình',exact:true}).click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:`/tmp/firstframe-scene-sketch-${width}.png`});await pop.getByRole('button',{name:'Đóng',exact:true}).click();
 }
 assert.deepEqual(errors,[]);
 console.log('PASS scene sketches: preview/keep/discard, regenerate preserves old selection, explicit replacement, lost-response inspect no extra call, reload, ID/order/stale, timeout, discard keeps unsaved text, missing image permits handoff, 3 widths');
 await context.close();await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
