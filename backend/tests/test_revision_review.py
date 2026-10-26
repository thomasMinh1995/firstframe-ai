import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.application.ai_provider import MalformedProviderResponseError
from app.application.revision_review import CardReview, card_spans, feedback_messages, review_context
from app.application.workflow import _card_review_schema
from test_projects import develop_project, payload, project_client, start_project


def context_fixture():
    previous = {"title": "Cuộc gọi", "logline": "Người con chần chừ.", "sections": [
        {"title": "Main character", "content": "Hai cha con vẫn thương nhau."},
        {"title": "Beginning", "content": "Anh nhìn điện thoại. Anh xóa tin nhắn."},
        {"title": "Middle", "content": "Anh bấm gọi."},
        {"title": "Ending", "content": "Cha bắt máy. Anh mỉm cười."},
    ]}
    draft = deepcopy(previous)
    draft["sections"][3]["content"] = "Cha bắt máy. Anh thôi bấu mép bàn; cắt khi cuộc gọi kết nối."
    author = {"idea": "Một cuộc gọi nhỡ.", "constraints": [], "clarifications": [
        {"question": "Quan hệ?", "answer": "Không cãi vã hay bất đồng."},
        {"question": "Kết?", "answer": "Chỉ hành động trong phòng; dừng khi vừa bắt máy."},
    ]}
    return draft, previous, author


def test_context_targets_only_changed_card_without_mutating_source():
    draft, previous, author = context_fixture()
    original = deepcopy((draft, previous, author))
    context = review_context(draft, previous, author, True)
    assert context["focus_card_ids"] == ["section-3-part-1"]
    assert [card["label"] for card in context["cards"][:5]] == [
        "Card 1 · Mở đầu · 1", "Card 2 · Mở đầu · 2", "Card 3 · Phần giữa",
        "Card 4 · Kết thúc · 1", "Card 5 · Kết thúc · 2",
    ]
    assert context["decisions"][-2]["text"] == author["clarifications"][0]["answer"]
    assert (draft, previous, author) == original
    assert review_context(draft, draft, author, True)["focus_card_ids"] == []
    assert review_context(draft, None, author, True)["focus_card_ids"] == []
    assert review_context(draft, previous, author, False)["cards"][4]["label"] == "Card 5 · Ending · 2"


@pytest.mark.parametrize("text,count", [
    ('  Mẹ chờ.\n\nCon về muộn!  “Ăn cơm nhé?”\r\nCon kéo ghế.  ', 4),
    ("3.5 phút. Con ngồi xuống.", 2), ("Mẹ chờ 👩‍👦. Con về.\nBát cơm còn ấm.", 3),
    ("", 1), ("x" * 201, 1),
])
def test_card_boundaries_match_editor(text, count):
    spans = card_spans(text)
    assert len(spans) == count
    assert all(text[a:b] == text[a:b].strip() for a, b in spans)


@pytest.mark.parametrize("text,expected", [
    ("Cha chờ.\ufeffCon về.", ["Cha chờ.", "Con về."]),
    ("\ufeffCha chờ.\ufeff", ["Cha chờ."]),
    ("Cha chờ.\u0085Con về.", ["Cha chờ.\u0085Con về."]),
    ("Cha chờ.\u001cCon về.", ["Cha chờ.\u001cCon về."]),
])
def test_card_quotes_use_browser_whitespace_rules(text, expected):
    assert [text[a:b] for a, b in card_spans(text)] == expected


def test_saved_answers_do_not_take_current_question_numbers():
    draft, previous, author = context_fixture()
    author["clarifications"][0]["input_index"] = None
    author["clarifications"][1]["input_index"] = 0
    decisions = review_context(draft, previous, author, True)["decisions"]
    assert decisions[-2]["label"] == "Lựa chọn đã lưu"
    assert decisions[-1]["label"] == "Làm rõ 1"


def test_provider_schema_limits_focus_sources_neighbor_and_disables_film_scores():
    context = review_context(*context_fixture(), True)
    model = _card_review_schema(context)
    data = {"reviews": [{"card_id": "section-3-part-1", "decision_id": "answer-1",
            "related_card_id": "section-3", "observation": "Đối chiếu hai card.",
            "comparison": "aligned", "suggestion": ""}], "passed": True, "rubric_scores": None}
    assert model.model_validate(data).reviews[0].card_id == "section-3-part-1"
    for field, value in [("card_id", "section-1"), ("decision_id", "invented"), ("related_card_id", None)]:
        invalid = deepcopy(data)
        invalid["reviews"][0][field] = value
        with pytest.raises(ValidationError):
            model.model_validate(invalid)
    with pytest.raises(ValidationError):
        model.model_validate(data | {"rubric_scores": dict.fromkeys([
            "story_clarity", "character", "conflict", "emotional_impact", "ending", "production_feasibility"], 4)})


