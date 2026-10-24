from copy import deepcopy
import json

from app.api.routes import projects as routes
from app.application.clarification import MAX_CHOICES
from test_projects import project_client, payload, start_project


def clarify(client, project):
    response = client.post(f"/api/projects/{project['id']}/clarify", json={"revision": project['revision']})
    assert response.status_code == 200, response.text
    return response.json()


def answer_all(client, project):
    data = payload(project)
    data['answers'] = [f'Lựa chọn {i + 1}: chỉ hành động, giữ kết mở.' for i in range(len(project['analysis']['missing_information']))]
    response = client.put(f"/api/projects/{project['id']}", json=data)
    assert response.status_code == 200, response.text
    return response.json()


def test_extended_conversation_keeps_answers_and_appends_without_generating(project_client):
    client, provider = project_client
    project = start_project(client)
    project = clarify(client, project)
    assert 5 <= len(project['analysis']['missing_information']) <= 6
    assert not project['draft']
    assert all(not a for a in project['answers'])
    project = answer_all(client, project)
    before = deepcopy(project)
    project = clarify(client, project)
    count = len(before['answers'])
    assert project['analysis']['missing_information'][:count] == before['analysis']['missing_information']
    assert project['answers'][:count] == before['answers']
    assert len(project['answers']) > count
    assert all(not a for a in project['answers'][count:])
    assert not project['draft'] and not project['plan_generations']
    assert all(r.stage == 'reasoning' for r in provider.requests)
    assert project['clarification_history'][-1]['answers'] == before['answers']
    assert client.post(f"/api/projects/{project['id']}/plan", json={'revision': project['revision']}).status_code == 422


def test_followup_failure_or_conflict_does_not_replace_answers(project_client, monkeypatch):
    client, provider = project_client
    project = clarify(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    requests = len(provider.requests)
    assert client.post(url+'/clarify', json={'revision':project['revision']}).status_code == 422
    assert len(provider.requests) == requests
    project = answer_all(client, project)
    before = deepcopy(project)
    from app.application.ai_provider import ProviderTimeoutError
    monkeypatch.setattr(provider, 'request_structured', lambda _: (_ for _ in ()).throw(ProviderTimeoutError('QA')))
    assert client.post(url+'/clarify', json={'revision':project['revision']}).status_code == 504
    assert client.get(url).json() == before
    assert client.post(url+'/clarify', json={'revision':project['revision']-1}).status_code == 409
    assert client.get(url).json() == before


def test_no_new_model_question_preserves_choices_and_streams_as_analysis(project_client, monkeypatch):
    client, provider = project_client
    project = clarify(client, start_project(client))
    project = answer_all(client, project)
    original = provider.request_structured
    def no_questions(request):
        result = original(request)
        if request.stage == 'reasoning': result.output.missing_information = []
        return result
    monkeypatch.setattr(provider, 'request_structured', no_questions)
    # Ask until the fixed framework is covered; no implicit generation when it is covered.
    project = clarify(client, project)
    project = answer_all(client, project)
    before = deepcopy(project)
    response = client.post(f"/api/projects/{project['id']}/clarify/stream", json={'revision':project['revision']})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[-1]['type']=='result'
    result = events[-1]['project']
    assert result['answers'] == before['answers']
    assert result['analysis']['missing_information'] == before['analysis']['missing_information']
    assert result['draft'] is None
    assert [(e['stage'], e['status']) for e in events[:-1]] == [('reasoning','active'),('reasoning','completed'),('saving','active'),('saving','completed')]


def test_bounded_questions_and_legacy_analysis_remain_compatible(project_client):
    client, provider = project_client
    legacy = start_project(client)
    legacy = client.post(f"/api/projects/{legacy['id']}/analyze",json={'revision':legacy['revision']}).json()
    assert len(legacy['answers']) == 2
    assert len(legacy['analysis']['missing_information']) == 2
    from app.application.clarification import conversation_questions
    existing = [f'Question {i}' for i in range(MAX_CHOICES-1)]
    questions = conversation_questions([' A new question ', 'A new question'],existing,{},'English')
    assert len(questions)==MAX_CHOICES and questions[-1]=='A new question'
    store=routes.get_project_store();raw=store.get(legacy['id'])
    raw['analysis']['missing_information']=[f'Question {i}' for i in range(MAX_CHOICES)]
    raw['answers']=['Keep it open']*MAX_CHOICES
    saved=store.save(raw,legacy['revision'])
    count=len(provider.requests)
    assert client.post(f"/api/projects/{legacy['id']}/clarify",json={'revision':saved['revision']}).status_code==422
    assert len(provider.requests)==count
