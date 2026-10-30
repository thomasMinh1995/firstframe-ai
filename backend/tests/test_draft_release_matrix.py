"""DR-09: use the real API/store/runner with deterministic providers."""
from copy import deepcopy
from uuid import uuid4
import pytest
from test_projects import project_client, start_project
from test_scene_suggestions import SceneProvider
from test_screenplay_writing import WritingProvider
from test_screenplay_review import ReviewProvider
from app.api.routes import draft_runs, screenplays
from app.application import draft_workflow

@pytest.mark.parametrize('count', [1, 2, 6])
@pytest.mark.parametrize('ask', [False, True])
def test_release_matrix_checkpoint_edit_source_adopt_pdf(project_client, monkeypatch, count, ask):
    client, mentor = project_client
    original = mentor.request_structured
    def reasoning(request):
        result = original(request)
        if not ask and result.output.__class__.__name__ == '_ReasoningOutput':
            result = result.__class__(output=result.output.model_copy(update={'missing_information': []}), model=result.model)
        return result
    monkeypatch.setattr(mentor, 'request_structured', reasoning)
    scenes, writing, review = SceneProvider(), WritingProvider(), ReviewProvider()
    scenes.count = count
    providers = [mentor, scenes, writing, review]
    monkeypatch.setattr(draft_runs, 'providers', lambda: providers)
    monkeypatch.setattr(draft_workflow, 'launch', lambda *values: draft_workflow.execute(*values))
    p = start_project(client)
    base = f"/api/projects/{p['id']}"; request = {'revision':p['revision'], 'request_id':str(uuid4())}
    url = base+'/draft-runs/'+request['request_id']
    assert client.post(base+'/draft-runs', json=request).status_code == 200
    r = client.get(url).json()
    if ask:
        assert r['status'] == 'needs_input' and r['can_continue'] is True
        c = client.get(url+'/candidate').json()
        answers = ['Tôi chọn giữ khoảng lặng.', *(['']*(len(c['project']['answers'])-1))]
        assert client.post(url+'/continue', json={'candidate_revision':c['revision'], 'answers':answers}).status_code == 200
    r = client.get(url).json(); c = client.get(url+'/candidate').json()
    assert r['status'] == 'ready', r
    assert r['completed_scenes'] == r['total_scenes'] == count
    ids = [i['id'] for i in r['workflow_items']]
    assert len(ids) == len(set(ids)) == 7+count
    assert len(next(i for i in r['workflow_items'] if i['kind']=='review')['children']) == count
    calls = [len(provider.requests) for provider in providers]
    assert client.post(base+'/draft-runs', json=request).status_code == 200
    for _ in range(3):
        assert client.get(url).json()['progress_revision'] == r['progress_revision']
        client.get(url+'/candidate')
    assert [len(provider.requests) for provider in providers] == calls
    before_reviews = deepcopy(c['project']['screenplay_reviews'])
    script = {k:deepcopy(c['project']['screenplay'][k]) for k in ('id','version','scenes')}
    text = '  Chữ tác giả: giữ lá thư chưa mở.\nKhông thêm hòa giải.  '
    script['scenes'][0]['blocks'][0]['text'] = text
    saved = client.put(url+'/candidate', json={'revision':c['revision'], 'save_id':str(uuid4()), 'draft':c['project']['draft'], 'answers':c['project']['answers'], 'screenplay':script})
    assert saved.status_code == 200, saved.text
    latest = saved.json()
    assert latest['project']['screenplay_reviews'] == before_reviews
    assert latest['project']['screenplay']['scenes'][0]['blocks'][0]['text'] == text
    assert [i['id'] for i in client.get(url).json()['workflow_items']] == ids
    assert client.post(url+'/adopt', json={'revision':p['revision'], 'candidate_revision':c['revision']}).status_code == 409
    adopted = client.post(url+'/adopt', json={'revision':p['revision'], 'candidate_revision':latest['revision']})
    assert adopted.status_code == 200, adopted.text
    project = adopted.json()
    assert project['screenplay'] == latest['project']['screenplay']
    assert client.post(url+'/adopt', json={'revision':p['revision'], 'candidate_revision':latest['revision']}).json() == project
    def no_ai(): raise AssertionError('Selection/export must work with AI disabled')
    monkeypatch.setattr(draft_runs, 'providers', no_ai)
    monkeypatch.setattr(screenplays, 'get_screenplay_provider', no_ai)
    selection_id = str(uuid4())
    selected = client.post(base+'/screenplay-selections', json={'revision':project['revision'], 'request_id':selection_id, 'source_version_id':'current'})
    assert selected.status_code == 200, selected.text
    assert selected.json()['screenplay_selections'][-1]['screenplay'] == project['screenplay']
    pdf = client.get(base+'/screenplay-selections/'+selection_id+'/pdf')
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    assert [len(provider.requests) for provider in providers] == calls
