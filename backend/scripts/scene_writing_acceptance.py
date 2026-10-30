"""Acceptance criteria for the eight frozen synthetic cases, not a general NLI judge."""
import re

QUIET = ['Cha đặt phong thư kín lên bàn rồi lùi lại.',
         'Con gái đặt tay cạnh phong thư, chưa nhận hoặc mở; dừng ở đó.']
EXPECTED = {
    'quiet-open-ending': QUIET,
    'parent-dialogue': QUIET,
    'gentle-comedy': ['Nam lấy chiếc túi đang cầm che chỗ khóa kẹt.',
        'Hà nhìn thấy, đưa tay chờ Nam chịu nhờ giúp; Nam miễn cưỡng đưa vạt áo ra.'],
    'limited-resources': ['Bình đặt đèn pin xuống.',
        'Lan kéo rèm để ánh đèn đường rọi vào bàn; cả hai nghiêng tờ giấy để đọc.'],
    'draft-workflow-qwen7b-2026-10-30': ['Bố đưa cho Linh một lá thư.',
        'Linh nhận thư nhưng chưa mở, giữ quyền quyết định.'],
    'draft-workflow-qwen7b-saved-brief-2026-10-30': [
        'Chiều mưa trong căn bếp nhỏ, con gái đặt chìa khóa lên bàn trước khi đi học xa.'],
    'later-scene': ['Linh đứng trước cánh cửa, tay nắm lấy lá thư chưa mở.'],
}


def assess(name, scene):
    actions = [b['text'] for b in scene['blocks'] if b['kind']=='action']
    dialogue = [b for b in scene['blocks'] if b['kind']=='dialogue']
    checks = {'no_unrequested_dialogue': not dialogue if name!='parent-dialogue' else len(dialogue)==2}
    if name == 'english':
        checks['english_heading'] = scene['heading']=='SCENE 2'
        checks['two_translated_beats'] = len(actions)==2
        text = ' '.join(actions).casefold()
        checks['english_text'] = text.isascii() and 'father' in text and 'daughter' in text
        checks['sealed_letter_and_table'] = bool(actions) and all(w in actions[0].casefold() for w in ('sealed','letter','table'))
        checks['daughter_has_not_opened_or_received'] = len(actions)==2 and all(w in actions[1].casefold() for w in ('hand','letter','open')) and bool(re.search(r'\b(not|neither|without|unopened)\b',actions[1].casefold()))
    else:
        checks['source_actions_in_exact_order_once'] = actions == EXPECTED[name]
    if name == 'parent-dialogue':
        checks['one_line_per_requested_speaker'] = [b['speaker'] for b in dialogue]==['Cha','Con gái']
        checks['father_child_address'] = len(dialogue)==2 and dialogue[0]['text'].startswith('Cha ') and dialogue[1]['text'].startswith('Con ')
        checks['no_wrong_pronouns_or_narrated_actions'] = not re.search(
            r'\b(tôi|bạn|em|đặt|đưa|nhận|kéo|mở|tha thứ|hòa giải)\b', ' '.join(b['text'] for b in dialogue).casefold())
    return checks
