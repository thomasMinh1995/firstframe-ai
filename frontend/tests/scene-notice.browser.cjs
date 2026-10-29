// Uses the shared intercepted project API; never modifies local projects.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { setup, fullProject, reveal } = require('./onboarding.browser.cjs');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const project = fullProject('p1');
    project.scene_outline = { id: '11111111-1111-4111-8111-111111111111', version: 1, scenes: [], source: {
      id: '22222222-2222-4222-8222-222222222222', project_revision: 0, version_id: 'current', draft: project.draft,
      response_language: 'vi', context: { idea: project.idea, constraints: [], clarifications: [], pending_questions: [] },
    } };
    const t = await setup(browser, { projects: [project] });
    const { page, mock } = t;
    // The real API preserves source metadata omitted from the save payload.
    mock.savePatch = { get scene_outline() {
      return { ...mock.projects[0].scene_outline, source: project.scene_outline.source };
    } };
    const navigate = label => page.locator('.workspace-stage-nav').getByRole('button',{name:new RegExp('^'+label+'(?: |$)')}).click();
    await navigate('Dàn cảnh');
    const area = page.locator('.scene-outline');
    const notice = area.locator('.scene-heading > [role="status"]');
    const pop = page.locator('.scene-popover:popover-open');
    await reveal(page, area);
    await area.getByRole('button', { name: 'Tự thêm cảnh', exact: true }).click();
    await pop.getByLabel('Tên cảnh', { exact: true }).fill('Cảnh kiểm thử');
    await pop.getByLabel('Chuyện gì xảy ra trong cảnh này?', { exact: true }).fill('Nhân vật mở cửa.');
    assert.match(await notice.textContent(), /Đã thêm cảnh trong bản chưa lưu/);
    mock.failSave = true;
    await pop.getByRole('button', { name: 'Lưu thay đổi dàn cảnh', exact: true }).click();
    await pop.getByRole('alert').waitFor();
    assert.match(await notice.textContent(), /Đã thêm cảnh trong bản chưa lưu/);
    assert.equal(await pop.getByLabel('Tên cảnh', { exact: true }).inputValue(), 'Cảnh kiểm thử');
    mock.failSave = false;
    await pop.getByRole('button', { name: 'Lưu thay đổi dàn cảnh', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#save-status').textContent === 'Đã lưu');
    assert.equal(await notice.textContent(), '');
    await pop.getByRole('button', { name: 'Đóng', exact: true }).click();
    // A later unrelated edit must not resurrect the old unsaved-scene message.
    await navigate('Ý tưởng');
    await reveal(page, page.locator('#project-title'));
    await page.locator('#project-title').fill('Tên mới');
    assert.equal(await notice.textContent(), '');
    // The global save button must clear the same notice too.
    await navigate('Dàn cảnh');
    await reveal(page, area);
    await area.getByRole('button', { name: 'Tự thêm cảnh', exact: true }).click();
    await pop.getByRole('button', { name: 'Đóng', exact: true }).click();
    assert.match(await notice.textContent(), /Đã thêm cảnh trong bản chưa lưu/);
    await page.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#save-status').textContent === 'Đã lưu');
    assert.equal(await notice.textContent(), '');
    assert.equal(mock.projects[0].scene_outline.scenes.length, 2);
    await t.close();
    console.log('PASS scene notice: save failure preserves notice/buffer; scene and global saves clear notice; later edits do not revive it.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