def test_card_soft_limit_counts_utf16_like_browser_and_handles_deletion():
    text = "Một cử chỉ 👩‍👦 rất nhỏ ".__mul__(30) + "khép lại."
    assert len(card_spans(text)) > 1
    assert all(len(text[a:b].encode("utf-16-le")) <= 400 for a, b in card_spans(text))
    draft, previous, author = context_fixture()
    draft["sections"][3]["content"] = "Cha bắt máy. "
    assert review_context(draft, previous, author, True)["focus_card_ids"] == ["section-3"]


def test_findings_pair_real_card_and_answer_with_exact_server_evidence():
    context = review_context(*context_fixture(), True)
    review = CardReview(card_id="section-3-part-1", decision_id="answer-1",
                       related_card_id="section-3", comparison="mismatch",
                       observation="Hai card lặp sự kiện bắt máy, có thể làm điểm dừng thiếu rõ ràng.",
                       suggestion="Gộp sự kiện bắt máy vào một card, giữ cử chỉ buông tay.")
    strengths, weaknesses, suggestions, clarifications = feedback_messages([review], context)
    assert not clarifications
    assert not strengths
    assert "Anh thôi bấu mép bàn" in weaknesses[0]
    assert "Card 4 · Kết thúc · 1: “Cha bắt máy.”" in weaknesses[0]
    assert "Làm rõ 2: “Chỉ hành động trong phòng; dừng khi vừa bắt máy.”" in weaknesses[0]
    assert len(weaknesses) == len(suggestions) == 1


def test_review_can_target_neighbor_while_preserving_valid_edited_card():
    context = review_context(*context_fixture(), True)
    data = dict(card_id="section-3", related_card_id="section-3-part-1", decision_id="answer-1",
                comparison="mismatch", observation="Card trước chưa khớp cách kể đã chọn.",
                suggestion="Sửa card trước, giữ cử chỉ trong card mới.")
    parsed = _card_review_schema(context).model_validate(dict(reviews=[data], passed=False, rubric_scores=None))
    _, issues, steps, _ = feedback_messages(parsed.reviews, context)
    assert issues[0].startswith("Card 4")
    assert steps[0].startswith("Card 4")
    with pytest.raises(ValidationError):
        _card_review_schema(context).model_validate(dict(reviews=[data, data], passed=False, rubric_scores=None))


def test_dataset_corrections_keep_recorded_review_count_and_source_enums():
    from app.application.dataset_corrections import validate_corrections
    context = review_context(*context_fixture(), True)
    schema = _card_review_schema(context).model_json_schema()
    schema["properties"]["reviews"]["maxItems"] = 3
    schema["$defs"]["FocusedCardReview"]["properties"]["card_id"] = {"const": "section-3-part-1"}
    data = dict(reviews=[dict(card_id="section-3-part-1", related_card_id="section-3", decision_id="answer-1",
        observation="Một đối chiếu.", comparison="aligned", suggestion="")], passed=True, rubric_scores=None)
    data["reviews"] *= 2
    step = dict(stage="evaluation", status="completed", output={}, request=dict(response_schema=schema,
        input_text="Card review context (JSON data):\n" + json.dumps(context, ensure_ascii=False)))
    sample = dict(status="completed", steps=[step])
    assert len(validate_corrections(sample, {"0": data})["0"]["reviews"]) == 2
    schema["properties"]["reviews"]["maxItems"] = 1
    with pytest.raises(ValueError):
        validate_corrections(sample, {"0": data})
    schema["properties"]["reviews"]["maxItems"] = 3
    changed = deepcopy(data)
    changed["reviews"][0].update(card_id="section-3", related_card_id="section-3-part-1")
    with pytest.raises(ValueError):
        validate_corrections(sample, {"0": changed})


