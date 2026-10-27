// Synthetic API/SQLite and fake writer only. A fresh ui_workspace_fixture is required.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');const {randomUUID:uuid}=require('node:crypto');
(async()=>{
 const directory=process.env.FIRSTFRAME_QA_DIRECTORY;assert.ok(directory&&path.basename(directory).startsWith('firstframe-workspace-'));
 const seed=JSON.parse(await fs.readFile(path.join(directory,'seed.json'),'utf8'));
 const browser=await chromium.launch({headless:true,channel:'chrome'}),context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 await context.addInitScript(()=>{try{localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'save',projectId:null}));}catch{}});
 const api='http://127.0.0.1:8034',url=`/api/projects/${seed.id}`;
 const req=async(route,method='GET',data)=>{const r=await context.request.fetch(api+route,{method,data});assert.equal(r.status(),200,await r.text());return r.json()};
 const read=()=>req(url),payload=p=>Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(k=>[k,p[k]]));
 let p=await req(url+'/scene-outline','POST',{revision:seed.revision,source_version_id:'current'});
 p=await req(url,'PUT',{...payload(p),scene_outline:{id:p.scene_outline.id,version:p.scene_outline.version,scenes:[0,1].map(()=>({id:uuid(),title:'Cảnh trùng tên',action:'Cha đặt thư. Con gái chưa mở.'}))}});
 p=await req(url+'/screenplay','POST',{revision:p.revision,request_id:uuid()});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:3034');
 const area=page.locator('.screenplay'),main=area.locator('.screenplay-columns > .screenplay-scene'),panel=area.locator('.screenplay-proposals'),latest=()=>panel.locator(':scope > .screenplay-proposal').first();
 const save=async()=>{await area.getByRole('button',{name:'Lưu kịch bản',exact:true}).click();await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.',{exact:true}).waitFor()};
 const generate=async()=>{await panel.getByRole('button',{name:'Nhờ FirstFrame viết thử cảnh này',exact:true}).click();await latest().getByRole('button',{name:'Chỉnh phương án',exact:true}).waitFor()};
 const nav=area.getByRole('navigation',{name:'Các cảnh kịch bản'});
 await main.getByRole('button',{name:'Thêm hành động',exact:true}).click();await main.getByLabel('Nội dung hành động',{exact:true}).fill('Tác giả viết trước khi gọi AI.');
 await generate();p=await read();const original=structuredClone(p.screenplay),proposal=p.screenplay_proposals.at(-1);
 assert.equal(proposal.source_screenplay.scenes[0].blocks[0].text,'Tác giả viết trước khi gọi AI.');assert.deepEqual(p.screenplay,original);
 const originalOutput=structuredClone(proposal.scene);
 await latest().getByRole('button',{name:'Chỉnh phương án',exact:true}).click();
 await latest().getByLabel('Nội dung hành động',{exact:true}).fill('  Cha đặt thư.\n\nCon gái nhìn, chưa mở.  ');
 assert.ok(await latest().getByRole('button',{name:'Dùng phương án cho cảnh này',exact:true}).isDisabled());
 await latest().getByRole('checkbox').check();await latest().getByRole('button',{name:'Dùng phương án cho cảnh này',exact:true}).click();
 assert.equal(await main.getByLabel('Nội dung hành động',{exact:true}).inputValue(),'  Cha đặt thư.\n\nCon gái nhìn, chưa mở.  ');
 assert.deepEqual((await read()).screenplay,original);
 assert.equal(await latest().getByRole('button',{name:'Lưu sửa và bỏ phương án này',exact:true}).count(),0);
 await area.getByRole('button',{name:'Hoàn tác dùng phương án',exact:true}).click();assert.equal(await main.getByLabel('Nội dung hành động',{exact:true}).inputValue(),'Tác giả viết trước khi gọi AI.');
 await latest().getByRole('button',{name:'Dùng phương án cho cảnh này',exact:true}).click();await save();
 p=await read();assert.equal(p.screenplay_proposals.at(-1).status,'applied');assert.deepEqual(p.screenplay_proposals.at(-1).scene,originalOutput);
 assert.equal(p.screenplay_proposals.at(-1).preview_scene.blocks[0].text,'  Cha đặt thư.\n\nCon gái nhìn, chưa mở.  ');
 assert.deepEqual(p.screenplay.scenes[1],original.scenes[1]);
 // A new proposal is not adopted and becomes stale when a neighboring scene changes.
 await generate();p=await read();const second=p.screenplay_proposals.at(-1),target=structuredClone(p.screenplay.scenes[0]);
 await nav.getByRole('button').nth(1).click();await main.getByRole('button',{name:'Thêm hành động',exact:true}).click();await main.getByLabel('Nội dung hành động',{exact:true}).fill('Cảnh sau đã đổi.');await save();
 await nav.getByRole('button').first().click();assert.ok(await latest().getByRole('button',{name:'Dùng phương án cho cảnh này',exact:true}).isDisabled());
 assert.match(await latest().innerText(),/Nguồn\/ngữ cảnh/);
 await latest().getByRole('button',{name:'Lưu sửa và bỏ phương án này',exact:true}).click();await latest().getByText(/đã bỏ/).waitFor();
 assert.deepEqual((await read()).screenplay.scenes[0],target);
 // Lost response retrieves the same saved output, never an automatic extra request.
 await req('/__test/control','POST',{lose_response_suffix:url+'/screenplay-proposals/stream'});
 await panel.getByRole('button',{name:'Nhờ FirstFrame viết thử cảnh này',exact:true}).click();await page.locator('.save-toolbar .error').waitFor();
 assert.ok(await panel.getByRole('button',{name:'Nhờ FirstFrame viết thử cảnh này',exact:true}).isDisabled());
 await panel.getByRole('button',{name:'Kiểm tra phương án đã lưu',exact:true}).click();await latest().getByRole('button',{name:'Chỉnh phương án',exact:true}).waitFor();
 assert.equal((await req('/__test/state')).writing_requests,3);
 // Timeout is a saved failure and does not remove the author's work.
 await req('/__test/control','POST',{fail_writing:true});await panel.getByRole('button',{name:'Nhờ FirstFrame viết thử cảnh này',exact:true}).click();await page.locator('.save-toolbar .error').waitFor();
 await panel.getByRole('button',{name:'Kiểm tra phương án đã lưu',exact:true}).click();await latest().getByText(/Lượt viết lỗi/).waitFor({state:'attached'});await latest().locator(':scope > summary').click();await latest().getByText(/Lượt viết lỗi/).waitFor();
 assert.equal((await read()).screenplay_proposals.at(-1).status,'failed');
 await main.getByLabel('Nội dung hành động',{exact:true}).fill('Tác giả vẫn tự sửa sau lỗi.');await save();
 await page.reload();await main.getByLabel('Nội dung hành động',{exact:true}).waitFor();assert.equal(await main.getByLabel('Nội dung hành động',{exact:true}).inputValue(),'Tác giả vẫn tự sửa sau lỗi.');
 p=await read();assert.equal(p.screenplay_proposals.length,4);assert.equal((await req('/__test/state')).writing_requests,4);
 assert.deepEqual(p.feedback_source,seed.feedback_source);
 // Closed/open proposal/source views do not write or generate.
 const before=await req('/__test/state');await latest().locator(':scope > summary').click();await latest().locator(':scope > summary').click();
 assert.equal((await req('/__test/state')).calls.filter(c=>c.method!=='GET').length,before.calls.filter(c=>c.method!=='GET').length);
 for(const width of [1280,390,320]){await page.setViewportSize({width,height:900});await panel.scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`/tmp/firstframe-m3-writing-${width}.png`});}
 assert.deepEqual(errors,[]);console.log('PASS M3 writing: save-before-call, separate/editable preview, replace confirmation, buffer-only use/undo, explicit save, raw output preserved, neighbor stale, discard, lost response no retry, timeout/manual save, reload, 3 widths');
 await context.close();await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
