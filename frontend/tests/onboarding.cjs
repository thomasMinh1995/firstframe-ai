const assert = require('node:assert/strict');
const {
  initialTour, reduceTour: reduce, parseTour, entryStep, nextStep, previousStep, continuation,
} = require(process.argv[2] + '/onboardingState.js');

const empty = Object.freeze({ projectId: null, hasAnalysis: false, hasDraft: false, briefChanged: false });
const idea = Object.freeze({ ...empty, projectId: 'p1' });
const analyzed = Object.freeze({ ...idea, hasAnalysis: true });
const draft = Object.freeze({ ...analyzed, hasDraft: true });
const changed = Object.freeze({ ...draft, briefChanged: true });
const record = (status, stepId = 'idea', projectId = 'p1') => JSON.stringify({ version: 2, status, stepId, projectId });
const load = raw => reduce(initialTour, { type: 'load', raw });
const open = (context, step) => {
  let s = reduce(load(null), { type: 'open', resume: false, context });
  return step ? reduce(s, { type: 'navigate', step, context }) : s;
};
const practice = (context, step) => reduce(open(context, step), { type: 'practice', context });

assert.equal(load(null).offerAllowed, true);
for (const raw of [undefined, '', '{', 'null', '[]', '{"version":2}', record('bogus'), record(['active']), record('active', 'unknown')]) {
  assert.equal(load(raw).offerAllowed, false);
  assert.equal(parseTour(raw), null);
}
for (const status of ['active', 'waiting']) {
  const s = load(record(status));
  assert.equal(s.record.status, 'paused');
  assert.equal(s.request, null);
}
for (const status of ['dismissed', 'completed']) assert.equal(load(record(status)).record.status, status);
assert.equal(reduce(load(record('dismissed')), { type: 'load', raw: null }).record.status, 'dismissed');
assert.deepEqual([entryStep(empty), entryStep(idea), entryStep(analyzed), entryStep(draft), entryStep(changed)],
  ['new-project', 'idea', 'choices', 'draft', 'idea']);
assert.equal(entryStep({ ...draft, hasAnalysis: false }), 'idea');
// Help always restarts at creation, regardless of data or saved tour progress.
for (const context of [empty, idea, analyzed, draft, changed]) {
  for (const status of ['active', 'waiting', 'paused', 'dismissed', 'completed']) {
    const restarted = reduce(load(record(status, 'script')), { type: 'open', resume: false, context });
    assert.equal(restarted.record.stepId, 'new-project');
    assert.equal(restarted.record.projectId, context.projectId);
    assert.equal(restarted.record.status, 'active');
  }
}
assert.equal(reduce(load(record('paused', 'script')), { type: 'open', resume: true, context: draft }).record.stepId, 'script');
assert.equal(nextStep('idea', idea), null);
assert.equal(nextStep('idea', analyzed), 'choices');
assert.equal(previousStep('draft', changed), 'idea');

// The first creation changes project ID; a PUT/save cannot release this wait.
let s = practice(empty, 'new-project');
assert.equal(continuation(s, empty), null);
s = reduce(s, { type: 'begin', kind: 'create', context: empty });
const create = s.request;
assert.ok(create);
assert.equal(reduce(s, { type: 'success', ticket: null, resultId: 'old' }), s);
s = reduce(s, { type: 'success', ticket: create, resultId: 'p1' });
assert.equal(s.record.projectId, 'p1');
assert.equal(continuation(s, idea), 'idea');
s = reduce(s, { type: 'open', resume: true, context: idea });
assert.equal(s.record.stepId, 'idea');

