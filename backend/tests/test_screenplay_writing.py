import json
from copy import deepcopy
from uuid import uuid4
import pytest
from pydantic import BaseModel
from test_projects import project_client,payload  # noqa: F401
from test_screenplays import prepare,start,edit,block
from app.api.routes import screenplays as routes
from app.api.schemas.screenplays import SceneWritingResult
from app.application.ai_provider import ProviderMetadata,StructuredResult,ProviderTimeoutError,MissingProviderConfigurationError

class WritingProvider:
    metadata=ProviderMetadata('fake','writer',{'temperature':0.3})
    def __init__(self):
        self.requests=[];self.error=None;self.hook=lambda:None
        self.output=SceneWritingResult(scene={'heading':'NỘI. NHÀ — CHIỀU','blocks':[
            {'kind':'action','text':'Cha đặt phong thư kín lên bàn rồi lùi lại.','speaker':''},
            {'kind':'dialogue','text':'Không sao đâu cha ạ…','speaker':'Con gái'}]})
    def request_structured(self,request):
        self.requests.append(request);self.hook()
        if self.error:raise self.error
        return StructuredResult(output=self.output,model='writer')

@pytest.fixture
def writing(project_client,monkeypatch):
    client,text=project_client;p=start(client,prepare(client)).json();provider=WritingProvider()
    monkeypatch.setattr(routes,'get_screenplay_provider',lambda:provider)
    return client,provider,p,text

def generate(client,p,rid=None):
    body={'revision':p['revision'],'request_id':rid or str(uuid4()),'target_scene_id':p['screenplay']['scenes'][0]['id'],'instructions':'Giữ kết mở.'}
    return client.post(f"/api/projects/{p['id']}/screenplay-proposals",json=body),body

def adopt(p,proposal):
    body=edit(p);replacement=proposal['preview_scene'] or proposal['scene']
    body['screenplay']['scenes']=[replacement if s['id']==proposal['target_scene_id'] else s for s in body['screenplay']['scenes']]
    body['screenplay_proposal_id']=proposal['id'];return body

def test_preview_edit_adopt_reload_legacy_and_scope(writing):
    client,provider,p,text=writing;url=f"/api/projects/{p['id']}";calls=len(text.requests)
    result,request=generate(client,p);assert result.status_code==200,result.text
    ready=result.json();proposal=ready['screenplay_proposals'][-1]
    assert ready['screenplay']==p['screenplay'] and proposal['source_screenplay']==p['screenplay']
    data=json.loads(provider.requests[0].input_text)
    assert data['author_intent']['idea']==p['screenplay']['source_outline']['source']['context']['idea']
    assert data['target_scene_id']==request['target_scene_id'] and len(data['screenplay_context'])==2
    assert data['source_scene']==p['screenplay']['source_outline']['scenes'][0]
    assert client.post(url+'/screenplay-proposals',json=request).json()==ready and len(provider.requests)==1
    revised=deepcopy(proposal['scene']);revised['blocks'][1]['text']='  Cha…\n\nCon hiểu.  '
    preview=client.put(url,json={**payload(ready),'screenplay_proposal_previews':{proposal['id']:revised}}).json()
    assert preview['screenplay']==p['screenplay'] and preview['screenplay_proposals'][-1]['scene']==proposal['scene']
    saved=client.put(url,json=adopt(preview,preview['screenplay_proposals'][-1])).json()
    assert saved['screenplay']['scenes'][0]==revised and saved['screenplay']['scenes'][1]==p['screenplay']['scenes'][1]
    assert saved['screenplay_versions'][-1]['screenplay']==p['screenplay'] and saved['screenplay_proposals'][-1]['status']=='applied'
    for key in ('draft','feedback_source','scene_outline','scene_sketches','selected_scene_sketches'):assert saved[key]==p[key]
    legacy=client.put(url,json=payload(saved)).json()
    assert legacy['screenplay']==saved['screenplay'] and legacy['screenplay_proposals']==saved['screenplay_proposals']
    assert client.get(url).json()==legacy and len(text.requests)==calls
    assert client.put(url,json=adopt(legacy,proposal)).status_code==409

