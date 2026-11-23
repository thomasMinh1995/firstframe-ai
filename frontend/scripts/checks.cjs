const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

const root = path.resolve(__dirname, '..');
for (const directory of [root, path.dirname(root)]) {
  const envFiles = fs.readdirSync(directory).filter(name => /^\.env(?:\.|$)/.test(name) && name !== '.env.example');
  if (envFiles.length) {
    console.error(`Refusing checks with env files in ${directory}: ${envFiles.join(', ')}. Use a clean checkout and explicit QA variables.`);
    process.exit(1);
  }
}
const commands = {
  typecheck: [require.resolve('typescript/bin/tsc'), '--noEmit'],
  lint: [path.join(root, 'node_modules/eslint/bin/eslint.js'), 'app', '--max-warnings=0'],
  test: [path.join(__dirname, 'test.cjs')],
  build: [require.resolve('next/dist/bin/next'), 'build'],
};
const command = commands[process.argv[2]];
if (!command) {
  console.error('Unknown check. Choose typecheck, lint, test or build.');
  process.exit(1);
}
const result = spawnSync(process.execPath, [...command, ...process.argv.slice(3)], {
  cwd: root, stdio: 'inherit', env: {...process.env, NEXT_TELEMETRY_DISABLED: '1'},
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
