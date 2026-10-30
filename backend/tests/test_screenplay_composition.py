import gzip
import json
from copy import deepcopy
from pathlib import Path
from typing import get_args
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.api.schemas.projects import ScreenplayProposal
from app.api.schemas.provenance import TextProvenance
from app.api.schemas.screenplays import SceneWritingResult, ScriptBlock
from app.application.ai_provider import ProviderMetadata, StructuredResult, MalformedProviderResponseError
from app.application.screenplay_composition import (
    actor_events, can_compose, composition_request, fixed_beats, render_composition, SceneSourceConflict,
)
from app.application.screenplay_writing import write_scene
from test_projects import project_client, payload
from test_screenplay_writing import writing, generate, adopt
from test_draft_runs import drafting, begin, complete
from app.api.routes import screenplays

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/evaluations/qa01-scene-language-qwen7b-2026-10-30'


def saved(name='quiet-open-ending', variant=False):
    with gzip.open(EVIDENCE/('variants-v10' if variant else 'final-v10')/name/'proposal.json.gz', 'rt') as f:
        return ScreenplayProposal.model_validate(json.load(f))


class Unchecked(BaseModel):
    data: dict
    def model_dump(self, *args, **kwargs):
        return self.data


class CompositionProvider:
    metadata = ProviderMetadata('ollama','qwen2.5:7b',{'num_ctx':16384})
    def __init__(self, bad=None):
        self.requests, self.bad, self.hook = [], bad, lambda: None
    def request_structured(self, request):
        self.requests.append(request)
        self.hook()
        data = json.loads(request.input_text)
        if 'fixed_action_beats' not in data:
            return StructuredResult(output=SceneWritingResult(scene={'heading':'Bếp','blocks':[
                {'kind':'action','text':'Cha đặt thư.','speaker':''}]}), model='qwen2.5:7b')
        result = {'heading':request.response_model.model_json_schema()['properties']['heading']['const'],
                  'translations':['Father places the sealed letter on the table.']*len(data['fixed_action_beats'])
                      if data['response_language']=='English' else [], 'dialogue':[]}
        line_type = request.response_model.model_fields['dialogue'].annotation
        if isinstance(line_type, type) and issubclass(line_type, BaseModel):
            result['dialogue'] = {}
            for key, field in line_type.model_fields.items():
                model = field.annotation
                row = {k:get_args(model.model_fields[k].annotation)[0] for k in ('speaker','self_reference','after_action')}
                row['intent'] = 'will_wait' if row['self_reference']=='Cha' else 'needs_time'
                result['dialogue'][key] = row
        if self.bad == 'heading': result['heading'] = 'Wrong heading'
        if self.bad == 'position': result['dialogue']['line_1']['after_action'] = 99
        if self.bad == 'speaker': result['dialogue']['line_1']['speaker'] = 'Con gái'
        if self.bad == 'intent': result['dialogue']['line_1']['intent'] = 'forgive'
        if self.bad == 'script': result['translations'][0] = 'Letter 漉漉的'
        if self.bad == 'extra': result['actions'] = ['Invented action']
        output = Unchecked(data=result) if self.bad else request.response_model.model_validate(result)
        return StructuredResult(output=output, model='qwen2.5:7b',raw_output=json.dumps(result,ensure_ascii=False))


@pytest.mark.parametrize('text,expected', [
    ('Con gái đặt chìa khóa lên bàn.', {('đặt chìa khóa','con gái')}),
    ('Cha đứng bên cạnh, đặt chìa khóa lên bàn.', {('đặt chìa khóa','cha')}),
    ('Cha không đặt chìa khóa lên bàn.', set()),
    ('Cha muốn đặt chìa khóa lên bàn.', set()),
    ('Cha và con gái đặt chìa khóa lên bàn.', set()),
    ('Cha đứng bên bàn. Cô đặt chìa khóa lên bàn.', set()),
    ('Cha đứng bên bàn, con gái không đặt chìa khóa, đặt chìa khóa lên bàn.', set()),
    ('Cha chuẩn bị đặt chìa khóa lên bàn.', set()),
])
def test_actor_check_is_literal_positive_and_does_not_guess_aliases(text, expected):
    assert set(actor_events(text,'Cha, Con gái')) == expected


