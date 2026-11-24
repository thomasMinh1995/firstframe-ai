// Uses intercepted project requests; no real project is changed.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {setup,fullProject,answer,confirmPlan}=require('./onboarding.browser.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  for(const viewport of [{width:1280,height:900},{width:897,height:771},{width:390,height:844}]){
   const project=fullProject('p1');
   project.analysis.missing_information=['Bạn muốn giữ điều gì?'];project.answers=['Giữ tiếng mưa.'];
   project.draft.sections=[{title:'Beginning',purpose:'Mở đầu',content:'Một người đứng dưới mưa. Cô mở chiếc ô.'}];
   const t=await setup(browser,{projects:[project],viewport});const {page,mock}=t;
   const nav=page.locator('.workspace-stage-nav');
   const go=label=>nav.getByRole('button',{name:new RegExp('^'+label+'(?: |$)')}).click();
   const stages=[['Ý tưởng','idea'],['Làm rõ','choices'],['Story plan','draft'],['Dàn cảnh','outline'],['Kịch bản','script']];
   await go('Ý tưởng');await page.locator('#project-title').fill('Tên đang sửa');
   const calls=structuredClone(mock.calls);
   for(const [label,id] of [...stages,...stages.slice().reverse()]){
    await go(label);
    assert.equal(await page.locator(`#workspace-${id}`).isVisible(),true);
    assert.match(await nav.locator('[aria-current="step"]').innerText(),new RegExp(label));
    const shown=await page.locator('.project-fields > [data-workspace-stage]').evaluateAll(nodes=>nodes.filter(n=>n.getClientRects().length).map(n=>n.dataset.workspaceStage));
    assert.deepEqual(shown,viewport.width>760?[`workspace-${id}`]:stages.map(s=>`workspace-${s[1]}`));
   }
   assert.equal(await page.locator('#project-title').inputValue(),'Tên đang sửa');
   assert.deepEqual(mock.calls,calls);
   // Tour reveals every hidden stage without writing to the project API.
   await page.getByRole('button',{name:'Hướng dẫn sử dụng',exact:true}).click();
   await page.getByText('Bước 1/7',{exact:true}).waitFor();
   for(let n=2;n<=6;n++){
    await page.getByRole('button',{name:'Tiếp',exact:true}).click();
    await page.getByText(`Bước ${n}/7`,{exact:true}).waitFor();
    assert.equal(await page.locator(`#workspace-${stages[n-2][1]}`).isVisible(),true);
   }
   await page.getByRole('button',{name:'Tiếp',exact:true}).click();
   await page.getByText('Bước 7/7',{exact:true}).waitFor();
   await page.getByRole('button',{name:'Hoàn tất hướng dẫn',exact:true}).click();
   assert.deepEqual(mock.calls,calls);
   await go('Story plan');await page.screenshot({path:`/private/tmp/desktop-panels-${viewport.width}.png`});
   await t.close();console.log(`PASS ${viewport.width}: five menus, retained input, seven tour steps, no API writes`);
  }
  const initial={...fullProject('p1'),analysis:null,draft:null};
  const t=await setup(browser,{projects:[initial],viewport:{width:1280,height:900}});
  const {page,mock}=t;
  let finish;mock.hold=new Promise(resolve=>{finish=resolve;});
  await page.getByRole('button',{name:'Cùng làm rõ ý tưởng',exact:true}).click();
  await page.locator('[data-desktop-stage="workspace-choices"]').waitFor();
  assert.equal(await page.locator('#workspace-operation').isVisible(),true);
  const prepareGroup=page.locator('.process-group').first();
  if(await prepareGroup.locator('button').getAttribute('aria-expanded')==='false')await prepareGroup.locator('button').click();
  assert.equal(await prepareGroup.locator('[data-progress-stage="prepare"]').isVisible(),true,'desktop menu CSS must not hide subprocess rows');
  await page.locator('.workspace-stage-nav').getByRole('button',{name:/^Ý tưởng/}).click();
  assert.equal(await page.locator('#workspace-operation').isVisible(),false);
  await page.locator('.workspace-stage-nav').getByRole('button',{name:/^Làm rõ/}).click();
  assert.equal(await page.locator('#workspace-operation').isVisible(),true);
  finish();mock.hold=null;
  await page.locator('#answer-0').waitFor();
  for(let i=0;i<6;i++)await answer(page,i,'Giữ tiếng mưa.');
  await page.locator('.clarification-current').getByRole('button',{name:'Tiếp tục',exact:true}).click();
  await page.locator('#clarification-complete').waitFor();
  await confirmPlan(page);
  await page.locator('.working-draft').waitFor();
  assert.equal(await page.locator('main').getAttribute('data-desktop-stage'),'workspace-draft');
  assert.equal(await page.locator('[data-workspace-stage="workspace-choices"]').isVisible(),false);
  await t.close();console.log('PASS automatic clarify/plan navigation and progress isolation');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
