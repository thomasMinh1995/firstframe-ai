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
