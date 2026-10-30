from copy import deepcopy
from uuid import uuid4
import pytest

from test_projects import project_client, start_project, payload
from test_scene_suggestions import SceneProvider
from test_screenplay_writing import WritingProvider
from test_screenplay_review import ReviewProvider
from app.api.routes import draft_runs as api
from app.application import draft_workflow as flow
from app.application.draft_run_store import DraftRunStore
from app.application.project_store import ProjectConflict


@pytest.fixture
def drafting(project_client, monkeypatch):
    client, mentor = project_client
    selected = [mentor, SceneProvider(), WritingProvider(), ReviewProvider()]
    monkeypatch.setattr(api, 'providers', lambda: selected)
    monkeypatch.setattr(flow, 'launch', lambda *args: flow.execute(*args))
    return client, selected


def begin(drafting):
    client, providers = drafting
    p = start_project(client)
    url = f"/api/projects/{p['id']}/draft-runs"
    body = {'revision':p['revision'], 'request_id':str(uuid4())}
    response = client.post(url, json=body)
    assert response.status_code == 200, response.text
    run_url = url + '/' + body['request_id']
    return client, providers, p, url, run_url, body


def complete(client, url):
    r = client.get(url).json()
    if r['status'] == 'needs_input':
        c = client.get(url+'/candidate').json()
        result = client.post(url+'/continue', json={'candidate_revision':c['revision'], 'answers':['']*len(c['project']['answers'])})
        assert result.status_code == 200, result.text
    r = client.get(url).json()
    assert r['status'] == 'ready', r
    return r, client.get(url+'/candidate').json()


def test_pipeline_checkpoints_provenance_and_atomic_adoption(drafting):
    client, providers, p, base, url, body = begin(drafting)
    r, c = complete(client, url)
    candidate = c['project']
    assert r['completed_scenes'] == r['total_scenes'] and r['total_scenes'] > 0
    assert all(s['blocks'] for s in candidate['screenplay']['scenes'])
    assert all(v['origin']=='ai_proposal' for v in candidate['screenplay']['provenance'].values())
    assert client.get(f"/api/projects/{p['id']}").json()['draft'] is None
    calls = [len(x.requests) for x in providers]
    assert client.post(base,json=body).status_code == 200
    assert client.post(base,json={**body,'revision':body['revision']+1}).status_code == 409
    for _ in range(3): client.get(url);client.get(url+'/candidate')
    assert [len(x.requests) for x in providers] == calls
    adopted = client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']})
    assert adopted.status_code == 200, adopted.text
    assert adopted.json()['screenplay'] == candidate['screenplay']
    assert client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']}).json() == adopted.json()
    assert client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']-1}).status_code == 409
    assert client.get(url).json()['adopted_revision'] == adopted.json()['revision']


def test_source_conflict_keeps_candidate_and_foreign_work(drafting):
    client, providers, p, base, url, body = begin(drafting)
    r,c=complete(client,url)
    changed=client.put(f"/api/projects/{p['id']}",json={**payload(p),'idea':'Một người mẹ chờ con trong bếp.'}).json()
    assert client.post(url+'/adopt',json={'revision':changed['revision'],'candidate_revision':c['revision']}).status_code==409
    assert client.get(url+'/candidate').json()==c
    assert client.get(f"/api/projects/{p['id']}").json()==changed


def test_unknown_scene_call_keeps_completed_scenes_and_never_retries(drafting,monkeypatch):
    from app.application.ai_provider import ProviderTimeoutError
    client, providers, p, base, url, body=begin(drafting)
    original=providers[2].request_structured
    calls=[]
    def fail(request):
        calls.append(request)
        if len(calls)==2: raise ProviderTimeoutError('unknown second scene')
        return original(request)
    monkeypatch.setattr(providers[2],'request_structured',fail)
    r=client.get(url).json()
    client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    r=client.get(url).json();c=client.get(url+'/candidate').json()
    assert r['status']=='interrupted' and r['completed_scenes']==1, r
    assert c['project']['screenplay']['scenes'][0]['blocks']
    assert client.post(url+'/continue',json={'candidate_revision':c['revision']}).status_code==409
    assert len(calls)==2


def test_candidate_edits_are_isolated_and_origins_are_server_owned(drafting):
    client, providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    script=c['project']['screenplay']
    edit={k:deepcopy(script[k]) for k in ('id','version','scenes')}
    edit['scenes'][0]['blocks'][0]['text']='  Chữ tác giả tự sửa.  '
    body={'revision':c['revision'],'draft':c['project']['draft'],'screenplay':edit}
    result=client.put(url+'/candidate',json=body)
    assert result.status_code==200,result.text
    assert client.put(url+'/candidate',json=body).status_code==409
    next=result.json();b=next['project']['screenplay']['scenes'][0]['blocks'][0]
    assert next['project']['screenplay']['provenance'][f"block:{b['id']}:text"]['origin']=='author_input'
    stored=api.store().get_run(p['id'],url.rsplit('/',1)[-1])
    assert stored['original']['screenplay']['scenes'][0]['blocks'][0]['text']!=b['text']
    assert client.get(f"/api/projects/{p['id']}").json()['screenplay'] is None