def test_saved_ai_actor_conflict_is_reconciled_without_mutating_any_snapshot():
    p = saved('draft-workflow-qwen7b-saved-brief-2026-10-30')
    before = p.model_dump(mode='json')
    first, changed = fixed_beats(p)
    assert changed and first == ['Chiều mưa trong căn bếp nhỏ, con gái đặt chìa khóa lên bàn trước khi đi học xa.']
    p.target_scene_id = p.source_screenplay.scenes[1].id
    second, changed = fixed_beats(p)
    assert changed and second == ['Cha đặt cạnh đó một lá thư xin lỗi rồi lùi lại.',
        'Cô chưa mở thư, nhưng ngồi xuống uống cùng cha một ngụm trà.']
    p.target_scene_id = before['target_scene_id']
    assert p.model_dump(mode='json') == before


@pytest.mark.parametrize('change', ['confirmed','outline_version','script_version','human_plan','human_script','human_location','written','mixed','short'])
def test_ambiguous_or_human_edited_sources_are_not_repartitioned(change):
    p = saved('draft-workflow-qwen7b-saved-brief-2026-10-30')
    script = p.source_screenplay; outline = script.source_outline
    if change == 'confirmed': outline.provenance[f'm2:{outline.scenes[1].id}:action'].author_confirmed = True
    if change == 'outline_version': outline.version = 2
    if change == 'script_version': script.version = 2
    if change == 'human_plan': outline.source.draft_provenance['title'] = TextProvenance(origin='author_input')
    if change == 'human_script': script.provenance['heading'] = TextProvenance(origin='author_input')
    if change == 'human_location': outline.provenance[f'm2:{outline.scenes[0].id}:location'] = TextProvenance(origin='author_input')
    if change == 'written': script.scenes[1].blocks = [ScriptBlock(id=str(uuid4()),kind='action',text='Cha đứng im.')]
    if change == 'mixed': outline.provenance[f'm2:{outline.scenes[1].id}:action'] = TextProvenance()
    if change == 'short': outline.source.context.idea = 'Con gái đặt chìa khóa lên bàn cạnh cha.'
    before = p.model_dump(mode='json')
    with pytest.raises(SceneSourceConflict): fixed_beats(p)
    assert p.model_dump(mode='json') == before


def test_complete_author_brief_survives_ai_outline_omissions_with_one_scene():
    p = saved('draft-workflow-qwen7b-saved-brief-2026-10-30')
    script = p.source_screenplay; outline = script.source_outline
    script.scenes = script.scenes[:1]; outline.scenes = outline.scenes[:1]
    outline.scenes[0].action = 'Con gái đặt chìa khóa lên bàn. Cha đứng sau lưng cô.'
    before = p.model_dump(mode='json')
    beats, changed = fixed_beats(p)
    assert changed and ' '.join(beats) == outline.source.context.idea
    assert len(beats) == 3 and 'một lá thư' in beats[1] and 'một ngụm trà' in beats[2]
    assert p.model_dump(mode='json') == before


def test_reconciled_second_scene_continues_only_after_matching_first_scene():
    p = saved('draft-workflow-qwen7b-saved-brief-2026-10-30')
    provider = CompositionProvider()
    first = write_scene(p,provider).scene
    p.source_screenplay.scenes[0] = first
    p.target_scene_id = p.source_screenplay.scenes[1].id
    second = write_scene(p,provider).scene
    assert ' '.join(b.text for s in (first,second) for b in s.blocks) == p.source_screenplay.source_outline.source.context.idea
    p.source_screenplay.scenes[0].blocks[0].text = 'Con gái đã đi khỏi nhà.'
    with pytest.raises(SceneSourceConflict): write_scene(p,provider)
    assert len(provider.requests) == 2


