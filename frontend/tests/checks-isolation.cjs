const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

const source = path.resolve(__dirname, '..');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'firstframe-check-isolation-'));
const frontend = path.join(root, 'frontend');
const marker = path.join(root, 'executed');
const commands = ['typecheck', 'lint', 'test', 'build'];
const stub = "#!/usr/bin/env node\nrequire('node:fs').writeFileSync(process.env.FIRSTFRAME_CHECK_MARKER, 'executed');\n";
function write(relative, content) {
  const file = path.join(frontend, relative);
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, content, {mode: 0o755});
}
function run(command) {
  fs.rmSync(marker, {force: true});
  const result = spawnSync('pnpm', [command], {cwd: frontend, encoding: 'utf8', timeout: 20000,
    env: {...process.env, PNPM_CONFIG_VERIFY_DEPS_BEFORE_RUN: 'false', FIRSTFRAME_CHECK_MARKER: marker}});
  assert.ifError(result.error);
  return result;
}
try {
  write('package.json', fs.readFileSync(path.join(source, 'package.json')));
  write('scripts/test.cjs', stub);
  for (const file of ['node_modules/.bin/tsc', 'node_modules/.bin/next',
    'node_modules/typescript/bin/tsc', 'node_modules/next/dist/bin/next']) write(file, stub);
  const guard = path.join(source, 'scripts/checks.cjs');
  if (fs.existsSync(guard)) write('scripts/checks.cjs', fs.readFileSync(guard));
  const failures = [];
  for (const directory of [root, frontend]) {
    for (const name of ['.env', '.env.production.local']) {
      const file = path.join(directory, name);
      fs.writeFileSync(file, 'FIRSTFRAME_FAKE_ENV=never-load\n');
      for (const command of commands) {
        const result = run(command);
        if (result.status === 0 || fs.existsSync(marker) || !result.stderr.includes('env')) {
          failures.push(`${path.basename(directory)}/${name}: ${command} did not refuse the env file`);
        }
      }
      fs.unlinkSync(file);
    }
  }
  assert.deepEqual(failures, [], 'Checks must stop before executing tools when env files exist');
  fs.writeFileSync(path.join(frontend, '.env.example'), 'EXAMPLE=allowed\n');
  for (const command of commands) {
    assert.equal(run(command).status, 0, `${command} must run in an isolated checkout`);
    assert.ok(fs.existsSync(marker), `${command} must execute its tool`);
  }
  console.log('Check isolation: all four commands refuse root/frontend env files and allow examples');
} finally {
  fs.rmSync(root, {recursive: true, force: true});
}
