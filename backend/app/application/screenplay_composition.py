"""Conservative first-draft composition for the local Qwen 7B profile."""
import json
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from app.api.schemas.provenance import TextProvenance
from app.api.schemas.screenplays import SceneWritingResult
from app.application.ai_provider import StructuredRequest
from app.application.provenance import draft_fields, scene_fields
from app.application.language import detect_response_language, resolve_response_language
from app.application.review_opposition import character_mentions, normalized, contains, NEGATION

PROMPT = Path(__file__).resolve().parents[3] / 'domains/short-film/prompts/screenplay_composition_prompt.md'
VERB = re.compile(r'\b(?:đặt|đưa|nhận|cầm|lấy|mở|đóng|put|puts|give|gives|take|takes|hold|holds|open|opens|close|closes)\b')
BOUNDARY = re.compile(r'\b(?:lên|xuống|trên|vào|ra|cạnh|bên|trước|sau|ở|rồi|và|nhưng|on|onto|in|at|to|before|after|then|and|but)\b')
TURN_REQUEST = re.compile(r'\b(cha|bố|con gái|con trai|chị|em)\s+(?:nói|đáp)\s+(?:một|1)\s+câu\b')
PRODUCTION_ONLY = re.compile(r'(?i)^(?:phim(?: ngắn)?|(?:a )?short film)\s+(?:dài\s+)?(?:\d+|một|hai|ba|bốn|năm|sáu|one|two|three|four|five|six)\s*(?:phút|giây|minutes?|seconds?)\s*[.!?]?$')
VISIBLE = re.compile(r'\b(ngồi|đứng|uống|đi|bước|nhìn|kéo|đẩy|nghiêng|sit|sits|stand|stands|drink|drinks|walk|walks|look|looks|pull|pulls|push|pushes|tilt|tilts)\b')
QUOTED = re.compile(r'''["“”]|(?:^|[\s(])'[^'\n]+'(?=$|[\s).,;!?])''')


class SceneSourceConflict(ValueError):
    pass


class DialogueTurn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    after_action: int = Field(ge=0, le=100)
    speaker: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=10000)


class BoundDialogueTurn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    after_action: int = Field(ge=0, le=100)
    speaker: str
    self_reference: str
    intent: Literal['uncertain', 'needs_time', 'will_wait']


UTTERANCE_SUFFIXES = {
    'Vietnamese': {'uncertain':'chưa biết phải nói thế nào.', 'needs_time':'cần thêm thời gian.', 'will_wait':'có thể chờ.'},
    'English': {'uncertain':'am not sure what to say.', 'needs_time':'need more time.', 'will_wait':'can wait.'},
}

# Non-event reactions cannot move props, repeat movement or decide an open outcome.
REACTIONS = {
    'Vietnamese': (
        {'invite':'{Other}, {self} nghe đây.', 'unhurried':'{Self} không muốn giục {other}.',
         'uncertain':'{Self} chưa biết bắt đầu thế nào.', 'give_space':'{Other} cứ nghĩ thêm một chút.',
         'listening':'{Self} muốn nghe {other} nói.', 'no_pressure':'{Self} không cần câu trả lời ngay.'},
        {'needs_time':'{Self} cần thêm một chút thời gian, {other}.', 'thinking':'{Self} vẫn đang nghĩ, {other}.',
         'uncertain':'{Self} chưa biết trả lời thế nào, {other}.', 'acknowledge':'{Self} nghe rồi, {other}.',
         'think_it_through':'{Self} muốn nghĩ kỹ hơn, {other}.', 'no_answer_yet':'{Self} chưa có câu trả lời, {other}.'}),
    'English': (
        {'invite':'What are you thinking?', 'unhurried':"I don't want to rush you.",
         'uncertain':"I'm not sure where to start.", 'give_space':'You can take your time.',
         'listening':'I want to hear what you think.', 'no_pressure':"You don't have to answer right now."},
        {'needs_time':'I need a little more time.', 'thinking':"I'm still thinking about it.",
         'uncertain':"I don't know what to say yet.", 'acknowledge':'I hear you.',
         'think_it_through':"I'd like to think it through.", 'no_answer_yet':"I don't have an answer yet."}),
}


class SceneComposition(BaseModel):
    model_config = ConfigDict(extra='forbid')
    heading: str = Field(min_length=1, max_length=500)
    translations: list[Annotated[str, Field(min_length=1, max_length=10000)]]
    dialogue: list[DialogueTurn]


