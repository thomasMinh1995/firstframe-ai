// Run against the production frontend with Playwright supplied via NODE_PATH.
// Every project request is intercepted: no backend, real project or model is used.
const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const url = process.env.TOUR_TEST_URL || 'http://localhost:3033';
const engine = process.env.TOUR_BROWSER || 'chrome';
const screenshots = process.env.TOUR_SCREENSHOTS || '/private/tmp/firstframe-tour-screenshots';
const key = 'firstframe:onboarding';
const clone = value => structuredClone(value);
const project = (id = 'p1') => ({ id, revision: 0, updated_at: '2026-10-21T10:00:00Z', title: 'Câu chuyện thử nghiệm',
  response_language: 'vi', idea: 'Một người thợ sửa xe gặp lại người bạn cũ.', constraints: [], answers: [],
  analysis: null, draft: null, feedback: null, feedback_is_current: false, versions: [], clarification_history: [] });
const analysis = () => ({ artifact_id: 'a1', summary: 'Một cuộc gặp bất ngờ.', missing_information: [], notes: [] });
const draft = () => ({ title: 'Cuộc gặp', logline: 'Một người thợ học cách lắng nghe.', sections: [] });
const fullProject = id => ({ ...project(id), analysis: analysis(), draft: draft() });
const countWrites = mock => mock.calls.filter(c => c.method !== 'GET').length;
const buffer = page => page.locator('input, textarea, select').evaluateAll(nodes => nodes.map(n => [n.id, n.value]));
const click = (page, name) => page.getByRole('button', { name, exact: true }).click();
const step = (page, n) => page.getByText(`Bước ${n}/6`, { exact: true }).waitFor({ state: 'visible' });
const focused = (page, selector) => page.waitForFunction(selector => document.activeElement.matches(selector), selector);
const status = (page, expected) => page.waitForFunction(({ key, expected }) => JSON.parse(localStorage.getItem(key))?.status === expected, { key, expected });

async function setup(browser, options = {}) {
  const context = await browser.newContext({ viewport: options.viewport || { width: 1280, height: 900 }, reducedMotion: 'reduce' });
  const mock = { projects: clone(options.projects || []), calls: [], failList: false, failSave: false, failAI: false, hold: null, ...options.mock };
  const errors = [];
  context.on('page', p => p.on('pageerror', e => errors.push(e.message)));
  if (options.storage !== undefined) await context.addInitScript(({ key, storage, origin }) => {
    // Once per context/origin, so reload can verify the app's persisted record.
    if (location.origin !== origin) return;
    try {
      if (!sessionStorage.getItem('tour-test-seeded')) {
        localStorage.setItem(key, storage); sessionStorage.setItem('tour-test-seeded', '1');
      }
    } catch { /* Sandboxed browser/dev-tool documents have no storage access. */ }
  }, { key, storage: options.storage, origin: new URL(url).origin });
  if (options.blockStorage) await context.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('storage denied'); };
    Storage.prototype.setItem = () => { throw new Error('storage denied'); };
  });
  await context.route('**/api/projects**', async route => {
    const req = route.request(), pathname = new URL(req.url()).pathname;
    const method = req.method();
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'GET, POST, PUT, OPTIONS', 'access-control-allow-headers': 'content-type' };
    const reply = (data, status = 200, type = 'application/json') => route.fulfill({ status, headers, contentType: type, body: typeof data === 'string' ? data : JSON.stringify(data) });
    if (method === 'OPTIONS') return reply('', 204);
    const body = req.postData() ? req.postDataJSON() : null;
    mock.calls.push({ method, pathname, body });
    const parts = pathname.split('/').filter(Boolean), id = parts[2];
    if (method === 'GET' && !id) return mock.failList ? reply({ detail: 'offline' }, 503) : reply(mock.projects.map(({ id, title, updated_at }) => ({ id, title, updated_at })));
    if (method === 'POST' && !id) {
      const created = { ...project(`p${mock.projects.length + 1}`), idea: '' };
      mock.projects.push(created); return reply(created);
    }
    const p = mock.projects.find(p => p.id === id);
    if (!p) return reply({ detail: 'missing' }, 404);
    if (method === 'GET') return reply(p);
    if (method === 'PUT') {
      if (mock.failSave) return reply({ detail: 'Xung đột phiên bản. Bản sửa vẫn được giữ.' }, 409);
      const changed = p.idea !== body.idea || JSON.stringify(p.constraints) !== JSON.stringify(body.constraints);
      Object.assign(p, body, { revision: p.revision + 1 });
      if (changed) { p.analysis = null; p.answers = []; }
      return reply(p);
    }
    if (mock.hold) await mock.hold;
    if (mock.failAI) return reply({ detail: 'Chọn ngôn ngữ đầu ra.' }, 422);
    if (parts[3] === 'analyze') p.analysis = analysis();
    else if (parts[3] === 'plan') p.draft = draft();
    else throw new Error(`Unexpected model operation: ${pathname}`);
    p.revision++;
    return reply(JSON.stringify({ type: 'progress', stage: 'reasoning', status: 'completed' }) + '\n'
      + JSON.stringify({ type: 'result', project: p }) + '\n', 200, 'application/x-ndjson');
  });
  const page = await context.newPage();
  await page.goto(url);
  await page.getByRole('button', { name: 'Dự án mới', exact: true }).waitFor();
  await page.waitForFunction(() => !document.querySelector('[data-tour="new-project"]').disabled);
  return { context, page, mock, errors, close: async () => { assert.deepEqual(errors, []); await context.close(); } };
}

