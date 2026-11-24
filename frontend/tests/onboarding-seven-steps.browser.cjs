const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { setup, fullProject } = require('./onboarding.browser.cjs');

const titles = ['Dự án mới', 'Chất liệu', 'Làm rõ', 'Story plan', 'Dàn cảnh', 'Viết & sửa', 'Lưu'];

async function check(browser, width) {
  const { page, mock, close } = await setup(browser, {
    projects: [fullProject('p1')], viewport: {width, height: 900},
  });
  const data = structuredClone(mock.projects);
  const requests = structuredClone(mock.calls);
  const dialog = page.getByRole('dialog');
  const click = name => dialog.getByRole('button', {name, exact: true}).click();
  await page.getByRole('button', {name: 'Hướng dẫn sử dụng', exact: true}).click();
  for (const [i, title] of titles.entries()) {
    await dialog.getByText(`Bước ${i + 1}/7`, {exact: true}).waitFor();
    assert.equal(await dialog.getByRole('heading').innerText(), title);
    if (i < 6) await click('Tiếp');
  }
  await click('Khám phá đề xuất và lịch sử');
  await page.waitForFunction(() => document.activeElement?.matches('.workspace-library > summary'));
  await page.getByRole('button', {name: 'Tiếp tục hướng dẫn', exact: true}).click();
  await click('Hoàn tất hướng dẫn');
  await page.waitForFunction(() => document.activeElement?.id === 'save-status');
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('firstframe:onboarding:v2')));
  assert.equal(stored.status, 'completed');
  assert.deepEqual(mock.projects, data);
  assert.deepEqual(mock.calls, requests, 'tour navigation must not save or request AI');
  await close();
  console.log(`PASS seven-step onboarding at ${width}px`);
}

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    for (const width of [1280, 390]) await check(browser, width);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
