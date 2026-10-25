// Production-build smoke against ui_workspace_fixture.py: real API/SQLite, fake AI only.
const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { edit, answer } = require('./onboarding.browser.cjs');
const engine = process.env.TOUR_BROWSER || 'chrome';
const url = 'http://127.0.0.1:3034';
const api = 'http://127.0.0.1:8034';
const output = process.env.TOUR_SCREENSHOTS || `/tmp/firstframe-release-${engine}`;
const click = (page, name) => page.getByRole('button', { name, exact: true }).click();
const notice = (page, text) => page.getByText(text, { exact: true }).waitFor();
const input = page => page.locator('#draft-logline');
const open = page => click(page, 'Sửa tóm tắt câu chuyện trong một câu');
const editableKeys = ['answers', 'constraints', 'draft', 'idea', 'response_language', 'revision', 'title'];

(async () => {
  assert.ok(['chrome', 'firefox', 'webkit'].includes(engine));
  const directory = process.env.FIRSTFRAME_QA_DIRECTORY;
  assert.ok(directory && path.basename(directory).startsWith('firstframe-workspace-'), 'Require disposable fixture directory');
  const seed = JSON.parse(await fs.readFile(path.join(directory, 'seed.json'), 'utf8'));
  await fs.mkdir(output, { recursive: true });
  const browser = await ({ chrome: chromium, firefox, webkit })[engine].launch({ headless: true,
    ...(engine === 'chrome' ? { channel: 'chrome' } : {}) });
  const report = { engine, version: browser.version(), results: [] };
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  const json = async route => {
    const response = await context.request.get(api + route);
    assert.equal(response.status(), 200); return response.json();
  };
  const page = await context.newPage();
  const pass = name => { report.results.push({ name, passed: true }); console.log(`PASS ${name}`); };
  try {
    // Verify the test fixture before any write. Never run this against a user's backend.
    const initial = await json('/__test/state'); assert.ok(Array.isArray(initial.provider_stages));
    assert.deepEqual((await json(`/api/projects/${seed.id}`)).draft, seed.draft);
    const stagesBefore = initial.provider_stages.length;
    await context.route('**/*', route => {
      const origin = new URL(route.request().url()).origin;
      return [url, api].includes(origin) ? route.continue() : route.abort('blockedbyclient');
    });
    await page.goto(url);
    await page.locator('.story-workspace').waitFor();
    assert.equal(await page.locator('.workspace-view-toggle').count(), 0);
    await click(page, 'Dự án mới');
    await page.waitForFunction(seedId => {
      const picker = document.querySelector('#project-picker');
      return picker && !picker.disabled && picker.value && picker.value !== seedId;
    }, seed.id);
    const id = await page.locator('#project-picker').inputValue(); report.projectId = id;
    const stored = () => json(`/api/projects/${id}`);
    await page.locator('#project-title').fill(`QA release ${engine}`);
    await page.locator('#response-language').selectOption('vi');
    await page.locator('#idea').fill('Một người cha muốn gặp con gái trước khi cô rời Việt Nam.');
    await page.locator('#constraints').fill('Hai nhân vật.');
    await click(page, 'Cùng làm rõ ý tưởng');
    await notice(page, 'Hãy trả lời các câu hỏi trước khi tạo bản phát triển.');
    await answer(page, 0, 'Con gái đi vào ngày mai.');
    await answer(page, 1, 'Người cha muốn xin lỗi, không ngăn con đi.');
    await click(page, 'Tạo bản phát triển từ lựa chọn của tôi');
    await notice(page, 'Đã tạo và lưu bản phát triển. Bạn có thể sửa trực tiếp bên dưới.');
    let p = await stored(); assert.ok(p.draft && p.feedback_is_current);
    pass('idea-clarification-plan-real-api');

    await open(page); await input(page).fill(`Buffer chưa bấm Xong ${engine}.`);
    const beforeEditing = await json('/__test/state');
    assert.equal(await input(page).inputValue(), `Buffer chưa bấm Xong ${engine}.`);
    await (await edit(page, 'section-0')).fill('Chi tiết được sửa tại card.');
    assert.equal(await input(page).inputValue(), `Buffer chưa bấm Xong ${engine}.`);
    const download = page.waitForEvent('download'); await click(page, 'Tải bản sao JSON');
    const backupFile = path.join(output, 'unsaved-buffer.json'); await (await download).saveAs(backupFile);
    const backup = JSON.parse(await fs.readFile(backupFile, 'utf8'));
    assert.equal(backup.draft.logline, `Buffer chưa bấm Xong ${engine}.`);
    assert.equal(backup.draft.sections[0].content, 'Chi tiết được sửa tại card.');
    assert.deepEqual((await stored()).draft, p.draft);
    const afterEditing = await json('/__test/state');
    assert.equal(afterEditing.calls.filter(c => c.method !== 'GET').length, beforeEditing.calls.filter(c => c.method !== 'GET').length);
    assert.deepEqual(afterEditing.provider_stages, beforeEditing.provider_stages);
    pass('card-buffer-backup-no-write');

    await click(page, 'Lưu thay đổi');
    await notice(page, 'Đã lưu thay đổi.'); await page.reload();
    await page.locator('.story-field-title').waitFor(); await open(page);
    assert.equal(await input(page).inputValue(), backup.draft.logline);
    assert.equal(new URL(page.url()).searchParams.get('workspace'), null);
    assert.deepEqual((await stored()).draft, backup.draft);
    pass('default-workspace-save-reload');

    await edit(page, 'draft-logline');
    await input(page).fill(`Review đọc buffer mới ${engine}.`);
    await click(page, 'Nhận phản hồi trên bản hiện tại');
    await notice(page, 'Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.');
    p = await stored(); assert.equal(p.draft.logline, `Review đọc buffer mới ${engine}.`);
    assert.deepEqual(p.feedback_source.draft, p.draft); assert.equal(p.feedback_is_current, true);
    pass('story-review-persists-open-editor');

    const beforeProposal = p;
    await click(page, 'Tạo bản đề xuất mới (giữ bản đang viết)');
    await notice(page, 'Đã giữ bản đề xuất cùng góp ý riêng. Bản đang viết chỉ thay khi bạn chọn nhận.');
    p = await stored(); assert.deepEqual(p.draft, beforeProposal.draft);
    const generation = p.plan_generations.at(-1); assert.equal(generation.applied_revision, null);
    const proposal = page.getByRole('region', { name: 'Các bản do AI tạo', exact: true }).locator(':scope > details').first();
    await proposal.locator(':scope > summary').click(); await proposal.getByRole('button', { name: 'Dùng bản đề xuất này', exact: true }).click();
    await notice(page, 'Đã nhận bản đề xuất. Bản trước được giữ trong lịch sử; có thể sửa và nhận phản hồi riêng.');
    p = await stored(); assert.deepEqual(p.draft, generation.draft);
    assert.ok(p.versions.some(v => JSON.stringify(v.draft) === JSON.stringify(beforeProposal.draft)));
    pass('accept-proposal-keeps-history');

    await edit(page, 'draft-logline');
    await input(page).fill(`Chữ trước khôi phục ${engine}.`);
    const historical = p.versions.at(-1);
    const history = page.locator('section.version-history').filter({ has: page.getByRole('heading', { name: 'Các phiên bản đã giữ', exact: true }) });
    const version = history.locator(':scope > details').first();
    await version.locator(':scope > summary').click(); await version.getByRole('button', { name: 'Dùng lại bản phát triển này', exact: true }).click();
    await notice(page, 'Đã dùng lại nội dung bản phát triển. Các phiên bản trước vẫn được giữ.');
    const restored = await stored(); assert.deepEqual(restored.draft, historical.draft);
    assert.deepEqual(restored.answers, p.answers);
    assert.ok(restored.versions.some(v => v.draft.logline === `Chữ trước khôi phục ${engine}.`));
    assert.deepEqual(restored.versions.slice(0, p.versions.length), p.versions);
    await page.reload();
    await page.locator('.story-field-title').waitFor(); await open(page);
    assert.equal(await input(page).inputValue(), historical.draft.logline);
    pass('restore-preserves-buffer-in-history-reopen');

    const state = await json('/__test/state');
    const calls = state.calls.filter(c => c.path.startsWith(`/api/projects/${id}`));
    for (const call of calls.filter(c => c.method === 'PUT')) assert.deepEqual(Object.keys(call.body).sort(), editableKeys);
    assert.ok(calls.every(c => c.status >= 200 && c.status < 300));
    assert.deepEqual(state.provider_stages.slice(stagesBefore), ['reasoning', 'planning', 'evaluation', 'evaluation', 'planning', 'evaluation']);
    assert.deepEqual(errors, []);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: path.join(output, 'workspace-final.png') });
    await fs.writeFile(path.join(output, 'project-final.json'), JSON.stringify(restored, null, 2));
    await fs.writeFile(path.join(output, 'api-calls.json'), JSON.stringify(calls, null, 2));
    pass('unchanged-payload-provider-stages-no-runtime-errors');
  } catch (error) {
    report.results.push({ passed: false, error: error.stack });
    await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
    throw error;
  } finally {
    await context.close(); await browser.close();
    await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
