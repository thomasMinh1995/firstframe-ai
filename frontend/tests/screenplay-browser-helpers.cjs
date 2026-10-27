// Explicit selection replaces the former automatic first scene; legacy suites keep testing the block editor.
async function openScriptScene(area, index = 0, {legacy = false} = {}) {
  await area.getByRole('navigation', {name: 'Các cảnh kịch bản'}).getByRole('button').nth(index).click();
  if (legacy) {
    const toggle = area.getByRole('button', {name: 'Dùng editor dạng khối', exact: true});
    if (await toggle.count()) await toggle.click();
  }
}
module.exports = {openScriptScene};
