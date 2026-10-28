import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from test_projects import project_client, payload  # noqa: F401
from test_screenplays import prepare,start,edit,block
from test_screenplay_writing import generate as write
from app.api.routes import screenplay_reviews as routes
from app.api.schemas.screenplays import SceneReviewResult
from app.application.ai_provider import ProviderMetadata,StructuredResult,ProviderTimeoutError,MissingProviderConfigurationError


class ReviewProvider:
    metadata=ProviderMetadata('fake','reviewer',{'temperature':0.3})
    def __init__(self):
        self.requests=[];self.error=None;self.mode='valid';self.hook=lambda:None
    def request_structured(self,request):
        self.requests.append(request);self.hook()
        if self.error:raise self.error
        data=json.loads(request.input_text);sources=data['sources']
        anchor=next(s for s in sources if s['is_target'] and s['field']=='text')
        choice=next(s for s in sources if s['category']=='author_choice')
        note={'kind':'craft','observation':'Cử chỉ hiện tại để lại khoảng lặng.','impact':'Người xem có thể tự hiểu sự đón nhận.','suggestion':'Cân nhắc giữ khoảng dừng, không bắt thêm lời giải thích.',
              'evidence':[{'source_id':anchor['id'],'quote':anchor['text'][:500]}]}
        if self.mode=='ui_all_fields':
            for field in ('heading','speaker'):
                source=next(s for s in sources if s['is_target'] and s['field']==field)
                note['evidence'].append({'source_id':source['id'],'quote':source['text'][:500]})
        if self.mode=='bad_id':note['evidence'][0]['source_id']='made-up'
        if self.mode=='lowercase_id':note['evidence'][0]['source_id']=anchor['id'].lower()
        if self.mode=='padded_id':note['evidence'][0]['source_id']=' '+anchor['id']+' '
        if self.mode=='original_id':note['evidence'][0]['source_id']=self.original_id
        if self.mode=='bad_quote':note['evidence'][0]['quote']='Chữ không có trong bản nguồn'
        if self.mode=='foreign_quote':note['evidence'][0]['quote']=next(s['text'] for s in sources if s['category']=='screenplay' and not s['is_target'] and s['field']=='text')
        if self.mode=='blank_quote':note['evidence'][0]['quote']=' '
        if self.mode=='neighbor_only':
            other=next(s for s in sources if s['category']=='screenplay' and not s['is_target'] and s['field']=='text')
            note['evidence']=[{'source_id':other['id'],'quote':other['text']}]
        if self.mode=='missing_choice':note['kind']='intent_mismatch'
        if self.mode=='choice_only':note['evidence']=[{'source_id':choice['id'],'quote':choice['text'][:500]}]
        if self.mode=='speaker_only':
            speaker=next(s for s in sources if s['is_target'] and s['field']=='speaker')
            note['evidence']=[{'source_id':speaker['id'],'quote':speaker['text']}]
        if self.mode=='mismatch':note['kind']='intent_mismatch';note['evidence'].append({'source_id':choice['id'],'quote':choice['text'][:500]})
        if self.mode=='empty_observation':note['observation']=' '
        output={'notes':[] if self.mode=='empty' else [note],'question':'Bạn muốn giữ khoảng lặng nào?' if self.mode=='empty' else ''}
        self.output=SceneReviewResult.model_validate(output)
        return StructuredResult(output=self.output,model='reviewer',raw_output=json.dumps(output,ensure_ascii=False))


@pytest.fixture
def reviewing(project_client,monkeypatch):
    client,text=project_client;p=start(client,prepare(client)).json();body=edit(p)
    body['screenplay']['scenes'][0]['blocks']=[block(text='Con gái nhìn thư, chưa mở.')]
    body['screenplay']['scenes'][1]['blocks']=[block(text='Cha đứng bên cửa.')]
    p=client.put(f"/api/projects/{p['id']}",json=body).json();provider=ReviewProvider()
    monkeypatch.setattr(routes,'get_review_provider',lambda:provider)
    return client,provider,p,text


