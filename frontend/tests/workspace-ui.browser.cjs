// Run against the local frontend with Playwright available through NODE_PATH.
// Project API requests are intercepted; real projects are never changed.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const {setup, fullProject, reveal} = require('./onboarding.browser.cjs');
(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    for (const viewport of [{width:1280,height:900},{width:390,height:844}]) {
      const project = fullProject('p1');
      project.analysis.missing_information = ['Ai xuất hiện?', 'Bạn muốn giữ điều gì?'];
      project.answers = ['', ''];
      project.draft.sections = [{title:'Beginning',purpose:'Mở câu chuyện',content:'Mở cửa. Nhìn mưa. Cầm ô. Bước ra. Dừng lại. Trở về.'}];
      project.versions = [{id:'v1',created_at:project.updated_at,idea:project.idea,constraints:[],questions:[],answers:[],draft:{...project.draft,title:'Bản cũ'},feedback:null,feedback_source:null}];
      const t = await setup(browser,{projects:[project],viewport});
      const {page,mock}=t;
      await page.locator('.working-draft').waitFor({state:'attached'});
      const navigate = label => page.locator('.workspace-stage-nav').getByRole('button',{name:new RegExp('^'+label+'(?: |$)')}).click();
      await navigate('Story plan');
      // Feedback opens as a modal; Escape and Close both return to the trigger.
      const trigger = page.getByRole('button',{name:'Xem góp ý cho card 3',exact:true});
      await trigger.click();
      const popup = page.getByRole('dialog',{name:'Góp ý cho card',exact:true});
      assert.equal(await popup.evaluate(n=>n.matches(':modal')),true);
      await popup.press('Escape'); await popup.waitFor({state:'detached'});
      await page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='Xem góp ý cho card 3');
      await trigger.click(); await popup.getByRole('button',{name:'Đóng góp ý cạnh card',exact:true}).click();
      await popup.waitFor({state:'detached'});
      await page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='Xem góp ý cho card 3');
      // Connectors use straight segments, including the row transition.
      const connectors=page.locator('.story-path-lines > path');
      await page.waitForFunction(()=>document.querySelectorAll('.story-path-lines > path').length===5);
      for (const d of await connectors.evaluateAll(nodes=>nodes.map(n=>n.getAttribute('d')))) assert.doesNotMatch(d,/[CQ]/);
      // Each submitted answer has a visible preparation state without an AI call.
      await navigate('Làm rõ');
      await reveal(page,page.locator('#answer-0'));
      await page.locator('#answer-0').fill('Một người thợ.');
      await page.locator('.clarification-current').getByRole('button',{name:'Tiếp tục',exact:true}).click();
      await page.getByText('FirstFrame đang chuẩn bị câu tiếp theo…',{exact:true}).waitFor();
      await page.locator('#answer-1').waitFor();
      assert.equal(mock.calls.some(c=>c.pathname.endsWith('/analyze')),false);
      await page.locator('#answer-1').fill('Giữ tiếng mưa.');
      await page.locator('.clarification-current').getByRole('button',{name:'Tiếp tục',exact:true}).click();
      await page.locator('#clarification-complete').waitFor();
      let finishAI;
      mock.hold = new Promise(resolve=>{finishAI=resolve;}); mock.failAI=true;
      await page.getByRole('button',{name:'Hỏi thêm từ câu trả lời của tôi',exact:true}).click();
      await page.getByText('FirstFrame đang suy nghĩ…',{exact:true}).waitFor();
      await page.screenshot({path:`/private/tmp/workspace-thinking-${viewport.width}.png`});
      finishAI();
      await page.locator('.save-toolbar .error[role="alert"]').waitFor();
      await page.locator('.firstframe-thinking').waitFor({state:'detached'});
      assert.equal(mock.projects[0].answers[0],'Một người thợ.');
      mock.hold=null; mock.failAI=false;
      // A failed save must block route changes and retain the editor buffer.
      await navigate('Ý tưởng');
      await reveal(page,page.locator('#project-title'));
      await page.locator('#project-title').fill('Tên mới chưa lưu');
      mock.failSave=true;
      await page.getByRole('link',{name:'Bản đã lưu',exact:true}).click();
      await page.getByText('Xung đột phiên bản. Bản sửa vẫn được giữ.',{exact:true}).waitFor();
      assert.equal(new URL(page.url()).pathname,'/');
      assert.equal(await page.locator('#project-title').inputValue(),'Tên mới chưa lưu');
      mock.failSave=false;
      // Navigating to the library saves pending edits and retains the chosen project.
      await page.getByRole('link',{name:'Bản đã lưu',exact:true}).click();
      await page.waitForURL('**/library?project=p1');
      await page.getByRole('heading',{name:'Bản đã lưu',exact:true}).waitFor();
      await page.getByRole('navigation',{name:'Loại nội dung đã lưu'}).getByRole('button',{name:'Story plan',exact:true}).click();
      assert.equal(mock.projects[0].answers[0],'Một người thợ.');
      assert.equal(await page.locator('.project-fields').count(),0);
      assert.equal(await page.locator('.workspace-stage-nav').count(),0);
      assert.match(await page.locator('.workspace-library').innerText(),/Các phiên bản đã giữ/);
      const version = page.locator('.version-history').filter({has:page.getByRole('heading',{name:'Các phiên bản đã giữ',exact:true})}).locator(':scope > details').first();
      await version.locator('summary').click();
      await version.getByRole('button',{name:'Dùng lại bản phát triển này',exact:true}).click();
      await page.getByText('Đã dùng lại nội dung bản phát triển. Các phiên bản trước vẫn được giữ.',{exact:true}).waitFor();
      assert.equal(mock.projects[0].draft.title,'Bản cũ');
      await page.screenshot({path:`/private/tmp/workspace-library-${viewport.width}.png`});
      await page.getByRole('link',{name:'← Quay lại viết',exact:true}).click();
      await page.waitForURL('**/?project=p1');
      await page.locator('.project-fields').waitFor();
      assert.equal(await page.locator('.workspace-library, .scene-history, .screenplay-history').count(),0);
      assert.equal(await page.locator('#project-picker').inputValue(),'p1');
      await navigate('Story plan');
      await page.getByRole('button',{name:'Xem góp ý cho card 3',exact:true}).click();
      await page.getByRole('dialog',{name:'Góp ý cho card'}).waitFor();
      await page.screenshot({path:`/private/tmp/workspace-popup-${viewport.width}.png`});
      await t.close();
      console.log(`PASS ${viewport.width}: modal, focus, straight arrows, thinking, library save/navigation/restore`);
    }
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