@pytest.mark.parametrize('change', ['staging','notes','authored_block','blocks','dialogue','new_action','direct_action','quote','single_quote','custom_address','use_address','empty','abstract'])
def test_existing_editing_capabilities_fall_back_to_the_full_writer(change):
    p = saved(); script = p.source_screenplay
    source = script.source_outline.scenes[1]
    target = next(s for s in script.scenes if s.id == p.target_scene_id)
    if change == 'staging': source.staging_choices['blocking'] = 'Giữ lối ra.'
    if change == 'notes': source.keep_or_avoid = 'Giữ khoảng cách.'
    if change == 'authored_block': script.provenance[f'block:{target.blocks[0].id}:text'] = TextProvenance(origin='author_input')
    if change == 'blocks': p.scope = 'blocks'
    if change == 'dialogue': target.blocks[0].kind = 'dialogue'; target.blocks[0].speaker = 'Cha'
    if change == 'new_action': p.instructions = 'Thêm một hành động ở cuối.'
    if change == 'direct_action': p.instructions = 'Cho cha rời phòng.'
    if change == 'quote': script.source_outline.source.context.idea += ' Giữ nguyên câu “Tôi hiểu”.'
    if change == 'single_quote': script.source_outline.source.context.idea += " Giữ câu 'Tôi hiểu'."
    if change == 'custom_address': script.source_outline.source.context.constraints.append('Cha xưng tôi với con.')
    if change == 'use_address': p.instructions = 'Dùng tôi/bạn, cha nói một câu và con gái đáp một câu.'
    if change == 'empty': source.action = ''
    if change == 'abstract': source.action = 'Đối diện với quá khứ.'
    assert not can_compose(p)


def test_foreign_authored_heading_is_retained_as_source_not_new_script_drift():
    p=saved();target=next(s for s in p.source_screenplay.scenes if s.id==p.target_scene_id)
    target.heading='李白'
    p.source_screenplay.provenance[f'script:{target.id}:heading']=TextProvenance(origin='author_input')
    provider=CompositionProvider();result=write_scene(p,provider)
    assert result.scene.heading=='李白'
    assert json.loads(provider.requests[-1].input_text)['heading_source']=={'text':'李白','origin':'author_choice'}


def test_composition_keeps_author_and_legacy_data_and_does_not_promote_ai_questions():
    p = saved()
    context = p.source_screenplay.source_outline.source
    context.draft_provenance['title'] = TextProvenance(origin='author_input')
    before = p.model_dump(mode='json')
    request, beats = composition_request(p,'Vietnamese'); data=json.loads(request.input_text)
    assert data['author_intent'] == context.context.ai_context()
    assert data['author_plan_fields']['title'] == context.draft.title
    assert data['legacy_plan_context'] and data['fixed_action_beats'] == beats
    assert p.model_dump(mode='json') == before
    p = saved('parent-dialogue',True)
    p.source_screenplay.source_outline.source.context.idea = 'Hai người ngồi cạnh bàn.'
    p.source_screenplay.source_outline.source.context.constraints = []
    from app.api.schemas.projects import AuthorAnswer
    p.source_screenplay.source_outline.source.context.clarifications = [AuthorAnswer(question='Cha hay con gái?',answer='Chưa chọn.')]
    assert not can_compose(p)


@pytest.mark.parametrize('name,variant', [('quiet-open-ending',False),('gentle-comedy',False),('limited-resources',False),
    ('draft-workflow-qwen7b-2026-10-30',False),('draft-workflow-qwen7b-saved-brief-2026-10-30',False),
    ('parent-dialogue',True),('english',True),('later-scene',True)])
