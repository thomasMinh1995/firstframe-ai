// Run against the production frontend with Playwright supplied via NODE_PATH.
// Every project request is intercepted: no backend, real project or model is used.
const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const url = process.env.TOUR_TEST_URL || 'http://localhost:3033';
const engine = process.env.TOUR_BROWSER || 'chrome';
const screenshots = process.env.TOUR_SCREENSHOTS || '/private/tmp/firstframe-tour-screenshots';
const key = 'firstframe:onboarding:v2';
const clone = value => structuredClone(value);
const project = (id = 'p1') => ({ id, revision: 0, updated_at: '2026-10-21T10:00:00Z', title: 'Câu chuyện thử nghiệm',
  response_language: 'vi', idea: 'Một người thợ sửa xe gặp lại người bạn cũ.', constraints: [], answers: [],
  analysis: null, draft: null, feedback: null, feedback_is_current: false, versions: [], clarification_history: [] });
const analysis = () => ({ artifact_id: 'a1', summary: 'Một cuộc gặp bất ngờ.', missing_information: [], notes: [] });
const draft = () => ({ title: 'Cuộc gặp', logline: 'Một người thợ học cách lắng nghe.', sections: [] });
const fullProject = id => ({ ...project(id), analysis: analysis(), draft: draft() });
const countWrites = mock => mock.calls.filter(c => c.method !== 'GET').length;
const buffer = page => page.evaluate(() => {
  const fields = Array.from(document.querySelectorAll('input, textarea, select'))
    .filter(n => !n.closest('.story-field') && !n.id.startsWith('answer-')).map(n => [n.id, n.value]);
  for (const button of document.querySelectorAll('[data-answer-open]')) {
    const id = button.dataset.answerOpen;
    fields.push([id, document.getElementById(id)?.value ?? document.getElementById(id + '-value')?.textContent ?? '']);
  }
  const draftFields = new Map();
  for (const n of document.querySelectorAll('.story-field')) {
    const id = n.querySelector('h3').id.replace(/-label$/, '').replace(/-part-\d+$/, '');
    const value = (n.querySelector('input, textarea')?.value ?? n.querySelector('.story-field-value').textContent).replace(/\s+/g, ' ').trim();
    draftFields.set(id, draftFields.has(id) ? draftFields.get(id) + ' ' + value : value);
  }
  return [...fields, ...draftFields].sort(([a], [b]) => a.localeCompare(b));
});
async function reveal(page, locator) {
  const ancestors = locator.locator('xpath=ancestor::details');
  for (let i = await ancestors.count() - 1; i >= 0; i--) {
    const item = ancestors.nth(i);
    if (await item.getAttribute('open') === null) await item.locator(':scope > summary').click();
  }
}
async function answer(page, index, value) {
  await reveal(page, page.locator('[data-answer-open]').first());
  const input = page.locator(`#answer-${index}`);
  if (!await input.count()) await page.locator(`[data-answer-open="answer-${index}"]`).click();
  await input.fill(value);
}
async function edit(page, id) {
  const field = page.locator('.story-field').filter({ has: page.locator(`[id="${id}-label"]`) });
  await field.waitFor({ state: 'attached' });
  await reveal(page, field);
  const input = page.locator(`[id="${id}"]`);
  if (!await input.count()) await field.getByRole('button', { name: /^Sửa / }).click();
  await input.focus();
  return input;
}
async function confirmPlan(page) {
  await reveal(page, page.locator('[data-choice-review]'));
  await page.getByRole('button', { name: 'Xem lại các lựa chọn', exact: true }).click();
  await page.locator('[data-tour-action="plan"]').click();
}
const click = async (page, name) => {
  if (['Tạo bản phát triển từ lựa chọn của tôi', 'Tạo bản đề xuất mới (giữ bản đang viết)'].includes(name)) return confirmPlan(page);
  const button = page.getByRole('button', { name, exact: true, includeHidden: true });
  await reveal(page, button); await button.click();
};
const fill = async (page, selector, value) => {
  const input = page.locator(selector); await reveal(page, input); await input.fill(value);
};
const select = async (page, selector, value) => {
  const input = page.locator(selector); await reveal(page, input); await input.selectOption(value);
};
const toggle = async (page, details) => {
  await reveal(page, details); await details.locator(':scope > summary').click();
};
const step = (page, n) => page.getByText(`Bước ${n}/7`, { exact: true }).waitFor({ state: 'visible' });
const focused = (page, selector) => page.waitForFunction(selector => document.activeElement.matches(selector), selector);
const status = (page, expected) => page.waitForFunction(({ key, expected }) => JSON.parse(localStorage.getItem(key))?.status === expected, { key, expected });

async function setup(browser, options = {}) {
  const context = await browser.newContext({ viewport: options.viewport || { width: 1280, height: 900 }, reducedMotion: 'reduce' });
  context.setDefaultTimeout(10000);
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
      if (mock.holdSave) {
        const pending = mock.holdSave; mock.holdSave = null;
        await pending;
      }
      if (mock.failSave || body.revision !== p.revision) return reply({ detail: 'Xung đột phiên bản. Bản sửa vẫn được giữ.' }, 409);
      const changed = p.idea !== body.idea || JSON.stringify(p.constraints) !== JSON.stringify(body.constraints);
      const reviewChanged = changed || p.response_language !== body.response_language
        || JSON.stringify(p.answers) !== JSON.stringify(body.answers) || JSON.stringify(p.draft) !== JSON.stringify(body.draft);
      if (mock.recordVersions && p.draft && JSON.stringify(p.draft) !== JSON.stringify(body.draft)) {
        p.versions.push({ id: `v${p.revision}`, created_at: p.updated_at, response_language: p.response_language,
          idea: p.idea, constraints: clone(p.constraints), questions: p.analysis?.missing_information || [], answers: clone(p.answers),
          draft: clone(p.draft), feedback: p.feedback_is_current ? clone(p.feedback) : null,
          feedback_source: p.feedback_is_current ? clone(p.feedback_source) : null });
      }
      Object.assign(p, body, { revision: p.revision + 1 });
      if (reviewChanged) p.feedback_is_current = false;
      if (reviewChanged && p.applicable_plan_ids) p.applicable_plan_ids = [];
      if (changed) { p.analysis = null; p.answers = []; }
      if (mock.savePatch) Object.assign(p, clone(mock.savePatch));
      if (mock.loseSaveResponse) return route.abort('failed');
      return reply(p);
    }
    if (mock.hold) await mock.hold;
    if (body.revision !== p.revision) return reply({ detail: 'Xung đột phiên bản. Bản sửa vẫn được giữ.' }, 409);
    if (parts[3] === 'plans' && parts[5] === 'accept') {
      const generation = p.plan_generations.find(g => g.id === parts[4]);
      if (!generation || generation.applied_revision !== null || !p.applicable_plan_ids.includes(generation.id)) {
        return reply({ detail: 'Nguồn đã thay đổi; bản đang viết được giữ.' }, 409);
      }
      p.versions.push({ id: `accept-${p.revision}`, created_at: p.updated_at, response_language: p.response_language,
        idea: p.idea, constraints: clone(p.constraints), questions: p.analysis?.missing_information || [], answers: clone(p.answers),
        draft: clone(p.draft), feedback: clone(p.feedback), feedback_source: clone(p.feedback_source) });
      p.draft = clone(generation.draft); p.feedback = clone(generation.feedback); p.feedback_source = clone(generation.feedback_source);
      p.feedback_is_current = !!p.feedback_source; p.revision++; generation.applied_revision = p.revision; p.applicable_plan_ids = [];
      if (mock.loseAcceptResponse) return route.abort('failed');
      return reply(p);
    }
    if (mock.failAI) return reply({ detail: 'Chọn ngôn ngữ đầu ra.' }, 422);
    if (parts[3] === 'clarify') {
      const old = p.analysis?.missing_information ?? [];
      const proposed = mock.clarifyQuestions ?? (old.length ? ['Bạn muốn giữ chi tiết nào nữa?', 'Nhịp nào cần chậm lại?']
        : ['Bạn muốn theo chân ai?', 'Điều muốn giữ?', 'Muốn dừng ở đâu?', 'Cách kể?', 'Cảm giác muốn giữ?', 'Giới hạn thực hiện?']);
      const extra = proposed.filter(q => !old.includes(q));
      p.analysis = { ...analysis(), artifact_id: `a-${p.revision}`, missing_information: [...old, ...extra] };
      p.answers = [...p.answers, ...extra.map(() => '')];
    }
    else if (parts[3] === 'analyze') p.analysis = analysis();
    else if (parts[3] === 'plan') {
      if (mock.planPatch) Object.assign(p, clone(mock.planPatch));
      else p.draft = draft();
      if (mock.losePlanResponse) { p.revision++; return route.abort('failed'); }
    }
    else if (parts[3] === 'review') {
      assert.ok(mock.reviewPatch, 'review requires an explicit test result');
      Object.assign(p, clone(mock.reviewPatch));
    }
    else throw new Error(`Unexpected model operation: ${pathname}`);
    p.revision++;
    const stages = parts[3] === 'plan' ? ['plan_choices','planning_context','planning','planning_structure','plan_checkpoint','evaluation','plan_save'] : ['reasoning','saving'];
    return reply(stages.flatMap(stage => ['active','completed'].map(status => JSON.stringify({ type: 'progress', stage, status }))).join('\n') + '\n'
      + JSON.stringify({ type: 'result', project: p }) + '\n', 200, 'application/x-ndjson');
  });
  const page = await context.newPage();
  const entry = new URL(url);
  await page.goto(entry.href);
  await page.getByRole('button', { name: 'Dự án mới', exact: true }).waitFor();
  await page.waitForFunction(() => !document.querySelector('[data-tour="new-project"]').disabled);
  return { context, page, mock, errors, close: async () => { assert.deepEqual(errors, []); await context.close(); } };
}