def review(client,p,rid=None):
    body={'revision':p['revision'],'request_id':rid or str(uuid4()),'target_scene_id':p['screenplay']['scenes'][0]['id'],'instructions':'Góp ý có căn cứ, không tự viết lại.'}
    return client.post(f"/api/projects/{p['id']}/screenplay-reviews",json=body),body


def test_review_manual_edit_new_review_keeps_old_snapshot(reviewing):
    client,provider,p,text=reviewing;url=f"/api/projects/{p['id']}";calls=len(text.requests)
    r,body=review(client,p);assert r.status_code==200,r.text
    ready=r.json();old=ready['screenplay_reviews'][-1]
    assert old['status']=='ready' and old['notes'][0]['assessment'] is None
    assert old['source_screenplay']==p['screenplay'] and old['id'] in ready['current_screenplay_review_ids']
    assert ready['screenplay']==p['screenplay'] and ready['screenplay_versions']==p['screenplay_versions']
    assert client.post(url+'/screenplay-reviews',json=body).json()==ready and len(provider.requests)==1
    edited=edit(ready);edited['screenplay']['scenes'][0]['blocks'][0]['text']='Con gái kéo ghế ngồi, để thư nguyên trên bàn.'
    saved=client.put(url,json=edited).json()
    assert old['id'] not in saved['current_screenplay_review_ids'] and saved['screenplay_reviews'][-1]==old
    fresh=review(client,saved)[0].json()
    assert len(provider.requests)==2 and json.loads(provider.requests[-1].input_text)['sources']!=json.loads(provider.requests[0].input_text)['sources']
    assert fresh['screenplay_reviews'][0]==old and fresh['screenplay_reviews'][-1]['id'] in fresh['current_screenplay_review_ids']
    for key in ('draft','feedback_source','scene_outline','scene_sketches','selected_scene_sketches'):assert fresh[key]==p[key]
    assert len(text.requests)==calls
    legacy=client.put(url,json=payload(fresh)).json();assert legacy['screenplay_reviews']==fresh['screenplay_reviews']
    assert client.get(url).json()==legacy


@pytest.mark.parametrize('mode',['bad_id','bad_quote','blank_quote','neighbor_only','missing_choice','empty_observation'])
def test_invalid_evidence_never_becomes_verified_feedback(reviewing,mode):
    client,provider,p,_=reviewing;provider.mode=mode
    r,_=review(client,p);assert r.status_code==502,r.text
    saved=client.get(f"/api/projects/{p['id']}").json();item=saved['screenplay_reviews'][-1]
    assert item['status']=='failed' and not item['notes'] and item['sources']
    assert saved['screenplay']==p['screenplay'] and not saved['current_screenplay_review_ids']


@pytest.mark.parametrize('mode',['empty','mismatch'])
def test_empty_feedback_and_choice_backed_mismatch_valid(reviewing,mode):
    client,provider,p,_=reviewing;provider.mode=mode;r,_=review(client,p);assert r.status_code==200,r.text
    saved=r.json();item=saved['screenplay_reviews'][-1]
    assert saved['screenplay']==p['screenplay']
    if mode=='empty':assert item['notes']==[] and item['question']
    else:assert len(item['notes'][0]['evidence'])==2


def test_assess_old_note_only_metadata_and_protects_revision_scope(reviewing):
    client,_,p,_=reviewing;url=f"/api/projects/{p['id']}";ready=review(client,p)[0].json();item=ready['screenplay_reviews'][-1];note=item['notes'][0]
    edited=edit(ready);edited['screenplay']['scenes'][1]['blocks'][0]['text']='Cảnh lân cận đổi.'
    current=client.put(url,json=edited).json();endpoint=f"{url}/screenplay-reviews/{item['id']}/notes/{note['id']}/assessment"
    assert client.post(endpoint,json={'revision':ready['revision'],'assessment':'misleading'}).status_code==409
    r=client.post(endpoint,json={'revision':current['revision'],'assessment':'misleading'});assert r.status_code==200,r.text
    assessed=r.json();assert assessed['screenplay']==current['screenplay'] and assessed['screenplay_versions']==current['screenplay_versions']
    assert assessed['screenplay_reviews'][-1]['source_screenplay']==item['source_screenplay']
    assert assessed['screenplay_reviews'][-1]['notes'][0]['assessment']=='misleading'
    assert item['id'] not in assessed['current_screenplay_review_ids']
    assert client.post(endpoint,json={'revision':assessed['revision'],'assessment':'accepted-rewrite'}).status_code==422
    assert client.put(url,json={**payload(assessed),'screenplay_reviews':[]}).status_code==422
    other=client.post('/api/projects').json()
    assert client.post(f"/api/projects/{other['id']}/screenplay-reviews/{item['id']}/notes/{note['id']}/assessment",json={'revision':other['revision'],'assessment':'helpful'}).status_code==404


