// Snapshot-bound #7 navigation. All requests are intercepted; no model or real data.
const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { setup, fullProject, reveal } = require('./onboarding.browser.cjs');
const engine = process.env.TOUR_BROWSER || 'chrome';
const output = process.env.TOUR_SCREENSHOTS || `/tmp/firstframe-revision-${engine}`;
const clone = x => structuredClone(x);
const writes = mock => mock.calls.filter(c => c.method !== 'GET');
const exactBuffer = page => page.evaluate(() => ({
  fields: [...document.querySelectorAll('input, textarea, select')]
    .filter(n => !n.closest('.story-field') && !n.id.startsWith('answer-')).map(n => [n.id, n.value]),
  answers: [...document.querySelectorAll('[data-answer-open]')].map(n => {
    const id = n.dataset.answerOpen;
    return [id, document.getElementById(id)?.value ?? document.getElementById(id + '-value')?.textContent];
  }),
  draft: [...document.querySelectorAll('[data-revision-target]')].map(n => [n.dataset.revisionTarget,
    n.querySelector('input, textarea')?.value ?? n.querySelector('.story-field-value').textContent]),
}));
function fixture() {
  const p = fullProject('p1');
  p.title = 'Tên dự án'; p.constraints = ['Không thoại']; p.answers = ['Giữ kết mở.'];
  p.analysis = { artifact_id: 'a1', summary: 'Tóm tắt AI không phải ý đồ.', notes: [], missing_information: ['Kết?'] };
  p.draft = { title: 'Tên phim', logline: 'Một bữa cơm.  Chưa có lời đáp.', sections: [
    { title: 'Beginning', purpose: 'Setup', content: 'Mẹ đặt bát cơm. Con kéo ghế.' },
    { title: 'Middle', purpose: 'Choice', content: 'Con nhìn mẹ.' },
    { title: 'Ending', purpose: 'Cut', content: 'Mẹ vẫn chờ.' },
    { title: 'Ending', purpose: 'Duplicate title', content: 'Con đặt tay xuống.' },
    { title: 'Main character', purpose: 'Context', content: 'Mẹ và con.\n  Không thêm ai.' },
  ] };
  p.author_context = { idea: p.idea, constraints: p.constraints,
    clarifications: [{ question: 'Kết?', answer: 'Giữ kết mở.', input_index: 0 }], pending_questions: [] };
  const note = (id, targets) => ({ note_id: id, artifact_id: 'f1', comparison: 'mismatch',
    observation: `Nhận xét ${id}`, suggestion: `Bước sửa ${id}`, decision_id: 'answer-0',
    decision_quote: 'Giữ kết mở.', decision_question: 'Kết?', targets });
  p.feedback = { artifact_id: 'f1', passed: false, rubric_scores: {}, findings: [], revision_notes: [
    note('n1', [{ target_id: 'section-3', quote: 'Con đặt tay xuống.' }]),
    note('n2', [{ target_id: 'draft-logline', quote: p.draft.logline }, { target_id: 'section-2', quote: 'Mẹ vẫn chờ.' }]),
    note('n3', [{ target_id: 'section-4', quote: p.draft.sections[4].content }]),
  ] };
  p.feedback_is_current = true;
  p.feedback_source = { project_id: p.id, artifact_id: 'f1', revision: p.revision,
    content_key: JSON.stringify({ draft: p.draft }), context: clone(p.author_context), draft: clone(p.draft) };
  return p;
}
async function openFeedback(page) {
  await reveal(page, page.locator('#workspace-feedback > summary'));
  const details = page.locator('#workspace-feedback');
  if (await details.getAttribute('open') === null) await details.locator(':scope > summary').click();
}
const actions = page => page.locator('#workspace-feedback').getByRole('button', { name: /^Sửa phần này:/ });
async function go(page, target) {
  await page.locator('#workspace-feedback').getByRole('button', { name: `Sửa phần này: ${target}`, exact: true }).click();
}
(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await ({ chrome: chromium, firefox, webkit })[engine].launch({ headless: true,
    ...(engine === 'chrome' ? { channel: 'chrome' } : {}) });
  const report = { engine, version: browser.version(), results: [] };
  async function run(name, viewport, fn, project = fixture(), mock = {}) {
    let t;
    try {
      t = await setup(browser, { viewport, projects: [project], mock });
      await t.page.locator('.story-workspace').waitFor(); await openFeedback(t.page);
      await fn(t); await t.close();
      report.results.push({ name, width: viewport.width, passed: true });
    } catch (e) {
      if (t) { await t.page.screenshot({ path: path.join(output, `${name}-${viewport.width}.png`) }).catch(() => {}); await t.context.close(); }
      report.results.push({ name, width: viewport.width, passed: false, error: e.stack }); console.error(e);
    }
  }
  try {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
      await run('duplicate-title-focus-buffer', viewport, async ({ page, mock }) => {
        await reveal(page, page.locator('#project-title'));
        await page.locator('#project-title').fill('Tên dự án chưa lưu');
        const before = await exactBuffer(page), server = clone(mock.projects), calls = mock.calls.length;
        const first = page.locator('#workspace-feedback article').first();
        assert.match(await first.innerText(), /Nhận xét n1[\s\S]*Bước sửa n1/);
        await first.scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(output, `priorities-${viewport.width}.png`) });
        await first.getByRole('button', { name: 'Sửa phần này: Kết thúc · Card 5', exact: true }).click();
        await page.waitForFunction(() => document.activeElement?.id === 'section-3');
        assert.deepEqual(await exactBuffer(page), before);
        assert.deepEqual(mock.projects, server); assert.equal(mock.calls.length, calls);
        await page.locator('#section-3').fill('Bản tự sửa chưa lưu.');
        assert.equal(await actions(page).count(), 0);
        await page.locator('#section-3').fill('Con đặt tay xuống.');
        assert.equal(await actions(page).count(), 4, 'undo to exact saved content enables navigation');
        await go(page, 'Nhân vật');
        await page.waitForFunction(() => document.activeElement?.id === 'section-4');
        assert.deepEqual(await exactBuffer(page), before); assert.equal(writes(mock).length, 0);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      });
      await run('explicit-multi-target', viewport, async ({ page, mock }) => {
        const before = await exactBuffer(page), calls = mock.calls.length;
        const pair = page.locator('#workspace-feedback article').nth(1);
        assert.match(await pair.innerText(), /Chọn phần bạn muốn tự sửa/);
        assert.equal(await pair.getByRole('button', { name: /^Sửa phần này:/ }).count(), 2);
        assert.notEqual(await page.evaluate(() => document.activeElement?.id), 'draft-logline');
        await pair.getByRole('button', { name: 'Sửa phần này: Kết thúc · Card 4', exact: true }).click();
        await page.waitForFunction(() => document.activeElement?.id === 'section-2');
        assert.deepEqual(await exactBuffer(page), before); assert.equal(mock.calls.length, calls);
        await go(page, 'Tóm tắt một câu');
        await page.waitForFunction(() => document.activeElement?.id === 'draft-logline');
        assert.deepEqual(await exactBuffer(page), before);
      });
      await run('author-buffer-and-undo', viewport, async ({ page, mock }) => {
        const before = await exactBuffer(page), calls = mock.calls.length;
        for (const id of ['idea', 'constraints']) {
          const field = page.locator(`#${id}`); await reveal(page, field);
          const original = await field.inputValue(); await field.fill(original + ' Nội dung chưa lưu.');
          assert.equal(await actions(page).count(), 0);
          await field.fill(original); assert.equal(await actions(page).count(), 4);
        }
        assert.deepEqual(await exactBuffer(page), before); assert.equal(mock.calls.length, calls);
      });
      const duplicates = fixture();
      duplicates.feedback.revision_notes = [{ ...duplicates.feedback.revision_notes[0], targets: [
        { target_id: 'section-2', quote: 'Mẹ vẫn chờ.' }, { target_id: 'section-3', quote: 'Con đặt tay xuống.' },
      ] }];
      await run('duplicate-pair-explicit-choice', viewport, async ({ page, mock }) => {
        assert.equal(await actions(page).count(), 2);
        const before = await exactBuffer(page), calls = mock.calls.length;
        await go(page, 'Kết thúc · Card 5');
        await page.waitForFunction(() => document.activeElement?.id === 'section-3');
        await go(page, 'Kết thúc · Card 4');
        await page.waitForFunction(() => document.activeElement?.id === 'section-2');
        assert.deepEqual(await exactBuffer(page), before); assert.equal(mock.calls.length, calls);
      }, duplicates);
      for (const corruption of ['wrong-section', 'partial-pair', 'artifact', 'question', 'missing-source', 'stale', 'legacy']) {
        const p = fixture(); p.feedback.revision_notes = [p.feedback.revision_notes[1]];
        const n = p.feedback.revision_notes[0];
        if (corruption === 'wrong-section') n.targets[0].target_id = 'section-1';
        if (corruption === 'partial-pair') n.targets[1].quote = 'Quote belongs elsewhere.';
        if (corruption === 'artifact') n.artifact_id = 'f2';
        if (corruption === 'question') n.decision_question = 'Another question';
        if (corruption === 'missing-source') p.feedback_source = null;
        if (corruption === 'stale') p.feedback_is_current = false;
        if (corruption === 'legacy') {
          delete p.feedback.revision_notes;
          p.feedback.findings = [
            { criterion_id: 'weakness-1', message: 'Góp ý cũ còn đọc được.', severity: 'warning', score: null },
            { criterion_id: 'suggestion-1', message: 'Gợi ý cũ không tạo cặp mới.', severity: 'info', score: null },
          ];
        }
        await run(`readonly-${corruption}`, viewport, async ({ page, mock }) => {
          assert.equal(await actions(page).count(), 0);
          const before = await exactBuffer(page);
          assert.match(await page.locator('#workspace-feedback').innerText(), corruption === 'legacy' ? /Góp ý cũ còn đọc được/ : /Nhận xét n2/);
          assert.deepEqual(await exactBuffer(page), before); assert.equal(writes(mock).length, 0);
        }, p);
      }
      const p = fixture(); p.feedback.revision_notes[0].targets = [{ target_id: 'draft-title', quote: p.draft.title }];
      await run('title-target-and-review-failure', viewport, async ({ page, mock }) => {
        await go(page, 'Tên phim'); await page.waitForFunction(() => document.activeElement?.id === 'draft-title');
        await page.locator('#draft-title').fill('Tên phim tự sửa');
        assert.equal(await actions(page).count(), 0);
        const before = await exactBuffer(page);
        mock.loseSaveResponse = true;
        await reveal(page, page.getByRole('button', { name: 'Nhận phản hồi trên bản hiện tại', exact: true }));
        await page.getByRole('button', { name: 'Nhận phản hồi trên bản hiện tại', exact: true }).click();
        await page.locator('.error[role="alert"]').waitFor();
        assert.equal(mock.projects[0].draft.title, 'Tên phim tự sửa', 'server wrote before response was lost');
        assert.deepEqual(await exactBuffer(page), before);
        assert.equal(writes(mock).length, 1, 'no review or retry after unconfirmed save');
        assert.equal(await actions(page).count(), 0);
      }, p);
    }
  } finally {
    await browser.close(); await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  }
  console.log(JSON.stringify(report)); process.exitCode = report.results.some(r => !r.passed) ? 1 : 0;
})().catch(e => { console.error(e); process.exitCode = 1; });