module.exports = { setup, project, analysis, draft, fullProject, edit, answer, reveal, confirmPlan };

if (require.main === module) (async () => {
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
    await fill(page, '#idea', 'Nội dung chưa lưu khi dùng Escape.');
    const practiceBuffer = await buffer(page);
    await page.keyboard.press('Escape'); await status(page, 'dismissed');
    await focused(page, '#idea');
    assert.deepEqual(await buffer(page), practiceBuffer); assert.equal(countWrites(mock), 0);
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Thực hành');
    assert.equal(await page.getByRole('button', { name: 'Tiếp tục hướng dẫn', exact: true }).isDisabled(), true);
    await focused(page, '#idea');
    await page.keyboard.press('Escape'); await focused(page, '#idea');
    // Dismiss during an actual pending request; its later result must not revive the tour.
    let releaseEscape; mock.hold = new Promise(resolve => { releaseEscape = resolve; });
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Thực hành');
    await click(page, 'Cùng làm rõ ý tưởng');
    await page.waitForFunction(() => document.querySelector('#tour-help').disabled);
    await page.getByRole('button', { name: 'Bỏ qua', exact: true }).focus();
    await page.keyboard.press('Escape'); await status(page, 'dismissed');
    await focused(page, '#workspace-title');
    releaseEscape();
    await page.waitForFunction(() => !document.querySelector('#tour-help').disabled);
    await status(page, 'dismissed'); assert.equal(await page.locator('dialog[open]').count(), 0);
    await t.close();
    t = await setup(browser, { projects: [project()], storage: JSON.stringify({ version: 2, status: 'paused', stepId: 'idea', projectId: 'p1' }) });
    ({ page } = t);
    await page.getByRole('button', { name: 'Tiếp tục hướng dẫn', exact: true }).focus();
    await page.keyboard.press('Escape'); await status(page, 'dismissed'); await focused(page, '#workspace-title');
    await t.close();

    // Complete all seven steps through real UI buttons, with no questions, sections or feedback.
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
    await fill(page, '#idea', 'Một người thợ sửa xe gặp lại người bạn cũ.');
    await fill(page, '#constraints', 'Kết thúc mở.');
    let before = await buffer(page), writes = countWrites(mock);
    assert.equal(await page.getByRole('button', { name: 'Tiếp tục hướng dẫn', exact: true }).isDisabled(), true);
    assert.deepEqual(await buffer(page), before);
    assert.equal(countWrites(mock), writes);
    await click(page, 'Cùng làm rõ ý tưởng');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 3);
    assert.match(await page.locator('#tour-description').innerText(), /Làm rõ/);
    assert.match(await page.getByRole('list', { name: 'Cách thực hiện' }).innerText(), /Trả lời.*quyết định sau/s);
    await click(page, 'Thực hành');
    await focused(page, '#answer-0');
    for (let i = 0; i < await page.locator('[data-answer-open]').count(); i++) await answer(page, i, 'Giữ kết mở.');
    await click(page, 'Tiếp tục');
    await click(page, 'Hỏi thêm từ câu trả lời của tôi');
    await page.waitForFunction(() => document.querySelectorAll('[data-answer-open]').length === 8);
    for (const i of [6, 7]) await answer(page, i, 'Giữ chi tiết im lặng.');
    await click(page, 'Tiếp tục');
    await click(page, 'Sửa câu trả lời 1');
    await page.locator('#answer-0').fill('Kết mở, dừng trước khi con trả lời.');
    await click(page, 'Xong');
    assert.equal(await page.locator('[data-tour-action="plan"]').count(), 0, 'answers alone do not approve planning');
    await click(page, 'Tạo bản phát triển từ lựa chọn của tôi');
    assert.equal(mock.projects[0].answers[0], 'Kết mở, dừng trước khi con trả lời.');
    assert.equal(mock.projects[0].answers.length, 8);
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 4);
    await click(page, 'Thực hành');
    await fill(page, '#draft-logline', 'Bản sửa chưa lưu của tác giả.');
    before = await buffer(page); writes = countWrites(mock);
    await click(page, 'Tiếp tục hướng dẫn'); await page.getByRole('dialog').waitFor();
    if (await page.getByText('Bước 5/7', { exact: true }).count()) { await click(page, 'Tiếp'); await step(page, 6); await click(page, 'Tiếp'); }
    await step(page, 7);
    await click(page, 'Hoàn tất hướng dẫn'); await status(page, 'completed');
    assert.deepEqual(await buffer(page), before);
    assert.equal(countWrites(mock), writes, 'finishing never saves or reviews');
    await focused(page, '[data-tour-action="save"]');
    await click(page, 'Lưu thay đổi');
    await page.reload(); await click(page, 'Hướng dẫn sử dụng'); await step(page, 4);
    assert.equal(await page.getByText('Bắt đầu cùng FirstFrame', { exact: true }).count(), 0);
    await click(page, 'Tiếp'); await step(page, 5); await click(page, 'Tiếp'); await step(page, 6); await click(page, 'Tiếp'); await step(page, 7);
    await click(page, 'Hoàn tất hướng dẫn');
    await focused(page, '#save-status');
    await t.close();

    // Existing analysis keeps language help available and focuses the first unanswered question.
    const questions = { ...project(), analysis: { ...analysis(), missing_information: ['Bạn muốn kết thúc thế nào?', 'Điều gì cần giữ?'] }, answers: ['Kết thúc mở', ''] };
    t = await setup(browser, { projects: [questions] }); ({ page, mock } = t);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 3);
    before = await buffer(page); writes = countWrites(mock);
    await click(page, 'Trước'); await step(page, 2); await click(page, 'Thực hành');
    await focused(page, '#idea');
    assert.deepEqual(await buffer(page), before); assert.equal(countWrites(mock), writes);
    await select(page, '#response-language', 'en');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 3); await click(page, 'Thực hành');
    await focused(page, '#answer-1');
    assert.equal(await page.locator('[data-tour-action="plan"]').count(), 0);
    await page.getByRole('button', { name: 'Để quyết định sau', exact: true }).click();
    assert.equal(countWrites(mock), writes);
    await click(page, 'Tạo bản phát triển từ lựa chọn của tôi');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 4);
    assert.equal(mock.projects[0].response_language, 'en');
    assert.match(mock.projects[0].answers[1], /Chưa quyết định/);
    await t.close();

    // A saved draft must not outrank a changed brief, even after the save clears analysis.
    t = await setup(browser, { projects: [fullProject('p1')] }); ({ page, mock } = t);
    assert.equal(await page.getByText('Bắt đầu cùng FirstFrame', { exact: true }).count(), 0);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 4); await click(page, 'Thực hành');
    await fill(page, '#idea', 'Một ý tưởng hoàn toàn khác.');
    await page.getByText(/Ý tưởng đã thay đổi\. Làm rõ lại/).waitFor();
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
    await fill(page, '#idea', 'Ý tưởng đã sửa nhưng chưa lưu.');
    before = await buffer(page); mock.failSave = true;
    await click(page, 'Cùng làm rõ ý tưởng'); await status(page, 'paused');
    assert.equal(mock.calls.filter(c => /\/(clarify|analyze)\/stream$/.test(c.pathname)).length, 0);
    assert.deepEqual(await buffer(page), before);
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 2); await click(page, 'Thực hành');
    mock.failSave = false; mock.failAI = true;
    await click(page, 'Cùng làm rõ ý tưởng'); await status(page, 'paused');
    assert.equal(JSON.parse(await page.evaluate(key => localStorage.getItem(key), key)).stepId, 'idea');
    const errorBeforeHelp = await page.locator('.error[role="alert"]').innerText();
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 2);
    assert.equal(await page.locator('.error[role="alert"]').innerText(), errorBeforeHelp, 'manual help preserves existing error');
    assert.deepEqual(await buffer(page), before);
    await t.close();

    // Reload resumes only on request, and switching projects resolves the new project's entry.
    t = await setup(browser, { projects: [project(), fullProject('p2')] }); ({ page, mock } = t);
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Thực hành');
    writes = countWrites(mock);
    await page.reload();
    await page.getByRole('button', { name: 'Tiếp tục hướng dẫn', exact: true }).waitFor();
    assert.equal(await page.locator('dialog[open]').count(), 0); assert.equal(countWrites(mock), writes);
    await select(page, '#project-picker', 'p2');
    await click(page, 'Tiếp tục hướng dẫn'); await step(page, 4);
    await t.close();

    // Another tab dismisses the tour while its analyze request is pending.
    t = await setup(browser, { projects: [project()] }); ({ page, mock } = t);
    let release; mock.hold = new Promise(resolve => { release = resolve; });
    await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Thực hành');
    await click(page, 'Cùng làm rõ ý tưởng');
    await page.waitForFunction(() => document.querySelector('[data-tour="new-project"]').disabled);
    const second = await t.context.newPage(); await second.goto(url);
    await second.evaluate(key => localStorage.setItem(key, JSON.stringify({ version: 2, status: 'dismissed', stepId: 'idea', projectId: 'p1' })), key);
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
    await page.locator('[data-tour="idea"]').evaluate(n => n.remove());
    await status(page, 'paused'); assert.equal(await page.locator('dialog[open]').count(), 0);
    await t.close();
    t = await setup(browser, { projects: [fullProject('p1')], viewport: { width: 390, height: 844 } }); ({ page } = t);
    await click(page, 'Hướng dẫn sử dụng'); await step(page, 4);
    await page.screenshot({ path: path.join(screenshots, 'mobile.png') });
    await page.setViewportSize({ width: 320, height: 260 });
    await page.waitForFunction(() => {
      const r = document.querySelector('.tour-card').getBoundingClientRect();
      return r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight;
    });
    assert.equal(await page.locator('.tour-spotlight').count(), 0);
    assert.match(await page.locator('#tour-description').innerText(), /card/);
    await click(page, 'Tiếp'); await step(page, 5); await click(page, 'Tiếp'); await step(page, 6); await click(page, 'Tiếp'); await step(page, 7); await click(page, 'Hoàn tất hướng dẫn');
    await t.close();

    // Every stage stays highlighted and agrees with the rail, even with long content.
    for (const viewport of [{ width: 897, height: 771 }, { width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      t = await setup(browser, { projects: [fullProject('p1')], viewport }); ({ page, mock } = t);
      const calls = clone(mock.calls);
      await page.locator('.scene-outline, .screenplay, .clarification-conversation').evaluateAll(nodes => {
        for (const node of nodes) node.style.minHeight = '2400px';
      });
      await click(page, 'Hướng dẫn sử dụng'); await step(page, 4);
      await click(page, 'Trước'); await click(page, 'Trước'); await step(page, 2);
      for (const [index, name] of ['idea', 'choices', 'draft', 'outline', 'script'].entries()) {
        await step(page, index + 2);
        assert.equal(await page.locator(`[data-tour="${name}"]`).evaluate(n => n.tagName), 'H2');
        await page.locator('.tour-spotlight').waitFor({ state: 'visible' });
        assert.equal(await page.locator('.workspace-stage-nav [aria-current="step"]').count(), 1);
        const label = await page.locator('#tour-title').innerText();
        assert.ok((await page.locator('.workspace-stage-nav [aria-current="step"]').innerText()).includes(label));
        await page.screenshot({ path: path.join(screenshots, `tour-${name}-${viewport.width}.png`) });
        await click(page, 'Thực hành');
        await focused(page, { idea: '#idea', choices: '[data-choice-review]', draft: '#draft-logline', outline: '#workspace-outline', script: '#workspace-script' }[name]);
        await click(page, 'Tiếp tục hướng dẫn');
      }
      await step(page, 7);
      await click(page, 'Hoàn tất hướng dẫn'); await status(page, 'completed');
      assert.deepEqual(mock.calls, calls, 'tour navigation makes no API requests');
      await t.close();
    }

    // Reading uses the entire working buffer, never a saved copy or a new AI result.
    const readingProject = {
      ...fullProject('p1'), constraints: ['Giữ kết thúc mở'], answers: ['Chưa quyết định'],
      analysis: { ...analysis(), missing_information: ['Điều gì cần giữ?'] },
      draft: { title: 'Bữa cơm muộn', logline: 'Mẹ để phần cơm cho con.', sections: [
        { title: 'Beginning', purpose: 'Mở đầu', content: 'Con mở cửa.\nQuạt vẫn quay.' },
        { title: 'Middle', purpose: 'Diễn tiến', content: 'Mẹ đẩy bát cơm sang.' },
        { title: 'Ending', purpose: 'Kết thúc', content: 'Hai mẹ con ngồi im.' },
        { title: 'Tone', purpose: 'Sắc thái', content: 'Lặng lẽ, không hòa giải.' },
        { title: 'Ghi chú riêng', purpose: 'Ghi chú', content: '<script>Không thực thi</script>' },
      ] },
      feedback: { passed: true, rubric_scores: {}, findings: [] }, feedback_is_current: true,
      versions: [{ id: 'v1', created_at: '2026-10-21T10:00:00Z', idea: 'Nguồn bản cũ',
        constraints: [], questions: [], answers: [], draft: draft(), feedback: null }],
    };
    for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      t = await setup(browser, { projects: [readingProject], viewport }); ({ page, mock } = t);
      const reading = page.locator('.story-draft-editor');
      assert.match(await reading.innerText(), /Bản đang viết · Đã lưu/);
      assert.equal(await reading.locator('.story-field-title .story-field-value').textContent(), 'Bữa cơm muộn');
      assert.equal(await reading.locator('.story-draft-path .story-field-value').first().textContent(), 'Con mở cửa.');
      assert.equal(await reading.locator('.story-draft-path > li').count(), 4);
      const tourCalls = clone(mock.calls), tourBuffer = await buffer(page);
      await click(page, 'Hướng dẫn sử dụng'); await step(page, 4);
      assert.match(await page.getByRole('list', { name: 'Cách thực hiện' }).innerText(), /Sửa từng card.*Xong.*Lưu thay đổi/s);
      await page.screenshot({ path: path.join(screenshots, `new-workflow-tour-${viewport.width}.png`) });
      await click(page, 'Thử xem góp ý');
      await focused(page, '.card-feedback-trigger');
      assert.equal(await page.locator('.card-feedback').count(), 0, 'tour focuses the trigger without selecting a card or calling AI');
      await click(page, 'Tiếp tục hướng dẫn'); await page.getByRole('dialog').waitFor();
    if (await page.getByText('Bước 5/7', { exact: true }).count()) { await click(page, 'Tiếp'); await step(page, 6); await click(page, 'Tiếp'); }
    await step(page, 7);
      await click(page, 'Khám phá đề xuất và lịch sử');
      await focused(page, '.workspace-library > summary');
      await click(page, 'Tiếp tục hướng dẫn'); await page.getByRole('dialog').waitFor();
    if (await page.getByText('Bước 5/7', { exact: true }).count()) { await click(page, 'Tiếp'); await step(page, 6); await click(page, 'Tiếp'); }
    await step(page, 7);
      await click(page, 'Hoàn tất hướng dẫn');
      assert.deepEqual(await buffer(page), tourBuffer);
      assert.deepEqual(mock.calls, tourCalls, 'new tour shortcuts never save, restore or call AI');
      await toggle(page, page.locator('.feedback-section'));
      assert.match(await page.locator('.feedback-section').innerText(), /Phản hồi cho đúng bản hiện tại/);
      const serverBefore = clone(mock.projects), callsBefore = clone(mock.calls);
      await fill(page, '#project-title', 'Tên dự án chưa lưu');
      await select(page, '#response-language', 'en');
      await answer(page, 0, 'Giữ sự lặng lẽ, chưa chốt kết thúc');
      await (await edit(page, 'draft-title')).fill('Tên phim tác giả đang sửa');
      await (await edit(page, 'draft-logline')).fill('Tóm tắt mới chưa lưu.');
      for (let i = 0; i < readingProject.draft.sections.length; i++) {
        await (await edit(page, `section-${i}`)).fill(`Bản sửa ${i}\nDòng hai của tác giả.`);
      }
      while (await reading.getByRole('button', { name: 'Xong', exact: true }).count()) await reading.getByRole('button', { name: 'Xong', exact: true }).first().click();
      before = await buffer(page);
      assert.match(await reading.innerText(), /Có thay đổi chưa lưu/);
      assert.match(await reading.innerText(), /Tên phim tác giả đang sửa/);
      assert.match(await reading.innerText(), /Tóm tắt mới chưa lưu/);
      for (let i = 0; i < 3; i++) assert.ok((await reading.innerText()).includes(`Bản sửa ${i}\nDòng hai của tác giả.`));
      await reading.locator('summary').click();
      assert.equal(await reading.getByText('Bản sửa 3', { exact: false }).isVisible(), false);
      await reading.locator('summary').click();
      for (let i = 3; i < 5; i++) assert.ok((await reading.innerText()).includes(`Bản sửa ${i}\nDòng hai của tác giả.`));
      assert.match(await page.locator('.feedback-section').innerText(), /thuộc bản trước/);
      await edit(page, 'draft-logline'); await focused(page, '#draft-logline');
      assert.deepEqual(await buffer(page), before, 'reading and focusing preserve every editable field');
      assert.deepEqual(mock.calls, callsBefore, 'reading/focusing sends no requests, including AI');
      assert.deepEqual(mock.projects, serverBefore, 'reading never changes saved data or history');
      assert.equal(await page.evaluate(() => {
        const event = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(event); return event.defaultPrevented;
      }), true, 'unsaved work still has the leave warning');
      assert.equal(await reading.evaluate(el => el.scrollWidth <= el.clientWidth), true, 'reader fits viewport');
      await reading.screenshot({ path: path.join(screenshots, `story-reading-${viewport.width}.png`) });
      mock.failSave = true;
      await click(page, 'Lưu thay đổi'); await page.locator('.error[role="alert"]').waitFor();
      assert.deepEqual(await buffer(page), before, '409 preserves the complete buffer');
      assert.deepEqual(mock.projects, serverBefore, '409 preserves saved draft and history');
      assert.match(await reading.innerText(), /Có thay đổi chưa lưu/);
      writes = countWrites(mock);
      await edit(page, 'draft-logline'); await focused(page, '#draft-logline');
      assert.equal(countWrites(mock), writes, 'navigation after failure does not retry the save');
      mock.failSave = false;
      await click(page, 'Lưu thay đổi');
      await page.getByText('Đã lưu thay đổi.', { exact: true }).waitFor();
      assert.deepEqual(await buffer(page), before);
      assert.match(await reading.innerText(), /Bản đang viết · Đã lưu/);
      assert.deepEqual(mock.projects[0].versions, serverBefore[0].versions);
      await page.reload(); await reading.waitFor();
      assert.deepEqual(await buffer(page), before, 'save/reopen preserves the exact edited content');
      assert.match(await reading.innerText(), /Tóm tắt mới chưa lưu/);
      assert.equal(mock.calls.some(c => /\/(clarify|analyze|plan|review)(\/stream)?$/.test(c.pathname)), false);
      await t.close();
    }
    t = await setup(browser, { projects: [project()] }); ({ page, mock } = t);
    assert.equal(await page.locator('.story-draft-editor').count(), 0, 'no draft means no invented reader');
    assert.equal(await page.locator('#idea').getAttribute('aria-describedby'), 'idea-help');
    await page.locator('.workspace-tools summary').click();
    assert.equal(await page.getByRole('link', { name: 'Đánh giá chất lượng dataset' }).isVisible(), true);
    assert.equal(countWrites(mock), 0);
    await t.close();
    t = await setup(browser, { projects: [fullProject('p1')] }); ({ page, mock } = t);
    assert.match(await page.locator('.story-draft-editor').innerText(), /Chưa có nội dung phác thảo/);
    assert.equal(await (await edit(page, 'draft-logline')).inputValue(), draft().logline);
    assert.equal(countWrites(mock), 0, 'legacy empty sections remain editable without AI');
    await t.close();
    t = await setup(browser, { projects: [{ ...fullProject('p1'), draft: {
      title: '', logline: ' ', sections: [{ title: 'Beginning', purpose: '', content: '' }],
    } }] }); ({ page, mock } = t);
    const emptyReading = await page.locator('.story-draft-editor').innerText();
    assert.match(emptyReading, /Chưa có nội dung/);
    assert.equal(await (await edit(page, 'draft-title')).inputValue(), '');
    assert.equal(await (await edit(page, 'draft-logline')).inputValue(), ' ');
    assert.equal(countWrites(mock), 0, 'empty values get labels, never generated content');
    await t.close();

    // The context card displays the server's saved projection, never a client-side merge.
    const intentA = { idea: 'Ý đồ A: giữ sự lặng lẽ.', constraints: ['Không thêm cãi vã'], clarifications: [
      { question: 'Lựa chọn giữ từ lượt trước?', answer: 'Một chiếc quạt cũ.', input_index: null },
      { question: 'Điều gì cần giữ?', answer: 'Chưa quyết định. Đây vẫn là lời tác giả.', input_index: 0 },
    ], pending_questions: [{ question: 'Hình ảnh cuối là gì?', input_index: 1 }] };
    const sourceA = { project_id: 'p1', artifact_id: 'f1', revision: 3, content_key: 'saved-source-a',
      context: intentA, draft: draft() };
    const intentProject = { ...fullProject('p1'), revision: 4, idea: intentA.idea, constraints: intentA.constraints,
      author_context: intentA, analysis: { ...analysis(), summary: 'AI tự đề xuất hòa giải.',
        missing_information: ['Điều gì cần giữ?', 'Hình ảnh cuối là gì?'] },
      answers: [intentA.clarifications[1].answer, ''], feedback: { artifact_id: 'f1', passed: true, rubric_scores: {}, findings: [] },
      feedback_is_current: true, feedback_source: sourceA, versions: [{ id: 'v1', created_at: '2026-10-22T10:00:00Z',
        idea: intentA.idea, constraints: intentA.constraints, questions: [], answers: [], draft: draft(),
        feedback: { artifact_id: 'f1', passed: true, rubric_scores: {}, findings: [] }, feedback_source: sourceA }] };
    const intentB = { idea: 'Ý đồ B: một chuyện vui ở bến xe.', constraints: ['Giữ sự hài hước'], clarifications: [], pending_questions: [] };
    for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      t = await setup(browser, { projects: [intentProject], viewport }); ({ page, mock } = t);
      await page.locator('.workspace-author-context > summary').click();
      const card = page.getByRole('region', { name: 'Ý đồ đã lưu hiện tại', exact: true });
      assert.match(await card.innerText(), /revision 4/);
      assert.match(await card.innerText(), /Một chiếc quạt cũ/);
      assert.match(await card.innerText(), /Chưa quyết định. Đây vẫn là lời tác giả/);
      assert.doesNotMatch(await card.innerText(), /AI tự đề xuất hòa giải/);
      await card.screenshot({ path: path.join(screenshots, `author-intent-with-choices-${viewport.width}.png`) });
      before = await buffer(page); const callsBefore = clone(mock.calls);
      await click(page, 'Chỉnh câu trả lời 2'); await focused(page, '#answer-0');
      await click(page, 'Trả lời câu hỏi 2'); await focused(page, '#answer-1');
      await click(page, 'Chỉnh điều muốn giữ'); await focused(page, '#constraints');
      await click(page, 'Chỉnh khoảnh khắc'); await focused(page, '#idea');
      assert.deepEqual(await buffer(page), before); assert.deepEqual(mock.calls, callsBefore);
      const feedbackSource = page.locator('.feedback-section .feedback-context');
      await toggle(page, feedbackSource);
      assert.match(await feedbackSource.innerText(), /Ý đồ A/);
      assert.equal(await feedbackSource.getByRole('button').count(), 0, 'feedback context is always read-only');
      await fill(page, '#project-title', 'Tên dự án chưa lưu');
      await (await edit(page, 'draft-logline')).fill('Bản sửa của tác giả chưa lưu');
      await answer(page, 0, 'Tôi thay câu trả lời nhưng chưa lưu');
      await fill(page, '#idea', intentB.idea);
      await fill(page, '#constraints', intentB.constraints[0]);
      before = await buffer(page);
      assert.match(await card.innerText(), /Có thay đổi chưa lưu/);
      assert.match(await card.innerText(), /Ý đồ A/); assert.doesNotMatch(await card.innerText(), /Ý đồ B/);
      assert.equal(await card.getByRole('button', { name: /Chỉnh câu trả lời/ }).count(), 0, 'hidden answer fields are not navigation targets');
      mock.failSave = true;
      await click(page, 'Lưu thay đổi'); await page.locator('.error[role="alert"]').waitFor();
      assert.deepEqual(await buffer(page), before);
      assert.match(await card.innerText(), /revision 4/); assert.match(await card.innerText(), /Ý đồ A/);
      assert.match(await feedbackSource.innerText(), /Ý đồ A/);
      writes = countWrites(mock);
      await click(page, 'Chỉnh khoảnh khắc'); await focused(page, '#idea');
      assert.equal(countWrites(mock), writes, 'context navigation cannot retry a failed save');
      mock.failSave = false;
      mock.savePatch = { author_context: intentB, feedback_is_current: false };
      await click(page, 'Lưu thay đổi'); await page.getByText('Đã lưu thay đổi.', { exact: true }).waitFor();
      assert.deepEqual(await buffer(page), before);
      assert.match(await card.innerText(), /Ý đồ B/); assert.doesNotMatch(await card.innerText(), /Ý đồ A|Một chiếc quạt cũ/);
      assert.match(await feedbackSource.innerText(), /Ý đồ A/); assert.doesNotMatch(await feedbackSource.innerText(), /Ý đồ B/);
      const oldVersion = page.locator('.version-history > details').first();
      await toggle(page, oldVersion);
      await oldVersion.locator('.feedback-context summary').click();
      assert.match(await oldVersion.locator('.feedback-context').innerText(), /Ý đồ A/);
      assert.equal(await oldVersion.locator('.feedback-context button').count(), 0);
      await card.screenshot({ path: path.join(screenshots, `author-intent-${viewport.width}.png`) });
      await page.reload(); await page.locator('.workspace-author-context > summary').click(); await card.waitFor();
      assert.match(await card.innerText(), /Ý đồ B/);
      await toggle(page, feedbackSource); assert.match(await feedbackSource.innerText(), /Ý đồ A/);
      assert.deepEqual(mock.projects[0].feedback_source, sourceA);
      assert.equal(mock.calls.some(c => /\/(clarify|analyze|plan|review)(\/stream)?$/.test(c.pathname)), false);
      await t.close();
    }
    // The server may have saved B even though the response was lost; A remains the last confirmed card.
    t = await setup(browser, { projects: [intentProject] }); ({ page, mock } = t);
    await fill(page, '#idea', intentB.idea); before = await buffer(page);
    mock.savePatch = { author_context: intentB }; mock.loseSaveResponse = true;
    await click(page, 'Lưu thay đổi'); await page.locator('.error[role="alert"]').waitFor();
    assert.deepEqual(await buffer(page), before);
    assert.equal(mock.projects[0].idea, intentB.idea, 'server committed before losing response');
    await page.locator('.workspace-author-context > summary').click();
    const confirmed = page.getByRole('region', { name: 'Ý đồ đã lưu hiện tại', exact: true });
    assert.match(await confirmed.innerText(), /Ý đồ A/); assert.match(await confirmed.innerText(), /bản cuối đã xác nhận/);
    assert.deepEqual(mock.projects[0].feedback_source, sourceA);
    assert.equal(countWrites(mock), 1, 'uncertain save is not retried automatically');
    await t.close();
    for (const source of [null, { ...sourceA, project_id: 'other-project' }, { ...sourceA, artifact_id: 'other-feedback' }]) {
      t = await setup(browser, { projects: [{ ...intentProject, feedback_source: source }] }); ({ page, mock } = t);
      const missing = page.locator('.feedback-section .feedback-context');
      await toggle(page, missing);
      assert.match(await missing.innerText(), /Chưa có đủ thông tin nguồn/);
      assert.doesNotMatch(await missing.innerText(), /Ý đồ A/);
      assert.equal(countWrites(mock), 0);
      await t.close();
    }
    // Manual revision is local to one feedback artifact, with no inferred field targets or auto-apply.
    const finding = (criterion_id, message) => ({ criterion_id, message, severity: 'info', score: null });
    const revisionDraft = { title: 'Bữa cơm', logline: 'Mẹ đợi con ăn cơm.', sections: [
      { title: 'Beginning', purpose: 'Mở đầu', content: 'Tiếng quạt quay.' },
      { title: 'Middle', purpose: 'Diễn tiến', content: 'Mẹ đẩy bát cơm sang.' },
      { title: 'Ending', purpose: 'Kết thúc', content: 'Hai người ngồi im.' },
    ] };
    const issue = 'Ending: hãy cân nhắc nhịp dừng.\nĐây là nhận định để tác giả xem lại.';
    const proposal = 'Giữ kết mở; thử để tiếng quạt thay lời giải thích, nếu phù hợp với ý bạn.';
    const revisionFeedback = { artifact_id: 'f1', passed: true, rubric_scores: {}, findings: [
      finding('strength-1', 'Giữ tiếng quạt trong khoảng lặng.'),
      finding('weakness-1', issue), finding('weakness-2', issue), finding('suggestion-1', proposal),
    ] };
    const revisionProject = { ...intentProject, draft: revisionDraft, feedback: revisionFeedback,
      feedback_source: { ...sourceA, draft: revisionDraft }, versions: [] };
    const chooseIssue = 'Chọn điểm yếu 2 để tự sửa', chooseProposal = 'Chọn gợi ý cải thiện 1 để tự sửa';
    for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      t = await setup(browser, { projects: [revisionProject], viewport, mock: { recordVersions: true } }); ({ page, mock } = t);
      const note = page.locator('.revision-note');
      await fill(page, '#project-title', 'Tên dự án đang sửa');
      before = await buffer(page); writes = countWrites(mock);
      const requestsBefore = clone(mock.calls), storedBefore = clone(mock.projects);
      await reveal(page, page.getByRole('button', { name: chooseIssue, exact: true, includeHidden: true })); await page.getByRole('button', { name: chooseIssue, exact: true }).focus(); await page.keyboard.press('Enter');
      await focused(page, '#selected-feedback-title');
      assert.equal(await note.locator('.preserve-lines').first().textContent(), issue);
      assert.equal(await page.locator('.feedback-choice[aria-pressed="true"]').count(), 1, 'duplicate messages keep distinct selection');
      await click(page, chooseProposal); await focused(page, '#selected-feedback-title');
      assert.equal(await note.locator('.preserve-lines').first().textContent(), proposal, 'suggestion is not paired with a weakness by index');
      assert.deepEqual(await buffer(page), before); assert.deepEqual(mock.calls, requestsBefore);
      assert.deepEqual(mock.projects, storedBefore);
      await click(page, 'Bỏ chọn góp ý này'); await focused(page, '#draft-editor-title');
      assert.equal(await note.count(), 0); assert.deepEqual(await buffer(page), before); assert.equal(countWrites(mock), writes);
      await click(page, chooseIssue); await focused(page, '#selected-feedback-title');
      await (await edit(page, 'draft-logline')).fill('Tác giả giữ sự chăm sóc qua hành động.');
      await (await edit(page, 'section-1')).fill('Mẹ đẩy bát cơm. Con kéo ghế ngồi xuống.');
      before = await buffer(page); const edited = clone(mock.projects[0].draft);
      edited.logline = await (await edit(page, 'draft-logline')).inputValue(); edited.sections[1].content = await (await edit(page, 'section-1')).inputValue();
      assert.match(await note.innerText(), /thuộc bản trước/);
      assert.equal(await page.getByRole('button', { name: chooseProposal }).isDisabled(), true);
      assert.deepEqual(mock.calls, requestsBefore, 'selection and typing send no requests');
      await note.screenshot({ path: path.join(screenshots, `manual-revision-${viewport.width}.png`) });
      mock.failSave = true;
      await click(page, 'Nhận phản hồi trên bản hiện tại'); await page.locator('.error[role="alert"]').waitFor();
      assert.deepEqual(await buffer(page), before); assert.equal(mock.calls.some(c => c.pathname.endsWith('/review/stream')), false);
      assert.deepEqual(mock.projects, storedBefore); assert.match(await note.innerText(), /thuộc bản trước/);
      mock.failSave = false; mock.failAI = true;
      await click(page, 'Nhận phản hồi trên bản hiện tại');
      await page.getByText('Không bắt đầu được thao tác. Bản đang sửa vẫn được giữ.', { exact: true }).waitFor();
      assert.deepEqual(mock.projects[0].draft, edited, 'AI failure never rolls back the saved manual draft');
      assert.deepEqual(mock.projects[0].feedback, revisionFeedback);
      assert.deepEqual(await buffer(page), before); assert.match(await note.innerText(), /thuộc bản trước/);
      assert.equal(mock.projects[0].versions.length, 1);
      mock.failAI = false;
      const reviewRevision = mock.projects[0].revision;
      mock.reviewPatch = { feedback: { artifact_id: 'f2', passed: true, rubric_scores: {}, findings: [finding('suggestion-1', proposal)] },
        feedback_is_current: true, feedback_source: { ...sourceA, artifact_id: 'f2', revision: reviewRevision,
          content_key: 'edited-source', draft: edited } };
      await click(page, 'Nhận phản hồi trên bản hiện tại');
      await page.getByText('Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.', { exact: true }).waitFor();
      assert.equal(await note.count(), 0, 'new feedback clears the previous artifact selection');
      assert.equal(mock.calls.filter(c => c.pathname.endsWith('/review/stream')).at(-1).body.revision, reviewRevision);
      assert.deepEqual(mock.projects[0].feedback_source.draft, edited);
      assert.deepEqual(await buffer(page), before);
      await page.reload(); await (await edit(page, 'draft-logline')).waitFor();
      assert.deepEqual(await buffer(page), before); assert.equal(await note.count(), 0, 'selection is not stored across reload');
      const version = page.locator('.version-history > details').first(); await toggle(page, version);
      assert.equal(await version.locator('.feedback-choice').count(), 0, 'history remains read-only');
      await click(page, chooseProposal); await focused(page, '#selected-feedback-title');
      await version.getByRole('button', { name: 'Dùng lại bản phát triển này', exact: true }).click();
      await page.getByText('Đã dùng lại nội dung bản phát triển. Các phiên bản trước vẫn được giữ.', { exact: true }).waitFor();
      assert.equal(await note.count(), 0, 'restore clears the selected note even when feedback ID is unchanged');
      assert.deepEqual(mock.projects[0].draft, revisionDraft);
      assert.deepEqual(mock.projects[0].feedback_source.draft, edited, 'restore does not rebind feedback to the restored draft');
      assert.ok(mock.projects[0].versions.some(v => v.feedback_source?.artifact_id === 'f1'));
      assert.ok(mock.calls.filter(c => c.body).every(c => !('selectedFeedback' in c.body)), 'selection never enters API payloads');
      await t.close();
    }
    // Another window saves while review is pending. Its late result must conflict, not replace either buffer.
    t = await setup(browser, { projects: [revisionProject], mock: { recordVersions: true } }); ({ page, mock } = t);
    await click(page, chooseIssue); await (await edit(page, 'draft-logline')).fill('Bản sửa cửa sổ một.');
    before = await buffer(page);
    let releaseReview; mock.hold = new Promise(resolve => { releaseReview = resolve; });
    const reviewStarted = page.waitForRequest(request => request.method() === 'POST' && request.url().endsWith('/review/stream'));
    await click(page, 'Nhận phản hồi trên bản hiện tại');
    await reviewStarted;
    await page.waitForFunction(() => document.querySelector('.project-fields').disabled);
    const peer = await t.context.newPage(); await peer.goto(url); await (await edit(peer, 'draft-logline')).waitFor();
    await (await edit(peer, 'draft-logline')).fill('Bản mới hơn từ cửa sổ hai.');
    await click(peer, 'Lưu thay đổi'); await peer.getByText('Đã lưu thay đổi.', { exact: true }).waitFor();
    releaseReview(); await page.locator('.error[role="alert"]').waitFor();
    assert.deepEqual(await buffer(page), before);
    assert.equal(mock.projects[0].draft.logline, 'Bản mới hơn từ cửa sổ hai.');
    assert.equal(await (await edit(peer, 'draft-logline')).inputValue(), 'Bản mới hơn từ cửa sổ hai.');
    assert.deepEqual(mock.projects[0].feedback, revisionFeedback);
    assert.equal(mock.projects[0].feedback_source.artifact_id, 'f1');
    assert.match(await page.locator('.revision-note').innerText(), /thuộc bản trước/);
    assert.equal(await (await edit(page, 'draft-logline')).isDisabled(), false, 'failed review unlocks the editor');
    await t.close();
    // Selection does not follow the author into a different project.
    t = await setup(browser, { projects: [revisionProject, { ...revisionProject, id: 'p2', title: 'Dự án hai',
      feedback_source: { ...revisionProject.feedback_source, project_id: 'p2' } }] }); ({ page } = t);
    await click(page, chooseIssue); await select(page, '#project-picker', 'p2');
    await page.waitForFunction(() => document.querySelector('#project-picker').value === 'p2' && !document.querySelector('#project-picker').disabled);
    assert.equal(await page.locator('.revision-note').count(), 0);
    await t.close();
    for (const p of [{ ...revisionProject, feedback_source: null }, { ...revisionProject,
      feedback: { ...revisionFeedback, passed: false, findings: [finding('strength-1', 'Giữ khoảng lặng.')] } }]) {
      t = await setup(browser, { projects: [p] }); ({ page, mock } = t);
      assert.equal(await page.locator('.feedback-choice:enabled').count(), 0, 'missing source and empty issue lists never invent actionable issues');
      assert.equal(await page.locator('.revision-note').count(), 0); assert.equal(countWrites(mock), 0);
      await t.close();
    }
    // A critic failure returns a durable draft/proposal, never a successful whole workflow.
    const recoveredDraft = { ...revisionDraft, title: 'Bản được giữ khi critic lỗi', logline: 'Nội dung planner đã tạo.' };
    const recoveryIntent = { ...intentA, clarifications: [...intentA.clarifications,
      { question: 'Hình ảnh cuối là gì?', answer: 'Giữ hình ảnh cuối còn mở.', input_index: 1 }], pending_questions: [] };
    const recoverySource = { ...sourceA, context: recoveryIntent, draft: revisionDraft };
    const recoveryBase = { ...revisionProject, answers: [revisionProject.answers[0], 'Giữ hình ảnh cuối còn mở.'],
      author_context: recoveryIntent, feedback_source: recoverySource };
    const generation = (existing, status = 'failed') => ({ id: 'g1', created_at: '2026-10-22T10:00:00Z',
      source_revision: 4, source_content: 'verified by backend', context: recoveryIntent, draft: recoveredDraft,
      critic_status: status, applied_revision: existing ? null : 5, feedback: null, feedback_source: null });
    const recoveryPatch = existing => ({ draft: existing ? revisionDraft : recoveredDraft,
      feedback: existing ? revisionFeedback : null, feedback_source: existing ? recoverySource : null,
      feedback_is_current: existing, plan_generations: [generation(existing)], applicable_plan_ids: existing ? ['g1'] : [] });
    const recoveredProject = existing => ({ ...recoveryBase, ...recoveryPatch(existing) });
    const proposals = page => page.getByRole('region', { name: 'Các bản do AI tạo', exact: true, includeHidden: true });
    for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      for (const existing of [false, true]) {
        const initial = { ...recoveryBase, ...(existing ? {} : { draft: null, feedback: null, feedback_source: null, feedback_is_current: false }) };
        t = await setup(browser, { projects: [initial], viewport, mock: { planPatch: recoveryPatch(existing) } }); ({ page, mock } = t);
        await confirmPlan(page);
        await page.locator('.error[role="alert"]').waitFor();
        assert.match(await page.locator('.error').innerText(), /chưa có góp ý hợp lệ/);
        assert.equal(await (await edit(page, 'draft-title')).inputValue(), existing ? revisionDraft.title : recoveredDraft.title);
        await toggle(page, proposals(page).locator(':scope > details').first());
        assert.match(await proposals(page).innerText(), /chưa có góp ý hợp lệ/);
        assert.match(await page.locator('.status-panel').innerText(), /Thao tác chưa hoàn tất/);
        const stored = clone(mock.projects), requests = clone(mock.calls);
        await toggle(page, proposals(page).locator(':scope > details').first()); await toggle(page, proposals(page).locator(':scope > details').first());
        assert.deepEqual(mock.projects, stored); assert.deepEqual(mock.calls, requests, 'viewing recovery makes no request');
        if (existing) {
          before = await buffer(page);
          await (await edit(page, 'draft-logline')).fill('Sửa chưa lưu phải giữ.');
          const acceptButton = page.getByRole('button', { name: 'Dùng bản đề xuất này', exact: true, includeHidden: true });
          const restoreButton = page.getByRole('button', { name: 'Mở lại bản đã lưu', exact: true, includeHidden: true });
          await reveal(page, acceptButton); await reveal(page, restoreButton);
          assert.equal(await acceptButton.isDisabled(), true);
          assert.equal(await restoreButton.isDisabled(), true);
          assert.deepEqual(mock.projects, stored);
          await (await edit(page, 'draft-logline')).fill(revisionDraft.logline);
          mock.loseAcceptResponse = true;
          await click(page, 'Dùng bản đề xuất này'); await page.locator('.error[role="alert"]').waitFor();
          assert.deepEqual(await buffer(page), before, 'lost acceptance response keeps the visible buffer');
          assert.equal(mock.projects[0].draft.title, recoveredDraft.title);
          const accepted = clone(mock.projects);
          mock.loseAcceptResponse = false;
          await click(page, 'Dùng bản đề xuất này'); await page.getByText('Xung đột phiên bản. Bản sửa vẫn được giữ.', { exact: true }).waitFor();
          assert.deepEqual(mock.projects, accepted, 'duplicate acceptance cannot save again');
          assert.deepEqual(await buffer(page), before);
          await click(page, 'Mở lại bản đã lưu');
          await page.getByText('Đã mở lại bản đã lưu. Không tạo lại hoặc gọi AI.', { exact: true }).waitFor();
          assert.equal(await (await edit(page, 'draft-title')).inputValue(), recoveredDraft.title);
          assert.equal(await page.locator('.feedback-section').count(), 0, 'old feedback is not attached to accepted unreviewed draft');
          assert.ok(mock.projects[0].versions.some(v => v.draft.title === revisionDraft.title));
        } else {
          assert.equal(await page.getByRole('button', { name: 'Dùng bản đề xuất này', exact: true }).count(), 0);
        }
        await page.reload(); await (await edit(page, 'draft-title')).waitFor();
        assert.equal(await (await edit(page, 'draft-title')).inputValue(), recoveredDraft.title);
        await toggle(page, proposals(page).locator(':scope > details').first());
        await proposals(page).screenshot({ path: path.join(screenshots, `plan-recovery-${existing ? 'proposal' : 'first'}-${viewport.width}.png`) });
        const savedDraft = clone(mock.projects[0].draft);
        mock.reviewPatch = { feedback: revisionFeedback, feedback_is_current: true,
          feedback_source: { ...recoverySource, draft: savedDraft, revision: mock.projects[0].revision } };
        await click(page, 'Nhận phản hồi trên bản hiện tại');
        await page.getByText('Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.', { exact: true }).waitFor();
        assert.deepEqual(mock.projects[0].draft, savedDraft);
        assert.equal(mock.calls.filter(c => c.pathname.endsWith('/plan/stream')).length, 1, 'no replan after critic failure');
        assert.equal(mock.calls.filter(c => c.pathname.endsWith('/review/stream')).length, 1);
        await t.close();
      }
    }
    // A dropped plan response can be reopened with a GET; no implicit retry or buffer replacement.
    t = await setup(browser, { projects: [{ ...recoveryBase, draft: null, feedback: null, feedback_source: null }],
      mock: { planPatch: recoveryPatch(false), losePlanResponse: true } }); ({ page, mock } = t);
    await confirmPlan(page); await page.locator('.error[role="alert"]').waitFor();
    assert.equal(await page.locator('#draft-title').count(), 0);
    assert.equal(mock.projects[0].draft.title, recoveredDraft.title);
    const writesBeforeReopen = countWrites(mock);
    await click(page, 'Mở lại bản đã lưu'); await (await edit(page, 'draft-title')).waitFor();
    assert.equal(countWrites(mock), writesBeforeReopen);
    assert.equal(await (await edit(page, 'draft-title')).inputValue(), recoveredDraft.title);
    await t.close();
    // A late acceptance from a different window conflicts and never refreshes/retries itself.
    t = await setup(browser, { projects: [recoveredProject(true)] }); ({ page, mock } = t);
    await toggle(page, proposals(page).locator(':scope > details').first()); before = await buffer(page);
    const other = await t.context.newPage(); await other.goto(url); await (await edit(other, 'draft-logline')).waitFor();
    await (await edit(other, 'draft-logline')).fill('Bản mới từ cửa sổ khác.'); await click(other, 'Lưu thay đổi');
    await other.getByText('Đã lưu thay đổi.', { exact: true }).waitFor();
    const peerStored = clone(mock.projects);
    await click(page, 'Dùng bản đề xuất này'); await page.locator('.error[role="alert"]').waitFor();
    assert.deepEqual(await buffer(page), before); assert.deepEqual(mock.projects, peerStored);
    assert.equal(mock.calls.filter(c => c.pathname.endsWith('/accept')).length, 1);
    await click(page, 'Mở lại bản đã lưu');
    await page.getByText('Đã mở lại bản đã lưu. Không tạo lại hoặc gọi AI.', { exact: true }).waitFor();
    assert.equal(await (await edit(page, 'draft-logline')).inputValue(), 'Bản mới từ cửa sổ khác.');
    assert.equal(await page.getByRole('button', { name: 'Dùng bản đề xuất này', exact: true }).isDisabled(), true);
    assert.match(await proposals(page).innerText(), /chỉ để tham khảo/);
    await t.close();
    // Successful regeneration also waits for acceptance and keeps its own critic source.
    const reviewedGeneration = { ...generation(true, 'reviewed'), feedback: { ...revisionFeedback, artifact_id: 'f2' },
      feedback_source: { ...recoverySource, artifact_id: 'f2', draft: recoveredDraft } };
    t = await setup(browser, { projects: [recoveryBase], mock: { planPatch: { ...recoveryPatch(true),
      plan_generations: [reviewedGeneration] } } }); ({ page, mock } = t);
    await click(page, chooseIssue); await confirmPlan(page);
    await page.getByText('Đã giữ bản đề xuất cùng góp ý riêng. Bản đang viết chỉ thay khi bạn chọn nhận.', { exact: true }).waitFor();
    assert.equal(await (await edit(page, 'draft-title')).inputValue(), revisionDraft.title);
    await toggle(page, proposals(page).locator(':scope > details').first());
    const beforeViewing = clone(mock.calls);
    await proposals(page).getByText('Ý đồ khi tạo bản này', { exact: true }).click();
    assert.match(await proposals(page).innerText(), new RegExp(sourceA.context.idea));
    assert.deepEqual(mock.calls, beforeViewing);
    const modelCalls = mock.calls.filter(c => c.pathname.endsWith('/stream')).length;
    await click(page, 'Dùng bản đề xuất này');
    await page.getByText('Đã nhận bản đề xuất. Bản trước được giữ trong lịch sử; có thể sửa và nhận phản hồi riêng.', { exact: true }).waitFor();
    assert.equal(await (await edit(page, 'draft-title')).inputValue(), recoveredDraft.title);
    assert.equal(mock.projects[0].feedback_source.artifact_id, 'f2');
    assert.deepEqual(mock.projects[0].feedback_source.draft, recoveredDraft);
    assert.equal(await page.locator('.revision-note').count(), 0);
    assert.equal(mock.calls.filter(c => c.pathname.endsWith('/stream')).length, modelCalls);
    await t.close();
    console.log('Plan recovery checks passed: durable first draft and separate proposal, explicit acceptance, dirty-buffer guard, lost plan/accept responses, no automatic retry, concurrent edits, old feedback isolation, reopen and review without replanning, desktop/mobile.');
    console.log('Manual revision checks passed: artifact-bound local selection, refusal, keyboard focus, no requests or rewrites, stale notes, save and AI failures, review/reopen, restore, history, project switch, concurrent saves and late conflicts.');
    console.log('Browser tour checks passed: full flow, no tour writes, buffers, keyboard, conditional data, failures, reload, project switch, cross-tab dismissal, storage, missing anchors and mobile viewport.');
    console.log('Story-plan reading checks passed: current buffer, optional details, zero navigation requests, stale feedback, leave warning, 409 preservation, save/reopen, missing data and desktop/mobile layouts.');
    console.log('Author-context checks passed: backend projection, retained/open/pending choices, no navigation requests, saved A/buffer B, 409 and lost-response preservation, historical provenance, reload, missing/mismatched sources and desktop/mobile.');
    console.log(`Screenshots: ${screenshots}`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
