const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { setup, fullProject, answer, edit, reveal, confirmPlan } = require('./onboarding.browser.cjs');
const engine = process.env.TOUR_BROWSER || 'chrome';
const output = process.env.TOUR_SCREENSHOTS || `/tmp/firstframe-focus-${engine}`;
const click = async (page, name) => {
  await reveal(page, page.getByRole('button', { name, exact: true, includeHidden: true }));
  await page.getByRole('button', { name, exact: true }).click();
};
const draft = { title: 'Cuộc gọi nhỡ', logline: 'Một người con chần chừ gọi lại.', sections: [
  { title: 'Beginning', purpose: 'Setup', content: 'Anh nhìn điện thoại. Anh xóa tin nhắn.' },
  { title: 'Middle', purpose: 'Choice', content: 'Anh bấm gọi.' },
  { title: 'Ending', purpose: 'Cut', content: 'Đầu dây bắt máy. Anh buông mép bàn; cắt khi vừa kết nối.' },
] };
const context = { idea: 'Một người thấy cuộc gọi nhỡ.', constraints: [], clarifications: [
  { question: 'Quan hệ?', answer: 'Hai cha con vẫn thương nhau.', input_index: 0 },
  { question: 'Cách kể?', answer: 'Chỉ hành động; dừng khi vừa bắt máy.', input_index: 1 },
], pending_questions: [] };
const message = 'Card 5 · Kết thúc · 2: “Anh buông mép bàn; cắt khi vừa kết nối.” ↔ Card 4 · Kết thúc · 1: “Đầu dây bắt máy.”\nLàm rõ 2: “Chỉ hành động; dừng khi vừa bắt máy.”\nGiữ cử chỉ buông tay đúng điểm dừng đã chọn.';
function fixture() {
 const p = { ...fullProject('focus'), title: 'QA bố cục', idea: context.idea, answers: context.clarifications.map(a => a.answer), draft,
  analysis: { artifact_id: 'a', summary: 'Một cuộc gọi nhỡ.', missing_information: context.clarifications.map(a => a.question), notes: [] },
  author_context: context, feedback_is_current: true,
  feedback: { artifact_id: 'f', passed: true, rubric_scores: {}, findings: [{ criterion_id: 'strength-1', message, severity: 'info', score: null }] },
  feedback_source: { project_id: 'focus', artifact_id: 'f', revision: 0, content_key: 'qa', context, draft } };
 return structuredClone(p);
}
(async () => {
 await fs.mkdir(output, { recursive: true });
 const browser = await ({ chrome: chromium, firefox, webkit })[engine].launch({ headless: true, ...(engine === 'chrome' ? { channel: 'chrome' } : {}) });
 const report = { engine, version: browser.version(), results: [] };
 try {
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
   let t;
   try {
    t = await setup(browser, { viewport, projects: [fixture()] });
    const { page, mock } = t;
    const stage = id => page.locator(`[data-workspace-stage="workspace-${id}"]`);
    assert.equal(await stage('idea').getAttribute('open'), null);
    assert.equal(await stage('choices').getAttribute('open'), null);
    assert.equal(await page.locator('.workspace-library').getAttribute('open'), null);
    const nav = page.getByRole('navigation', { name: 'Hành trình câu chuyện' });
    await nav.getByRole('button', { name: /^Làm rõ/ }).click();
    await page.waitForFunction(() => document.querySelector('[aria-current="step"]').textContent.includes('Làm rõ'));
    await click(page, 'Sửa câu trả lời 1');
    assert.equal(await page.locator('.clarification-thread > li').first().locator('#answer-0').count(), 1, 'editing keeps the first turn in place');
    await page.locator('#answer-0').fill('Chữ đang gõ, chưa lưu.');
    await stage('choices').locator(':scope > summary').click();
    await nav.getByRole('button', { name: /^Story plan/ }).click();
    await nav.getByRole('button', { name: /^Làm rõ/ }).click();
    assert.equal(await page.locator('#answer-0').inputValue(), 'Chữ đang gõ, chưa lưu.');
    await click(page, 'Hủy');
    assert.equal(await page.locator('#answer-0-value').innerText(), context.clarifications[0].answer);
    assert.equal(mock.calls.filter(c => c.method !== 'GET').length, 0);
    await nav.getByRole('button', { name: /^Story plan/ }).click();
    await page.waitForFunction(() => document.querySelector('[aria-current="step"]').textContent.includes('Story plan'));
    await click(page, 'Xem góp ý cho card 5');
    const inspector = page.getByRole('complementary', { name: 'Góp ý cạnh Card 5 · Kết thúc · 2' });
    await inspector.waitFor();
    assert.match(await inspector.innerText(), /Dựa trên Làm rõ 2/);
    assert.match(await inspector.innerText(), /Giữ cử chỉ buông tay/);
    await inspector.locator('summary').filter({ hasText: 'Xem nguồn đối chiếu' }).click();
    assert.match(await inspector.innerText(), /Chỉ hành động; dừng khi vừa bắt máy/);
    await (await edit(page, 'section-2-part-1')).fill('Anh thả tay; cắt khi kết nối.');
    assert.match(await inspector.innerText(), /Góp ý cũ thuộc bản trước/);
    await inspector.getByRole('button', { name: 'Đóng góp ý cạnh card', exact: true }).click();
    await page.waitForFunction(() => document.activeElement?.getAttribute('aria-label') === 'Xem góp ý cho card 5');
    assert.equal(await page.locator('#section-2-part-1').inputValue(), 'Anh thả tay; cắt khi kết nối.');
    await click(page, 'Xem góp ý cho card 5');
    await page.locator('#section-2-part-1').press('Escape');
    assert.match(await inspector.innerText(), /Dựa trên Làm rõ 2/);
    assert.equal(mock.calls.filter(c => c.method !== 'GET').length, 0, 'all view actions and canceled edit are local');
    await (await edit(page, 'section-2-part-1')).fill('Anh buông tay khỏi mép bàn; cắt khi vừa kết nối.');
    await page.locator('[data-card-id="section-2-part-1"] .story-field-actions').getByRole('button', { name: 'Xong', exact: true }).click();
    assert.equal(await page.locator('#save-status').innerText(), 'Có thay đổi chưa lưu');
    const bar = await page.locator('.save-toolbar').boundingBox();
    assert.ok(bar.y >= 0 && bar.y + bar.height <= viewport.height, 'save stays in view near selected card');
    mock.failSave = true; await click(page, 'Lưu thay đổi'); await page.locator('.save-toolbar .error').waitFor();
    assert.match(await page.locator('[data-card-id="section-2-part-1"]').innerText(), /Anh buông tay khỏi mép bàn/);
    mock.failSave = false; await click(page, 'Lưu thay đổi');
    await page.waitForFunction(() => document.getElementById('save-status').textContent === 'Đã lưu');
    const writes = mock.calls.filter(c => c.method !== 'GET');
    assert.deepEqual(Object.keys(writes.at(-1).body).sort(), ['answers','constraints','draft','idea','response_language','revision','title']);
    assert.equal(writes.length, 2, 'one failed save and one explicit successful save');
    assert.deepEqual(mock.projects[0].answers, context.clarifications.map(a => a.answer));
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.getByRole('button', { name: 'Xem góp ý cho card 5', exact: true }).click();
    await page.screenshot({ path: path.join(output, `focus-${viewport.width}.png`) });
    report.results.push({ name: 'editing', width: viewport.width, passed: true }); await t.close();
    t = await setup(browser, { viewport, projects: [{ ...fixture(), analysis: null, draft: null, feedback: null,
      feedback_source: null, answers: [], feedback_is_current: false }] });
    await click(t.page, 'Cùng làm rõ ý tưởng');
    await t.page.waitForFunction(() => document.activeElement.id === 'answer-0');
    const count = await t.page.locator('[data-answer-open]').count();
    for (let i=0; i<count; i++) await answer(t.page, i, 'Giữ sự lặng lẽ.');
    await click(t.page, 'Tiếp tục');
    assert.equal(await t.page.locator('[data-workspace-stage="workspace-idea"]').getAttribute('open'), null);
    await confirmPlan(t.page);
    await t.page.waitForFunction(() => document.activeElement.id === 'workspace-draft');
    await t.page.waitForFunction(() => document.querySelector('.workspace-stage-nav [aria-current="step"]')?.textContent.includes('Story plan'));
    assert.equal(await t.page.locator('[data-workspace-stage="workspace-choices"]').getAttribute('open'), null);
    report.results.push({ name: 'new-flow', width: viewport.width, passed: true }); await t.close();
   } catch (e) {
    if (t) { await t.page.screenshot({ path: path.join(output, `failure-${viewport.width}.png`) }).catch(() => {}); await t.context.close(); }
    report.results.push({ width: viewport.width, passed: false, error: e.stack }); console.error(e);
   }
  }
 } finally { await browser.close(); await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2)); }
 console.log(JSON.stringify(report)); process.exitCode = report.results.some(r => !r.passed) ? 1 : 0;
})().catch(e => { console.error(e); process.exitCode = 1; });