def test_all_eight_saved_sources_have_one_call_and_correct_target_identity(name,variant):
    p = saved(name,variant); before = p.model_dump(mode='json'); provider=CompositionProvider()
    result = write_scene(p,provider)
    assert len(provider.requests)==1 and result.scene.id==p.target_scene_id
    target=next(s for s in p.source_screenplay.scenes if s.id==p.target_scene_id)
    assert result.scene.source_scene_id == target.source_scene_id
    assert result.parameters['composition']=='source-preserving-v1'
    assert p.model_dump(mode='json')==before
    if name=='english': assert result.scene.heading=='SCENE 2'
    else: assert [b.text for b in result.scene.blocks if b.kind=='action']==fixed_beats(p)[0]
    if name=='parent-dialogue':
        assert [(b.speaker,b.text) for b in result.scene.blocks if b.kind=='dialogue']==[
            ('Cha','Cha có thể chờ.'),('Con gái','Con cần thêm thời gian.')]


@pytest.mark.parametrize('bad', ['heading','position','speaker','intent','extra','script'])
def test_invalid_composition_is_rejected_instead_of_repaired(bad):
    p=saved('english' if bad=='script' else 'parent-dialogue',True)
    before=p.model_dump(mode='json'); provider=CompositionProvider(bad)
    with pytest.raises(MalformedProviderResponseError) as failure:write_scene(p,provider)
    assert failure.value.raw_output and len(provider.requests)==1
    assert p.model_dump(mode='json')==before


def test_free_dialogue_positions_cannot_escape_fixed_actions():
    p=saved('gentle-comedy');p.instructions='Viết lời thoại.'
    request,beats=composition_request(p,'Vietnamese')
    output=request.response_model(heading='Khoảnh khắc',translations=[],dialogue=[{
        'after_action':99,'speaker':'Hà','text':'Để chị giúp.'}])
    with pytest.raises(ValueError,match='outside'):render_composition(output,beats,'Vietnamese')


@pytest.mark.parametrize('name,variant', [('draft-workflow-qwen7b-2026-10-30',False),
    ('draft-workflow-qwen7b-saved-brief-2026-10-30',False),('parent-dialogue',True),('english',True)])
def test_content_gate_rejects_the_saved_semantic_failures(name, variant):
    from scripts.scene_writing_acceptance import assess
    scene=json.loads((EVIDENCE/('variants-v10' if variant else 'final-v10')/name/'result.json').read_text())['scene']
    assert not all(assess(name,scene).values())


@pytest.fixture
def qwen_api(writing,monkeypatch):
    client, _, p, _ = writing
    store=screenplays.projects.get_project_store();raw=store.get(p['id'])
    for outline in (raw['scene_outline'],raw['screenplay']['source_outline']):
        for s in outline['scenes']:s['staging_choices']={}
    store.save(raw,raw['revision'])
    p=client.get(f"/api/projects/{p['id']}").json()
    provider=CompositionProvider()
    monkeypatch.setattr(screenplays,'get_screenplay_provider',lambda:provider)
    return client,provider,p


def test_api_composition_preview_idempotency_apply_and_source_preservation(qwen_api):
    client,provider,p=qwen_api;url=f"/api/projects/{p['id']}"
    result,body=generate(client,p)
    assert result.status_code==200,result.text
    ready=result.json();proposal=ready['screenplay_proposals'][-1]
    assert proposal['parameters']['composition']=='source-preserving-v1'
    assert ready['screenplay']==p['screenplay'] and proposal['source_screenplay']==p['screenplay']
    assert client.post(url+'/screenplay-proposals',json=body).json()==ready
    assert len(provider.requests)==1
    accepted=client.put(url,json=adopt(ready,proposal))
    assert accepted.status_code==200,accepted.text
    changed=accepted.json()
    assert changed['screenplay']['scenes'][0]==proposal['scene']
    assert changed['screenplay']['scenes'][1]==p['screenplay']['scenes'][1]
    assert changed['screenplay']['source_outline']==p['screenplay']['source_outline']
    assert changed['screenplay_versions'][-1]['screenplay']==p['screenplay']


