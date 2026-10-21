const assert = require('node:assert/strict');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {HighlightedQuote, FidelityPanel} = require(process.argv[2]);
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));
assert.equal(render(HighlightedQuote, {text:'🙂 A. quyết định pass. Sau đó học.', quote:'quyết định pass.'}), '🙂 A. <mark>quyết định pass.</mark> Sau đó học.');
assert.equal(render(HighlightedQuote, {text:'Lặp. Lặp.', quote:'Lặp.'}), 'Lặp. Lặp.');
assert.equal(render(HighlightedQuote, {text:'Đã sửa rồi.', quote:'pass'}), 'Đã sửa rồi.');
assert.ok(render(HighlightedQuote, {text:'<script>x</script>', quote:'<script>x</script>'}).includes('&lt;script&gt;'));
const report = {status:'unverified', withheld_count:1, checks:[{kind:'fidelity', section_index:0, section_title:'Middle', section_text:'Bản cũ: quyết định pass.', draft_quote:'quyết định pass.', author_quote:'Kết mở.', explanation:'Cần đối chiếu.', suggestion:'KHÔNG HIỂN THỊ', suggestion_status:'unverified', verification_note:'Chưa đủ căn cứ.'}]};
const html=render(FidelityPanel,{report,uiLanguage:'vi'});
assert.ok(html.includes('<mark>quyết định pass.</mark>'));
assert.ok(html.includes('Phần giữa'));
assert.ok(html.includes('bản chụp'));
assert.ok(html.includes('Nhận xét chưa xác minh'));
assert.ok(!html.includes('KHÔNG HIỂN THỊ'));
assert.ok(html.includes('Chưa đủ căn cứ.'));
assert.equal(render(FidelityPanel,{report:null,uiLanguage:'vi'}),'');
console.log('Fidelity rendering: 11 assertions passed');

const {isFidelityReport} = require(require('node:path').join(require('node:path').dirname(process.argv[2]), 'apiClient.js'));
assert.equal(isFidelityReport(report), true);
assert.equal(isFidelityReport({...report, checks:[{}]}), false);
assert.equal(isFidelityReport({...report, withheld_count:-1}), false);
assert.equal(isFidelityReport(null), false);
console.log('Fidelity response validation: 4 assertions passed');

const assessed = {...report, checks: [{...report.checks[0], assessment: {
  relation: 'contradictory', relation_reason: 'Hai nguồn trái nhau.',
  concern: 'supported', concern_reason: 'Nhận xét có căn cứ.',
  revision: 'violates', revision_reason: 'Đề xuất đổi ý đồ.'
}}]};
assert.equal(isFidelityReport(assessed), true);
assert.equal(isFidelityReport({...assessed, checks:[{...assessed.checks[0], assessment:{}}]}), false);
const assessedHtml = render(FidelityPanel, {report: assessed, uiLanguage:'vi'});
assert.ok(assessedHtml.includes('Hai trích dẫn có mâu thuẫn?'));
assert.ok(assessedHtml.includes('Nhận xét có căn cứ?'));
assert.ok(assessedHtml.includes('Gợi ý có giữ ý đồ?'));
assert.ok(assessedHtml.includes('Trái ý đồ'));
assert.ok(!assessedHtml.includes('KHÔNG HIỂN THỊ'));
console.log('Independent assessment: 7 assertions passed');
