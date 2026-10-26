const assert = require('node:assert/strict');
const { anchoredReview } = require(process.argv[2] + '/CardFeedback.js');
const source = { draft: { title: 'Cuộc gọi', logline: 'Một người chần chừ.', sections: [
 { title: 'Characters', content: 'Hai cha con.' }, { title: 'Beginning', content: 'Anh nhìn máy. Anh bấm gọi.' },
 { title: 'Ending', content: 'Cha bắt máy. Anh buông tay.' },
] }, context: { idea: 'Một cuộc gọi nhỡ.', constraints: [], clarifications: [
 { question: 'Kết?', answer: 'Dừng khi bắt máy.', input_index: 0 },
] } };
const vi = 'Card 4 · Kết thúc · 2: “Anh buông tay.” ↔ Card 3 · Kết thúc · 1: “Cha bắt máy.”\nLàm rõ 1: “Dừng khi bắt máy.”\nMột cử chỉ đúng điểm dừng.';
const find = message => anchoredReview({ message }, source);
const result = find(vi);
assert.deepEqual(result.cardIds, ['section-2-part-1','section-2']);
assert.equal(result.observation, 'Một cử chỉ đúng điểm dừng.');
assert.equal(result.decision.text, 'Dừng khi bắt máy.');
assert.deepEqual(find(vi.replaceAll('Kết thúc','Ending').replace('Làm rõ','Clarification')).cardIds, result.cardIds);
assert.equal(find(vi.replace('Anh buông tay.', 'Anh cúp máy.')), null);
assert.equal(find(vi.replace('Dừng khi bắt máy.', 'Kể thêm cuộc nói chuyện.')), null);
assert.equal(find('Card 4 cần thêm cảm xúc.'), null);
assert.equal(anchoredReview({ message: vi }, null), null);
assert.deepEqual(find('Characters: “Hai cha con.”\nLàm rõ 1: “Dừng khi bắt máy.”\nChỉ hai người.').cardIds, ['section-0']);
assert.deepEqual(find('logline: “Một người chần chừ.”\nLàm rõ 1: “Dừng khi bắt máy.”\nGiữ ngắn.').cardIds, ['draft-logline']);
assert.equal(find(vi.replace('Card 3 · Kết thúc · 1: “Cha bắt máy.”', 'Card 4 · Kết thúc · 2: “Anh buông tay.”')), null);
assert.equal(find('Card 4 · Kết thúc · 2: “Anh buông tay.”\nÝ tưởng: “Một cuộc gọi nhỡ.”\nGắn với ý tưởng.').decision.label, 'Ý tưởng');
console.log('Card feedback checks passed: exact VN/EN sources, pair and context anchors, forged quotes, self-pairs, legacy fallback.');

const { readRevisionNotes, validatedTargets } = require(process.argv[2] + '/revisionNotes.js');
source.artifact_id = 'f1';
const note = { note_id: 'n1', artifact_id: 'f1', comparison: 'uncertain', observation: 'Bounded question',
 suggestion: 'Check the stopping point', decision_id: 'answer-0', decision_question: 'Kết?', decision_quote: 'Dừng khi bắt máy.',
 targets: [{ target_id: 'section-2-part-1', quote: 'Anh buông tay.' }, { target_id: 'section-2', quote: 'Cha bắt máy.' }] };
