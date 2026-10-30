import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from app.api.schemas.projects import ScreenplayProposal, PendingQuestion
from app.api.schemas.screenplays import ScriptBlock
from app.application.screenplay_composition import can_compose, composition_request, fixed_beats, per_scene_dialogue, speaker_voices, speaker_addresses
from app.application.ai_provider import ProviderMetadata, StructuredResult, MalformedProviderResponseError
from app.application.screenplay_writing import write_scene
from scripts.check_multiscene_writing import prepare, contracts

CASES = json.loads((Path(__file__).resolve().parents[2]/'docs/evaluations/qa01-new-briefs-qwen7b-2026-10-30/cases.json').read_text())


def proposal(case, index=0):
    script=prepare(case)
    return ScreenplayProposal(id=str(uuid4()),created_at='QA',source_revision=1,source_content='synthetic QA',
        source_screenplay=script,source_outline=script.source_outline.model_copy(deep=True),
        target_scene_id=script.scenes[index].id,prompt_version='QA')


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_author_per_scene_dialogue_uses_source_constraints_not_empty_request(case):
    p=proposal(case); before=p.model_dump(mode='json')
    assert per_scene_dialogue(p)==case['required_speakers']
    assert can_compose(p)
    request,_=composition_request(p,'English' if case['language']=='en' else 'Vietnamese')
    field=request.response_model.model_fields['dialogue'].annotation
    if case['required_speakers']:
        fields=field.model_json_schema()['properties']
        assert list(fields)==['line_1','line_2']
        for name,speaker in zip(fields,case['required_speakers']):
            model=field.model_fields[name].annotation
            schema=model.model_json_schema()['properties']
            assert schema['speaker']['const']==speaker and 'text' in schema and 'intent' not in schema
    assert p.model_dump(mode='json')==before


@pytest.mark.parametrize('text',[
    'Mỗi cảnh không cần hai câu thoại, mẹ nói một câu, con gái đáp một câu.',
    'Mỗi cảnh có hai câu thoại, đều do mẹ nói.',
    'Mẹ nói một câu, con gái đáp một câu.',
    'Each scene has two short dialogue lines, both from Mother.',
    'Mỗi cảnh có thể có hai câu thoại, mẹ nói một câu, con gái đáp một câu.',
    'Mỗi cảnh có hai câu thoại; không cho mẹ nói một câu, con gái đáp một câu.',
])
def test_dialogue_binding_does_not_guess_order_or_scope(text):
    case=deepcopy(CASES[0]);case['constraints']=[text]
    assert per_scene_dialogue(proposal(case))==[]


def test_conflicting_order_is_not_silently_chosen():
    case=deepcopy(CASES[0])
    case['constraints'].append('Mỗi cảnh có hai câu thoại: con gái nói một câu, mẹ đáp một câu.')
    assert per_scene_dialogue(proposal(case))==[]
    assert not can_compose(proposal(case))


@pytest.mark.parametrize('text',[
    'Mỗi cảnh có ba câu thoại, mẹ nói trước rồi con gái trả lời.',
    'Mẹ nói một câu, con gái đáp một câu.',
])
def test_unsupported_dialogue_request_is_not_silently_replaced_with_silence(text):
    case=deepcopy(CASES[0]);case['constraints']=[text]
    assert not can_compose(proposal(case))


def test_model_plan_and_pending_questions_are_not_author_dialogue_requests():
    p=proposal(CASES[0]); source=p.source_screenplay.source_outline.source
    request=source.context.constraints[1];source.context.constraints=[]
    source.draft.sections[0].content=request
    source.context.pending_questions=[PendingQuestion(question=request,input_index=0)]
    assert per_scene_dialogue(p)==[]


def test_completed_dialogue_does_not_block_next_reconciled_author_beat():
    case=deepcopy(CASES[0]);case['origin']='ai_proposal'
    p=proposal(case);first=p.source_screenplay.scenes[0]
    first.blocks=[ScriptBlock(id=str(uuid4()),kind='action',text=case['scenes'][0]['action']),
                  ScriptBlock(id=str(uuid4()),kind='dialogue',text='Con cần thêm thời gian.',speaker='Con gái')]
    p.target_scene_id=p.source_screenplay.scenes[1].id
    beats,reconciled=fixed_beats(p)
    assert reconciled and beats==[case['scenes'][1]['action']]
    request,_=composition_request(p,'Vietnamese');data=json.loads(request.input_text)
    assert data['previous_scenes'][0]['blocks'][1]['text']=='Con cần thêm thời gian.'
    assert data['fixed_action_beats']==beats
    assert data['target_scene']['characters']=='Mẹ, Con gái'
    first.blocks[0].text='Mẹ cất vé vào ngăn kéo.'
    assert not fixed_beats(p)[1]


def test_scene_refinement_uses_full_writer_instead_of_ignoring_new_request():
    p=proposal(CASES[0]);p.instructions='Chỉ viết một câu của mẹ ở cảnh này.'
    assert not can_compose(p)


