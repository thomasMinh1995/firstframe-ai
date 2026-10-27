// Isolated SQLite/API and fake provider; no real model or author projects.
const {chromium} = require('playwright');
const assert = require('node:assert/strict'), fs = require('node:fs/promises'), path = require('node:path');
const {randomUUID: uuid} = require('node:crypto');
(async () => {
  const directory = process.env.FIRSTFRAME_QA_DIRECTORY;
  assert.ok(directory && path.basename(directory).startsWith('firstframe-workspace-'));
  const seed = JSON.parse(await fs.readFile(path.join(directory, 'seed.json'), 'utf8'));
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const context = await browser.newContext({viewport: {width: 1280, height: 900}, reducedMotion: 'reduce'});
  await context.addInitScript(() => localStorage.setItem('firstframe:onboarding', JSON.stringify({version: 1, status: 'dismissed', stepId: 'save', projectId: null})));
  const api = 'http://127.0.0.1:8034', url = `/api/projects/${seed.id}`;
  const request = async (route, method = 'GET', data) => {
    const r = await context.request.fetch(api + route, {method, data});
    assert.equal(r.status(), 200, await r.text()); return r.json();
  };
  const read = () => request(url), payload = p => Object.fromEntries(['revision', 'title', 'idea', 'constraints', 'answers', 'draft', 'response_language'].map(k => [k, p[k]]));
  let project = await request(url + '/scene-outline', 'POST', {revision: seed.revision, source_version_id: 'current'});
  project = await request(url, 'PUT', {...payload(project), scene_outline: {id: project.scene_outline.id, version: project.scene_outline.version,
    scenes: [0, 1].map(() => ({id: uuid(), title: 'Lá thư', action: 'Cha đặt thư. Con gái chưa mở.'}))}});
  project = await request(url + '/screenplay', 'POST', {revision: project.revision, request_id: uuid()});
  const source = structuredClone(project.screenplay.source_outline), scriptId = project.screenplay.id;
  const page = await context.newPage(), errors = [];
  page.on('pageerror', e => errors.push(e.message)); await page.goto('http://127.0.0.1:3034');
  const area = page.getByRole('region', {name: 'M3 Kịch bản', exact: true});
  const editor = area.getByLabel('Editor liền mạch', {exact: true});
  const enable = async () => {if (!await editor.count()) await area.getByRole('navigation', {name: 'Các cảnh kịch bản'}).getByRole('button').first().click(); await editor.waitFor();};
  const save = async () => {
    const response = page.waitForResponse(r => r.url() === api + url && r.request().method() === 'PUT');
    await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click(); assert.equal((await response).status(), 200);
    await page.getByText('Đã lưu kịch bản và mọi sửa đang chờ.', {exact: true}).waitFor();
  };
  const block = i => editor.locator('[data-script-block]').nth(i), text = i => block(i).locator('textarea');
  const state = () => request('/__test/state'), writes = s => s.calls.filter(c => c.method !== 'GET').length;
  const initialState = await state(); await enable();
  assert.equal((await read()).screenplay.scenes[0].blocks.length, 0, 'opening placeholder does not create a block');
  assert.equal(writes(await state()), writes(initialState));
  const original = '  Cha đặt thư.\n\nCon ga\u0301i nhìn 🙂.  ';
  await text(0).fill(original); const firstId = await block(0).getAttribute('data-script-block');
  await save(); assert.equal((await read()).screenplay.scenes[0].blocks[0].text, original);
  const point = original.indexOf('Con'); await text(0).evaluate((e, p) => e.setSelectionRange(p, p), point); await text(0).press('Enter');
  assert.equal(await editor.locator('[data-script-block]').count(), 2);
  assert.equal(await block(0).getAttribute('data-script-block'), firstId);
  assert.equal(await text(0).inputValue() + await text(1).inputValue(), original);
  const secondId = await block(1).getAttribute('data-script-block'); assert.notEqual(firstId, secondId);
  await text(1).press('Home'); await text(1).evaluate(e => e.setSelectionRange(0, 0)); await text(1).press('Backspace');
  assert.equal(await text(0).inputValue(), original); assert.equal(await editor.locator('[data-script-block]').count(), 1);
  await editor.getByRole('button', {name: 'Hoàn tác thao tác đoạn', exact: true}).click();
  assert.equal(await block(1).getAttribute('data-script-block'), secondId);
  await text(1).focus(); await text(1).evaluate(e => e.setSelectionRange(0, 0)); await text(1).press('Backspace');
  // Synthetic composition keyboard events must not split a Vietnamese word.
  await text(0).dispatchEvent('compositionstart', {data: 'ấ'});
  await text(0).dispatchEvent('keydown', {key: 'Enter', code: 'Enter', isComposing: true, keyCode: 229});
  await text(0).dispatchEvent('compositionend', {data: 'ấ'});
  assert.equal(await editor.locator('[data-script-block]').count(), 1); assert.equal(await text(0).inputValue(), original);
  await text(0).focus(); await text(0).evaluate(e => e.setSelectionRange(e.value.length, e.value.length)); await text(0).press('Shift+Enter');
  assert.equal(await editor.locator('[data-script-block]').count(), 1); assert.equal(await text(0).inputValue(), original + '\n');
  // Native insertion preserves multiline paste-like text literally; HTML is not executed.
  const pasted = '\n  <img src=x onerror="window.badPaste=true">\n\nLá thư vẫn kín.  ';
  await page.keyboard.insertText(pasted); assert.equal(await text(0).inputValue(), original + '\n' + pasted);
  assert.equal(await page.evaluate(() => window.badPaste), undefined);
  const action = await text(0).inputValue(); await text(0).press('End'); await text(0).evaluate(e => e.setSelectionRange(e.value.length, e.value.length)); await text(0).press('Enter');
  const spokenId = await block(1).getAttribute('data-script-block');
  await editor.getByLabel('Đang viết', {exact: true}).selectOption('character');
  const speaker = block(1).locator('[data-script-field="speaker"]'); await speaker.fill('Con gái'); await speaker.press('Enter');
  assert.equal(await page.evaluate(() => document.activeElement.dataset.scriptField), 'text');
  const speech = '  Không sao đâu cha ạ…\n\nCha cứ để đó.  ';
  await text(1).fill(speech); await text(1).press('End'); await text(1).evaluate(e => e.setSelectionRange(e.value.length, e.value.length)); await text(1).press('Enter');
  assert.equal(await block(2).locator('[data-script-field="speaker"]').count(), 0);
  await save(); project = await read();
  assert.deepEqual(project.screenplay.scenes[0].blocks.map(b => b.kind), ['action', 'dialogue', 'action']);
  assert.equal(project.screenplay.scenes[0].blocks[0].id, firstId); assert.equal(project.screenplay.scenes[0].blocks[0].text, action);
  assert.equal(project.screenplay.scenes[0].blocks[1].id, spokenId); assert.equal(project.screenplay.scenes[0].blocks[1].speaker, 'Con gái');
  assert.equal(project.screenplay.scenes[0].blocks[1].text, speech); assert.equal(project.screenplay.scenes[0].blocks[2].text, '');
  assert.deepEqual(project.screenplay.source_outline, source); assert.equal(project.screenplay.id, scriptId);
  // Kind conversion needs explicit confirmation before dropping a speaker; immediate undo restores it.
  await text(1).focus(); page.once('dialog', d => d.dismiss()); await editor.getByLabel('Đang viết', {exact: true}).selectOption('action');
  assert.equal(await speaker.inputValue(), 'Con gái');
  page.once('dialog', d => d.accept()); await editor.getByLabel('Đang viết', {exact: true}).selectOption('action');
  assert.equal(await block(1).locator('input').count(), 0); assert.equal(await text(1).inputValue(), speech);
  await editor.getByRole('button', {name: 'Hoàn tác thao tác đoạn', exact: true}).click(); assert.equal(await speaker.inputValue(), 'Con gái');
  // Reorder/delete/undo work without changing IDs. A subsequent edit invalidates structural undo.
  await block(2).locator('summary').click(); await block(2).getByRole('button', {name: 'Xóa khối', exact: true}).click();
  await editor.getByRole('button', {name: 'Hoàn tác thao tác đoạn', exact: true}).click(); assert.equal(await editor.locator('[data-script-block]').count(), 3);
  await block(1).locator('summary').click(); await block(1).getByRole('button', {name: 'Đưa khối lên', exact: true}).click();
  assert.equal(await block(0).getAttribute('data-script-block'), spokenId);
  await editor.getByRole('button', {name: 'Hoàn tác thao tác đoạn', exact: true}).click(); assert.equal(await block(0).getAttribute('data-script-block'), firstId);
  if (!await block(2).locator('details').evaluate(e => e.open)) await block(2).locator('summary').click();
  await block(2).getByRole('button', {name: 'Xóa khối', exact: true}).click(); await text(0).fill(action + '\nSửa mới hơn.');
  assert.equal(await editor.getByRole('button', {name: 'Hoàn tác thao tác đoạn', exact: true}).count(), 0);
  const nav = area.getByRole('navigation', {name: 'Các cảnh kịch bản'});
  await nav.getByRole('button').nth(1).click(); assert.equal(await editor.count(), 1, 'each explicitly selected scene uses the integrated editor');
  await enable(); await text(0).fill('Nội dung đầu.'); const removedId = await block(0).getAttribute('data-script-block');
  await block(0).locator('summary').click(); await block(0).getByRole('button', {name: 'Xóa khối', exact: true}).click();
  await text(0).fill('Nội dung mới.'); assert.notEqual(await block(0).getAttribute('data-script-block'), removedId, 'deleted IDs cannot be reused by the placeholder');
  await nav.getByRole('button').first().click(); await enable(); assert.equal(await text(0).inputValue(), action + '\nSửa mới hơn.');
  await save(); const roundTrip = structuredClone((await read()).screenplay);
  await page.reload(); await enable(); assert.equal(await text(0).inputValue(), roundTrip.scenes[0].blocks[0].text);
  assert.deepEqual(await editor.locator('[data-script-block]').evaluateAll(es => es.map(e => e.dataset.scriptBlock)), roundTrip.scenes[0].blocks.map(b => b.id));
  await text(1).focus(); await text(1).press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.tagName), 'SUMMARY', 'Tab remains native focus navigation');
  await editor.screenshot({path: path.join(directory, 'continuous-editor-current.png')});
  // Fake review references still focus the intended native field in the new editor.
  const panel = area.locator('.screenplay-feedback'); await panel.getByRole('button', {name: 'Nhận góp ý cảnh này', exact: true}).click();
  const latest = panel.locator(':scope > .script-review').first(); await latest.getByRole('group', {name: 'Ghi nhận của tác giả'}).waitFor();
  const beforeLink = await state(); await latest.getByRole('button', {name: 'Đến phần đang viết', exact: true}).first().click();
  await page.waitForFunction(id => document.activeElement.closest('[data-script-block]')?.dataset.scriptBlock === id, firstId);
  assert.equal(writes(await state()), writes(beforeLink));
  await text(0).fill('Buffer chưa lưu cần giữ.'); assert.equal(await latest.getByRole('button', {name: 'Đến phần đang viết', exact: true}).count(), 0);
  const offline = r => r.request().method() === 'PUT' ? r.abort('failed') : r.continue(); await page.route('**' + url, offline);
  await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click(); await page.locator('.save-toolbar .error').waitFor();
  assert.equal(await text(0).inputValue(), 'Buffer chưa lưu cần giữ.'); assert.deepEqual((await read()).screenplay, roundTrip);
  await page.unroute('**' + url, offline); project = await read(); await request(url, 'PUT', {...payload(project), title: 'Tên từ cửa sổ khác'});
  await area.getByRole('button', {name: 'Lưu kịch bản', exact: true}).click(); await page.locator('.save-toolbar .error').filter({hasText: 'cửa sổ khác'}).waitFor();
  assert.equal(await text(0).inputValue(), 'Buffer chưa lưu cần giữ.');
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({width, height: 900}); assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({path: path.join(directory, `continuous-editor-${width}.png`)});
  }
  // Existing Windows line endings have different stored/displayed offsets. Do not delete the wrong characters.
  project = await read(); const windows = structuredClone(project.screenplay);
  windows.scenes[0].blocks = [{id: uuid(), kind: 'action', speaker: '', text: 'A\r\nBC\r\nD'}];
  await request(url, 'PUT', {...payload(project), screenplay: {id: windows.id, version: windows.version, scenes: windows.scenes}});
  await page.reload(); await enable(); assert.equal(await text(0).inputValue(), 'A\nBC\nD');
  await text(0).focus(); await text(0).evaluate(e => e.setSelectionRange(2, 4)); await text(0).press('Enter');
  await save(); project = await read();
  assert.equal(project.screenplay.scenes[0].blocks[0].text, 'A\r\n');
  assert.equal(project.screenplay.scenes[0].blocks[1].text, '\r\nD');
  await text(1).focus(); await text(1).evaluate(e => e.setSelectionRange(0, 0)); await text(1).press('Backspace');
  assert.equal(await text(0).evaluate(e => e.selectionStart), 2, 'merge restores the displayed boundary, not the raw CRLF offset');
  await save(); assert.equal((await read()).screenplay.scenes[0].blocks[0].text, 'A\r\n\r\nD');
  const after = await state(); assert.deepEqual(after.provider_stages, []); assert.equal(after.image_requests, 0); assert.equal(after.writing_requests, 0); assert.equal(after.review_requests, 1);
  assert.deepEqual(errors, []);
  console.log('PASS continuous editor: explicit selection/no writes, exact round-trip/IDs, split/merge/undo, synthetic IME, Shift+Enter, multiline insertion, character/dialogue mapping, unfinished draft, conversion confirmation, reorder/delete, newer-edit guard, scene buffer, saved reload, fake review focus, offline/409, CRLF selection/merge caret, 3 widths, zero real model calls');
  await context.close(); await browser.close();
})().catch(e => {console.error(e); process.exit(1);});
