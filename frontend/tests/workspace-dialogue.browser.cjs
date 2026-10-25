const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { setup, project, answer, reveal } = require('./onboarding.browser.cjs');
const engine = process.env.TOUR_BROWSER || 'chrome';
const output = process.env.TOUR_SCREENSHOTS || `/tmp/firstframe-dialogue-${engine}`;
const click = async (page, name) => {
 await reveal(page,page.getByRole('button',{name,exact:true,includeHidden:true}));
 await page.getByRole('button',{name,exact:true}).click();
};
const writes = mock => mock.calls.filter(c=>c.method!=='GET');
const plans = mock => mock.calls.filter(c=>c.pathname.endsWith('/plan/stream'));
const draft = { title:'Bát cơm trước cửa',logline:'Người cha mang cơm nhưng ngại gõ cửa.',sections:[
 {title:'Beginning',purpose:'Setup',content:'Cha mang bát cơm. Ông dừng trước cửa phòng.'},
 {title:'Middle',purpose:'Choice',content:'Ông đưa tay định gõ. Bàn tay lại buông xuống.'},
 {title:'Ending',purpose:'Cut',content:'Ông đặt bát cơm trước cửa. Khung hình dừng ở bát cơm.'},
]};
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const browser=await ({chrome:chromium,firefox,webkit})[engine].launch({headless:true,...(engine==='chrome'?{channel:'chrome'}:{})});
 const report={engine,version:browser.version(),results:[]};
 try {
  for(const viewport of [{width:1440,height:1000},{width:390,height:844}]) {
   let t;
   try {
    t=await setup(browser,{viewport,projects:[{...project(),idea:'Một người cha đứng trước cửa phòng con.'}]});
    const {page,mock}=t;
    await click(page,'Cùng làm rõ ý tưởng');
    await page.waitForFunction(()=>document.activeElement.id==='answer-0');
    assert.equal(await page.locator('[data-answer-open]').count(),6);
    assert.equal(await page.locator('[data-tour-action="plan"]').count(),0);
    for(let i=0;i<6;i++) await answer(page,i,`Lựa chọn riêng ${i+1}.`);
    await click(page,'Tiếp tục');
    const originalAnswers=await page.locator('.clarification-answer p').allTextContents();
    assert.equal(originalAnswers.length,6);
    assert.equal(plans(mock).length,0);
    await click(page,'Hỏi thêm từ câu trả lời của tôi');
    await page.locator('#answer-6').waitFor();
    assert.equal(await page.locator('[data-answer-open]').count(),8);
    assert.deepEqual(await page.locator('.clarification-answer p').allTextContents(),originalAnswers);
    assert.equal(plans(mock).length,0,'follow-up cannot start a plan');
    await answer(page,6,'Giữ sự lặng lẽ.'); await answer(page,7,'Dừng khi đặt bát cơm.');
    await click(page,'Tiếp tục');
    await click(page,'Xem lại các lựa chọn');
    await page.getByRole('heading',{name:'FirstFrame · Bạn đồng ý để tôi tạo bản phát triển?',exact:true}).waitFor();
    assert.equal(await page.locator('.consent-choices > details').count(),8);
    assert.equal(plans(mock).length,0,'review is not consent');
    await click(page,'Chưa, tôi muốn sửa tiếp');
    assert.equal(await page.locator('[data-tour-action="plan"]').count(),0);
    await click(page,'Xem lại các lựa chọn');
    await click(page,'Sửa câu trả lời 1');
    await page.locator('#answer-0').fill('Mới nhất: hai cha con vẫn thương nhau, không tranh cãi.');
    assert.equal(await page.locator('[data-tour-action="plan"]').count(),0,'editing revokes the reviewed snapshot');
    await click(page,'Xong'); await click(page,'Xem lại các lựa chọn');
    assert.match(await page.locator('.consent-choices').innerText(),/Mới nhất: hai cha con vẫn thương nhau/);
    assert.equal(plans(mock).length,0);
    let release;mock.hold=new Promise(resolve=>release=resolve);mock.planPatch={draft};
    await page.locator('[data-tour-action="plan"]').click();
    await page.waitForFunction(()=>document.activeElement.id==='workspace-operation');
    assert.equal(await page.locator('.plan-process-group').count(),3);
    assert.equal(await page.locator('.plan-process-children > li').count(),8);
    assert.equal(await page.locator('[data-progress-stage="planning"]').getAttribute('data-progress-status'),'pending');
    assert.equal(plans(mock).length,1);
    assert.equal(mock.projects[0].answers[0],'Mới nhất: hai cha con vẫn thương nhau, không tranh cãi.');
    assert.deepEqual(Object.keys(plans(mock)[0].body),['revision']);
    await page.screenshot({path:path.join(output,`pending-${viewport.width}.png`)});
    mock.hold=null;release();
    await page.locator('.story-draft-path').waitFor();
    await page.waitForFunction(()=>document.activeElement.id==='workspace-draft');
    await page.waitForFunction(()=>document.querySelector('.workspace-stage-nav [aria-current="step"]')?.textContent.includes('Story plan'));
    assert.equal(await page.locator('.plan-process-group.is-completed').count(),3);
    assert.equal(await page.locator('[data-progress-status="pending"]').count(),0);
    assert.deepEqual(mock.projects[0].draft,draft);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.equal(plans(mock).length,1);
    await page.screenshot({path:path.join(output,`done-${viewport.width}.png`)});
    report.results.push({width:viewport.width,passed:true,calls:writes(mock)});await t.close();
   } catch(error) {
    if(t){await t.page.screenshot({path:path.join(output,`failure-${viewport.width}.png`)}).catch(()=>{});await t.context.close();}
    report.results.push({width:viewport.width,passed:false,error:error.stack});console.error(error);
   }
  }
 } finally {await browser.close();await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2));}
 console.log(JSON.stringify(report.results.map(r=>({width:r.width,passed:r.passed}))));process.exitCode=report.results.some(r=>!r.passed)?1:0;
})().catch(e=>{console.error(e);process.exitCode=1});