def test_late_result_keeps_neighbor_edit_and_discard_is_not_reactivated(reviewing):
    client,provider,p,_=reviewing;url=f"/api/projects/{p['id']}";rid=str(uuid4())
    def while_waiting():
        current=client.get(url).json();assert review(client,current)[0].status_code==409
        assert write(client,current)[0].status_code==409
        edit_body=edit(current);edit_body['screenplay']['scenes'][1]['blocks'][0]['text']='Sửa mới trong lúc chờ.'
        current=client.put(url,json=edit_body).json()
        assert client.post(f'{url}/screenplay-reviews/{rid}/discard',json={'revision':current['revision']}).status_code==200
    provider.hook=while_waiting;r,body=review(client,p,rid);assert r.status_code==200,r.text
    late=r.json();assert late['screenplay']['scenes'][1]['blocks'][0]['text']=='Sửa mới trong lúc chờ.'
    assert late['screenplay_reviews'][-1]['status']=='discarded' and late['screenplay_reviews'][-1]['notes']
    assert not late['current_screenplay_review_ids'] and len(provider.requests)==1
    assert client.post(url+'/screenplay-reviews',json=body).status_code==200 and len(provider.requests)==1
    body['instructions']='Yêu cầu khác';assert client.post(url+'/screenplay-reviews',json=body).status_code==409


@pytest.mark.parametrize('error,status',[(ProviderTimeoutError('timeout'),504),(MissingProviderConfigurationError('missing'),503)])
def test_failure_keeps_script_and_manual_save(reviewing,error,status):
    client,provider,p,_=reviewing;provider.error=error;r,_=review(client,p);assert r.status_code==status
    url=f"/api/projects/{p['id']}";saved=client.get(url).json();assert saved['screenplay']==p['screenplay'] and saved['screenplay_reviews'][-1]['status']=='failed'
    body=edit(saved);body['screenplay']['scenes'][0]['blocks'][0]['text']='Tự sửa sau lỗi.';assert client.put(url,json=body).status_code==200


def test_source_uses_old_m2_intent_not_new_m1_or_open_questions(reviewing):
    client,provider,p,_=reviewing;url=f"/api/projects/{p['id']}";source=deepcopy(p['screenplay']['source_outline'])
    p=client.put(url,json={**payload(p),'constraints':[*p['constraints'],'NEW_M1_MUST_NOT_LEAK']}).json()
    ready=review(client,p)[0].json();data=json.loads(provider.requests[0].input_text)
    assert 'NEW_M1_MUST_NOT_LEAK' not in provider.requests[0].input_text
    assert ready['screenplay_reviews'][-1]['source_screenplay']['source_outline']==source
    assert any(s['category']=='screenplay' and s['is_target'] for s in data['sources'])
    assert any(s['category']=='screenplay' and not s['is_target'] for s in data['sources'])
    assert 'screenplay_reviews' not in routes.projects.dataset_snapshot(routes.projects.load_project(p['id']))