@pytest.mark.parametrize("change", [
    {"card_id": "invented"}, {"decision_id": "answer-99"}, {"related_card_id": "invented"},
    {"card_id": "section-1"}, {"decision_id": "idea"}, {"suggestion": ""}, {"related_card_id": None},
    {"related_card_id": "section-3-part-1"},
    {"comparison": "aligned"},
])
def test_rejects_invented_sources_skipped_edit_and_unsupported_issue(change):
    context = review_context(*context_fixture(), True)
    data = dict(card_id="section-3-part-1", decision_id="answer-1", related_card_id="section-3",
                comparison="mismatch", observation="Một vấn đề.", suggestion="Một bước sửa.")
    with pytest.raises(MalformedProviderResponseError):
        feedback_messages([CardReview(**(data | change))], context)


def test_project_review_uses_latest_answer_and_changed_card_keeps_contract(project_client):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["answers"][0] = "Mới nhất: không cãi vã, chỉ ngại mở lời."
    data["draft"]["sections"][-1]["content"] = "Anh thôi bấu mép bàn; dừng khi bắt máy."
    saved = client.put(url, json=data).json()
    response = client.post(url + "/review", json={"revision": saved["revision"]})
    assert response.status_code == 200, response.text
    reviewed = response.json()
    request = provider.requests[-1]
    context = json.JSONDecoder().raw_decode(request.input_text.split("Card review context (JSON data):\n", 1)[1])[0]
    assert context["focus_card_ids"] == [f"section-{len(data['draft']['sections']) - 1}"]
    assert context["decisions"][-2]["text"] == data["answers"][0]
    assert reviewed["feedback_is_current"]
    assert reviewed["draft"] == saved["draft"]
    assert reviewed["answers"] == saved["answers"]
    assert reviewed["feedback_source"]["context"] == reviewed["author_context"]
    assert set(reviewed["feedback"]) == set(project["feedback"])
    assert all("card_id" not in finding for finding in reviewed["feedback"]["findings"])
    repeated = client.post(url + "/review", json={"revision": reviewed["revision"]})
    assert repeated.status_code == 200
    again = json.JSONDecoder().raw_decode(provider.requests[-1].input_text.split("Card review context (JSON data):\n", 1)[1])[0]
    assert again["focus_card_ids"] == context["focus_card_ids"]
    assert repeated.json()["draft"] == reviewed["draft"]


def test_structured_priorities_keep_pairs_and_exact_sources():
    from app.application.revision_review import revision_notes
    draft, _, author = context_fixture()
    # Duplicate titles and identical text still have distinct snapshot-local IDs.
    draft['sections'][2] = deepcopy(draft['sections'][1])
    context = review_context(draft, None, author, True)
    reviews = [CardReview(card_id=key, related_card_id=None, decision_id='answer-1',
        comparison='mismatch', observation=f'Problem {i}', suggestion=f'Next step {i}')
        for i, key in enumerate(['section-1', 'section-2', 'draft-logline'])]
    notes = revision_notes(reviews, context, 'f1')
    assert [(n.observation, n.suggestion) for n in notes] == [
        ('Problem 0', 'Next step 0'), ('Problem 1', 'Next step 1'), ('Problem 2', 'Next step 2')]
    assert [n.targets[0].target_id for n in notes] == ['section-1', 'section-2', 'draft-logline']
    assert all(n.artifact_id == 'f1' and n.decision_question == 'Kết?' for n in notes)
    assert notes[0].targets[0].quote == notes[1].targets[0].quote == 'Anh nhìn điện thoại.'


def issue_provider(provider, monkeypatch):
    original = provider.request_structured

    def with_issue(request):
        result = original(request)
        if request.response_model.__name__ == '_RevisionReviewOutput':
            result.output.reviews[0].comparison = 'mismatch'
            result.output.reviews[0].observation = 'This detail conflicts with the stated stopping point.'
            result.output.reviews[0].suggestion = 'End on the chosen gesture.'
        return result
    monkeypatch.setattr(provider, 'request_structured', with_issue)