assert.deepEqual(validatedTargets(note, source, 'f1').map(t => t.target_id), ['section-2-part-1', 'section-2']);
for (const change of [
 { artifact_id: 'f2' }, { decision_question: 'Other question' }, { decision_quote: 'Other answer' },
 { targets: [note.targets[0], { target_id: 'section-1', quote: 'Cha bắt máy.' }] },
 { targets: [note.targets[0], note.targets[0]] },
]) assert.equal(validatedTargets({ ...note, ...change }, source, 'f1'), null);
assert.equal(validatedTargets(note, { ...source, artifact_id: 'f2' }, 'f1'), null);
assert.equal(readRevisionNotes({}), null);
assert.equal(readRevisionNotes({ revision_notes: [note, note] }), null);
assert.equal(readRevisionNotes({ revision_notes: [{ ...note, targets: null }] }), null);
assert.deepEqual(readRevisionNotes({ revision_notes: [] }), []);
assert.deepEqual(readRevisionNotes({ revision_notes: [note] }), [note]);
// Whitespace and same-title sections are significant; never relocate a quote by text.
const duplicate = structuredClone(source);
duplicate.draft.sections.push({ ...duplicate.draft.sections[2] });
assert.equal(validatedTargets({ ...note, targets: [{ target_id: 'section-3', quote: 'Cha bắt máy.' }] }, duplicate, 'f1')[0].target_id, 'section-3');
assert.equal(validatedTargets({ ...note, targets: [{ target_id: 'section-3', quote: ' Cha bắt máy.' }] }, duplicate, 'f1'), null);
console.log('Structured priority checks passed: artifact, question and exact target binding, duplicates, partial pairs and legacy metadata.');

// AI verdicts must not be presented as a judgment of the writer or demo readiness.
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { CardFeedback } = require(process.argv[2] + '/CardFeedback.js');
const { StoryFeedback, StoryResultCards } = require(process.argv[2] + '/StoryResultCards.js');
const evaluation = { artifact_id: 'f1', passed: true, rubric_scores: { story_clarity: 4 },
  findings: [], revision_notes: [] };
const noAction = () => assert.fail('Reading feedback must not trigger an edit or AI action');
for (const language of ['vi', 'en']) {
  for (const passed of [true, false, null]) {
    const result = { analysis: { summary: 'Một khoảnh khắc.', notes: [], missing_information: [] },
      story_plan: source.draft, evaluation: { ...evaluation, passed } };
    const before = structuredClone(result);
    const html = renderToStaticMarkup(React.createElement(StoryResultCards, { result, uiLanguage: language }));
    assert.ok(!html.includes('Sẵn sàng cho bản demo') && !html.includes('Ready for demo pass'));
    assert.ok(!html.includes('Cần chỉnh sửa') && !html.includes('Needs revision'));
    assert.ok(!html.includes('result-pill'), 'AI passed is not a readiness badge');
    assert.ok(html.includes(language === 'vi' ? 'không đánh giá năng lực viết' : 'do not assess your writing ability'));
    assert.ok(html.includes(language === 'vi' ? 'chứng minh bản thảo đã tốt hơn' : 'prove that your draft has improved'));
    assert.ok(html.includes('4/5'), 'Reference scores remain available');
    assert.deepEqual(result, before);
  }
  for (const revision_notes of [null, []]) {
    const html = renderToStaticMarkup(React.createElement(StoryFeedback, {
      evaluation: { ...evaluation, revision_notes }, uiLanguage: language, onChoose: noAction, onTarget: noAction,
    }));
    assert.ok(html.includes(language === 'vi' ? 'có thể sai hoặc bỏ sót' : 'may be wrong or miss things'));
    assert.ok(html.includes(language === 'vi' ? 'bạn quyết định giữ hay tự sửa' : 'you decide what to keep or revise yourself'));
  }
}
for (const current of [true, false]) {
  const html = renderToStaticMarkup(React.createElement(CardFeedback, {
    cardId: 'section-2', label: 'Kết thúc', evaluation, source, current, onClose: noAction, onReview: noAction,
  }));
  assert.ok(html.includes('có thể sai hoặc bỏ sót'));
  assert.ok(html.includes('không đánh giá năng lực viết'));
  assert.ok(html.includes('bạn quyết định giữ hay tự sửa'));
}
console.log('HITL presentation checks passed: VI/EN, true/false/unknown AI verdicts, reference scores, legacy/structured feedback, current/stale cards, no actions or mutation.');
