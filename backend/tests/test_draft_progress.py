from copy import deepcopy
from datetime import datetime

import pytest
from pydantic import ValidationError

from test_draft_runs import drafting, begin, complete  # noqa: F401
from test_projects import project_client  # noqa: F401
from app.api.routes import draft_runs as api
from app.application import draft_workflow as flow, draft_progress as progress
from app.application.ai_provider import ProviderTimeoutError
from app.application.draft_run_store import DraftRunStore
from app.api.schemas.draft_runs import WorkflowItem


def item(run, key):
    return next(i for i in progress.all_items(run) if i['id'] == key)


def test_needs_input_describes_saved_analysis_without_an_extra_model_call(drafting):
    client, providers, p, base, url, body = begin(drafting)
    run = client.get(url).json()
    candidate = client.get(url+'/candidate').json()
    assert run['status'] == 'needs_input' and run['can_continue']
    assert run['progress_version'] == 1 and run['progress_revision'] > 0
    assert item(run, 'analysis')['status'] == 'completed'
    assert item(run, 'analysis')['result']['id'] == candidate['project']['analysis']['artifact_id']
    assert item(run, 'analysis')['result']['candidate_revision'] == candidate['revision']
    assert item(run, 'intent')['status'] == 'needs_input'
    assert all(item(run, k)['status'] == 'pending' for k in ('plan','plan_review','outline','review','draft'))
    assert len(providers[0].requests) == 1
    assert len(run['workflow_items']) == 7
    datetime.fromisoformat(item(run, 'analysis')['started_at'])
    datetime.fromisoformat(item(run, 'analysis')['finished_at'])


@pytest.mark.parametrize('count', [1, 2, 6])
def test_dynamic_scene_items_and_review_results_survive_read_only_reload(drafting, count):
    client, providers, p, base, url, body = begin(drafting)
    providers[1].count = count
    run, candidate = complete(client, url)
    assert len(run['workflow_items']) == 7 + count
    script = candidate['project']['screenplay']
    writes = [i for i in run['workflow_items'] if i['kind'] == 'write']
    assert [i['scene_id'] for i in writes] == [s['id'] for s in script['scenes']]
    assert all(i['status'] == 'completed' and i['result']['id'] == i['scene_id'] for i in writes)
    assert item(run, 'review')['status'] == item(run, 'draft')['status'] == 'completed'
    reviews = item(run, 'review')['children']
    assert len(reviews) == count and all(i['status'] == 'completed' for i in reviews)
    assert {i['result']['id'] for i in reviews} == {r['id'] for r in candidate['project']['screenplay_reviews']}
    assert item(run, 'plan_review')['result']['id'] == candidate['plan_review']['metadata']['artifact_id']
    assert not run['can_continue'] and run['continue_block_reason'] == 'not_resumable'
    raw = api.store().get_run(p['id'], body['request_id'])
    calls = [len(p.requests) for p in providers]
    for _ in range(2):
        assert client.get(url).json() == run
        assert client.get(base).json()[0] == run
    assert api.store().get_run(p['id'], body['request_id']) == raw
    assert calls == [len(p.requests) for p in providers]


def test_progress_revision_can_advance_without_candidate_revision(drafting):
    client, providers, p, base, url, body = begin(drafting)
    before = api.store().get_run(p['id'], body['request_id'])
    def start(r):
        progress.update_item(r, 'plan', 'running')
    after = api.store().change(p['id'], body['request_id'], start)
    assert after['progress_revision'] == before['progress_revision'] + 1
    assert after['candidate_revision'] == before['candidate_revision']
    again = api.store().change(p['id'], body['request_id'], start)
    assert again['progress_revision'] == after['progress_revision']
    assert item(again, 'plan')['started_at'] == item(after, 'plan')['started_at']