def per_scene_dialogue(proposal, reconciled=False):
    """Bind two speakers only when the author explicitly requests that order per scene."""
    script = proposal.source_screenplay
    target = next(s for s in script.scenes if s.id == proposal.target_scene_id)
    source = next(s for s in script.source_outline.scenes if s.id == target.source_scene_id)
    sources = script.source_outline.scenes if reconciled else [source]
    names = {}
    for s in sources:
        for name in re.split(r'[,;/\n]', s.characters):
            if name.strip():
                names.setdefault(normalized(name), name.strip())
    cast = list(names.values())
    if len(cast) != 2 or len(set(map(normalized, cast))) != 2:
        return []
    context = script.source_outline.source.context
    texts = [context.idea, *context.constraints, *[a.answer for a in context.clarifications]]
    requested = set()
    for text in texts:
        text = normalized(text)
        count = re.search(r'\bmỗi cảnh\b[^.!?\n]{0,80}\bhai câu(?: thoại)?\b|\beach scene\b[^.!?\n]{0,80}\btwo (?:short )?dialogue lines\b', text)
        if (not count or NEGATION.search(count.group()) or QUOTED.search(text)
                or re.search(r'\b(có thể|may|optional)\b', count.group())):
            continue
        for first, second in (cast, cast[::-1]):
            a, b = map(lambda name: re.escape(normalized(name)), (first, second))
            order = (rf'\b{a}\s+nói (?:một câu|trước)[,; ]+{b}\s+đáp (?:một câu|sau)\b|'
                     rf'\b{a}\s+trước (?:rồi|và)\s+{b}\b|\b{a}\s+first and\s+{b}\s+second\b')
            match = re.search(order, text)
            prefix = re.split(r'[.;!?]', text[:match.start()])[-1] if match else ''
            if match and not NEGATION.search(prefix) and not contains(prefix, 'đừng'):
                requested.add((first, second))
    if len(requested) == 1 and any(re.fullmatch(
            r'(?:hoàn toàn\s+)?không(?: có| lời)? thoại|(?:strictly )?no dialogue|without dialogue', clause.strip())
            for text in texts for clause in re.split(r'[,;.!?]', normalized(text))):
        raise SceneSourceConflict('Yêu cầu hai lượt thoại mâu thuẫn với yêu cầu im lặng; hãy chọn lại trước khi viết.')
    return list(next(iter(requested))) if len(requested) == 1 else []


def speaker_voices(proposal, speakers):
    context = proposal.source_screenplay.source_outline.source.context
    clauses = [clause for text in [context.idea, *context.constraints, *[a.answer for a in context.clarifications]]
               for clause in re.split(r'[,;.!?]', normalized(text))]
    voices = {}
    for speaker in speakers:
        choices = {match.group(1) for clause in clauses
                   if (match := re.search(rf'\b{re.escape(normalized(speaker))}\s+xưng\s+(\w+)\b(?=\s*(?:gọi\b|và\b|với\b|đừng\b|$))', clause))
                   and not NEGATION.search(clause[:match.start()]) and not contains(clause[:match.start()], 'đừng')}
        if len(choices) == 1:
            voices[speaker] = choices.pop()
    return voices


def speaker_addresses(proposal, speakers, voices):
    context = proposal.source_screenplay.source_outline.source.context
    clauses = [clause for text in [context.idea, *context.constraints, *[a.answer for a in context.clarifications]]
               for clause in re.split(r'[,;.!?]', normalized(text))]
    addresses = {}
    for speaker in speakers:
        choices = set()
        mentions_call = False
        for clause in clauses:
            own = re.search(rf'\b{re.escape(normalized(speaker))}\s+xưng\s+\w+\b', clause)
            if own:
                suffix = clause[own.end():]
                call = re.search(r'\bgọi(?:\s+.+?\s+là)?\s+(\w+)\b', suffix)
                mentions_call |= call is not None
                if call and not NEGATION.search(clause[:own.start()]+suffix[:call.start()]) and not contains(suffix[:call.start()], 'đừng'):
                    choices.add(call.group(1))
        if len(choices) == 1:
            addresses[speaker] = choices.pop()
        elif not mentions_call and len(speakers) == 2:
            peer = next(s for s in speakers if s != speaker)
            pair = {voices.get(speaker), voices.get(peer)}
            if pair in ({'mẹ','con'},{'cha','con'},{'bố','con'},{'chị','em'}):
                addresses[speaker] = voices[peer]
            elif normalized(peer) in {'mẹ','cha','bố','con gái','con trai','chị','em'}:
                addresses[speaker] = 'con' if normalized(peer).startswith('con ') else normalized(peer)
    return addresses


