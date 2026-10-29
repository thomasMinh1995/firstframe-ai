// Real local UI; every project/image request is intercepted. No model or saved user data is used.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {randomUUID:uuid}=require('node:crypto');
const {setup,fullProject}=require('./onboarding.browser.cjs');
const fixture=require('../../docs/evaluations/m3-scene-review-qwen7b-2026-10-27/inputs.json')[0].project;
const base=process.env.TOUR_TEST_URL || 'http://localhost:3033';
const pixel=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3XcAAAAASUVORK5CYII=','base64');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  for(const width of [1280,897,390,320]){
   const p=structuredClone(fixture);p.id='library-test';p.title='Thư viện kiểm thử';
   const script=p.screenplay;script.version=3;
   const originalSource=structuredClone(script.source_outline);
   script.scenes.forEach((s,i)=>{s.heading='NỘI. CÙNG TÊN — CHIỀU';s.blocks[0].text=('Nội dung dài của cảnh '+(i+1)+'.\n').repeat(12);});
   const old=structuredClone(script);old.version=2;old.source_outline.version=2;
   old.source_outline.scenes[0].action='NGUỒN LỊCH SỬ PHẢI GIỮ RIÊNG';
   old.scenes[0].blocks[0].text='Nội dung lịch sử.';
   p.screenplay_versions=[{id:uuid(),created_at:p.updated_at,screenplay:old}];
   p.scene_sketches=script.source_outline.scenes.map(s=>({id:uuid(),scene_id:s.id,created_at:p.updated_at,source_revision:p.revision,
    source_content:'source',source_outline:structuredClone(script.source_outline),instructions:'',prompt:'',prompt_version:'v1',provider:'fake',model:'fake',parameters:{},status:'ready',asset_id:uuid(),error:null,duration_seconds:1}));
   p.selected_scene_sketches=Object.fromEntries(p.scene_sketches.map(s=>[s.scene_id,s.id]));
   const empty=fullProject('empty');
   const t=await setup(browser,{projects:[p,empty],viewport:{width,height:1000}});const {page,mock,context}=t;
   let missing=false,failRestore=true;
   await context.route('**/scene-sketches/*/image',route=>missing?route.fulfill({status:404}):route.fulfill({contentType:'image/png',body:pixel}));
   await context.route('**/screenplay-versions/*/restore',route=>{
    const body=route.request().postDataJSON(),project=mock.projects.find(x=>x.id===p.id);
    mock.calls.push({method:'POST',pathname:new URL(route.request().url()).pathname,body});
    if(failRestore)return route.fulfill({status:409,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:JSON.stringify({detail:'Bản đã thay đổi; chưa khôi phục.'})});
    assert.equal(body.revision,project.revision);
    project.screenplay_versions.push({id:uuid(),created_at:project.updated_at,screenplay:structuredClone(project.screenplay)});
    project.screenplay=structuredClone(old);project.screenplay.version=4;project.revision++;
    return route.fulfill({contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:JSON.stringify(project)});
   });
   await page.goto(`${base}/library?project=${p.id}`);
   const tabs=page.getByRole('navigation',{name:'Loại nội dung đã lưu'});
   await page.getByRole('heading',{name:'Bản đã lưu',exact:true}).waitFor();
   assert.equal(await tabs.getByRole('button',{name:'Kịch bản',exact:true}).getAttribute('aria-pressed'),'true');
   const scenes=page.locator('.library-scene');assert.equal(await scenes.count(),script.scenes.length);
   assert.equal(await page.locator('.library-attachment').count(),script.scenes.length);
   assert.equal(await page.locator('.library-attachment img').count(),script.scenes.length);
   // Identical scene headings still open the correct source by immutable scene ID.
   await scenes.nth(1).locator('.library-script-hit').click();
   const source=page.locator('.library-source:visible,.library-mobile-source:visible');
   assert.match(await source.innerText(),new RegExp('Cảnh 2'));
   assert.ok((await source.innerText()).includes(originalSource.scenes.find(s=>s.id===script.scenes[1].source_scene_id).action));
   await source.getByRole('button',{name:'Đóng Dàn cảnh',exact:true}).press('Escape');
   await page.waitForFunction(()=>document.activeElement?.classList.contains('library-script-hit'));
   assert.equal(await source.count(),0);
   const image=scenes.first().getByRole('button',{name:'Xem hình phác cảnh 1',exact:true});await image.click();
   const preview=page.getByRole('dialog',{name:'Hình phác · Cảnh 1',exact:true});assert.equal(await preview.evaluate(n=>n.matches(':modal')),true);
   await preview.press('Escape');await preview.waitFor({state:'detached'});await image.waitFor();
   await page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='Xem hình phác cảnh 1');
   // Historical script reads its own source and never borrows mismatched current images.
   await page.getByRole('complementary',{name:'Các phiên bản kịch bản'}).getByRole('button',{name:/Phiên bản 2/}).click();
   await page.getByText('Nội dung lịch sử.',{exact:true}).waitFor();
   assert.match(await source.innerText(),/NGUỒN LỊCH SỬ PHẢI GIỮ RIÊNG/);
   assert.equal(await page.locator('.library-attachment img').count(),0);
   assert.equal(await page.locator('.library-image-empty').count(),script.scenes.length);
   await tabs.getByRole('button',{name:'Dàn cảnh',exact:true}).click();await page.getByRole('heading',{name:'Dàn cảnh đang lưu',exact:true}).waitFor();
   await tabs.getByRole('button',{name:'Story plan',exact:true}).click();await page.getByRole('heading',{name:'Story plan đang lưu',exact:true}).waitFor();
   await tabs.getByRole('button',{name:'Kịch bản',exact:true}).click();
   assert.equal(mock.calls.filter(c=>c.method!=='GET').length,0,'browsing, versions, sources and images must never write/call AI');
   assert.deepEqual(mock.projects[0].screenplay.source_outline,originalSource);
   // Restore failure keeps the selected history and source. Successful restore preserves all other stages.
   const outline=structuredClone(mock.projects[0].scene_outline),draft=structuredClone(mock.projects[0].draft);
   await page.getByRole('button',{name:'Khôi phục kịch bản này',exact:true}).click();await page.getByText('Bản đã thay đổi; chưa khôi phục.',{exact:true}).waitFor();
   assert.equal(mock.projects[0].screenplay.version,3);await page.getByText('Nội dung lịch sử.',{exact:true}).waitFor();
   failRestore=false;await page.getByRole('button',{name:'Khôi phục kịch bản này',exact:true}).click();
   await page.getByRole('complementary',{name:'Các phiên bản kịch bản'}).getByRole('button',{name:/Phiên bản 4/}).waitFor();
   await page.waitForFunction(()=>document.querySelector('.library-versions button[aria-pressed="true"]')?.textContent.includes('Phiên bản 4'));
   assert.deepEqual(mock.projects[0].scene_outline,outline);assert.deepEqual(mock.projects[0].draft,draft);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   if(width===1280||width===390)await page.screenshot({path:`/private/tmp/firstframe-saved-library-${width}.png`,fullPage:true});
   await page.locator('#project-picker').selectOption('empty');await page.getByRole('heading',{name:'Chưa có kịch bản đã lưu',exact:true}).waitFor();
   assert.equal(await page.locator('.library-scene,.library-attachment').count(),0,'project switch clears old script/images');
   // An unavailable image is reported without losing the scene text.
   missing=true;
   for(const sketch of mock.projects[0].scene_sketches){sketch.id=uuid();mock.projects[0].selected_scene_sketches[sketch.scene_id]=sketch.id;}
   await page.locator('#project-picker').selectOption(p.id);await page.getByRole('button',{name:'Phiên bản 3',exact:false}).click();
   await page.getByText(/Tệp ảnh thiếu hoặc lỗi/).first().waitFor();assert.equal(await scenes.count(),script.scenes.length);
   assert.deepEqual(t.errors,[]);await t.close();
   console.log(`PASS ${width}: script-first layout, every attachment, image dialog/focus, source IDs/history, missing/mismatched images, no browsing writes, restore failure/success, project reset and long content`);
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
