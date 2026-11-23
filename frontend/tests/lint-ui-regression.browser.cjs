// ui_workspace_fixture.py: disposable SQLite, fake text/image providers only.
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const {randomUUID: uuid} = require('node:crypto');
(async () => {
  const directory = process.env.FIRSTFRAME_QA_DIRECTORY;
  assert.ok(directory && path.basename(directory).startsWith('firstframe-workspace-'));
  const seed = JSON.parse(await fs.readFile(path.join(directory, 'seed.json'), 'utf8'));
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    context.setDefaultTimeout(10000);
    await context.addInitScript(() => localStorage.setItem('firstframe:onboarding:v2', JSON.stringify({version: 3, status: 'dismissed', stepId: 'save', projectId: null})));
    const base = '/api/projects/' + seed.id;
    const request = async (route = '', method = 'GET', data) => {
      const response = await context.request.fetch('http://127.0.0.1:8034' + base + route, {method, data});
      assert.equal(response.status(), 200, await response.text()); return response.json();
    };
    let p = await request();
    if (!p.scene_outline) p = await request('/scene-outline', 'POST', {revision: p.revision, source_version_id: 'current'});
    const first = p.scene_outline.scenes[0].id;
    const imageId = uuid();
    p = await request('/scene-sketches', 'POST', {revision: p.revision, request_id: imageId, scene_id: first, instructions: ''});
    p = await request('/scene-sketches/' + imageId + '/keep', 'POST', {revision: p.revision});
    p = await request('/screenplay', 'POST', {revision: p.revision, request_id: uuid()});
    const errors = [], page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:3034');
    await page.getByRole('navigation', {name: 'Hành trình câu chuyện'}).getByRole('button', {name: /Viết & sửa/}).click();
    const area = page.locator('.screenplay');
    await area.locator('.screenplay-scene-list button').first().click();
    const editor = area.getByLabel('Editor liền mạch', {exact: true}).locator('textarea').first();
    await editor.fill('Chữ đang viết: má gọi con về ăn cơm.');
    await area.getByRole('button', {name: 'Dàn cảnh & góp ý', exact: true}).click();
    assert.equal(await editor.inputValue(), 'Chữ đang viết: má gọi con về ăn cơm.');
    await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click();
    await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.', {exact: true}).waitFor();
    assert.equal((await request()).screenplay.scenes[0].blocks[0].text, 'Chữ đang viết: má gọi con về ăn cơm.');
    const image = area.locator('.screenplay-scene-list img').first();
    await page.waitForFunction(() => document.querySelector('.screenplay-scene-list img')?.naturalWidth === 768);
    assert.ok((await image.getAttribute('src')).includes(imageId), 'The local image URL must remain direct');
    assert.equal(await image.getAttribute('width'), '768');
    await image.dispatchEvent('error');
    await area.locator('.screenplay-scene-list').getByRole('status').waitFor();
    await page.getByRole('button', {name: 'Hướng dẫn sử dụng', exact: true}).click();
    await page.getByRole('dialog').waitFor();
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({state: 'hidden'});
    // Force parent/reader rerenders without allowing terminal polling to restart.
    const run = {id: 'lint-run', project_id: p.id, source_revision: p.revision, status: 'ready', step: 'done', sending: false,
      cancel_requested: false, candidate_revision: 0, completed_scenes: p.screenplay.scenes.length, total_scenes: p.screenplay.scenes.length,
      error: null, review_error: null, adopted_revision: null};
    let reads = 0;
    await context.route(/\/api\/projects\/[^/]+\/draft-runs(?:\/.*)?$/, route => {
      const pathname = new URL(route.request().url()).pathname;
      reads++;
      return route.fulfill({json: pathname.endsWith('/candidate') ? {revision: 0, project: p}
        : pathname.endsWith('/draft-runs') ? [run] : run});
    });
    await page.reload();
    await page.getByRole('button', {name: 'Tùy chọn: tạo nháp tự động', exact: true}).click();
    const panel = page.locator('#draft-run');
    await panel.getByText('Bản nháp riêng đã lưu', {exact: true}).waitFor();
    const before = reads;
    for (let i = 0; i < 3; i++) {
      await panel.locator('details').first().locator('summary').click();
      await page.getByRole('button', {name: 'Hướng dẫn sử dụng', exact: true}).click();
      await page.getByRole('dialog').waitFor(); await page.keyboard.press('Escape');
      await page.getByRole('dialog').waitFor({state: 'hidden'});
    }
    await page.waitForTimeout(1800);
    assert.equal(reads, before, 'Parent rerenders must not restart terminal polling');
    await page.goto('http://127.0.0.1:3034/library');
    await page.locator('.saved-library').waitFor();
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height: 1000});
      await page.getByRole('button', {name: 'Xem hình phác cảnh 1', exact: true}).click();
      const preview = page.getByRole('dialog', {name: 'Hình phác · Cảnh 1'});
      await preview.waitFor();
      assert.ok((await preview.locator('img').getAttribute('src')).includes(imageId));
      assert.ok(await preview.locator('img').evaluate(img => img.complete && img.naturalWidth === 768));
      await page.keyboard.press('Escape'); await preview.waitFor({state: 'hidden'});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    assert.deepEqual(errors, []);
    console.log('PASS production UI: SQLite save, retained Vietnamese buffer, direct local image/fallback, tour Escape, stable terminal polling and library images at 3 widths');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exit(1);});