// Input-only steps work without a save, model response, or any text edit.
assert.equal(continuation(practice(idea, 'idea'), idea), null);
for (const [from, to] of [['draft', 'outline'], ['outline', 'script'], ['script', 'save']]) {
  assert.equal(nextStep(from, draft), to);
  assert.equal(previousStep(to, draft), from);
  const waiting = practice(draft, from);
  assert.equal(continuation(waiting, draft), to);
  assert.equal(reduce(waiting, { type: 'open', resume: true, context: draft }).record.stepId, to);
}
for (const step of ['choices', 'draft', 'outline', 'script', 'save']) {
  assert.equal(continuation(load(record('paused', step)), changed), 'idea');
  assert.equal(nextStep(step, changed), 'idea');
}
assert.equal(nextStep('save', draft), null);

// Data appearing alone is not a successful request for the current tour.
s = practice(idea, 'idea');
assert.equal(continuation(s, analyzed), null);
s = reduce(s, { type: 'begin', kind: 'analyze', context: idea });
const analysis = s.request;
assert.equal(reduce(s, { type: 'success', ticket: analysis, resultId: 'other' }), s);
assert.equal(continuation(s, analyzed), null);
const failed = reduce(s, { type: 'failed', ticket: analysis });
assert.equal(failed.record.status, 'paused');
assert.equal(continuation(failed, idea), 'idea');
s = reduce(s, { type: 'success', ticket: analysis, resultId: 'p1' });
assert.equal(continuation(s, analyzed), 'choices');
assert.equal(reduce(s, { type: 'success', ticket: analysis, resultId: 'p1' }), s, 'duplicate result ignored');

s = practice(analyzed, 'choices');
assert.equal(continuation(s, draft), null, 'new draft needs the matching result');
s = reduce(s, { type: 'begin', kind: 'plan', context: analyzed });
s = reduce(s, { type: 'success', ticket: s.request, resultId: 'p1' });
assert.equal(continuation(s, draft), 'draft');
assert.equal(continuation(practice(draft, 'choices'), draft), 'draft', 'existing draft can be viewed without regeneration');

// Dismissal, restart, switching projects and cross-tab changes invalidate callbacks.
s = reduce(practice(idea, 'idea'), { type: 'begin', kind: 'analyze', context: idea });
const oldTicket = s.request;
s = reduce(s, { type: 'dismiss', context: idea });
assert.equal(reduce(s, { type: 'success', ticket: oldTicket, resultId: 'p1' }), s);
s = reduce(s, { type: 'open', resume: false, context: idea });
s = reduce(s, { type: 'navigate', step: 'idea', context: idea });
s = reduce(s, { type: 'practice', context: idea });
s = reduce(s, { type: 'begin', kind: 'analyze', context: idea });
assert.equal(reduce(s, { type: 'success', ticket: oldTicket, resultId: 'p1' }), s);
const newTicket = s.request;
for (const terminal of ['dismissed', 'completed']) {
  const external = reduce(s, { type: 'external', raw: record(terminal) });
  assert.equal(external.record.status, terminal);
  assert.equal(reduce(external, { type: 'success', ticket: newTicket, resultId: 'p1' }), external);
}
const switched = reduce(s, { type: 'pause' });
assert.equal(reduce(switched, { type: 'success', ticket: newTicket, resultId: 'p1' }), switched);
assert.equal(continuation(switched, { ...draft, projectId: 'p2' }), 'draft');
assert.equal(reduce(s, { type: 'external', raw: null }).record.status, 'paused');
assert.equal(reduce(s, { type: 'external', raw: null }).offerAllowed, false);

const finish = reduce(open(draft, 'save'), { type: 'complete', context: draft });
assert.equal(finish.record.status, 'completed');
assert.equal(reduce(open(draft, 'save'), { type: 'complete', context: changed }).record.stepId, 'idea');
assert.equal(reduce(open(draft, 'draft'), { type: 'complete', context: draft }).record.status, 'active');
assert.deepEqual(empty, { projectId: null, hasAnalysis: false, hasDraft: false, briefChanged: false });
console.log('Tour checks passed: storage, seven-step navigation, local practice, old drafts, operation failures, request/session isolation, first creation, cross-tab dismissal and completion.');