def test_plan_readable_during_critic_and_critic_error_is_separate(drafting, monkeypatch):
    client, providers, p, base, url, body = begin(drafting)
    original = providers[0].request_structured
    observed = []
    def critic(request):
        if request.stage == 'evaluation':
            run = client.get(url).json()
            c = client.get(url+'/candidate').json()
            assert c['project']['draft']
            assert item(run, 'plan')['status'] == 'completed'
            assert item(run, 'plan_review')['status'] == 'running'
            observed.append(run)
            raise ProviderTimeoutError('SECRET raw output and prompt')
        return original(request)
    monkeypatch.setattr(providers[0], 'request_structured', critic)
    run, c = complete(client, url)
    assert len(observed) == 1
    assert item(run,'plan_review')['status'] == 'warning'
    assert item(run,'review')['status'] == 'completed'
    assert item(run,'draft')['status'] == 'completed'
    assert run['review_error'] and 'SECRET' not in str(run)
    assert c['plan_review'] is None


def test_review_only_failure_keeps_readable_draft_and_marks_unrun_scenes(drafting):
    client, providers, p, base, url, body = begin(drafting)
    providers[3].error = ProviderTimeoutError('raw private prompt')
    run, c = complete(client,url)
    assert item(run,'draft')['status'] == 'completed'
    assert item(run,'plan_review')['status'] == 'completed'
    assert item(run,'review')['status'] == 'warning'
    assert [i['status'] for i in item(run,'review')['children']] == ['warning','skipped']
    assert all(s['blocks'] for s in c['project']['screenplay']['scenes'])
    assert 'raw private prompt' not in str(run)


def test_unknown_scene_call_has_stable_ids_no_secret_and_continue_agrees(drafting, monkeypatch):
    client, providers, p, base, url, body = begin(drafting)
    original = providers[2].request_structured
    seen = []
    def fail(request):
        seen.append(client.get(url).json())
        if len(seen) == 2:
            raise ProviderTimeoutError('SECRET unsafe raw output')
        return original(request)
    monkeypatch.setattr(providers[2], 'request_structured', fail)
    r = client.get(url).json()
    client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    r = client.get(url).json()
    writes = [i for i in r['workflow_items'] if i['kind']=='write']
    assert [i['status'] for i in writes] == ['completed','interrupted']
    assert [i['id'] for i in writes] == [i['id'] for i in seen[0]['workflow_items'] if i['kind']=='write']
    assert not r['can_continue'] and r['continue_block_reason']=='unknown_result'
    assert 'SECRET' not in str(r)
    assert client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']}).status_code == 409
    assert len(seen)==2


def test_cancel_keeps_late_completed_scene_and_skips_future_work(drafting):
    client, providers, p, base, url, body = begin(drafting)
    during=[]
    def cancel():
        during.append(client.post(url+'/cancel').json())
    providers[2].hook=cancel
    r=client.get(url).json()
    client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    r=client.get(url).json()
    assert during[0]['cancel_requested'] and not during[0]['can_continue']
    assert [i['status'] for i in r['workflow_items'] if i['kind']=='write']==['completed','skipped']
    assert item(r,'review')['status']=='skipped'
    assert r['status']=='cancelled' and r['continue_block_reason']=='cancelled'
    assert len(providers[2].requests)==1 and not providers[3].requests


def test_restart_between_received_output_and_checkpoint_is_atomic(drafting, monkeypatch):
    client, providers, p, base, url, body = begin(drafting)
    class Crash(BaseException): pass
    original=DraftRunStore.change
    armed=[True]
    def crash(self,project_id,run_id,fn):
        def wrapped(r):
            fn(r)
            if armed[0] and r['completed_scenes']==2:
                armed[0]=False
                raise Crash()
        return original(self,project_id,run_id,wrapped)
    monkeypatch.setattr(DraftRunStore,'change',crash)
    r=client.get(url).json()
    with pytest.raises(Crash):
        client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    monkeypatch.setattr(DraftRunStore,'change',original)
    r=client.get(url).json()
    ids=[i['id'] for i in r['workflow_items'] if i['kind']=='write']
    assert [item(r,i)['status'] for i in ids]==['completed','running']
    assert not client.get(url+'/candidate').json()['project']['screenplay']['scenes'][1]['blocks']
    rev=r['progress_revision']
    api.store().recover('new-owner')
    r=client.get(url).json()
    assert r['progress_revision']>rev and r['can_continue']
    assert item(r,ids[0])['status']=='completed' and item(r,ids[1])['status']=='interrupted'
    run,c=complete_after_continue(client,url,r)
    assert all(item(run,i)['status']=='completed' for i in ids)
    assert len(providers[2].requests)==2


