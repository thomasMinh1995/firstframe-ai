// Cross-engine card-workspace regression. Uses the existing isolated request mock.
const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { setup, fullProject, answer, edit, reveal, confirmPlan } = require('./onboarding.browser.cjs');
const engine = process.env.TOUR_BROWSER || 'chrome';
const url = process.env.TOUR_TEST_URL || 'http://localhost:3033';
const output = process.env.TOUR_SCREENSHOTS || `/tmp/firstframe-workspace-${engine}`;
const clone = value => structuredClone(value);
const click = async (page, name) => {
  if (['Tạo bản phát triển từ lựa chọn của tôi','Tạo bản đề xuất mới (giữ bản đang viết)'].includes(name)) return confirmPlan(page);
  await reveal(page, page.getByRole('button', { name, exact: true, includeHidden: true }));
  await page.getByRole('button', { name, exact: true }).click();
};
const readTitle = page => page.locator('.story-field-title .story-field-value').innerText();
const overview = page => page.locator('.story-draft-overview');
const proposals = page => page.getByRole('region', { name: 'Các bản do AI tạo', exact: true });
const history = page => page.locator('section.version-history').filter({ has: page.getByRole('heading', { name: 'Các phiên bản đã giữ', exact: true }) });
const input = page => page.locator('#draft-logline');
const open = page => click(page, 'Sửa tóm tắt câu chuyện trong một câu');
const saved = page => page.waitForFunction(() => document.querySelector('#save-status').textContent === 'Đã lưu');
const reopened = page => page.getByText('Đã mở lại bản đã lưu. Không tạo lại hoặc gọi AI.', { exact: true }).waitFor();
const failed = page => page.locator('.error[role="alert"]').waitFor();
const returnedFocus = (page, label) => page.waitForFunction(label => document.activeElement?.getAttribute('aria-label') === label, label, { timeout: 3000 });
const writes = mock => mock.calls.filter(c => c.method !== 'GET');
const section = (title, content) => ({ title, purpose: 'Story section', content });
const original = { title: 'Bản đang viết', logline: 'Mẹ đẩy bát cơm, con kéo ghế ngồi xuống.', sections: [
  section('Characters', 'Hai mẹ con.'), section('Beginning', 'Mẹ giữ phần cơm.'),
  section('Middle', 'Con ngập ngừng kéo ghế.'), section('Ending', 'Hai người ngồi ăn trong im lặng.'),
] };
const proposed = { ...clone(original), title: 'Bản đề xuất', logline: 'Một cách kể khác do AI đề xuất.' };
const old = { ...clone(original), title: 'Bản lịch sử', logline: 'Nội dung cũ cần khôi phục.' };
const feedback = id => ({ artifact_id: id, passed: true, rubric_scores: {}, findings: [] });
function fixture(critic = 'reviewed') {
  const p = { ...fullProject('p1'), draft: clone(original), answers: ['Giữ kết mở.'],
    analysis: { artifact_id: 'a1', summary: 'Một bữa cơm muộn.', missing_information: ['Điều muốn giữ?'], notes: [] } };
  const context = { idea: p.idea, constraints: [], clarifications: [
    { question: 'Điều muốn giữ?', answer: p.answers[0], input_index: 0 },
  ], pending_questions: [] };
  const source = (id, draft) => ({ project_id: p.id, artifact_id: id, revision: p.revision,
    content_key: id, context, draft: clone(draft) });
  Object.assign(p, { author_context: context, feedback: feedback('f1'), feedback_is_current: true,
    feedback_source: source('f1', original), applicable_plan_ids: ['g1'], plan_generations: [{
      id: 'g1', created_at: p.updated_at, source_revision: p.revision, source_content: 'fixture', context, draft: clone(proposed),
      critic_status: critic, applied_revision: null, feedback: critic === 'reviewed' ? feedback('f2') : null,
      feedback_source: critic === 'reviewed' ? source('f2', proposed) : null,
    }], versions: [{ id: 'v0', created_at: p.updated_at, response_language: p.response_language,
      idea: 'Ý tưởng trước đây', constraints: [], questions: [], answers: [], draft: clone(old), feedback: null }] });
  return p;
}
async function backup(page, filename) {
  const download = page.waitForEvent('download'); await click(page, 'Tải bản sao JSON');
  await (await download).saveAs(filename);
  return JSON.parse(await fs.readFile(filename, 'utf8'));
}
async function noOverflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
}

