const assert = require('node:assert/strict');
const Module = require('node:module');
const test = require('node:test');
const React = require('react');
const originalLoad = Module._load;
let slots, cursor, effects, changed;
const same = (a, b) => a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
const hooks = {
  ...React,
  useId: () => 'qa-editor',
  useState(initial) {
    const index = cursor++;
    if (!(index in slots)) slots[index] = typeof initial === 'function' ? initial() : initial;
    return [slots[index], value => {
      const next = typeof value === 'function' ? value(slots[index]) : value;
      if (!Object.is(next, slots[index])) { slots[index] = next; changed = true; }
    }];
  },
  useRef(initial) { const index = cursor++; return slots[index] ??= {current: initial}; },
  useMemo(fn, deps) {
    const index = cursor++;
    if (!same(slots[index]?.deps, deps)) slots[index] = {deps, value: fn()};
    return slots[index].value;
  },
  useCallback(fn, deps) { return hooks.useMemo(() => fn, deps); },
  useEffect(fn, deps) {
    const index = cursor++;
    if (!same(slots[index]?.deps, deps)) effects.push(() => {
      slots[index]?.cleanup?.(); slots[index] = {deps, cleanup: fn()};
    });
  },
};
Module._load = function(name, ...args) { return name === 'react' ? hooks : originalLoad.call(this, name, ...args); };
require.extensions['.css'] = () => {};
const {DraftWorkflow} = require(process.argv[2] + '/DraftWorkflow.js');
const {ScreenplayEditor} = require(process.argv[2] + '/ScreenplayEditor.js');
Module._load = originalLoad;
const listeners = new Map();
global.window = global.document = {
  activeElement: null,
  addEventListener: (name, fn) => { const set = listeners.get(name) ?? new Set(); set.add(fn); listeners.set(name, set); },
  removeEventListener: (name, fn) => listeners.get(name)?.delete(fn),
  getElementById: () => null, querySelectorAll: () => [],
};
global.matchMedia = () => ({matches: false, addEventListener() {}, removeEventListener() {}});
global.ResizeObserver = class { observe() {} disconnect() {} };
global.requestAnimationFrame = () => 1;
global.cancelAnimationFrame = () => {};
function mount(Component, props) {
  slots = []; listeners.clear();
  return nextProps => {
    props = nextProps ?? props;
    let tree, count = 0;
    do {
      assert.ok(count++ < 12, 'Effects must settle without a render loop');
      cursor = 0; effects = []; changed = false; tree = Component(props);
      effects.forEach(fn => fn());
    } while (changed);
    return tree;
  };
}
const fire = name => [...listeners.get(name) ?? []].forEach(fn => fn({detail: 'review'}));
test('Manual scrolling uses the latest callback', () => {
const run = {workflow_items: [], status: 'running'};
const calls = [];
const workflowProps = {run, candidate: null, following: false, onRead() {}, onFollowingChange: () => calls.push('old')};
const renderWorkflow = mount(DraftWorkflow, workflowProps);
renderWorkflow();
renderWorkflow({...workflowProps, onFollowingChange: () => calls.push('new')});
fire('wheel');
assert.deepEqual(calls, ['new'], 'Manual scrolling must call the latest parent callback');
});
test('Review opens a current scene after a same-ID script edit', () => {
const scene = id => ({id, source_scene_id: id, heading: id, blocks: []});
const project = {id: 'project', screenplay: {id: 'script', scenes: [scene('old')], source_outline: {scenes: [], source: {draft: {title: '', logline: '', sections: []}, context: {premise: '', constraints: [], pending_questions: [], clarifications: []}}}}};
const editorProps = {project, savedProject: {id: 'other'}};
const renderEditor = mount(ScreenplayEditor, editorProps);
renderEditor();
const updated = {...editorProps, project: {...project, screenplay: {...project.screenplay, scenes: [scene('new')]}}};
renderEditor(updated);
fire('workspace-tool-change');
const tree = renderEditor();
function find(node, name) {
  if (!node || typeof node !== 'object') return;
  if (node.type?.name === name) return node;
  for (const child of React.Children.toArray(node.props?.children)) { const match = find(child, name); if (match) return match; }
}
assert.equal(find(tree, 'ContinuousSceneEditor')?.props.scene.id, 'new', 'Opening review after a same-ID script edit must select a current scene');
});