def complete_after_continue(client,url,r):
    response=client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    assert response.status_code==200,response.text
    return complete(client,url)


def test_legacy_projection_never_writes_or_invents_review_times(drafting):
    client, providers, p, base, url, body = begin(drafting)
    r,c=complete(client,url)
    def old(r):
        for k in ('progress_version','progress_revision','workflow_items','plan_review_result'):
            r.pop(k,None)
    api.store().change(p['id'],body['request_id'],old)
    raw=api.store().get_run(p['id'],body['request_id'])
    calls=[len(p.requests) for p in providers]
    r=client.get(url).json()
    assert r['progress_version']==0 and r['progress_revision']==0
    assert item(r,'plan_review')['status']=='unknown'
    assert item(r,'intent')['status']=='unknown'
    assert item(r,'plan')['status']=='completed'
    assert all(i['started_at'] is None and i['finished_at'] is None for i in progress.all_items(r))
    assert api.store().get_run(p['id'],body['request_id'])==raw
    assert [len(p.requests) for p in providers]==calls
    assert client.get(base).json()[0]==r


@pytest.mark.parametrize('reason',['configuration_changed','candidate_edited','cancelled','adopted','provider_unavailable'])
def test_continuation_capabilities_match_backend_guards(drafting,monkeypatch,reason):
    client,providers,p,base,url,body=begin(drafting)
    if reason in ('candidate_edited','adopted'):
        r,c=complete(client,url)
        if reason=='adopted':
            client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']})
        else:
            edit={k:deepcopy(c['project']['screenplay'][k]) for k in ('id','version','scenes')}
            edit['scenes'][0]['blocks']=[]
            saved=client.put(url+'/candidate',json={'revision':c['revision'],'draft':c['project']['draft'],'screenplay':edit})
            assert saved.status_code==200,saved.text
            r=client.get(url).json()
            assert item(r,'draft')['status']=='needs_input'
            assert item(r,'review')['status']=='completed' # Its original source remains readable.
    elif reason=='configuration_changed':
        monkeypatch.setattr(flow,'configuration',lambda p:{'changed':True})
    elif reason=='cancelled':
        client.post(url+'/cancel')
    else:
        def missing():
            from app.application.ai_provider import MissingProviderConfigurationError
            raise MissingProviderConfigurationError('SECRET provider config')
        monkeypatch.setattr(api,'providers',missing)
    r=client.get(url).json()
    assert not r['can_continue'] and r['continue_block_reason']==reason,r
    assert r['continue_block_message'] and 'SECRET' not in str(r)
    response=client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    assert response.status_code in (409,503),response.text


def test_invalid_progress_and_artifact_update_roll_back_together(drafting):
    client,providers,p,base,url,body=begin(drafting)
    original=api.store().get_run(p['id'],body['request_id'])
    def corrupt(r):
        r['candidate_revision']+=1
        r['candidate']['idea']='Must not persist'
        progress.update_item(r,'plan','completed')
    with pytest.raises(ValueError,match='saved result'):
        api.store().change(p['id'],body['request_id'],corrupt)
    assert api.store().get_run(p['id'],body['request_id'])==original
    with pytest.raises(ValidationError):
        WorkflowItem(id='write:1',kind='write',status='invented')


def test_restart_during_plan_critic_does_not_replay_or_claim_success(drafting,monkeypatch):
    client,providers,p,base,url,body=begin(drafting)
    class Crash(BaseException):pass
    original=providers[0].request_structured
    attempts=[]
    def crash(request):
        if request.stage=='evaluation':
            attempts.append(request)
            raise Crash()
        return original(request)
    monkeypatch.setattr(providers[0],'request_structured',crash)
    r=client.get(url).json()
    with pytest.raises(Crash):
        client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    assert item(client.get(url).json(),'plan')['status']=='completed'
    api.store().recover('new-process')
    r=client.get(url).json()
    assert r['can_continue'] and item(r,'plan_review')['status']=='interrupted'
    r,c=complete_after_continue(client,url,r)
    assert item(r,'plan_review')['status']=='warning'
    assert item(r,'plan_review')['error_code']=='unknown_result'
    assert c['plan_review'] is None and len(attempts)==1