(async () => {
  assert.ok(['chrome', 'firefox', 'webkit'].includes(engine));
  await fs.mkdir(output, { recursive: true });
  const browser = await ({ chrome: chromium, firefox, webkit })[engine].launch({ headless: true,
    ...(engine === 'chrome' ? { channel: 'chrome' } : {}) });
  const report = { engine, version: browser.version(), results: [] };
  async function run(name, viewport, fn, extra = {}) {
    let t; const started = Date.now(); const label = `${name}-${viewport.width}`;
    try {
      t = await setup(browser, { viewport, projects: [fixture()], ...extra });
      await t.page.locator('.story-workspace').waitFor();
      // Existing data regressions exercise the expanded workspace; focused tests cover collapsed defaults.
      for (const selector of ['.workspace-stage', '.workspace-library', '.save-more', '#workspace-feedback']) {
        for (const details of await t.page.locator(selector).all()) {
          if (await details.getAttribute('open') === null) await details.locator(':scope > summary').click();
        }
      }
      await fn(t); await noOverflow(t.page); await t.close();
      report.results.push({ name: label, passed: true, durationMs: Date.now() - started });
      console.log(`PASS ${label}`);
    } catch (error) {
      if (t) {
        await t.page.screenshot({ path: path.join(output, `${label}-failure.png`), fullPage: true }).catch(() => {});
        await t.context.close();
      }
      report.results.push({ name: label, passed: false, error: error.stack });
      console.error(`FAIL ${label}: ${error.message}`);
    }
  }
  try {
    console.log(`Story workspace: ${engine} ${report.version}`);
    for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      await run('segmented-story-cards', viewport, async ({ page, mock }) => {
        const before = clone(mock.projects[0]);
        const cards = page.locator('.story-draft-path > li');
        assert.equal(await cards.count(), 9);
        await page.waitForFunction(() => document.querySelectorAll('.story-path-lines > path').length === 8);
        assert.equal((await page.locator('.story-path-lines > path').evaluateAll(paths => paths.filter(p => p.getAttribute('d').includes(' C ')).length)), viewport.width > 600 ? 2 : 0);
        assert.deepEqual(mock.projects[0], before); assert.equal(writes(mock).length, 0);
        await (await edit(page, 'section-1')).fill('Mẹ chờ bên quạt.');
        await (await edit(page, 'section-1-part-1')).fill('Con đặt đôi đũa cạnh bát mẹ.');
        await page.locator('#section-1').press('Escape');
        const expected = before.draft.sections[1].content.replace('Con về muộn.', 'Con đặt đôi đũa cạnh bát mẹ.');
        const copy = await backup(page, path.join(output, `beats-${viewport.width}.json`));
        assert.equal(copy.draft.sections[1].content, expected, 'cancel preserves the other card and exact separators');
        mock.reviewPatch = { feedback: feedback('new-beats'), feedback_is_current: true,
          feedback_source: { ...before.feedback_source, artifact_id: 'new-beats', draft: clone(copy.draft) } };
        await click(page, 'Nhận phản hồi trên bản hiện tại');
        await page.getByText('Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.', { exact: true }).waitFor();
        assert.equal(writes(mock)[0].body.draft.sections[1].content, expected);
        assert.deepEqual(Object.keys(writes(mock)[0].body).sort(), ['answers', 'constraints', 'draft', 'idea', 'response_language', 'revision', 'title']);
        assert.deepEqual(mock.projects[0].feedback_source.draft, copy.draft);
        assert.deepEqual(mock.projects[0].draft.sections.map(s => s.title), before.draft.sections.map(s => s.title));
        await page.getByRole('navigation', { name: 'Hành trình câu chuyện', exact: true }).getByRole('button', { name: /^Story plan/ }).click();
        await page.screenshot({ path: path.join(output, `s-path-${viewport.width}.png`), fullPage: true });
      }, { projects: [{ ...fixture(), draft: { ...clone(original), sections: [section('Characters', 'Hai mẹ con.'),
        section('Beginning', 'Mẹ chờ.  \nCon về muộn. Tiếng quạt vẫn quay.'),
        section('Middle', 'Mẹ giữ cơm. Con kéo ghế. Bát cơm được đẩy sang.'),
        section('Ending', 'Con ngồi xuống. Đôi đũa đặt cạnh bát. Khoảng lặng còn đó.')] } }] });
      await run('clarification-conversation', viewport, async ({ page, mock }) => {
        assert.equal(await page.locator('.clarification-composer textarea').count(), 1);
        assert.equal(await page.locator('#answer-1').count(), 0);
        await answer(page, 2, 'Kết thúc vẫn để mở.');
        await click(page, 'Lưu thay đổi'); await saved(page);
        assert.deepEqual(mock.projects[0].answers, ['', '', 'Kết thúc vẫn để mở.'], 'jumping ahead never creates null answers');
        await answer(page, 0, 'Giữ sự lặng lẽ.'); await click(page, 'Tiếp tục');
        await page.locator('#answer-1').waitFor();
        assert.equal(await page.locator('#answer-0-value').innerText(), 'Giữ sự lặng lẽ.');
        await click(page, 'Để quyết định sau');
        await page.locator('#clarification-complete').waitFor();
        assert.equal(await page.locator('.clarification-composer textarea').count(), 0);
        assert.equal(writes(mock).length, 1, 'conversation navigation and defer never call API');
        await click(page, 'Sửa câu trả lời 1'); await page.locator('#answer-0').fill('Giữ tiếng quạt và khoảng lặng.');
        await click(page, 'Xong');
        await page.screenshot({ path: path.join(output, `conversation-${viewport.width}.png`), fullPage: true });
        await click(page, 'Tạo bản phát triển từ lựa chọn của tôi');
        await page.getByText('Đã tạo và lưu bản phát triển. Bạn có thể sửa trực tiếp bên dưới.', { exact: true }).waitFor();
        assert.equal(mock.projects[0].answers[0], 'Giữ tiếng quạt và khoảng lặng.');
        assert.match(mock.projects[0].answers[1], /Chưa quyết định/);
        assert.equal(mock.projects[0].answers[2], 'Kết thúc vẫn để mở.');
        assert.deepEqual(writes(mock).map(c => c.method), ['PUT', 'PUT', 'POST']);
        assert.ok(writes(mock)[2].pathname.endsWith('/plan/stream'));
        await page.reload();
        await page.getByRole('navigation', { name: 'Hành trình câu chuyện' }).getByRole('button', { name: /^Làm rõ/ }).click();
        await page.locator('.clarification-thread').waitFor();
        assert.equal(await page.locator('#answer-0-value').innerText(), 'Giữ tiếng quạt và khoảng lặng.');
      }, { projects: [{ ...fixture(), draft: null, feedback: null, versions: [], plan_generations: [], applicable_plan_ids: [],
        answers: [], analysis: { artifact_id: 'chat', summary: 'Một bữa cơm muộn.', missing_information: ['Điều muốn giữ?', 'Điều chưa rõ?', 'Muốn kết thúc ra sao?'], notes: [] } }] });
      await run('navigation-buffer', viewport, async ({ page, mock }) => {
        const stored = clone(mock.projects); const initialCalls = mock.calls.length;
        await click(page, 'Sửa tên phim tạm thời'); await page.locator('#draft-title').fill('Tên phim chưa bấm Xong.');
        await open(page); await input(page).fill('Logline chưa bấm Xong.');
        await click(page, 'Sửa mở đầu'); await page.locator('#section-1').fill('Mở đầu chưa bấm Xong.');
        await page.locator('#project-title').fill('Tên dự án chưa lưu.');
        await answer(page, 0, 'Lựa chọn chưa lưu.');
        const before = await backup(page, path.join(output, `navigation-before-${viewport.width}.json`));
        await page.evaluate(() => {
          history.replaceState(null, '', '?qa=keep#workspace-draft');
          history.pushState(null, '', '?workspace=classic&qa=keep#workspace-draft');
        });
        await page.goBack(); await page.locator('.story-workspace').waitFor();
        assert.deepEqual(await backup(page, path.join(output, `navigation-back-${viewport.width}.json`)), before);
        await page.goForward(); await page.locator('.story-workspace').waitFor();
        assert.deepEqual(await backup(page, path.join(output, `navigation-forward-${viewport.width}.json`)), before);
        assert.equal(await page.locator('.workspace-view-toggle').count(), 0);
        await input(page).fill('Tiếp tục viết tại card.');
        await page.locator('.story-field').filter({ has: input(page) }).getByRole('button', { name: 'Xong', exact: true }).click();
        await open(page); await input(page).fill('Chỉ hủy sửa trong phiên này.'); await input(page).press('Escape');
        assert.match(await overview(page).innerText(), /Tiếp tục viết tại card/);
        assert.equal(await page.locator('#save-status').innerText(), 'Có thay đổi chưa lưu');
        const after = await backup(page, path.join(output, `navigation-after-${viewport.width}.json`));
        assert.deepEqual(after, { ...before, draft: { ...before.draft, logline: 'Tiếp tục viết tại card.' } });
        assert.deepEqual(mock.projects, stored); assert.equal(mock.calls.length, initialCalls, 'history navigation must not reload or call API');
        await Promise.all([
          page.waitForEvent('dialog', { timeout: 5000 }).then(async dialog => {
            assert.equal(dialog.type(), 'beforeunload'); await dialog.dismiss();
          }),
          page.evaluate(() => { setTimeout(() => location.reload(), 0); }),
        ]);
        assert.deepEqual(await backup(page, path.join(output, `cancel-reload-${viewport.width}.json`)), after);
        assert.equal(mock.calls.length, initialCalls, 'canceling reload keeps the in-memory buffer');
      });
      await run('default-workspace-reload', viewport, async ({ page, mock }) => {
        for (const query of ['', '?workspace=unknown', '?workspace=classic', '?workspace=story']) {
          await page.goto(`${url}/${query}`); await page.locator('.story-field-title').waitFor();
          assert.equal(await page.locator('.story-workspace').count(), 1);
          assert.equal(await page.locator('.workspace-view-toggle, .story-reading').count(), 0);
          assert.doesNotMatch(await page.locator('.workspace-mode-label').innerText(), /xem thử/);
          await page.reload(); await page.locator('.story-field-title').waitFor();
          assert.equal(await page.locator('.story-workspace').count(), 1);
        }
        assert.equal(writes(mock).length, 0);
      });
      await run('editor-buffer', viewport, async ({ page, mock }) => {
        const stored = clone(mock.projects); await open(page);
        assert.equal(await page.evaluate(() => document.activeElement.id), 'draft-logline');
        await input(page).fill('Tiếng Việt: chữ chưa bấm Xong.');
        await click(page, 'Sửa mở đầu'); await page.locator('#section-1').fill('Chỉ hủy trường này.');
        await page.locator('#section-1').press('Escape');
        assert.equal(await input(page).inputValue(), 'Tiếng Việt: chữ chưa bấm Xong.');
        await returnedFocus(page, 'Sửa mở đầu');
        assert.deepEqual(mock.projects, stored); assert.equal(writes(mock).length, 0);
        await click(page, 'Lưu thay đổi'); await saved(page);
        assert.equal(await input(page).count(), 0, 'successful save ends editing');
        assert.equal(mock.projects[0].draft.logline, 'Tiếng Việt: chữ chưa bấm Xong.');
        assert.deepEqual(Object.keys(writes(mock)[0].body).sort(), ['answers', 'constraints', 'draft', 'idea', 'response_language', 'revision', 'title']);
        await open(page); await input(page).fill('Hủy sau lần lưu.'); await overview(page).getByRole('button', { name: 'Hủy', exact: true }).click();
        assert.match(await overview(page).innerText(), /Tiếng Việt: chữ chưa bấm Xong/);
        await page.getByRole('navigation', { name: 'Hành trình câu chuyện', exact: true }).getByRole('button', { name: /^Story plan/ }).click();
        await page.screenshot({ path: path.join(output, `cards-${viewport.width}.png`) });
      });
      await run('save-review-failures', viewport, async ({ page, mock }) => {
        await open(page); await input(page).fill('Review phải đọc chữ còn mở.'); mock.failSave = true;
        await click(page, 'Nhận phản hồi trên bản hiện tại'); await failed(page);
        assert.equal(await input(page).inputValue(), 'Review phải đọc chữ còn mở.');
        assert.equal(mock.calls.some(c => c.pathname.endsWith('/review/stream')), false);
        mock.failSave = false; mock.failAI = true;
        await click(page, 'Nhận phản hồi trên bản hiện tại'); await failed(page);
        assert.equal(mock.projects[0].draft.logline, 'Review phải đọc chữ còn mở.');
        assert.match(await overview(page).innerText(), /Review phải đọc chữ còn mở/);
        mock.failAI = false;
        mock.reviewPatch = { feedback: feedback('f3'), feedback_is_current: true,
          feedback_source: { ...mock.projects[0].feedback_source, artifact_id: 'f3', draft: clone(mock.projects[0].draft) } };
        await click(page, 'Nhận phản hồi trên bản hiện tại');
        await page.getByText('Đã lưu phản hồi và phiên bản cho đúng nội dung hiện tại.', { exact: true }).waitFor();
        assert.equal(mock.projects[0].feedback_source.draft.logline, 'Review phải đọc chữ còn mở.');
      });
      for (const critic of ['reviewed', 'failed']) await run(`proposal-${critic}`, viewport, async ({ page, mock }) => {
        const before = clone(mock.projects[0]); await proposals(page).locator(':scope > details > summary').click();
        assert.equal(writes(mock).length, 0); await open(page); await input(page).fill('Chưa lưu.');
        assert.equal(await page.getByRole('button', { name: 'Dùng bản đề xuất này', exact: true }).isDisabled(), true);
        await overview(page).getByRole('button', { name: 'Hủy', exact: true }).click();
        mock.loseAcceptResponse = true; await click(page, 'Dùng bản đề xuất này'); await failed(page);
        assert.equal(await readTitle(page), original.title); assert.deepEqual(mock.projects[0].draft, proposed);
        await click(page, 'Mở lại bản đã lưu'); await page.getByText('Đã mở lại bản đã lưu. Không tạo lại hoặc gọi AI.', { exact: true }).waitFor();
        assert.equal(await readTitle(page), proposed.title);
        assert.deepEqual(mock.projects[0].feedback_source, before.plan_generations[0].feedback_source);
        assert.deepEqual(mock.projects[0].versions.at(-1).draft, original);
        assert.equal(writes(mock).length, 1); assert.ok(writes(mock)[0].pathname.endsWith('/accept'));
      }, { projects: [fixture(critic)] });
      await run('restore-history', viewport, async ({ page, mock }) => {
        const before = clone(mock.projects[0]); await open(page); await input(page).fill('Chữ trước khôi phục.');
        await answer(page, 0, 'Giữ lựa chọn mới.');
        await history(page).locator(':scope > details').last().locator('summary').click();
        await history(page).getByRole('button', { name: 'Dùng lại bản phát triển này', exact: true }).click();
        await page.getByText('Đã dùng lại nội dung bản phát triển. Các phiên bản trước vẫn được giữ.', { exact: true }).waitFor();
        assert.deepEqual(mock.projects[0].draft, old); assert.equal(await readTitle(page), old.title);
        assert.equal(mock.projects[0].answers[0], 'Giữ lựa chọn mới.');
        assert.ok(mock.projects[0].versions.some(v => v.draft.logline === 'Chữ trước khôi phục.'));
        assert.deepEqual(mock.projects[0].versions[0], before.versions[0]);
        assert.deepEqual(mock.projects[0].feedback_source, before.feedback_source); assert.equal(mock.projects[0].feedback_is_current, false);
        assert.deepEqual(writes(mock).map(c => [c.method, c.body.revision]), [['PUT', 0], ['PUT', 1]]);
      }, { mock: { recordVersions: true } });
      await run('two-tab-buffer', viewport, async ({ page, context, mock }) => {
        const other = await context.newPage(); await other.goto(url);
        await other.locator('.story-field-title').waitFor(); await open(page); await input(page).fill('Tab A cần giữ.');
        await open(other); await input(other).fill('Tab B thắng.'); await click(other, 'Lưu thay đổi'); await saved(other);
        await click(page, 'Lưu thay đổi'); await failed(page);
        assert.equal(await input(page).inputValue(), 'Tab A cần giữ.'); assert.equal(mock.projects[0].draft.logline, 'Tab B thắng.');
        const copy = await backup(page, path.join(output, `buffer-${viewport.width}.json`)); assert.equal(copy.draft.logline, 'Tab A cần giữ.');
        assert.equal(await page.getByRole('button', { name: 'Mở lại bản đã lưu', exact: true }).isDisabled(), true);
        await history(page).locator(':scope > details').last().locator('summary').click();
        await history(page).getByRole('button', { name: 'Dùng lại bản phát triển này', exact: true }).click(); await failed(page);
        assert.equal(await input(page).inputValue(), 'Tab A cần giữ.'); assert.equal(writes(mock).length, 3);
        await overview(page).getByRole('button', { name: 'Hủy', exact: true }).click();
        await click(page, 'Mở lại bản đã lưu'); await reopened(page); assert.match(await overview(page).innerText(), /Tab B thắng/);
      });
      for (const operation of ['accept', 'restore']) await run(`two-tab-late-${operation}`, viewport, async ({ page, context, mock }) => {
        const other = await context.newPage(); await other.goto(url); await other.locator('.story-field-title').waitFor();
        let release; const pending = new Promise(resolve => { release = resolve; });
        if (operation === 'accept') {
          mock.hold = pending; await proposals(page).locator(':scope > details > summary').click(); await click(page, 'Dùng bản đề xuất này');
        } else {
          mock.holdSave = pending; await history(page).locator(':scope > details').last().locator('summary').click();
          await history(page).getByRole('button', { name: 'Dùng lại bản phát triển này', exact: true }).click();
        }
        await open(other); await input(other).fill('B thắng trong khi A chờ.'); await click(other, 'Lưu thay đổi'); await saved(other);
        mock.hold = null; release(); await failed(page);
        assert.equal(await readTitle(page), original.title); assert.equal(mock.projects[0].draft.logline, 'B thắng trong khi A chờ.');
        assert.equal(mock.projects[0].plan_generations[0].applied_revision, null);
        assert.equal(mock.projects[0].versions.length, 1);
        await click(page, 'Mở lại bản đã lưu'); await reopened(page); assert.match(await overview(page).innerText(), /B thắng trong khi A chờ/);
      });
      await run('tour-keyboard', viewport, async ({ page, mock }) => {
        await click(page, 'Hướng dẫn sử dụng'); await click(page, 'Thực hành'); await input(page).waitFor();
        assert.equal(await page.evaluate(() => document.activeElement.id), 'draft-logline');
        await input(page).fill('Đang gõ tiếng Việt.');
        await input(page).dispatchEvent('keydown', { key: 'Escape', isComposing: true }); assert.equal(await input(page).count(), 1);
        await input(page).press('Escape'); assert.equal(await input(page).count(), 0);
        await returnedFocus(page, 'Sửa tóm tắt câu chuyện trong một câu');
        assert.equal(await page.getByRole('button', { name: 'Tiếp tục hướng dẫn', exact: true }).count(), 1);
        assert.equal(writes(mock).length, 0);
      });
    }
    await run('narrow-legacy', { width: 320, height: 740 }, async ({ page }) => {
      assert.equal(await page.locator('.story-draft-path > li').count(), 6);
      assert.deepEqual(await page.locator('.story-draft-path h3').allTextContents(), Array.from({ length: 6 }, (_, i) => `Nhịp ${i + 1}`));
      await click(page, 'Sửa nhịp 1'); await page.locator('#section-0').fill('Một dòng rất dài '.repeat(30)); await noOverflow(page);
    }, { projects: [{ ...fixture(), draft: { ...clone(original), sections: Array.from({ length: 6 }, (_, i) => section(`Nhịp ${i + 1}`, 'Chữ không có khoảng trắng: ' + 'a'.repeat(100))) } }] });
  } finally {
    await browser.close(); await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  }
  process.exitCode = report.results.some(r => !r.passed) ? 1 : 0;
})().catch(error => { console.error(error); process.exitCode = 1; });