def test_recovery_and_active_run_claim(drafting,monkeypatch):
    client,providers=drafting
    monkeypatch.setattr(flow,'launch',lambda *args:None)
    p=start_project(client);base=f"/api/projects/{p['id']}/draft-runs"
    body={'revision':p['revision'],'request_id':str(uuid4())}
    assert client.post(base,json=body).status_code==200
    assert client.post(base,json={**body,'request_id':str(uuid4())}).status_code==409
    api.store().recover('new-process')
    url=base+'/'+body['request_id']
    assert client.get(url).json()['status']=='interrupted'
    assert client.post(url+'/continue',json={'candidate_revision':0}).status_code==200
    assert client.post(url+'/continue',json={'candidate_revision':0}).status_code==409
    assert client.post(url+'/cancel').status_code==200
    # A running cancellation remains active until the worker acknowledges it.
    assert client.get(url).json()['cancel_requested'] is True


def test_cancel_during_scene_keeps_late_result_without_starting_next(drafting):
    client,providers,p,base,url,body=begin(drafting)
    providers[2].hook=lambda:client.post(url+'/cancel')
    r=client.get(url).json()
    client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    r=client.get(url).json();c=client.get(url+'/candidate').json()
    assert r['status']=='cancelled' and r['completed_scenes']==1
    assert len(providers[2].requests)==1
    assert c['project']['screenplay']['scenes'][0]['blocks']
    assert client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']}).status_code==409


def test_candidate_answer_save_replay_and_critic_failure_keep_script(drafting):
    from app.application.ai_provider import ProviderTimeoutError
    client,providers,p,base,url,body=begin(drafting)
    c=client.get(url+'/candidate').json()
    b={'revision':c['revision'],'save_id':str(uuid4()),'answers':['']*len(c['project']['answers'])}
    saved=client.put(url+'/candidate',json=b)
    assert saved.status_code==200,saved.text
    assert client.put(url+'/candidate',json=b).json()==saved.json()
    assert client.put(url+'/candidate',json={**b,'answers':['Tôi tự chọn.']*len(b['answers'])}).status_code==409
    providers[3].error=ProviderTimeoutError('review unavailable')
    r,c=complete(client,url)
    assert r['review_error'] and all(s['blocks'] for s in c['project']['screenplay']['scenes'])
    assert api.store().get_run(p['id'],body['request_id'])['original']['screenplay']


def test_received_model_result_survives_restart_without_duplicate_call(drafting):
    from app.application.ai_provider import StructuredRequest
    from app.application.workflow import _ReasoningOutput
    client,providers,p,base,url,body=begin(drafting)
    provider=flow.RecordedProvider(providers[0],api.store(),p['id'],body['request_id'])
    req=StructuredRequest(stage='reasoning',instructions='QA',input_text='same source',response_model=_ReasoningOutput)
    first=provider.request_structured(req)
    before=len(providers[0].requests)
    second=flow.RecordedProvider(providers[0],api.store(),p['id'],body['request_id']).request_structured(req)
    assert second.output==first.output and len(providers[0].requests)==before


def test_background_start_returns_early_and_cancel_does_not_spawn_again(drafting,monkeypatch):
    from threading import Event
    client,providers=drafting
    entered,release=Event(),Event();futures=[]
    original=providers[0].request_structured
    def hold(request):
        if request.stage=='reasoning':
            entered.set();assert release.wait(5)
        return original(request)
    monkeypatch.setattr(providers[0],'request_structured',hold)
    monkeypatch.setattr(flow,'launch',lambda *args:futures.append(flow.POOL.submit(flow.execute,*args)))
    try:
        client,providers,p,base,url,body=begin(drafting)
        assert entered.wait(2)
        assert client.get(url).json()['status']=='running'
        assert client.post(base,json=body).status_code==200 and len(futures)==1
        assert client.post(url+'/cancel').status_code==200
    finally:
        release.set()
        for future in futures:future.result(timeout=5)
    assert client.get(url).json()['status']=='cancelled'
    assert len(providers[0].requests)==1 and not providers[1].requests


@pytest.mark.parametrize('count',[2,6])
def test_supported_short_fixture_completes_every_scene(drafting,count):
    client,providers=drafting
    providers[1].count=count
    client,providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    assert r['completed_scenes']==r['total_scenes']==count
    assert len(providers[2].requests)==count