def test_cancellation_request_advances_progress_but_not_text(drafting,monkeypatch):
    client,providers,p,base,url,body=begin(drafting)
    monkeypatch.setattr(flow,'launch',lambda *args:None)
    r=client.get(url).json()
    client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    before=client.get(url).json()
    after=client.post(url+'/cancel').json()
    assert after['status']=='running' and after['cancel_requested']
    assert after['progress_revision']>before['progress_revision']
    assert after['candidate_revision']==before['candidate_revision']
    assert after['continue_block_reason']=='cancelled'


def test_initial_analysis_failure_is_not_a_completed_card(drafting):
    client,providers=drafting
    def fail(request):raise ProviderTimeoutError('SECRET model input')
    providers[0].request_structured=fail
    client,providers,p,base,url,body=begin(drafting)
    r=client.get(url).json()
    assert item(r,'analysis')['status']=='interrupted'
    assert item(r,'analysis')['result'] is None
    assert item(r,'plan')['status']=='pending'
    assert not r['can_continue'] and r['continue_block_reason']=='unknown_result'
    assert 'SECRET' not in str(r)


def test_no_questions_runs_without_a_second_analysis_or_intent_call(drafting,monkeypatch):
    client,providers=drafting
    original=providers[0].request_structured
    def answer(request):
        result=original(request)
        if request.stage=='reasoning':
            return result.__class__(output=result.output.model_copy(update={'missing_information':[]}),model=result.model)
        return result
    monkeypatch.setattr(providers[0],'request_structured',answer)
    client,providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    assert item(r,'intent')['status']=='completed'
    assert len([q for q in providers[0].requests if q.stage=='reasoning'])==1


def test_legacy_partial_resume_initializes_progress_only_when_writing(drafting,monkeypatch):
    client,providers,p,base,url,body=begin(drafting)
    # A saved human-input checkpoint from before progress fields existed.
    def strip(r):
        for k in ('workflow_items','progress_version','progress_revision'):r.pop(k,None)
    api.store().change(p['id'],body['request_id'],strip)
    assert client.get(url).json()['progress_version']==0
    r,c=complete(client,url)
    assert r['progress_version']==1 and r['progress_revision']>0
    assert item(r,'analysis')['finished_at'] is None
    assert all(i['status']=='completed' for i in r['workflow_items'])


def test_api_contract_is_in_openapi_and_private_run_metadata_is_filtered(drafting):
    client,providers,p,base,url,body=begin(drafting)
    schema=client.get('/openapi.json').json()
    assert 'workflow_items' in schema['components']['schemas']['DraftRunResponse']['properties']
    assert 'unknown' in schema['components']['schemas']['WorkflowItem']['properties']['status']['enum']
    api.store().change(p['id'],body['request_id'],lambda r:r.update(private_future_field='SECRET'))
    r=client.get(url).json()
    assert 'private_future_field' not in r
    assert not {'calls','candidate','original','source_content','config','owner','plan_review_result'} & r.keys()


def test_cancel_before_critic_does_not_report_it_as_failed_or_completed(drafting,monkeypatch):
    client,providers,p,base,url,body=begin(drafting)
    original=DraftRunStore.change
    def cancel_after_plan(self,project_id,run_id,fn):
        def wrapped(r):
            fn(r)
            if r['step']=='plan_review' and not r['cancel_requested']:
                r['cancel_requested']=True
        return original(self,project_id,run_id,wrapped)
    monkeypatch.setattr(DraftRunStore,'change',cancel_after_plan)
    r=client.get(url).json()
    client.post(url+'/continue',json={'candidate_revision':r['candidate_revision']})
    r=client.get(url).json()
    assert r['status']=='cancelled'
    assert item(r,'plan')['status']=='completed'
    assert item(r,'plan_review')['status']=='cancelled'
    assert item(r,'outline')['status']=='skipped'
    assert not [q for q in providers[0].requests if q.stage=='evaluation']
    assert not providers[1].requests
