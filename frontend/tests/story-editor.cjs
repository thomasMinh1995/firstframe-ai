// Compile StoryPlanEditor.tsx to a temporary CommonJS directory; pass it as argv[2].
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { StoryPlanEditor, splitStorySection, replaceStoryBeat } = require(process.argv[2] + '/StoryPlanEditor.js');
const section = (title, content) => ({ title, purpose: 'Keep original purpose', content });
const render = draft => {
  const before = structuredClone(draft);
  const html = renderToStaticMarkup(React.createElement(StoryPlanEditor, {
    draft, dirty: true, onChange: () => assert.fail('Reading must never edit a draft'),
  }));
  assert.deepEqual(draft, before, 'Reading preserves the existing contract and section order');
  return html;
};
const draft = { title: 'Cơm tối', logline: 'Một cử chỉ nhỏ.', sections: [
  section('Characters', 'Nhân vật giữ nguyên.'), section('Beginning', 'Bắt đầu im lặng.'),
  section('Middle', 'Con kéo ghế.'), section('Ending', 'Mẹ đẩy bát cơm.'),
] };
let html = render(draft);
const path = html.split('<ol')[1].split('</ol>')[0];
assert.ok(path.includes('section-1-label') && path.includes('section-2-label') && path.includes('section-3-label'));
assert.ok(!path.includes('Nhân vật giữ nguyên.'));
assert.ok(path.indexOf('Bắt đầu im lặng.') < path.indexOf('Con kéo ghế.'));
assert.ok(path.indexOf('Con kéo ghế.') < path.indexOf('Mẹ đẩy bát cơm.'));
assert.match(html, /<details[^>]*class="story-draft-context"/);
assert.ok(html.includes('section-0-label'), 'Context retains its original index for editing');
html = render({ ...draft, sections: [section('A quiet gesture', '<script>unsafe</script>')] });
assert.ok(html.split('<ol')[1].split('</ol>')[0].includes('A quiet gesture'), 'Unknown legacy sections remain primary content');
assert.ok(html.includes('&lt;script&gt;unsafe&lt;/script&gt;'));
assert.ok(!html.includes('story-draft-context'));
html = render({ ...draft, sections: [] });
assert.ok(html.includes('Chưa có nội dung phác thảo.'));
assert.ok(!html.includes('Vải đầu mùa'));
const source = '  Mẹ chờ.\n\nCon về muộn!  “Ăn cơm nhé?”\r\nCon kéo ghế.  ';
let spans = splitStorySection(source);
assert.equal(spans.length, 4);
let next = replaceStoryBeat(source, spans, 1, 'Con về rất muộn.');
assert.equal(next.content, source.replace('Con về muộn!', 'Con về rất muộn.'));
const otherEdit = replaceStoryBeat(next.content, next.spans, 3, 'Con đặt đũa cạnh bát mẹ.');
const canceled = replaceStoryBeat(otherEdit.content, otherEdit.spans, 1, source.slice(spans[1].start, spans[1].end));
assert.equal(canceled.content, source.replace('Con kéo ghế.', 'Con đặt đũa cạnh bát mẹ.'));
assert.equal(replaceStoryBeat(source, spans, 0, 'a'.repeat(10001)), null);
const long = 'Một cử chỉ rất nhỏ '.repeat(35) + 'khép lại buổi tối.';
spans = splitStorySection(long);
assert.ok(spans.length > 1 && spans.every(s => s.end - s.start <= 200));
assert.equal(replaceStoryBeat(long, spans, 1, long.slice(spans[1].start, spans[1].end)).content, long);
const unicode = 'Mẹ chờ 👩‍👦. Con về.\nBát cơm còn ấm.';
assert.equal(splitStorySection(unicode).length, 3);
assert.equal(splitStorySection('3.5 phút. Con ngồi xuống.').length, 2);
for (const [text, expected] of [
  ['Cha chờ.\uFEFFCon về.', ['Cha chờ.', 'Con về.']],
  ['\uFEFFCha chờ.\uFEFF', ['Cha chờ.']],
  ['Cha chờ.\u0085Con về.', ['Cha chờ.\u0085Con về.']],
  ['Cha chờ.\u001CCon về.', ['Cha chờ.\u001CCon về.']],
]) assert.deepEqual(splitStorySection(text).map(s => text.slice(s.start, s.end)), expected);
html = render({ ...draft, sections: [section('Beginning', 'A. B.'), section('Middle', 'C. D.'), section('Ending', 'E. F.')] });
assert.equal((html.match(/class="story-card-number"/g) || []).length, 6);
assert.ok(html.includes('section-0-part-1-label'));
console.log('Story editor checks passed: real sections, original indices, reading order, legacy fallback, escaping, empty draft and no mutation.');
console.log('Beat checks passed: exact whitespace, multi-card edits/cancel, length limit, Unicode, long prose, decimals and six real cards.');