def test_initial_and_manual_feedback_persist_the_same_structured_contract(project_client, monkeypatch):
    client, provider = project_client
    issue_provider(provider, monkeypatch)
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    initial = deepcopy(project['feedback'])
    assert len(initial['revision_notes']) == 1
    note = initial['revision_notes'][0]
    assert note['artifact_id'] == initial['artifact_id']
    assert note['suggestion'] == 'End on the chosen gesture.'
    assert project['feedback_source'] is not None
    assert project['plan_generations'][-1]['feedback'] == initial
    assert client.get(url).json() == project
    data = payload(project)
    data['draft']['logline'] = 'The writer changes the logline.'
    saved = client.put(url, json=data).json()
    response = client.post(url + '/review', json={'revision': saved['revision']})
    assert response.status_code == 200, response.text
    reviewed = response.json()
    latest = reviewed['feedback']['revision_notes'][0]
    assert latest['targets'] == [{'target_id': 'draft-logline', 'quote': data['draft']['logline']}]
    assert latest['artifact_id'] != note['artifact_id']
    assert reviewed['feedback_source']['draft'] == data['draft']
    assert any(v['feedback'] == initial for v in reviewed['versions'])
    assert client.get(url).json() == reviewed


@pytest.mark.parametrize('corruption', ['artifact', 'wrong-section', 'partial-pair', 'decision-question', 'duplicate-target', 'shape'])
def test_invalid_priority_metadata_is_read_only_without_losing_project(project_client, monkeypatch, corruption):
    client, provider = project_client
    issue_provider(provider, monkeypatch)
    project = develop_project(client, start_project(client))
    from app.api.routes.projects import get_project_store
    store = get_project_store()
    raw = store.get(project['id'])
    note = raw['feedback']['revision_notes'][0]
    if corruption == 'artifact':
        note['artifact_id'] = 'another-feedback'
    elif corruption == 'wrong-section':
        note['targets'][0]['target_id'] = 'draft-logline'
    elif corruption == 'partial-pair':
        note['targets'].append({'target_id': 'section-999', 'quote': 'invented'})
    elif corruption == 'decision-question':
        note['decision_question'] = 'A different question with the same answer'
    elif corruption == 'duplicate-target':
        note['targets'].append(deepcopy(note['targets'][0]))
    else:
        raw['feedback']['revision_notes'] = [{'broken': True}]
    stored = store.save(raw, project['revision'])
    reopened = client.get(f"/api/projects/{project['id']}").json()
    if corruption == 'shape':
        assert reopened['feedback']['revision_notes'] is None
    else:
        assert reopened['feedback_source'] is None
    assert reopened['draft'] == project['draft']
    assert reopened['answers'] == project['answers']
    assert reopened['feedback']['findings'] == project['feedback']['findings']
    assert store.get(project['id']) == stored, 'GET must never migrate stored notes'


@pytest.mark.parametrize('suggestion', ['', 'Bạn muốn dừng ở cuộc gọi hay sau đó?'])
def test_uncertain_is_neutral_and_keeps_exact_sources(suggestion):
    from app.application.workflow import _card_review_schema, revision_evaluation, _evaluation_findings
    from app.application.revision_review import revision_notes
    from app.api.schemas.story import EvaluationResponse
    draft, previous, author = context_fixture()
    original = deepcopy((draft, previous, author))
    context = review_context(draft, previous, author, True)
    review = _card_review_schema(context).model_validate(dict(reviews=[dict(
        card_id='section-3-part-1', related_card_id='section-3', decision_id='answer-1',
        comparison='uncertain', observation='Chưa đủ căn cứ để xác định điểm dừng có trái ý đồ.',
        suggestion=suggestion)], passed=True, rubric_scores=None))
    result = revision_evaluation(review, context)
    assert result.passed is None, 'Neither a confirmed violation nor a pass'
    assert not result.weaknesses and not result.strengths
    findings = _evaluation_findings(result, 'Vietnamese')
    assert any(f.criterion_id == 'clarification-1' and f.severity == 'info' for f in findings)
    assert not any(f.criterion_id.startswith('weakness-') for f in findings)
    notes = revision_notes(review.reviews, context, 'f1')
    feedback = EvaluationResponse(artifact_id='f1', passed=result.passed,
        findings=[f.__dict__ for f in findings], revision_notes=notes)
    assert feedback.revision_notes[0].suggestion == suggestion
    assert feedback.revision_notes[0].decision_quote == author['clarifications'][1]['answer']
    assert feedback.revision_notes[0].targets[0].quote == context['cards'][4]['text']
    assert (draft, previous, author) == original
    broken = feedback.model_dump()
    broken['revision_notes'][0]['comparison'] = 'mismatch'
    broken['revision_notes'][0]['suggestion'] = '   '
    assert EvaluationResponse.model_validate(broken).revision_notes is None
    # Uncertainty never bypasses anchor validation.
    review.reviews[0].card_id = 'invented'
    with pytest.raises(MalformedProviderResponseError):
        revision_evaluation(review, context)