def test_author_scene_cap_rejects_extra_scenes_without_truncating_or_writing(drafting):
    client, providers = drafting
    p = start_project(client)
    base = f"/api/projects/{p['id']}"
    p = client.put(base, json={**payload(p), 'constraints':['Tối đa một cảnh.', 'Chỉ hai nhân vật.']}).json()
    rid = str(uuid4()); url = base+'/draft-runs/'+rid
    assert client.post(base+'/draft-runs', json={'revision':p['revision'], 'request_id':rid}).status_code == 200
    c = client.get(url+'/candidate').json()
    if client.get(url).json()['status'] == 'needs_input':
        assert client.post(url+'/continue', json={'candidate_revision':c['revision'], 'answers':['']*len(c['project']['answers'])}).status_code == 200
    r = client.get(url).json(); c = client.get(url+'/candidate').json()
    assert r['status'] == 'partial' and c['project']['draft']
    assert not c['project']['scene_outline']['scenes'] and c['project']['screenplay'] is None
    assert len(providers[1].requests) == 1 and not providers[2].requests
    assert client.get(base).json()['draft'] is None
    # Replaying a durable received but invalid result must not send another model call.
    if r['can_continue']:
        client.post(url+'/continue', json={'candidate_revision':c['revision'], 'answers':c['project']['answers']})
    assert len(providers[1].requests) == 1 and not providers[2].requests


def test_character_answer_does_not_force_two_scenes_in_automatic_run(drafting, monkeypatch):
    client, providers = drafting
    original = providers[0].request_structured
    def ask_characters(request):
        result = original(request)
        if request.stage == 'reasoning':
            result = result.__class__(output=result.output.model_copy(update={
                'missing_information':['Bao nhiêu nhân vật trong cảnh?']}), model=result.model)
        return result
    monkeypatch.setattr(providers[0], 'request_structured', ask_characters)
    providers[1].count = 1
    client, providers, p, base, url, body = begin(drafting)
    assert client.get(url).json()['status'] == 'needs_input'
    c = client.get(url+'/candidate').json()
    assert client.post(url+'/continue', json={'candidate_revision':c['revision'], 'answers':['2']}).status_code == 200
    r = client.get(url).json()
    assert r['status'] == 'ready' and r['completed_scenes'] == 1
    schema = providers[1].requests[0].response_model.model_json_schema()['properties']['scenes']
    assert schema['minItems'] == 1 and schema['maxItems'] == 6


def test_candidate_cleared_scene_is_partial_not_complete(drafting):
    client,providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    script=c['project']['screenplay']
    edit={k:deepcopy(script[k]) for k in ('id','version','scenes')}
    edit['scenes'][0]['blocks']=[]
    result=client.put(url+'/candidate',json={'revision':c['revision'],'draft':c['project']['draft'],'screenplay':edit})
    assert result.status_code==200,result.text
    assert client.get(url).json()['status']=='partial'
    assert client.get(url).json()['completed_scenes']==1
    assert client.post(url+'/continue',json={'candidate_revision':result.json()['revision']}).status_code==409


def test_workspace_scene_changed_during_run_cannot_be_overwritten(drafting):
    client,providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    p=client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']}).json()
    result=client.post(base,json={'revision':p['revision'],'request_id':str(uuid4())})
    next_url=base+'/'+result.json()['id']
    r,c=complete(client,next_url)
    edit={k:deepcopy(p['screenplay'][k]) for k in ('id','version','scenes')}
    edit['scenes'][0]['blocks'][0]['text']='Chữ tác giả mới trong lúc chạy.'
    p=client.put(f"/api/projects/{p['id']}",json={**payload(p),'screenplay':edit}).json()
    assert client.post(next_url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']}).status_code==409
    assert client.get(f"/api/projects/{p['id']}").json()['screenplay']['scenes'][0]['blocks'][0]['text']=='Chữ tác giả mới trong lúc chạy.'


def test_restart_between_received_scene_and_checkpoint_reuses_result(drafting,monkeypatch):
    client,providers,p,base,url,body=begin(drafting)
    class Crash(BaseException):
        pass
    original=DraftRunStore.change
    armed=[True]
    def fail_checkpoint(self,project_id,run_id,fn):
        def wrapped(r):
            fn(r)
            if armed[0] and r['step']=='write' and r['completed_scenes']==2:
                armed[0]=False
                raise Crash()
        return original(self,project_id,run_id,wrapped)
    monkeypatch.setattr(DraftRunStore,'change',fail_checkpoint)
    r=client.get(url).json()
    with pytest.raises(Crash):
        client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    monkeypatch.setattr(DraftRunStore,'change',original)
    assert len(providers[2].requests)==2
    assert client.get(url).json()['completed_scenes']==1
    api.store().recover('simulated-restart')
    r=client.get(url).json()
    response=client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    assert response.status_code==200,response.text
    assert client.get(url).json()['status']=='ready'
    assert len(providers[2].requests)==2, 'received second scene must be replayed from SQLite'


def test_adopted_partial_run_does_not_block_next_run(drafting):
    client,providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    script={k:deepcopy(c['project']['screenplay'][k]) for k in ('id','version','scenes')}
    script['scenes'][1]['blocks']=[]
    c=client.put(url+'/candidate',json={'revision':c['revision'],'draft':c['project']['draft'],'screenplay':script}).json()
    adopted=client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']})
    assert adopted.status_code==200,adopted.text
    next_run=client.post(base,json={'revision':adopted.json()['revision'],'request_id':str(uuid4())})
    assert next_run.status_code==200,next_run.text
