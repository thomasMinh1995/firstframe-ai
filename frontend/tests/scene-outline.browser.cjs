// Real disposable API/SQLite from ui_workspace_fixture.py; no real AI calls.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;
 assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'),'Require disposable DB fixture');
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 await context.addInitScript(()=>{try{localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'new-project',projectId:null}));}catch{}});
 const errors=[];context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 const api='http://127.0.0.1:8034',base='http://127.0.0.1:3034';
 const read=async route=>{const r=await context.request.get(api+route);assert.equal(r.status(),200);return r.json()};
 assert.ok(Array.isArray((await read('/__test/state')).provider_stages));
 const before=await read('/__test/state');
 const page=await context.newPage();await page.goto(base);await page.locator('#workspace-outline').waitFor();
 assert.equal(await page.locator('#project-picker').inputValue(),seed.id);
 await page.getByRole('button',{name:'Bắt đầu dàn cảnh từ bản đã chọn',exact:true}).click();
 const area=page.locator('.scene-outline');await area.getByRole('button',{name:'Tự thêm cảnh',exact:true}).waitFor();
 const add=()=>area.getByRole('button',{name:'Tự thêm cảnh',exact:true}).click();
 const pop=()=>page.locator('.scene-popover:popover-open');
 await add();await pop().getByLabel('Tên cảnh',{exact:true}).fill('Lá thư trên bàn');
 await pop().getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).fill('  Cha đặt thư.\n\nCon gái nhìn, chưa mở.  ');
 await pop().getByRole('tab',{name:'Dàn cảnh',exact:true}).click();
 assert.equal(await pop().locator('[role=tabpanel]:visible textarea').count(),2);
 await pop().getByLabel('Bạn muốn người xem cảm nhận điều gì? · tùy chọn',{exact:true}).fill('Còn xa cách nhưng quan tâm.');
 await pop().getByRole('tab',{name:'Phác hình',exact:true}).click();assert.match(await pop().innerText(),/Không cần ảnh để lưu/);
 await pop().getByRole('tab',{name:'Nội dung',exact:true}).click();assert.equal(await pop().getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).inputValue(),'  Cha đặt thư.\n\nCon gái nhìn, chưa mở.  ');
 await pop().getByLabel('Tên cảnh',{exact:true}).press('Escape');assert.equal(await pop().count(),0);
 assert.equal((await read(`/api/projects/${seed.id}`)).scene_outline.scenes.length,0);
 await area.locator('[data-select-scene]').first().click();assert.equal(await pop().getByLabel('Tên cảnh',{exact:true}).inputValue(),'Lá thư trên bàn');
 await pop().getByRole('button',{name:'Lưu thay đổi dàn cảnh',exact:true}).click();
 await page.getByText('Đã lưu thay đổi dàn cảnh và mọi sửa đang chờ trong dự án.',{exact:true}).waitFor();
 await pop().getByRole('button',{name:'Đóng',exact:true}).click();
 let stored=await read(`/api/projects/${seed.id}`);const firstId=stored.scene_outline.scenes[0].id;assert.equal(stored.scene_outline.version,2);
 await add();await pop().getByLabel('Tên cảnh',{exact:true}).fill('Ở cửa');await pop().getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).fill('Con gái đứng lại.');
 await pop().getByRole('button',{name:'Lên trước',exact:true}).click();await pop().getByRole('button',{name:'Đóng',exact:true}).click();
 assert.equal(await area.locator('[data-scene-id]').last().getAttribute('data-scene-id'),firstId);
 for(let i=3;i<=6;i++){await add();await pop().getByLabel('Tên cảnh',{exact:true}).fill('Cảnh '+i);await pop().getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).fill('Một hành động nhỏ '+i+'.');await pop().getByRole('button',{name:'Đóng',exact:true}).click();}
 assert.equal(await area.locator('.story-path-lines > path').count(),5);await area.scrollIntoViewIfNeeded();await page.screenshot({path:'/tmp/firstframe-m2-g1-board.png',fullPage:true});
 await page.getByRole('button',{name:'Lưu thay đổi',exact:true}).click();await page.getByText('Đã lưu thay đổi.',{exact:true}).waitFor();
 await page.reload();await area.locator('[data-scene-id]').first().waitFor();assert.equal(await area.locator('[data-scene-id]').count(),6);
 const loaded=await read(`/api/projects/${seed.id}`);assert.equal(loaded.scene_outline.scenes[1].id,firstId);assert.equal(loaded.draft.title,seed.draft.title);assert.equal(loaded.feedback_source.content_key,seed.feedback_source.content_key);
 // Xóa + undo cannot overwrite a later edit to another scene.
 await area.getByRole('button',{name:'Xóa cảnh 1: Ở cửa',exact:true}).click();await area.locator('[data-select-scene]').first().click();await pop().getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).fill('Bản mới sau khi bỏ cảnh.');await pop().getByRole('button',{name:'Đóng',exact:true}).click();
 await area.getByRole('button',{name:'Hoàn tác thao tác cảnh',exact:true}).click();assert.match(await area.innerText(),/Không tự ghi đè/);assert.equal(await area.locator('[data-scene-id]').count(),5);
 // Conflict: window B saves a title while A holds scene and project-title buffers.
 const other=await context.newPage();await other.goto(base);await other.locator('#workspace-outline').waitFor();
 const title=page.locator('#project-title');await page.locator('[data-workspace-stage="workspace-idea"] > summary').click();await title.fill('Tên chưa lưu cửa sổ A');
 await other.locator('[data-workspace-stage="workspace-idea"] > summary').click();await other.locator('#project-title').fill('Tên cửa sổ B');await other.getByRole('button',{name:'Lưu thay đổi',exact:true}).click();await other.getByText('Đã lưu thay đổi.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Lưu thay đổi',exact:true}).click();await page.locator('.error').filter({hasText:'cửa sổ khác'}).waitFor();assert.equal(await title.inputValue(),'Tên chưa lưu cửa sổ A');await area.locator('[data-select-scene]').first().click();assert.equal(await pop().getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).inputValue(),'Bản mới sau khi bỏ cảnh.');await pop().getByRole('button',{name:'Đóng',exact:true}).click();
 // Lost HTTP response after successful save is handled without reloading the author buffer.
 await other.locator('.scene-outline [data-select-scene]').first().click();await other.locator('.scene-popover:popover-open').getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).fill('Bản cửa sổ B được lưu trước khi mất response.');await other.locator('.scene-popover:popover-open').getByRole('button',{name:'Đóng',exact:true}).click();
 await context.request.post(api+'/__test/control',{data:{lose_response_suffix:`/api/projects/${seed.id}`}});await other.getByRole('button',{name:'Lưu thay đổi',exact:true}).click();await other.locator('.error').filter({hasText:'phản hồi bị mất'}).waitFor();await other.locator('.scene-outline [data-select-scene]').first().click();assert.equal(await other.locator('.scene-popover:popover-open').getByLabel('Chuyện gì xảy ra trong cảnh này?',{exact:true}).inputValue(),'Bản cửa sổ B được lưu trước khi mất response.');await other.close();
 // Resume the real saved version in a fresh window, exercise empty/undo and handoff.
 const fresh=await context.newPage();await fresh.goto(base);const fa=fresh.locator('.scene-outline');await fa.locator('[data-scene-id]').first().waitFor();const count=await fa.locator('[data-scene-id]').count();while(await fa.locator('[data-scene-id]').count())await fa.getByRole('button',{name:/^Xóa cảnh/}).first().click();assert.equal(await fa.locator('[data-scene-id]').count(),0);await fa.getByRole('button',{name:'Hoàn tác thao tác cảnh',exact:true}).click();assert.equal(await fa.locator('[data-scene-id]').count(),1);assert.ok(count>=1);
 await fa.getByRole('button',{name:'Lưu bản dàn cảnh để viết tiếp',exact:true}).click();await fresh.getByText(/Đã lưu bản nguồn M2 phiên bản/).waitFor();assert.match(await fa.innerText(),/M3 viết kịch bản chưa triển khai/);assert.ok((await read(`/api/projects/${seed.id}`)).scene_handoff);
 // Verify responsive rendering against the same saved data; no mutations or AI.
 for(const width of [1280,768,390,320]){await fresh.setViewportSize({width,height:900});await fa.locator('[data-select-scene]').first().click();const dialog=fresh.locator('.scene-popover:popover-open');await dialog.getByRole('tab',{name:'Dàn cảnh',exact:true}).click();await dialog.getByRole('button',{name:'Thông tin: Kể cảnh này bằng hình ảnh',exact:true}).click();const rect=await dialog.boundingBox();assert.ok(rect.x>=0&&rect.x+rect.width<=width+1);assert.ok(await fresh.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));if(width===1280||width===390)await fresh.screenshot({path:`/tmp/firstframe-m2-g1-${width}.png`});await dialog.getByRole('button',{name:'Đóng',exact:true}).click();}
 assert.deepEqual((await read('/__test/state')).provider_stages,before.provider_stages);assert.deepEqual(errors,[]);
 console.log('PASS M2 manual real API: source/save/reopen, tabs/Esc buffers, ID/reorder, safe undo, two-window 409, lost response, empty outline, handoff, 4 widths, zero AI calls');
 await context.close();await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