def test_api_composition_late_result_does_not_overwrite_neighbor_edits(qwen_api):
    from test_screenplays import edit,block
    client,provider,p=qwen_api;url=f"/api/projects/{p['id']}"
    def edit_neighbor():
        current=client.get(url).json();body=edit(current)
        body['screenplay']['scenes'][1]['blocks']=[block(text='Chữ tác giả mới trong lúc đợi.')]
        assert client.put(url,json=body).status_code==200
    provider.hook=edit_neighbor
    result,_=generate(client,p);assert result.status_code==200,result.text
    late=result.json()
    assert late['screenplay']['scenes'][1]['blocks'][0]['text']=='Chữ tác giả mới trong lúc đợi.'
    assert not late['applicable_screenplay_proposal_ids'] and len(provider.requests)==1


def test_api_ambiguous_source_conflict_returns_422_before_model(qwen_api):
    client,provider,p=qwen_api;url=f"/api/projects/{p['id']}"
    store=screenplays.projects.get_project_store();raw=store.get(p['id'])
    outline=raw['screenplay']['source_outline'];scene=outline['scenes'][0]
    outline['source']['context']['idea']='Con gái đặt chìa khóa lên bàn. Cha đứng bên cạnh.'
    scene['action']='Cha đứng bên cạnh, đặt chìa khóa lên bàn.';scene['characters']='Cha, Con gái'
    outline['provenance'][f"m2:{scene['id']}:action"]={'origin':'ai_proposal','author_confirmed':False}
    store.save(raw,raw['revision']);p=client.get(url).json()
    result,_=generate(client,p)
    assert result.status_code==422,result.text
    assert not provider.requests
    failed=client.get(url).json()
    assert failed['screenplay']==p['screenplay'] and failed['screenplay_proposals'][-1]['status']=='failed'


@pytest.mark.parametrize('count',[1,2,6])
def test_automatic_run_with_qwen_profile_keeps_count_checkpoints_and_source(drafting,count):
    client,providers=drafting;providers[1].count=count;providers[2]=CompositionProvider()
    client,providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    assert r['completed_scenes']==r['total_scenes']==count
    assert len(providers[2].requests)==count
    assert all(s['blocks'] for s in c['project']['screenplay']['scenes'])
    assert client.get(f"/api/projects/{p['id']}").json()['screenplay'] is None


def test_received_composition_can_be_revalidated_without_resending(project_client):
    from app.application.draft_run_store import DraftRunStore
    from app.application.draft_workflow import RecordedProvider
    client,_=project_client;p=client.post('/api/projects').json()
    store=DraftRunStore(screenplays.projects.get_project_store().path);rid=str(uuid4())
    store.create_run(p['id'],rid,p['revision'],{},'test')
    provider=CompositionProvider();wrapped=RecordedProvider(provider,store,p['id'],rid)
    first,_=composition_request(saved('parent-dialogue',True),'Vietnamese')
    a=wrapped.request_structured(first)
    reconstructed,_=composition_request(saved('parent-dialogue',True),'Vietnamese')
    b=wrapped.request_structured(reconstructed)
    assert a.output.model_dump()==b.output.model_dump() and len(provider.requests)==1


def test_unknown_composition_call_cannot_be_retried(drafting):
    from app.application.ai_provider import ProviderTimeoutError
    client,providers=drafting;provider=CompositionProvider();providers[2]=provider
    def timeout():raise ProviderTimeoutError('unknown local result')
    provider.hook=timeout
    client,providers,p,base,url,body=begin(drafting)
    r=client.get(url).json()
    if r['status']=='needs_input':
        c=client.get(url+'/candidate').json()
        client.post(url+'/continue',json={'candidate_revision':c['revision'],'answers':['']*len(c['project']['answers'])})
    r=client.get(url).json();c=client.get(url+'/candidate').json()
    assert r['status']=='interrupted' and not r['can_continue']
    assert client.post(url+'/continue',json={'candidate_revision':c['revision']}).status_code==409
    assert len(provider.requests)==1 and not c['project']['screenplay']['scenes'][0]['blocks']