(async () => {
  await fs.mkdir(screenshots, { recursive: true });
  assert.ok(['chrome', 'firefox', 'webkit'].includes(engine), 'TOUR_BROWSER must be chrome, firefox or webkit');
  const browser = await ({ chrome: chromium, firefox, webkit })[engine].launch({
    ...(engine === 'chrome' ? { channel: 'chrome' } : {}), headless: true,
  });
  console.log(`Testing ${engine} ${browser.version()} at ${url}`);
  try {
    // Escape works outside the modal too; disappearing openers use the workspace fallback.
    let t = await setup(browser), { page, mock } = t;
    await page.keyboard.press('Escape'); await status(page, 'dismissed');
    await focused(page, '#workspace-title');
    assert.equal(countWrites(mock), 0);
    await t.close();
    t = await setup(browser); ({ page, mock } = t);
    await click(page, 'Bắt đầu hướng dẫn'); await step(page, 1);
    await page.keyboard.press('Escape'); await focused(page, '#workspace-title');
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 1);
    await click(page, 'Đóng hướng dẫn'); await focused(page, '#tour-help');
    await t.close();
    t = await setup(browser, { projects: [project()] }); ({ page, mock } = t);
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Thực hành');
    await page.locator('#idea').fill('Nội dung chưa lưu khi dùng Escape.');
    const practiceBuffer = await buffer(page);
    await page.keyboard.press('Escape'); await status(page, 'dismissed');
    await focused(page, '#idea');
    assert.deepEqual(await buffer(page), practiceBuffer); assert.equal(countWrites(mock), 0);
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Thực hành');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 3);
    await page.keyboard.press('Escape'); await focused(page, '#workspace-title');
    // Dismiss during an actual pending request; its later result must not revive the tour.
    let releaseEscape; mock.hold = new Promise(resolve => { releaseEscape = resolve; });
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Tiếp'); await click(page, 'Thực hành');
    await click(page, 'Cùng làm rõ ý tưởng');
    await page.waitForFunction(() => document.querySelector('#tour-help').disabled);
    await page.getByRole('button', { name: 'Bỏ qua', exact: true }).focus();
    await page.keyboard.press('Escape'); await status(page, 'dismissed');
    await focused(page, '#workspace-title');
    releaseEscape();
    await page.waitForFunction(() => !document.querySelector('#tour-help').disabled);
    await status(page, 'dismissed'); assert.equal(await page.locator('dialog[open]').count(), 0);
    await t.close();
    t = await setup(browser, { projects: [project()], storage: JSON.stringify({ version: 1, status: 'paused', stepId: 'idea', projectId: 'p1' }) });
    ({ page } = t);
    await page.getByRole('button', { name: 'Tiếp tục hướng dẫn', exact: true }).focus();
    await page.keyboard.press('Escape'); await status(page, 'dismissed'); await focused(page, '#workspace-title');
    await t.close();

    // Complete all six steps through real UI buttons, with no questions, sections or feedback.
    t = await setup(browser); ({ page, mock } = t);
    await click(page, 'Bắt đầu hướng dẫn'); await step(page, 1);
    await focused(page, '#tour-title');
    const tabOrder = await page.locator('.tour-card button:enabled').allTextContents();
    // Check each stop, not just containment: WebKit may skip buttons by default.
    for (let i = 0; i <= tabOrder.length; i++) {
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.textContent), tabOrder[i % tabOrder.length]);
    }
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.evaluate(() => document.activeElement.textContent), tabOrder.at(-1));
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press(i < 6 ? 'Tab' : 'Shift+Tab');
      assert.equal(await page.evaluate(() => !!document.activeElement.closest('dialog')), true, 'focus stays in modal');
    }
    await assert.rejects(page.locator('[data-tour="new-project"]').click({ timeout: 300 }), /Timeout/);
    assert.equal(countWrites(mock), 0, 'spotlight does not allow clicks through');
    await page.screenshot({ path: path.join(screenshots, 'desktop.png') });
    await click(page, 'Thực hành');
    await focused(page, '[data-tour="new-project"]');
    await click(page, 'Dự án mới');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 2);
    await click(page, 'Thực hành');
    await page.locator('#idea').fill('Một người thợ sửa xe gặp lại người bạn cũ.');
    await page.locator('#constraints').fill('Kết thúc mở.');
    let before = await buffer(page), writes = countWrites(mock);
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 3);
    assert.deepEqual(await buffer(page), before);
    assert.equal(countWrites(mock), writes);
    await click(page, 'Thực hành');
    await click(page, 'Cùng làm rõ ý tưởng');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 4);
    assert.match(await page.locator('#tour-description').innerText(), /không có câu hỏi/);
    await click(page, 'Thực hành');
    await focused(page, '[data-tour-action="plan"]');
    await click(page, 'Tạo bản phát triển từ lựa chọn của tôi');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 5);
    await click(page, 'Thực hành');
    await page.locator('#draft-logline').fill('Bản sửa chưa lưu của tác giả.');
    before = await buffer(page); writes = countWrites(mock);
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 6);
    await click(page, 'Hoàn tất hướng dẫn'); await status(page, 'completed');
    assert.deepEqual(await buffer(page), before);
    assert.equal(countWrites(mock), writes, 'finishing never saves or reviews');
    await focused(page, '[data-tour-action="save"]');
    await click(page, 'Lưu thay đổi');
    await page.reload(); await click(page, 'Hướng dẫn sử dụng'); await step(page, 5);
    assert.equal(await page.getByText('Bắt đầu cùng FirstFrame', { exact: true }).count(), 0);
    await click(page, 'Tiếp'); await step(page, 6);
    await click(page, 'Hoàn tất hướng dẫn');
    await focused(page, '#save-status');
    await t.close();

    // Existing analysis keeps language help available and focuses the first unanswered question.
    const questions = { ...project(), analysis: { ...analysis(), missing_information: ['Bạn muốn kết thúc thế nào?', 'Điều gì cần giữ?'] }, answers: ['Kết thúc mở', ''] };
    t = await setup(browser, { projects: [questions] }); ({ page, mock } = t);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 4);
    before = await buffer(page); writes = countWrites(mock);
    await click(page, 'Trước'); await step(page, 3); await click(page, 'Thực hành');
    await focused(page, '#response-language');
    assert.deepEqual(await buffer(page), before); assert.equal(countWrites(mock), writes);
    await page.locator('#response-language').selectOption('en');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 4); await click(page, 'Thực hành');
    await focused(page, '#answer-1');
    assert.equal(await page.locator('[data-tour-action="plan"]').isDisabled(), true);
    await page.getByRole('button', { name: 'Để quyết định sau', exact: true }).nth(1).click();
    assert.equal(countWrites(mock), writes);
    await click(page, 'Tạo bản phát triển từ lựa chọn của tôi');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 5);
    assert.equal(mock.projects[0].response_language, 'en');
    assert.match(mock.projects[0].answers[1], /Chưa quyết định/);
    await t.close();

    // A saved draft must not outrank a changed brief, even after the save clears analysis.
    t = await setup(browser, { projects: [fullProject('p1')] }); ({ page, mock } = t);
    assert.equal(await page.getByText('Bắt đầu cùng FirstFrame', { exact: true }).count(), 0);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 5); await click(page, 'Thực hành');
    await page.locator('#idea').fill('Một ý tưởng hoàn toàn khác.');
    before = await buffer(page); writes = countWrites(mock);
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 2);
    await page.keyboard.press('Escape'); await status(page, 'dismissed');
    assert.deepEqual(await buffer(page), before); assert.equal(countWrites(mock), writes);
    await click(page, 'Lưu thay đổi');
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 2);
    assert.ok(mock.projects[0].draft); assert.equal(mock.projects[0].analysis, null);
    await t.close();

    // Save rejection prevents analyze; a later AI rejection does not unlock the next step.
    t = await setup(browser, { projects: [project()] }); ({ page, mock } = t);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 2); await click(page, 'Thực hành');
    await page.locator('#idea').fill('Ý tưởng đã sửa nhưng chưa lưu.');
    before = await buffer(page); mock.failSave = true;
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 3); await click(page, 'Thực hành');
    await click(page, 'Cùng làm rõ ý tưởng'); await status(page, 'paused');
    assert.equal(mock.calls.filter(c => c.pathname.endsWith('/analyze/stream')).length, 0);
    assert.deepEqual(await buffer(page), before);
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 3); await click(page, 'Thực hành');
    mock.failSave = false; mock.failAI = true;
    await click(page, 'Cùng làm rõ ý tưởng'); await status(page, 'paused');
    assert.equal(JSON.parse(await page.evaluate(key => localStorage.getItem(key), key)).stepId, 'language');
    const errorBeforeHelp = await page.locator('.error[role="alert"]').innerText();
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 2);
    assert.equal(await page.locator('.error[role="alert"]').innerText(), errorBeforeHelp, 'manual help preserves existing error');
    assert.deepEqual(await buffer(page), before);
    await t.close();

    // Reload resumes only on request, and switching projects resolves the new project's entry.
    t = await setup(browser, { projects: [project(), fullProject('p2')] }); ({ page, mock } = t);
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Tiếp'); await click(page, 'Thực hành');
    writes = countWrites(mock);
    await page.reload();
    await page.getByRole('button', { name: 'Tiếp tục hướng dẫn', exact: true }).waitFor();
    assert.equal(await page.locator('dialog[open]').count(), 0); assert.equal(countWrites(mock), writes);
    await page.locator('#project-picker').selectOption('p2');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 5);
    await t.close();

    // Another tab dismisses the tour while its analyze request is pending.
    t = await setup(browser, { projects: [project()] }); ({ page, mock } = t);
    let release; mock.hold = new Promise(resolve => { release = resolve; });
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Tiếp'); await click(page, 'Thực hành');
    await click(page, 'Cùng làm rõ ý tưởng');
    await page.waitForFunction(() => document.querySelector('[data-tour="new-project"]').disabled);
    const second = await t.context.newPage(); await second.goto(url);
    await second.evaluate(key => localStorage.setItem(key, JSON.stringify({ version: 1, status: 'dismissed', stepId: 'language', projectId: 'p1' })), key);
    await page.getByRole('region', { name: 'Tiến độ hướng dẫn' }).waitFor({ state: 'detached' });
    release();
    await page.waitForFunction(() => !document.querySelector('#tour-help').disabled);
    await status(page, 'dismissed'); assert.equal(await page.locator('dialog[open]').count(), 0);
    await t.close();

    // Broken/blocked storage never prevents manual use or repeatedly invites the user.
    for (const options of [{ storage: '{bad' }, { storage: JSON.stringify({ version: 99 }) }, { blockStorage: true }]) {
      t = await setup(browser, options); ({ page } = t);
      assert.equal(await page.getByText('Bắt đầu cùng FirstFrame', { exact: true }).count(), 0);
      await click(page, 'Hướng dẫn sử dụng'); await step(page, 1);
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('dialog[open]').count(), 0);
      await t.close();
    }
    t = await setup(browser, { mock: { failList: true } }); ({ page } = t);
    assert.equal(await page.getByText('Bắt đầu cùng FirstFrame', { exact: true }).count(), 0);
    assert.equal(await page.locator('#tour-help').isDisabled(), true);
    await t.close();

    // Missing targets pause safely; a tiny viewport falls back to a scrollable modal.
    t = await setup(browser, { projects: [project()] }); ({ page } = t);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 2);
    await page.locator('#idea').evaluate(n => n.remove());
    await status(page, 'paused'); assert.equal(await page.locator('dialog[open]').count(), 0);
    await t.close();
    t = await setup(browser, { projects: [fullProject('p1')], viewport: { width: 390, height: 844 } }); ({ page } = t);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 5);
    await page.screenshot({ path: path.join(screenshots, 'mobile.png') });
    await page.setViewportSize({ width: 320, height: 260 });
    await page.waitForFunction(() => {
      const r = document.querySelector('.tour-card').getBoundingClientRect();
      return r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight;
    });
    assert.equal(await page.locator('.tour-spotlight').count(), 0);
    assert.match(await page.locator('#tour-description').innerText(), /Bản phát triển đang làm việc/);
    await click(page, 'Tiếp'); await step(page, 6); await click(page, 'Hoàn tất hướng dẫn');
    await t.close();
    console.log('Browser tour checks passed: full flow, no tour writes, buffers, keyboard, conditional data, failures, reload, project switch, cross-tab dismissal, storage, missing anchors and mobile viewport.');
    console.log(`Screenshots: ${screenshots}`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
