from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.application.revision_review import review_context
from app.application.workflow import _card_review_schema
from test_draft_runs import begin, complete, drafting
from test_projects import project_client


@pytest.mark.parametrize('unchanged', [False, True])
def test_related_card_is_constrained_even_without_an_edited_card(unchanged):
    draft = {'title': 'Mở cửa', 'logline': 'Hai chị em mở tiệm.', 'sections': [
        {'title': 'Beginning', 'content': 'Chị đặt trà.'},
        {'title': 'Ending', 'content': 'Em treo biển. Em kéo ghế. Em cầm trà. Hai người chờ.'},
    ]}
    context = review_context(draft, deepcopy(draft) if unchanged else None, {
        'idea': 'Mở tiệm trong mưa.', 'constraints': [],
        'clarifications': [{'question': 'Kết?', 'answer': 'Hai người ngồi chờ, chưa có khách.'}],
    }, True)
    before = deepcopy((draft, context))
    assert not context['neighbor_checks'] and not context['focus_card_ids']
    model = _card_review_schema(context)
    data = {'reviews': [{'card_id': 'section-1-part-3', 'decision_id': 'answer-0',
        'related_card_id': 'section-1-part-4', 'comparison': 'mismatch',
        'observation': 'Đối chiếu kết thúc.', 'suggestion': 'Giữ hình ảnh hai người chờ.'}],
        'passed': False, 'rubric_scores': None}
    with pytest.raises(ValidationError):
        model.model_validate(data)
    # The fourth visible card is part-3; never invent part-4 or guess an alias.
    for related in [None, 'section-1', 'section-1-part-2']:
        valid = deepcopy(data)
        valid['reviews'][0]['related_card_id'] = related
        assert model.model_validate(valid).reviews[0].related_card_id == related
    assert (draft, context) == before


def test_invalid_saved_review_keeps_draft_progress_and_never_retries(drafting, monkeypatch):
    client, providers, project, base, url, body = begin(drafting)
    original = providers[0].request_structured
    attempts = []

    def invalid_review(request):
        result = original(request)
        if request.stage == 'evaluation':
            attempts.append(request)
            # Simulate a legacy provider result that bypassed its response schema.
            result.output.reviews[0].related_card_id = 'section-99'
        return result

    monkeypatch.setattr(providers[0], 'request_structured', invalid_review)
    run, candidate = complete(client, url)
    assert len(attempts) == 1
    assert 'liên kết card' in run['review_error']
    assert all(scene['blocks'] for scene in candidate['project']['screenplay']['scenes'])
    counts = [len(provider.requests) for provider in providers]
    from app.api.routes import draft_runs as api
    stored = deepcopy(api.store().get_run(project['id'], body['request_id']))
    for _ in range(2):
        assert client.get(url).json() == run
        assert client.get(url + '/candidate').json() == candidate
    assert api.store().get_run(project['id'], body['request_id']) == stored
    assert [len(provider.requests) for provider in providers] == counts
    assert client.get(f"/api/projects/{project['id']}").json()['draft'] is None
