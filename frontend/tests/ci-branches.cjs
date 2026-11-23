const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const workflow = fs.readFileSync(path.resolve(__dirname, '../../.github/workflows/checks.yml'), 'utf8');
for (const event of ['pull_request', 'push']) {
  const branches = workflow.match(new RegExp(`^  ${event}:\\n    branches: \\[(.+)\\]`, 'm'))?.[1].split(',').map(s => s.trim());
  for (const branch of ['dev', 'main']) assert.ok(branches?.includes(branch), `${event} must validate ${branch}`);
}
console.log('PASS CI validates dev/main pull requests and pushes');