def reaction_options(proposal, pair, language):
    voices = speaker_voices(proposal, pair)
    addresses = speaker_addresses(proposal, pair, voices)
    if language == 'Vietnamese':
        pronouns = {'mẹ','cha','bố','con','chị','em','tôi','tao','tớ','mình','cháu','cô','chú','bác','ông','bà','anh','cậu','bạn','mày'}
        if (set(voices) != set(pair) or set(addresses) != set(pair)
                or any(v not in pronouns for v in [*voices.values(), *addresses.values()])):
            return {}
    index = next(i for i,s in enumerate(proposal.source_screenplay.scenes) if s.id == proposal.target_scene_id)
    previous = [b for s in proposal.source_screenplay.scenes[:index] for b in s.blocks if b.kind == 'dialogue']
    result = {}
    for i, speaker in enumerate(pair):
        own, other = voices.get(speaker,''), addresses.get(speaker,'')
        options = {key: text.format(self=own, Self=own.capitalize(), other=other, Other=other.capitalize())
                   for key,text in REACTIONS[language][i].items()}
        result[speaker] = {key:text for key,text in options.items()
                           if not any(normalized(b.speaker) == normalized(speaker) and b.text == text for b in previous)}
        if not result[speaker]:
            raise SceneSourceConflict('Đã dùng hết phản hồi ngắn; hãy viết hoặc review thoại riêng cho cảnh này.')
    return result


def can_compose(proposal, language=None):
    if proposal.scope != 'scene':
        return False
    script = proposal.source_screenplay
    target = next(s for s in script.scenes if s.id == proposal.target_scene_id)
    source = next(s for s in script.source_outline.scenes if s.id == target.source_scene_id)
    if source.staging_choices or source.keep_or_avoid.strip() or source.viewer_intent.strip():
        return False
    if re.search(
            r'(?i)\b(thêm|bớt|đổi|thay|sửa|xoá|xóa|chuyển|add|remove|replace|rewrite|change)\b', proposal.instructions):
        return False
    instruction = normalized(proposal.instructions).replace('kết mở','')
    for clause in re.split(r'[,.!?;]', instruction):
        events = list(VERB.finditer(clause)) + list(VISIBLE.finditer(clause)) + list(re.finditer(r'\b(rời|chạm|ôm|leave|touch|hug)\b', clause))
        if any(not NEGATION.search(clause[:event.start()]) and not contains(clause[:event.start()], 'đừng') for event in events):
            return False  # Action/performance changes need the expressive writer, not fixed beats.
    texts = [script.source_outline.source.context.idea, *script.source_outline.source.context.constraints,
             *[a.answer for a in script.source_outline.source.context.clarifications], proposal.instructions]
    if any(QUOTED.search(text) for text in texts):
        return False
    if not all(b.kind == 'action' and b.text.strip() in source.action
               and not script.provenance.get(f'block:{b.id}:text', TextProvenance()).is_author_choice
               for b in target.blocks):
        return False
    beats, reconciled = fixed_beats(proposal)
    action = ' '.join(beats)
    if not action or not (VERB.search(normalized(action)) or VISIBLE.search(normalized(action))) or QUOTED.search(action):
        return False
    pair = per_scene_dialogue(proposal, reconciled)
    if pair and proposal.instructions.strip():
        return False  # A scene-specific refinement needs the full writer's scope handling.
    if pair:
        lang = language or resolve_response_language(script.source_outline.source.context.idea, script.source_outline.source.response_language)
        if not reaction_options(proposal, pair, lang):
            return False
    if not pair and any(re.search(
            r'\bmỗi cảnh\b.{0,100}\b(câu|thoại)\b|\beach scene\b.{0,100}\b(dialogue|lines)\b|\b(nói|đáp)\s+(một|hai|ba|\d+)\s+câu\b',
            normalized(text)) for text in texts[:-1]):
        return False  # Unknown counts/order must not silently become zero dialogue.
    if not pair and any(re.search(r'\bxưng\s+(?!hô\b)\w+|\b(dùng|gọi|use|address)\b.{0,40}\b(tôi|bạn)\b|\bgọi\b.{1,40}\blà\b', clause)
           and not NEGATION.search(clause) and not contains(clause, 'đừng')
           for text in texts for clause in re.split(r'[,.!?;]|\b(nhưng|mà|but)\b', normalized(text)) if clause):
        return False
    if TURN_REQUEST.search(normalized(proposal.instructions)) and not re.search(
            r'\b(chưa quyết định|chưa biết|kết mở|undecided|open ending|unsure)\b', normalized(' '.join(texts))):
        return False
    requested_roles = TURN_REQUEST.findall(normalized(proposal.instructions))
    if requested_roles and not all(any(contains(t, role) for t in texts[:-1]) for role in requested_roles):
        return False
    return True


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]