def test_empty_target_bad_scope_quota_and_large_context(reviewing):
    client,provider,p,_=reviewing;url=f"/api/projects/{p['id']}"
    empty=edit(p);empty['screenplay']['scenes'][0]['blocks']=[];empty=client.put(url,json=empty).json()
    assert review(client,empty)[0].status_code==422 and not provider.requests
    large=edit(empty);large['screenplay']['scenes'][0]['blocks']=[block(text='x'*10000)]
    large=client.put(url,json=large).json();r,_=review(client,large);assert r.status_code==422 and 'chưa gửi AI' in r.text and not provider.requests
    ready=client.get(url).json();store=routes.projects.get_project_store();raw=store.get(p['id']);raw['screenplay_reviews']=[{**raw['screenplay_reviews'][0],'id':str(uuid4())} for _ in range(100)];store.save(raw,raw['revision'])
    full=client.get(url).json();assert review(client,full)[0].status_code==422 and not provider.requests
    assert client.put(url,json=payload(full)).status_code==200


def test_short_ids_are_transport_only_with_explicit_block_kind_and_target(reviewing):
    client,provider,p,_=reviewing;url=f"/api/projects/{p['id']}"
    body=edit(p);body['screenplay']['scenes'][0]['blocks'].append(block('dialogue','Không sao đâu cha ạ…'))
    p=client.put(url,json=body).json();r,_=review(client,p);assert r.status_code==200,r.text
    saved=r.json();item=saved['screenplay_reviews'][-1];data=json.loads(provider.requests[-1].input_text)
    sources=data['sources'];ids=[s['id'] for s in sources]
    assert len(set(ids))==len(ids) and all(s[0] in 'SAC' and s[1:].isdigit() for s in ids)
    assert 'target_scene_id' not in data and all('scene_id' not in s and 'block_id' not in s for s in sources)
    assert all(s['id'].startswith({'screenplay':'S','author_choice':'A','context':'C'}[s['category']]) for s in sources)
    action=next(s for s in sources if s['text']=='Con gái nhìn thư, chưa mở.')
    dialogue=next(s for s in sources if s['text']=='Không sao đâu cha ạ…')
    speaker=next(s for s in sources if s['is_target'] and s['field']=='speaker')
    neighbor=next(s for s in sources if s['text']=='Cha đứng bên cửa.')
    assert action['is_target'] and action['block_kind']=='action' and action['field']=='text'
    assert dialogue['is_target'] and dialogue['block_kind']=='dialogue' and dialogue['field']=='text'
    assert speaker['block_kind']=='dialogue' and speaker['text']=='Con gái'
    assert not neighbor['is_target'] and neighbor['block_kind']=='action'
    assert all(not s['is_target'] and s['block_kind'] is None for s in sources if s['category']!='screenplay')
    original=f"block:{p['screenplay']['scenes'][0]['blocks'][0]['id']}:text"
    assert item['notes'][0]['evidence'][0]['source_id']==original
    assert provider.output.notes[0].evidence[0].source_id==action['id'],'raw provider result must not be rewritten'
    assert any(s['id']==original for s in item['sources']) and all(s['id'] not in ids for s in item['sources'])
    assert item['prompt_version']=='screenplay-review-v4-author-control'
    assert saved['screenplay']==p['screenplay'] and client.get(url).json()['screenplay_reviews']==saved['screenplay_reviews']


@pytest.mark.parametrize('mode',['lowercase_id','padded_id','original_id','foreign_quote','choice_only','speaker_only'])
def test_alias_validation_never_guesses_source_or_relocates_quote(reviewing,mode):
    client,provider,p,_=reviewing;url=f"/api/projects/{p['id']}"
    body=edit(p);body['screenplay']['scenes'][0]['blocks'].append(block('dialogue','Cha…'))
    p=client.put(url,json=body).json();provider.mode=mode
    provider.original_id=f"block:{p['screenplay']['scenes'][0]['blocks'][0]['id']}:text"
    r,_=review(client,p);assert r.status_code==502,r.text
    saved=client.get(url).json();assert saved['screenplay']==p['screenplay']
    assert saved['screenplay_reviews'][-1]['status']=='failed' and not saved['screenplay_reviews'][-1]['notes']
    assert len(provider.requests)==1