@pytest.mark.parametrize('comparison, suggestion, expected', [
    ('aligned', '', True), ('uncertain', '', None),
    ('uncertain', 'Bạn có muốn làm rõ điểm dừng không?', None),
    ('mismatch', 'Cân nhắc bỏ phần vượt điểm dừng.', False),
])
def test_fake_provider_verdict_persists_without_changing_writer_data(
        project_client, monkeypatch, comparison, suggestion, expected):
    client, provider = project_client
    original = provider.request_structured

    def respond(request):
        result = original(request)
        if request.stage == 'evaluation' and hasattr(result.output, 'reviews'):
            result.output.reviews[0].comparison = comparison
            result.output.reviews[0].suggestion = suggestion
            result.output.reviews[0].observation = 'Đối chiếu giới hạn và điểm dừng trong nguồn.'
            result.output.passed = expected is not True  # Ignore the model's aggregate verdict.
        return result

    monkeypatch.setattr(provider, 'request_structured', respond)
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    assert project['feedback']['passed'] is expected
    assert project['plan_generations'][-1]['critic_status'] == 'reviewed'
    assert project['plan_generations'][-1]['feedback'] == project['feedback']
    changed = payload(project)
    changed['draft']['logline'] = 'Bản sửa thủ công phải được giữ.'
    saved = client.put(url, json=changed).json()
    assert not saved['feedback_is_current']
    assert saved['feedback'] == project['feedback']
    response = client.post(url + '/review', json={'revision': saved['revision']})
    assert response.status_code == 200, response.text
    reviewed = response.json()
    assert reviewed['feedback']['passed'] is expected
    assert reviewed['feedback_is_current']
    assert reviewed['feedback_source']['draft'] == saved['draft']
    assert reviewed['feedback_source']['context'] == saved['author_context']
    assert reviewed['feedback']['artifact_id'] != project['feedback']['artifact_id']
    for key in ['draft', 'answers', 'constraints', 'idea']:
        assert reviewed[key] == saved[key]
    assert client.get(url).json() == reviewed
    assert client.put(url, json=payload(saved)).status_code == 409
    assert client.get(url).json() == reviewed
    if comparison == 'uncertain':
        assert reviewed['feedback']['revision_notes'][0]['suggestion'] == suggestion
        assert all(f['severity'] == 'info' for f in reviewed['feedback']['findings'])
        assert not any(f['criterion_id'].startswith('weakness-') for f in reviewed['feedback']['findings'])
    # GET leaves the historical verdict and source intact too.
    assert any(v['feedback'] == project['feedback'] for v in reviewed['versions'])


def test_mixed_review_keeps_uncertainty_separate_without_hiding_violation():
    from app.application.workflow import _RevisionReviewOutput, revision_evaluation
    context = review_context(*context_fixture(), True)
    common = dict(card_id='section-3-part-1', related_card_id='section-3', decision_id='answer-1')
    review = _RevisionReviewOutput(reviews=[
        CardReview(**common, comparison='uncertain', observation='Chưa rõ.', suggestion=''),
        CardReview(**common, comparison='mismatch', observation='Vượt điểm dừng.', suggestion='Cân nhắc bỏ phần sau điểm dừng.'),
    ], passed=True, rubric_scores=None)
    result = revision_evaluation(review, context)
    assert result.passed is False
    assert len(result.weaknesses) == len(result.clarifications) == len(result.suggestions) == 1


def test_old_uncertain_feedback_is_read_without_regrading_or_migration(project_client, monkeypatch):
    client, provider = project_client
    issue_provider(provider, monkeypatch)
    project = develop_project(client, start_project(client))
    from app.api.routes.projects import get_project_store
    store = get_project_store()
    raw = store.get(project['id'])
    raw['feedback']['revision_notes'][0]['comparison'] = 'uncertain'
    # Older uncertain output was stored as failed with weakness findings.
    assert raw['feedback']['passed'] is False
    stored = store.save(raw, project['revision'])
    calls = len(provider.requests)
    reopened = client.get(f"/api/projects/{project['id']}").json()
    assert reopened['feedback'] == stored['feedback']
    assert reopened['feedback_source'] == stored['feedback_source']
    assert reopened['feedback']['revision_notes'][0]['suggestion']
    assert store.get(project['id']) == stored
    assert len(provider.requests) == calls