def actor_events(text, characters):
    """Only explicit actors, literal positive verb/object pairs; never resolve pronouns."""
    for sentence in re.split(r'[.!?;]', normalized(text)):
        previous = set()
        for clause in sentence.split(','):
            matches = list(VERB.finditer(clause))
            if not matches:
                previous = character_mentions(clause, characters)
                continue
            for match in matches:
                prefix = clause[:match.start()].strip()
                actors = character_mentions(prefix, characters)
                if not prefix:
                    actors = previous
                if (len(actors) != 1 or NEGATION.search(prefix)
                        or re.search(r'\b(?:muốn|nếu|có thể|chuẩn bị|định|want|wants|if|might|could|preparing|planning)\b', prefix)):
                    previous = set()
                    continue
                predicate = BOUNDARY.split(clause[match.start():], maxsplit=1)[0].strip()
                if len(predicate.split()) >= 3:
                    yield predicate, next(iter(actors))
                previous = actors


def author_sequence(author, count):
    parts = [s for s in sentences(author.idea) if not PRODUCTION_ONLY.fullmatch(s)]
    if len(parts) < count or not all(VERB.search(normalized(s)) or VISIBLE.search(normalized(s)) for s in parts):
        return None
    return [parts[i*len(parts)//count:(i+1)*len(parts)//count] for i in range(count)]


def fixed_beats(proposal):
    script = proposal.source_screenplay
    outline = script.source_outline
    author = outline.source.context
    texts = [author.idea, *author.constraints, *[a.answer for a in author.clarifications]]
    conflict = False
    for scene in outline.scenes:
        origin = outline.provenance.get(f'm2:{scene.id}:action', TextProvenance())
        if origin.origin != 'ai_proposal' or origin.is_author_choice:
            continue
        characters = ', '.join(name.strip() for name in re.split(r'[,;/\n]', scene.characters)
                               if name.strip() and any(contains(t, normalized(name.strip())) for t in texts))
        if not characters:
            continue
        facts = {}
        for text in texts:
            for predicate, actor in actor_events(text, characters):
                facts.setdefault(predicate, set()).add(actor)
        if any(predicate in facts and len(facts[predicate]) == 1 and actor not in facts[predicate]
               for predicate, actor in actor_events(scene.action, characters)):
            conflict = True
    target = next(s for s in script.scenes if s.id == proposal.target_scene_id)
    source = next(s for s in outline.scenes if s.id == target.source_scene_id)
    count = len(script.scenes)
    index = next(i for i, s in enumerate(script.scenes) if s.id == target.id)
    sequence = author_sequence(author, count)
    # A complete, concrete author brief must survive an AI outline that omits beats.
    # Never repartition human/legacy choices or an already-written screenplay.
    fresh_ai = not (outline.version != 1 or script.version != 1
            or any(p.is_author_choice for p in script.provenance.values())
            or any(p.is_author_choice for p in outline.source.draft_provenance.values())
            or any(p.is_author_choice for p in outline.provenance.values())
            or any(s.blocks and (i >= index
                       or sequence is None or [b.text for b in s.blocks if b.kind == 'action'] != sequence[i])
                   for i, s in enumerate(script.scenes))
            or any((p := outline.provenance.get(f'm2:{s.id}:action', TextProvenance())).origin != 'ai_proposal'
                   or p.is_author_choice for s in outline.scenes))
    if not conflict and not (sequence and fresh_ai):
        return sentences(source.action), False
    if not fresh_ai:
        raise SceneSourceConflict('Dàn cảnh AI mâu thuẫn người thực hiện; hãy review nguồn trước khi viết cảnh.')
    if not sequence:
        raise SceneSourceConflict('Chưa đủ nhịp tác giả để sửa dàn cảnh AI an toàn; hãy review nguồn trước khi viết cảnh.')
    return sequence[index], True


def composition_request(proposal, language):
    script = proposal.source_screenplay
    outline = script.source_outline
    context = outline.source
    index = next(i for i, s in enumerate(script.scenes) if s.id == proposal.target_scene_id)
    source = next(s for s in outline.scenes if s.id == script.scenes[index].source_scene_id)
    beats, reconciled = fixed_beats(proposal)
    if not beats or len(beats) > 100:
        raise SceneSourceConflict('Cảnh cần có 1–100 nhịp nguồn không rỗng trước khi viết.')
    author_text = '\n'.join([context.context.idea, *context.context.constraints,
                             *[a.answer for a in context.context.clarifications]])
    roles = TURN_REQUEST.findall(normalized(proposal.instructions))
    roles = roles if len(set(roles)) == len(roles) and all(contains(author_text, r) for r in roles) else []
    turn_type = list[DialogueTurn]
    turn_field = Field(max_length=0)
    pair = per_scene_dialogue(proposal, reconciled)
    voices = speaker_voices(proposal, pair)
    addresses = speaker_addresses(proposal, pair, voices)
    reactions = reaction_options(proposal, pair, language) if pair else {}
    if pair:
        if not reactions:
            raise SceneSourceConflict('Chưa đủ thông tin xưng hô để dựng hai lượt thoại; hãy review nguồn.')
        lines = {}
        for i, speaker in enumerate(pair):
            line = create_model(f'ReactionLine{i+1}', __base__=BoundDialogueTurn,
                                speaker=(Literal[speaker], ...), after_action=(Literal[len(beats)], ...),
                                self_reference=(Literal[voices.get(speaker,'I')], ...),
                                intent=(Literal[tuple(reactions[speaker])], ...))
            lines[f'line_{i+1}'] = (line, ...)
        turn_type = create_model('RequestedConversation', __config__=ConfigDict(extra='forbid'), **lines)
        turn_field = Field()
    elif roles:
        lines = {}
        for i, role in enumerate(roles):
            speaker = ({'cha':'Father','bố':'Father','con gái':'Daughter','con trai':'Son','chị':'Older sister','em':'Younger sibling'}[role]
                       if language == 'English' else role.capitalize())
            pronoun = 'I' if language == 'English' else 'Con' if role.startswith('con ') else speaker
            line = create_model(f'RequestedLine{i+1}', __base__=BoundDialogueTurn,
                                speaker=(Literal[speaker], ...), self_reference=(Literal[pronoun], ...),
                                after_action=(Literal[min(i+1, len(beats))], ...))
            lines[f'line_{i+1}'] = (line, ...)
        turn_type = create_model('RequestedDialogue', __config__=ConfigDict(extra='forbid'), **lines)
        turn_field = Field()
    elif (re.search(r'(?i)\b(thoại|dialogue|conversation|tranh luận|trò chuyện|talk|argue)\b', proposal.instructions)
          and not re.search(r'(?i)\b(có thể|may|optional)\b', proposal.instructions)
          and not re.search(r'(?i)\b(không|no|without)\b.{0,25}\b(thoại|dialogue|speech)\b', proposal.instructions)):
        turn_field = Field(max_length=100)
    heading = (f'SCENE {index+1}' if language == 'English' else f'CẢNH {index+1}' if reconciled
               else script.scenes[index].heading.strip() or source.title.strip() or f'CẢNH {index+1}')
    heading_type = Literal[heading]
    translate_actions = language == 'English' and detect_response_language(' '.join(beats)) != 'English'
    translation_count = len(beats) if translate_actions else 0
    result_model = create_model('QwenSceneComposition', __base__=SceneComposition,
        heading=(heading_type, ...), translations=(list[Annotated[str, Field(min_length=1, max_length=10000)]],
            Field(min_length=translation_count, max_length=translation_count)),
        dialogue=(turn_type, turn_field))
    plan = draft_fields(context.draft)
    authored_plan = {k:v for k,v in plan.items()
                     if context.draft_provenance.get(k, TextProvenance()).is_author_choice}
    legacy_plan = {k:v for k,v in plan.items()
                   if context.draft_provenance.get(k, TextProvenance()).origin == 'legacy_unknown'}
    source_choices = {k:v for k,v in scene_fields(outline.scenes).items()
                      if outline.provenance.get(k, TextProvenance()).is_author_choice}
    data = {'response_language':language, 'translate_actions':translate_actions, 'scene_number':index+1, 'total_scenes':len(script.scenes),
        'heading_source': {'text':script.scenes[index].heading,
            'origin': 'author_choice' if script.provenance.get(f'script:{script.scenes[index].id}:heading', TextProvenance()).is_author_choice
                      else script.provenance.get(f'script:{script.scenes[index].id}:heading', TextProvenance()).origin},
        'fixed_action_beats':beats, 'reconciled_ai_outline':reconciled,
        'author_intent':context.context.ai_context(), 'author_plan_fields':authored_plan,
        'legacy_plan_context':legacy_plan,
        'author_scene_choices':source_choices,
        'target_scene': {'title':source.title, 'characters':source.characters,
                         'location':source.location, 'time':source.time, 'goal':source.goal} if not reconciled else {'number':index+1,'characters':pair},
        'speaker_self_references':voices, 'speaker_addresses':addresses,
        'dialogue_options':reactions,
        'future_scene_actions':([' '.join(s) for s in author_sequence(context.context, len(script.scenes))[index+1:]]
                                if reconciled else [s.action for s in outline.scenes[index+1:]]),
        'previous_scenes':[s.model_dump(exclude={'id','source_scene_id'}) for s in script.scenes[:index]],
        'already_completed_actions':[b.text for s in script.scenes[:index] for b in s.blocks if b.kind == 'action'],
        'author_request':proposal.instructions}
    instructions = PROMPT.read_text(encoding='utf-8')
    if language == 'English':
        instructions = instructions.split('Vietnamese dialogue:')[0] + 'Use English for every translation and dialogue line. Preserve actual proper names; translate unnamed role labels.'
    if translate_actions:
        instructions += '\nTranslate explicit negation as explicit negation (not, not yet, without). Never replace a negative fact with hesitation, intention or uncertainty; preserve what has and has not happened.'
    return StructuredRequest(stage='screenplay_generation', instructions=instructions,
        input_text=json.dumps(data,ensure_ascii=False), response_model=result_model), beats


def render_composition(output, beats, language, source=None):
    actions = output.translations if language == 'English' and (source is None or source['translate_actions']) else beats
    turns = list(output.dialogue.model_dump().values()) if isinstance(output.dialogue, BaseModel) else [t.model_dump() for t in output.dialogue]
    for turn in turns:
        if 'intent' in turn:
            turn['text'] = (source['dialogue_options'][turn['speaker']][turn['intent']] if source and source.get('dialogue_options')
                            else turn['self_reference'] + ' ' + UTTERANCE_SUFFIXES[language][turn['intent']])
    if source:
        action_texts = [*beats, *actions, *source['already_completed_actions'], *source['future_scene_actions']]
        action_sentences = {normalized(s) for t in action_texts for s in sentences(t)}
        for turn in turns:
            if any(normalized(s) in action_sentences for s in sentences(turn['text'])):
                raise ValueError('A spoken line repeats source action instead of speech.')
            voice = source['speaker_self_references'].get(turn['speaker'])
            if voice in {'mẹ','cha','bố','con','chị','em'} and re.search(r'(?:^|[,;.!?]\s*)tôi\b', normalized(turn['text'])):
                raise ValueError('Spoken self-reference contradicts the author voice.')
            address = source['speaker_addresses'].get(turn['speaker'])
            vocative = re.search(r',\s*(mẹ|cha|bố|con|chị|em)\s*(?:ạ|ơi)?[.!?]*$', normalized(turn['text']))
            vocative = vocative or re.match(r'(mẹ|cha|bố|con|chị|em)\s+(?:ạ|ơi)\s*[,!?.]', normalized(turn['text']))
            if address and vocative and vocative.group(1) != address:
                raise ValueError('Spoken address contradicts the author voice.')
    if any(t['after_action'] > len(actions) for t in turns):
        raise ValueError('Dialogue position is outside the fixed action beats.')
    if [t['after_action'] for t in turns] != sorted(t['after_action'] for t in turns):
        raise ValueError('Requested dialogue order must follow the action order.')
    blocks = []
    for index in range(len(actions)+1):
        if index:
            blocks.append({'kind':'action','text':actions[index-1],'speaker':''})
        blocks.extend({'kind':'dialogue','text':t['text'],'speaker':t['speaker']}
                      for t in turns if t['after_action'] == index)
    return SceneWritingResult(scene={'heading':output.heading, 'blocks':blocks}).scene