@pytest.mark.parametrize('index',range(6))
def test_frozen_six_inputs_with_fake_provider_only(project_client,monkeypatch,index):
    client,_=project_client
    root=Path(__file__).resolve().parents[2]
    cases=json.loads((root/'docs/evaluations/m3-scene-review-qwen7b-2026-10-27/inputs.json').read_text())
    case=cases[index];p=routes.ProjectResponse.model_validate(case['project'])
    routes.projects.get_project_store().create(p.model_dump(exclude_computed_fields=True))
    provider=ReviewProvider();provider.mode='mismatch' if case['variant']=='violating' else 'empty'
    monkeypatch.setattr(routes,'get_review_provider',lambda:provider)
    r=client.post(f'/api/projects/{p.id}/screenplay-reviews',json=case['request']);assert r.status_code==200,r.text
    saved=r.json();item=saved['screenplay_reviews'][-1];sources=json.loads(provider.requests[0].input_text)['sources']
    prompt=provider.requests[0].instructions
    assert 'Missing expression, dialogue or an immediate decision is not a violation unless' in prompt
    assert 'Distinguish using an already permitted element from introducing a new prohibited one' in prompt
    assert 'A suggestion is optional' in prompt
    assert 'every observation, impact, suggestion and question' in prompt
    assert 'Do not keep secondary craft/uncertain notes or questions' in prompt
    assert 'Suggest a small action the author may consider' not in prompt
    assert item['prompt_version']=='screenplay-review-v4-author-control'
    assert saved['screenplay']==case['project']['screenplay'] and saved['scene_outline']==case['project']['scene_outline']
    assert item['source_screenplay']==case['project']['screenplay'] and len(provider.requests)==1
    target_texts=[s for s in sources if s['is_target'] and s['field']=='text']
    target=next(s for s in p.screenplay.scenes if s.id==case['request']['target_scene_id'])
    assert [(s['text'],s['block_kind']) for s in target_texts]==[(b.text,b.kind) for b in target.blocks]
    original_ids={s['id'] for s in item['sources']}
    assert all(e['source_id'] in original_ids for n in item['notes'] for e in n['evidence'])


@pytest.mark.parametrize('folder,version',[
    ('m3-scene-review-qwen7b-2026-10-27','screenplay-review-v1'),
    ('m3-scene-review-short-sources-qwen7b-2026-10-27','screenplay-review-v2-short-sources'),
    ('m3-scene-review-constraint-first-qwen7b-2026-10-27','screenplay-review-v3-constraint-first'),
    ('m3-scene-review-constraint-first-gemma2-2026-10-27','screenplay-review-v3-constraint-first'),
])
def test_old_reviews_reopen_unchanged_without_provider(project_client,monkeypatch,folder,version):
    client,_=project_client;provider=ReviewProvider()
    monkeypatch.setattr(routes,'get_review_provider',lambda:provider)
    root=Path(__file__).resolve().parents[2]/'docs/evaluations'/folder
    for row in json.loads((root/'results.json').read_text()):
        old=json.loads((root/row['name']/'project-after.json').read_text())
        p=routes.ProjectResponse.model_validate(old)
        routes.projects.get_project_store().create(p.model_dump(exclude_computed_fields=True))
        reopened=client.get(f'/api/projects/{p.id}').json()
        assert reopened['screenplay_reviews']==old['screenplay_reviews']
        assert reopened['screenplay']==old['screenplay']
        assert reopened['screenplay_reviews'][-1]['prompt_version']==version
    assert not provider.requests


def test_ui_all_fields_evidence_keeps_script_and_sources(reviewing):
    client,provider,p,_=reviewing
    body=edit(p)
    body['screenplay']['scenes'][0]['blocks'].append(block(kind='dialogue',text='Cha cứ để đó.'))
    p=client.put(f"/api/projects/{p['id']}",json=body).json()
    provider.mode='ui_all_fields'
    result,_=review(client,p)
    assert result.status_code==200,result.text
    saved=result.json();reviewed=saved['screenplay_reviews'][-1]
    sources={s['id']:s for s in reviewed['sources']}
    assert [sources[e['source_id']]['field'] for e in reviewed['notes'][0]['evidence']]==['text','heading','speaker']
    assert saved['screenplay']==p['screenplay'] and reviewed['source_screenplay']==p['screenplay']
