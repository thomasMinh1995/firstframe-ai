// Fresh ui_workspace_fixture per run, fake providers only, no author database.
const {chromium} = require('playwright'), assert = require('node:assert/strict');
const fs = require('node:fs/promises'), path = require('node:path'), {randomUUID: uuid} = require('node:crypto');
(async () => {
  const directory = process.env.FIRSTFRAME_QA_DIRECTORY;
  assert.ok(directory && path.basename(directory).startsWith('firstframe-workspace-'));
  const seed = JSON.parse(await fs.readFile(path.join(directory, 'seed.json'), 'utf8'));
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
  await context.addInitScript(() => localStorage.setItem('firstframe:onboarding', JSON.stringify({version: 1, status: 'completed', stepId: 'save', projectId: null})));
  const api = 'http://127.0.0.1:8034', url = `/api/projects/${seed.id}`;
  const req = async (route, method = 'GET', data) => {
    const response = await context.request.fetch(api + route, {method, data}); assert.equal(response.status(), 200, await response.text()); return response.json();
  };
  const read = () => req(url), payload = p => Object.fromEntries(['revision', 'title', 'idea', 'constraints', 'answers', 'draft', 'response_language'].map(k => [k, p[k]]));
  let p = await req(url + '/scene-outline', 'POST', {revision: seed.revision, source_version_id: 'current'});
  p = await req(url, 'PUT', {...payload(p), scene_outline: {id: p.scene_outline.id, version: p.scene_outline.version,
    scenes: Array.from({length: 12}, (_, i) => ({id: uuid(), title: i < 2 ? 'Hai cảnh trùng tên' : `Cảnh ${i + 1}`, action: 'Cha đặt thư. Con gái chưa mở.'}))}});
  p = await req(url + '/screenplay', 'POST', {revision: p.revision, request_id: uuid()});
  const script = structuredClone(p.screenplay);
  script.scenes[0].blocks = [{id: uuid(), kind: 'action', text: 'SAVED_A: Phong thư còn kín.', speaker: ''}];
  script.scenes[1].blocks = [{id: uuid(), kind: 'dialogue', text: 'SAVED_B: Cha cứ để đó.', speaker: 'Con gái'}];
  p = await req(url, 'PUT', {...payload(p), screenplay: {id: script.id, version: script.version, scenes: script.scenes}});
  const source = structuredClone(p.screenplay.source_outline), m2 = structuredClone(p.scene_outline), m1 = structuredClone(p.draft);
  const page = await context.newPage(), errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('http://127.0.0.1:3034');
  const area = page.getByRole('region', {name: 'Kịch bản', exact: true}), nav = area.getByRole('navigation', {name: 'Các cảnh kịch bản'});
  const editor = area.getByLabel('Editor liền mạch', {exact: true}), comparison = area.getByRole('complementary', {name: 'Kịch bản đã lưu để đối chiếu'});
  const state = () => req('/__test/state'), writes = s => s.calls.filter(c => c.method !== 'GET').length;
  const scene = i => nav.getByRole('button').nth(i), savedScene = i => comparison.locator('[data-reading-scene]').nth(i);
  const choose = i => scene(i).click(), text = () => editor.locator('textarea').first();
  const save = async () => {
    const result = page.waitForResponse(r => r.url() === api + url && r.request().method() === 'PUT');
    await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click(); assert.equal((await result).status(), 200);
    await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.', {exact: true}).waitFor();
  };
  await comparison.waitFor(); await area.getByRole('status').filter({hasText: 'Chọn một cảnh để viết'}).waitFor();
  assert.equal(await editor.count(), 0); assert.equal(await area.getByLabel('Tiêu đề cảnh', {exact: true}).count(), 0);
  assert.equal(await comparison.locator('[data-reading-scene]').count(), 12); assert.match(await savedScene(0).innerText(), /SAVED_A/);
  assert.equal(await nav.locator('.screenplay-scene-arrow').count(), 11);
  assert.deepEqual(await nav.getByRole('button').evaluateAll(bs => bs.map(b => b.dataset.scriptScene)), p.screenplay.scenes.map(s => s.id));
  const boxes = await nav.getByRole('button').evaluateAll(bs => bs.map(b => ({y: b.getBoundingClientRect().y, x: b.getBoundingClientRect().x})));
  assert.ok(boxes.every(b => Math.abs(b.y - boxes[0].y) < 1)); assert.ok(boxes.every((b, i) => !i || b.x > boxes[i - 1].x));
  const beforeNavigation = await state();
  await scene(11).focus(); assert.ok(await nav.evaluate(e => e.scrollLeft > 0), 'keyboard focus reveals the final scene');
  await choose(0); assert.equal(await text().inputValue(), 'SAVED_A: Phong thư còn kín.');
  assert.equal(await savedScene(0).getAttribute('data-selected'), 'true');
  const writing = await area.locator('.screenplay-columns > .screenplay-scene').boundingBox(), savedBox = await comparison.boundingBox();
  assert.ok(writing.x + writing.width <= savedBox.x + 1, 'desktop writing is left of saved script');
  await text().fill('EDIT_A:  Con ga\u0301i nhìn thư.\n\nChưa mở.  ');
  await choose(1); assert.equal(await text().inputValue(), 'SAVED_B: Cha cứ để đó.'); await text().fill('EDIT_B: Không sao đâu cha ạ…');
  await choose(0); assert.equal(await text().inputValue(), 'EDIT_A:  Con ga\u0301i nhìn thư.\n\nChưa mở.  ');
  assert.match(await savedScene(0).innerText(), /SAVED_A/); assert.match(await savedScene(1).innerText(), /SAVED_B/);
  assert.ok(!(await comparison.innerText()).includes('EDIT_A')); assert.ok(!(await comparison.innerText()).includes('EDIT_B'));
  assert.equal(writes(await state()), writes(beforeNavigation), 'scene navigation and typing never save or call AI');
  // Prototype shortcuts reveal existing support/read regions without saving or replacing the editor.
  const beforeShortcuts = await state();
  await area.getByRole('button', {name: 'Dàn cảnh & góp ý', exact: true}).click();
  assert.ok(await area.locator('.screenplay-source').evaluate(e => e.open));
  assert.ok(await area.locator('.screenplay-feedback-tools').evaluate(e => e.open));
  assert.ok(await area.locator('.screenplay-tools > details').first().locator(':scope > summary').evaluate(e => e === document.activeElement));
  await area.getByRole('button', {name: 'Đọc toàn bộ', exact: true}).click();
  assert.ok(await area.locator('.screenplay-reading').evaluate(e => e === document.activeElement));
  assert.equal(await text().inputValue(), 'EDIT_A:  Con ga\u0301i nhìn thư.\n\nChưa mở.  ');
  assert.match(await savedScene(0).innerText(), /SAVED_A/);
  assert.equal(writes(await state()), writes(beforeShortcuts));
  await area.locator('.screenplay-source > summary').click();await area.locator('.screenplay-feedback-tools > summary').click();
  // Hold a save response: even after server commit, comparison must not claim the pending buffer is saved.
  let release, entered;
  const ready = new Promise(resolve => {entered = resolve;}), held = new Promise(resolve => {release = resolve;});
  const hold = async route => {if (route.request().method() !== 'PUT') return route.continue(); const response = await route.fetch(); entered(); await held; await route.fulfill({response});};
  await page.route('**' + url, hold); const pending = page.waitForResponse(r => r.url() === api + url && r.request().method() === 'PUT');
  await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click(); await ready;
  assert.match(await savedScene(0).innerText(), /SAVED_A/); release(); assert.equal((await pending).status(), 200);
  await savedScene(0).getByText(/EDIT_A/).waitFor(); await page.unroute('**' + url, hold);
  assert.match(await savedScene(1).innerText(), /EDIT_B/); p = await read(); const confirmed = structuredClone(p.screenplay);
  assert.deepEqual(p.screenplay.source_outline, source); assert.deepEqual(p.scene_outline, m2); assert.deepEqual(p.draft, m1);
  // Switching versions in the existing full reader cannot replace the comparison or author buffer.
  const reader = area.locator('.screenplay-reading'), options = reader.getByLabel('Bản để đọc và đối chiếu', {exact: true});
  const old = p.screenplay_versions.find(v => v.screenplay.scenes[0].blocks[0]?.text === 'SAVED_A: Phong thư còn kín.'); assert.ok(old);
  await options.selectOption(old.id); assert.match(await savedScene(0).innerText(), /EDIT_A/); assert.equal(await text().inputValue(), confirmed.scenes[0].blocks[0].text);
  await options.selectOption('current');
  // A fresh render starts unselected, with all saved text still available.
  await page.reload(); await comparison.waitFor(); assert.equal(await editor.count(), 0);
  assert.match(await savedScene(0).innerText(), /EDIT_A/); await choose(0);
  const unsaved = 'BUFFER_KEEP_AFTER_FAILURE'; await text().fill(unsaved);
  const offline = r => r.request().method() === 'PUT' ? r.abort('failed') : r.continue(); await page.route('**' + url, offline);
  await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click(); await page.locator('.save-toolbar .error').waitFor();
  assert.equal(await text().inputValue(), unsaved); assert.match(await savedScene(0).innerText(), /EDIT_A/);
  await page.getByRole('button', {name: 'Dự án mới', exact: true}).click(); await page.locator('.save-toolbar .error').waitFor();
  assert.equal(await page.locator('#project-picker').inputValue(), seed.id); assert.equal(await text().inputValue(), unsaved);
  await page.unroute('**' + url, offline); p = await read(); await req(url, 'PUT', {...payload(p), title: 'Cửa sổ khác'});
  await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click(); await page.locator('.save-toolbar .error').filter({hasText: 'cửa sổ khác'}).waitFor();
  assert.equal(await text().inputValue(), unsaved); assert.match(await savedScene(0).innerText(), /EDIT_A/);
  // Recover this disposable fixture by reloading, then test a new script identity and project switch.
  await page.reload(); await comparison.waitFor(); await choose(0); await text().fill('SAVE_BEFORE_PROJECT_SWITCH');
  await page.getByRole('button', {name: 'Dự án mới', exact: true}).click();
  await page.waitForFunction(id => document.querySelector('#project-picker').value !== id, seed.id);
  assert.equal(await comparison.count(), 0); assert.equal(await editor.count(), 0);
  await page.locator('#project-picker').selectOption(seed.id); await comparison.waitFor(); assert.equal(await editor.count(), 0);
  assert.match(await savedScene(0).innerText(), /SAVE_BEFORE_PROJECT_SWITCH/); await choose(0);
  await area.getByRole('checkbox').check(); await area.getByRole('button', {name: 'Bắt đầu bản kịch bản khác', exact: true}).click();
  await page.getByText('Đã giữ nguồn và khung cảnh kịch bản. Chưa tạo nội dung hoặc gọi AI.', {exact: true}).waitFor();
  assert.equal(await editor.count(), 0); assert.equal(await comparison.locator('[data-selected=true]').count(), 0);
  assert.ok(!(await comparison.innerText()).includes('SAVE_BEFORE_PROJECT_SWITCH'));
  await choose(0); assert.equal(await text().inputValue(), '');
  const beforeView = await state();
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({width, height: 1000}); await choose(0);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    if (width < 700) {
      const a = await area.locator('.screenplay-columns > .screenplay-scene').boundingBox(), b = await comparison.boundingBox();
      assert.ok(b.y >= a.y + a.height - 1); const arrow = await nav.locator('.screenplay-scene-arrow').first().evaluate(e => getComputedStyle(e).transform); assert.notEqual(arrow, 'none');
    }
    await area.locator('.screenplay-columns').screenshot({path: path.join(directory, `scene-layout-${width}.png`)});
  }
  const final = await state(); assert.equal(writes(final), writes(beforeView));
  assert.deepEqual(final.provider_stages, []); assert.equal(final.writing_requests, 0); assert.equal(final.review_requests, 0); assert.equal(final.image_requests, 0);
  assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('firstframe:onboarding')).status), 'completed');
  assert.deepEqual(errors, []);
  console.log('PASS M3 layout: explicit scene selection, straight arrows/keyboard scroll, desktop comparison/mobile stack, duplicate names/IDs, multi-scene buffer, confirmed saved-only response, reader independence, reload, offline/409, project/script reset, no model or navigation writes, preserved tour');
  await context.close(); await browser.close();
})().catch(e => {console.error(e); process.exit(1);});