def test_only_positive_unambiguous_author_voice_is_used():
    p=proposal(CASES[0]);ctx=p.source_screenplay.source_outline.source.context
    ctx.constraints=['Không cho mẹ xưng tôi. Mẹ xưng mẹ. Con gái xưng con.']
    assert speaker_voices(p,['Mẹ','Con gái'])=={'Mẹ':'mẹ','Con gái':'con'}
    ctx.constraints.append('Mẹ xưng tôi.')
    assert speaker_voices(p,['Mẹ','Con gái'])=={'Con gái':'con'}


class SpeechProvider:
    metadata=ProviderMetadata('ollama','qwen2.5:7b',{'num_ctx':16384})
    def __init__(self,text):self.text=text;self.calls=0
    def request_structured(self,request):
        self.calls+=1; data=json.loads(request.input_text)
        output={'heading':request.response_model.model_json_schema()['properties']['heading']['const'],'translations':[],
                'dialogue':{'line_1':dict(speaker='Mẹ',after_action=len(data['fixed_action_beats']),text=self.text),
                            'line_2':dict(speaker='Con gái',after_action=len(data['fixed_action_beats']),text='Con cần thêm thời gian, mẹ.')}}
        return StructuredResult(output=request.response_model.model_validate(output),model='qwen2.5:7b',raw_output=json.dumps(output,ensure_ascii=False))


@pytest.mark.parametrize('text',['Tôi chưa sẵn sàng.','Con, tôi có thể chờ.','Con chưa biết, mẹ ạ.','Mẹ ơi, con chưa biết.',
    'Mẹ đặt vé tàu lên bàn bếp.','Con gái nhận vé rồi cất vào túi áo.',
    'Mẹ đặt vé tàu lên bàn bếp. Con thấy thế nào?'])
def test_invalid_speech_keeps_raw_frame_and_source_and_does_not_retry(text):
    p=proposal(CASES[0]);before=p.model_dump(mode='json');provider=SpeechProvider(text)
    with pytest.raises(MalformedProviderResponseError) as failure:write_scene(p,provider)
    assert text in failure.value.raw_output and provider.calls==1
    assert p.model_dump(mode='json')==before


def test_author_custom_self_reference_is_not_replaced_by_family_default():
    p=proposal(CASES[0]);ctx=p.source_screenplay.source_outline.source.context
    ctx.constraints[1]='Mỗi cảnh có hai câu thoại: mẹ nói một câu, con gái đáp một câu. Mẹ xưng tôi, con gái xưng con.'
    result=write_scene(p,SpeechProvider('Tôi chưa sẵn sàng.'))
    assert result.scene.blocks[1].text=='Tôi chưa sẵn sàng.'


def test_explicit_address_overrides_family_defaults():
    p=proposal(CASES[1]);voices=speaker_voices(p,['Hạnh','Nam'])
    assert voices=={'Hạnh':'chị','Nam':'em'}
    assert speaker_addresses(p,['Hạnh','Nam'],voices)=={'Hạnh':'em','Nam':'chị'}


def test_negative_or_conflicting_address_is_not_promoted_to_a_binding():
    p=proposal(CASES[0]);ctx=p.source_screenplay.source_outline.source.context
    ctx.constraints=['Mẹ xưng mẹ đừng gọi con là mẹ. Con gái xưng con.']
    voices=speaker_voices(p,['Mẹ','Con gái'])
    assert 'Mẹ' not in speaker_addresses(p,['Mẹ','Con gái'],voices)
    ctx.constraints=['Mẹ xưng mẹ gọi con. Mẹ xưng mẹ gọi bạn. Con gái xưng con.']
    assert 'Mẹ' not in speaker_addresses(p,['Mẹ','Con gái'],speaker_voices(p,['Mẹ','Con gái']))


@pytest.mark.parametrize('index',range(3))
def test_already_english_actions_are_not_translated_again(index):
    p=proposal(CASES[2],index);request,beats=composition_request(p,'English')
    data=json.loads(request.input_text)
    assert not data['translate_actions']
    assert request.response_model.model_json_schema()['properties']['translations']['maxItems']==0
    from app.application.screenplay_composition import render_composition
    output=request.response_model.model_validate({'heading':f'SCENE {index+1}','translations':[],
        'dialogue':{'line_1':{'speaker':'Mara','after_action':1,'text':'We can wait.'},
                    'line_2':{'speaker':'Owen','after_action':1,'text':'No need to rush.'}}})
    scene=render_composition(output,beats,'English',data)
    assert scene.blocks[0].text==CASES[2]['scenes'][index]['action']


def test_vietnamese_actions_still_require_translation_for_english_output():
    p=proposal(CASES[0]);request,beats=composition_request(p,'English')
    assert json.loads(request.input_text)['translate_actions']
    assert request.response_model.model_json_schema()['properties']['translations']['minItems']==len(beats)


def test_runner_marks_missing_or_reordered_dialogue_as_failed_contract():
    p=proposal(CASES[0]);scene=p.source_screenplay.scenes[0]
    assert not contracts(CASES[0],scene)['requested_dialogue_count']
    scene.blocks=[ScriptBlock(id=str(uuid4()),kind='dialogue',text='Con chưa biết.',speaker='Con gái'),
                  ScriptBlock(id=str(uuid4()),kind='dialogue',text='Mẹ đợi.',speaker='Mẹ')]
    checks=contracts(CASES[0],scene)
    assert checks['requested_dialogue_count'] and not checks['requested_speaker_order']