def test_neighbor_edit_while_waiting_preserved_and_stales(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    def change():
        current=client.get(url).json();body=edit(current);body['screenplay']['scenes'][1]['blocks']=[block(text='Cảnh lân cận vừa thay.')]
        assert client.put(url,json=body).status_code==200
    provider.hook=change;late=generate(client,p)[0].json();proposal=late['screenplay_proposals'][-1]
    assert late['screenplay']['scenes'][1]['blocks'][0]['text']=='Cảnh lân cận vừa thay.' and not late['applicable_screenplay_proposal_ids']
    assert client.put(url,json=adopt(late,proposal)).status_code==409
    assert client.get(url).json()['screenplay']==late['screenplay']

def test_pending_discard_late_result_replay_wrong_request(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}";rid=str(uuid4())
    def drop():
        current=client.get(url).json();assert generate(client,current)[0].status_code==409
        assert client.post(f'{url}/screenplay-proposals/{rid}/discard',json={'revision':current['revision']}).status_code==200
    provider.hook=drop;result,body=generate(client,p,rid);assert result.status_code==200,result.text
    saved=result.json();proposal=saved['screenplay_proposals'][-1]
    assert proposal['status']=='discarded' and proposal['scene'] and saved['screenplay']==p['screenplay']
    assert client.put(url,json=adopt(saved,proposal)).status_code==409
    assert client.post(url+'/screenplay-proposals',json=body).status_code==200 and len(provider.requests)==1
    body['instructions']='Khác';assert client.post(url+'/screenplay-proposals',json=body).status_code==409

@pytest.mark.parametrize('error,status',[(ProviderTimeoutError('timeout'),504),(MissingProviderConfigurationError('missing'),503)])
def test_failure_keeps_author_and_manual_save(writing,error,status):
    client,provider,p,_=writing;provider.error=error;url=f"/api/projects/{p['id']}"
    assert generate(client,p)[0].status_code==status
    failed=client.get(url).json();assert failed['screenplay']==p['screenplay'] and failed['screenplay_proposals'][-1]['status']=='failed'
    body=edit(failed);body['screenplay']['scenes'][0]['blocks']=[block()];assert client.put(url,json=body).status_code==200

@pytest.mark.parametrize('data',[{'scenes':[]},{'scene':{'heading':'Cảnh','blocks':[]}},
    {'scene':{'heading':'Cảnh','blocks':[{'kind':'dialogue','text':'Nói','speaker':''}]}},
    {'scene':{'heading':'Cảnh','blocks':[{'kind':'action','text':'Làm','speaker':'','id':str(uuid4())}]}}])
def test_bad_result_durable_never_applied(writing,data):
    class Raw(BaseModel):
        def model_dump(self,*args,**kwargs):return data
    client,provider,p,_=writing;provider.output=Raw();result,_=generate(client,p);assert result.status_code==502,result.text
    saved=client.get(f"/api/projects/{p['id']}").json()
    assert saved['screenplay_proposals'][-1]['status']=='failed' and saved['screenplay']==p['screenplay']

def test_scope_forgery_conflict_metadata_and_no_new_m1_leak(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    p=client.put(url,json={**payload(p),'constraints':[*p['constraints'],'M1_NEW_CONTEXT_NOT_FOR_WRITER']}).json()
    ready=generate(client,p)[0].json();proposal=ready['screenplay_proposals'][-1]
    assert 'M1_NEW_CONTEXT_NOT_FOR_WRITER' not in provider.requests[0].input_text
    wrong=adopt(ready,proposal);wrong['screenplay']['scenes'][1]['blocks']=[block()];assert client.put(url,json=wrong).status_code==409
    forged=deepcopy(proposal['scene']);forged['source_scene_id']=str(uuid4())
    assert client.put(url,json={**payload(ready),'screenplay_proposal_previews':{proposal['id']:forged}}).status_code==422
    assert client.post(f'{url}/screenplay-proposals/{proposal["id"]}/discard',json={'revision':p['revision']}).status_code==409
    changed=client.put(url,json={**payload(ready),'title':'Metadata only'}).json();assert proposal['id'] in changed['applicable_screenplay_proposal_ids']
    scenes=deepcopy(changed['scene_outline']['scenes']);scenes[0]['action']='M2 đổi.'
    changed=client.put(url,json={**payload(changed),'scene_outline':{'id':changed['scene_outline']['id'],'version':changed['scene_outline']['version'],'scenes':scenes}}).json()
    assert proposal['id'] not in changed['applicable_screenplay_proposal_ids']


def test_large_context_rejected_before_call_without_losing_work(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    body=edit(p);body['screenplay']['scenes'][1]['blocks']=[block(text='Nội dung dài. '*700)]
    p=client.put(url,json=body).json()
    result,_=generate(client,p);assert result.status_code==422 and 'chưa gửi AI' in result.text
    saved=client.get(url).json();assert saved['screenplay']==p['screenplay'] and provider.requests==[]
    assert saved['screenplay_proposals'][-1]['error']=='ScreenplayContextTooLarge'


def test_writer_preserves_frozen_trial_sources_with_position_and_provenance():
    from pathlib import Path
    from app.api.schemas.projects import ScreenplayProposal
    from app.application.screenplay_writing import write_scene
    root=Path(__file__).resolve().parents[2]/'docs/evaluations/m3-scene-writing-qwen7b-2026-10-27'
    for name in ('quiet-open-ending','gentle-comedy','limited-resources'):
        after=json.loads((root/name/'project-after.json').read_text())
        proposal=ScreenplayProposal.model_validate(after['screenplay_proposals'][-1]);provider=WritingProvider()
        write_scene(proposal,provider)
        frozen=json.loads((root/name/'request.json').read_text());actual=provider.requests[0]
        assert actual.instructions != frozen['instructions']
        assert 'The scene wrapper is required' in actual.instructions
        data = json.loads(actual.input_text)
        assert list(data)[-1] == 'author_intent'
        script = proposal.source_screenplay
        assert data.pop('scene_position') == {'number':next(i+1 for i,s in enumerate(script.scenes) if s.id == proposal.target_scene_id), 'total':len(script.scenes)}
        origins = data.pop('source_scene_field_origins')
        assert origins and set(origins.values()) <= {'author_choice','ai_proposal','legacy_unknown'}
        assert data == frozen['input']
        schema = actual.response_model.model_json_schema()
        assert schema['$defs']['WrittenAction']['properties']['speaker']['const'] == ''
        assert 'speaker' in schema['$defs']['WrittenDialogue']['required']


@pytest.mark.parametrize('field', ['heading', 'text', 'speaker'])
def test_new_foreign_script_is_rejected_without_altering_author_script(writing, field):
    client, provider, p, _ = writing
    value = provider.output.model_dump()
    if field == 'heading': value['scene']['heading'] = 'Bếp 漉漉的'
    else: value['scene']['blocks'][1][field] += ' 漉漉的'
    provider.output = SceneWritingResult.model_validate(value)
    result, _ = generate(client, p)
    assert result.status_code == 502
    saved = client.get(f"/api/projects/{p['id']}").json()
    assert saved['screenplay'] == p['screenplay']
    assert saved['screenplay_proposals'][-1]['status'] == 'failed'
    assert len(provider.requests) == 1


def test_script_guard_preserves_supplied_names_quotes_and_latin_languages():
    from app.application.screenplay_writing import validate_writing_language
    validate_writing_language({'text':'  Con chưa mở thư.\nCha chờ. Café — ☂  '}, '')
    validate_writing_language({'text':'Alice waits by the door.'}, '')
    validate_writing_language({'text':'Lan đọc tên 李白 và chữ 你好.'}, 'Tên 李白, chữ 你好 do tác giả cung cấp.')
    with pytest.raises(ValueError, match='writing script'):
        validate_writing_language({'text':'Lan 漉漉的'}, 'Lan đọc tên 李白.')


def test_saved_qwen_mixed_language_response_cannot_be_adopted_as_ready(writing):
    from pathlib import Path
    client, provider, p, _ = writing
    root = Path(__file__).resolve().parents[2]
    saved = root/'docs/evaluations/qa01-scene-structure-qwen7b-2026-10-30/saved-scenes/draft-workflow-qwen7b-2026-10-30/response.json'
    provider.output = SceneWritingResult.model_validate(json.loads(saved.read_text())['output'])
    response, _ = generate(client, p)
    assert response.status_code == 502
    assert client.get(f"/api/projects/{p['id']}").json()['screenplay'] == p['screenplay']


def test_writer_labels_ai_and_author_fields_without_promoting_legacy(writing):
    from app.api.schemas.projects import ScreenplayProposal
    from app.api.schemas.provenance import TextProvenance
    from app.application.screenplay_writing import write_scene, PROMPT_VERSION
    _, provider, p, _ = writing
    script = routes.projects.load_project(p['id']).screenplay.model_copy(deep=True)
    source = script.source_outline.scenes[0]
    script.source_outline.provenance[f'm2:{source.id}:action'] = TextProvenance(origin='ai_proposal')
    script.source_outline.provenance[f'm2:{source.id}:title'] = TextProvenance(origin='ai_proposal', author_confirmed=True)
    script.source_outline.provenance.pop(f'm2:{source.id}:location', None)
    source.location = 'Bếp'
    proposal = ScreenplayProposal(id=str(uuid4()), created_at='2026-10-30', source_revision=p['revision'],
        source_content='', source_screenplay=script, source_outline=script.source_outline,
        target_scene_id=script.scenes[0].id, prompt_version=PROMPT_VERSION)
    write_scene(proposal, provider)
    data = json.loads(provider.requests[-1].input_text)
    assert data['source_scene_field_origins']['action'] == 'ai_proposal'
    assert data['source_scene_field_origins']['title'] == 'author_choice'
    assert data['source_scene_field_origins']['location'] == 'legacy_unknown'
    assert 'If an AI/unknown beat contradicts the author' in provider.requests[-1].instructions
    proposal.source_screenplay.scenes.reverse()
    write_scene(proposal, provider)
    reordered = json.loads(provider.requests[-1].input_text)
    assert reordered['scene_position'] == {'number':2, 'total':2}
    assert reordered['source_scene']['id'] == source.id


@pytest.mark.parametrize('block', [
    {'kind':'action', 'text':'Đặt thư.', 'speaker':'Cha'},
    {'kind':'dialogue', 'text':'Con à.'},
    {'kind':'dialogue', 'text':'Con à.', 'speaker':'   '},
    {'kind':'action', 'text':'   ', 'speaker':''},
    {'kind':'narration', 'text':'Đặt thư.', 'speaker':''},
])
def test_writing_contract_does_not_repair_invalid_blocks(block):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SceneWritingResult.model_validate({'scene':{'heading':'NỘI. BẾP', 'blocks':[block]}})


def test_wrong_target_project_extra_fields_and_quota_never_call(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    _,body=generate(client,p);ready=client.get(url).json();count=len(provider.requests)
    assert client.post(url+'/screenplay-proposals',json={**body,'revision':ready['revision'],'request_id':str(uuid4()),'target_scene_id':str(uuid4())}).status_code==422
    assert client.post(url+'/screenplay-proposals',json={**body,'source_screenplay':{}}).status_code==422
    other=client.post('/api/projects').json()
    assert client.post(f"/api/projects/{other['id']}/screenplay-proposals/{body['request_id']}/discard",json={'revision':other['revision']}).status_code==404
    store=routes.projects.get_project_store();raw=store.get(p['id'])
    raw['screenplay_proposals']=[{**raw['screenplay_proposals'][0],'id':str(uuid4())} for _ in range(100)]
    store.save(raw,raw['revision']);full=client.get(url).json()
    assert generate(client,full)[0].status_code==422 and len(provider.requests)==count
    updated=edit(full);updated['screenplay']['scenes'][0]['blocks']=[block(text='Vẫn viết tay khi đủ quota.')]
    assert client.put(url,json=updated).status_code==200


@pytest.mark.parametrize('mutation',['duplicate','too_large'])
def test_invalid_preview_rejected_without_breaking_project(writing,mutation):
    client,_,p,_=writing;url=f"/api/projects/{p['id']}";p=generate(client,p)[0].json()
    proposal=p['screenplay_proposals'][-1];preview=deepcopy(proposal['scene'])
    if mutation=='duplicate':preview['blocks']=[preview['blocks'][0],preview['blocks'][0]]
    else:preview['blocks']=[block(text='x'*10000) for _ in range(21)]
    r=client.put(url,json={**payload(p),'screenplay_proposal_previews':{proposal['id']:preview}})
    assert r.status_code==422 and client.get(url).json()==p
