from copy import deepcopy
from uuid import uuid4

from test_projects import project_client, payload  # noqa: F401
from test_screenplays import prepare, start, edit, block
from app.api.routes import projects as routes
from app.api.schemas.projects import ScreenplayReview
from app.application.screenplay_review import review_sources
from app.api.schemas.provenance import TextProvenance


def autosave(p, session, **changes):
    return {**edit(p), "save_mode": "autosave", "edit_session_id": session,
            "save_id": str(uuid4()), **changes}


def test_autosave_coalesces_history_but_keeps_versions_and_exact_unicode(project_client):
    client, provider = project_client
    p = start(client, prepare(client)).json()
    url, session = f"/api/projects/{p['id']}", str(uuid4())
    baseline = deepcopy(p['screenplay'])
    history_count = len(p['screenplay_versions'])
    for text in ['  Một nét chỉ.  ', '  Con ga\u0301i nhìn.\n\nMẹ chờ.  ', 'Kết còn mở.']:
        body = autosave(p, session)
        body['screenplay']['scenes'][0]['blocks'] = [block(text=text)]
        response = client.put(url, json=body)
        assert response.status_code == 200, response.text
        p = response.json()
        assert p['screenplay']['scenes'][0]['blocks'][0]['text'] == text
        assert len(p['screenplay_versions']) == history_count + 1
        assert p['screenplay_versions'][-1]['screenplay'] == baseline
        assert p['last_save_id'] == body['save_id'] and p['last_save_revision'] == p['revision']
    assert p['screenplay']['version'] == baseline['version'] + 3
    assert client.get(url).json() == p
    # A new editing session gets its own restore point.
    before = deepcopy(p['screenplay'])
    body = autosave(p, str(uuid4()))
    body['screenplay']['scenes'][0]['blocks'][0]['text'] = 'Một phiên khác.'
    p = client.put(url, json=body).json()
    assert len(p['screenplay_versions']) == history_count + 2
    assert p['screenplay_versions'][-1]['screenplay'] == before


def test_save_id_replay_conflict_and_untrusted_metadata(project_client):
    client, _ = project_client
    p = start(client, prepare(client)).json()
    url = f"/api/projects/{p['id']}"
    body = autosave(p, str(uuid4()), title='Đã đổi tên')
    saved = client.put(url, json=body).json()
    assert client.put(url, json=body).json() == saved
    assert client.put(url, json={**body, 'title': 'Nội dung khác'}).status_code == 409
    assert client.put(url, json=autosave(p, str(uuid4()))).status_code == 409
    assert client.put(url, json={**edit(saved), 'save_mode': 'autosave'}).status_code == 422
    for field, value in [('edit_sessions', {}), ('draft_provenance', {}), ('last_save_id', str(uuid4()))]:
        assert client.put(url, json={**edit(saved), field: value}).status_code == 422
    forged = edit(saved)
    forged['scene_outline'] = {k: deepcopy(saved['scene_outline'][k]) for k in ('id', 'version', 'scenes')}
    forged['scene_outline']['provenance'] = {}
    assert client.put(url, json=forged).status_code == 422
    assert client.get(url).json() == saved
    # Omitted fields preserve data; explicit null is a different request even with the same save ID.
    legacy = {**payload(saved), 'save_id': str(uuid4())}
    preserved = client.put(url, json=legacy).json()
    assert client.put(url, json={**legacy, 'screenplay': None}).status_code == 409
    assert client.get(url).json()['screenplay'] == preserved['screenplay']


def test_manual_edit_origins_legacy_unknown_and_snapshot_persistence(project_client):
    client, _ = project_client
    p = start(client, prepare(client)).json()
    url = f"/api/projects/{p['id']}"
    body = edit(p)
    body['screenplay']['scenes'][0]['blocks'] = [block()]
    p = client.put(url, json=body).json()
    s = p['screenplay']['scenes'][0]
    assert p['screenplay']['provenance'][f"block:{s['blocks'][0]['id']}:text"]['origin'] == 'author_input'
    old = deepcopy(p['screenplay'])
    p = client.put(url, json={**payload(p), 'title': 'Client cũ'}).json()
    assert p['screenplay'] == old
    # Remove only provenance in a QA store to emulate a legacy snapshot.
    raw = routes.get_project_store().get(p['id'])
    raw['screenplay']['source_outline'].pop('provenance', None)
    raw['screenplay'].pop('provenance', None)
    routes.get_project_store().save(raw, raw['revision'])
    p = routes.load_project(p['id'])
    review = ScreenplayReview(id=str(uuid4()), created_at='now', source_revision=p.revision,
        source_content=p.content_key(), source_screenplay=p.screenplay, source_outline=p.scene_outline,
        target_scene_id=p.screenplay.scenes[0].id, prompt_version='test')
    sources = review_sources(review)
    legacy = next(s for s in sources if s.id.endswith(':action') and s.id.startswith('m2:'))
    assert legacy.provenance.origin == 'legacy_unknown' and legacy.category == 'context'
    assert next(s for s in sources if s.id == 'intent:idea').category == 'author_choice'


def test_ai_scene_remains_proposal_after_adoption_and_manual_fields_are_separate(project_client, monkeypatch):
    from test_scene_suggestions import SceneProvider
    from test_scene_outline import begin
    client, _ = project_client
    _, p = begin(client)
    url = f"/api/projects/{p['id']}"
    provider = SceneProvider()
    monkeypatch.setattr(routes, 'get_scene_provider', lambda: provider)
    result = client.post(url + '/scene-suggestions', json={'revision': p['revision'], 'request_id': str(uuid4()),
        'mode': 'list', 'instructions': '', 'target_scene_id': None})
    assert result.status_code == 200, result.text
    p = result.json()
    proposal = p['scene_proposals'][-1]
    body = {**payload(p), 'scene_outline': {k: deepcopy(p['scene_outline'][k]) for k in ('id', 'version', 'scenes')},
            'scene_proposal_id': proposal['id']}
    body['scene_outline']['scenes'] = proposal['scenes']
    p = client.put(url, json=body).json()
    s = p['scene_outline']['scenes'][0]
    key = f"m2:{s['id']}:action"
    assert p['scene_outline']['provenance'][key] == {'origin': 'ai_proposal', 'author_confirmed': False}
    body = {**payload(p), 'scene_outline': {k: deepcopy(p['scene_outline'][k]) for k in ('id', 'version', 'scenes')}}
    body['scene_outline']['scenes'][0]['location'] = 'Bếp của mẹ'
    p = client.put(url, json=body).json()
    assert p['scene_outline']['provenance'][key]['origin'] == 'ai_proposal'
    assert p['scene_outline']['provenance'][f"m2:{s['id']}:location"]['origin'] == 'author_input'
    p = start(client, p).json()
    script = routes.load_project(p['id']).screenplay
    review = ScreenplayReview(id=str(uuid4()), created_at='now', source_revision=p['revision'],
        source_content='test', source_screenplay=script, source_outline=script.source_outline,
        target_scene_id=script.scenes[0].id, prompt_version='test')
    sources = {s.id: s for s in review_sources(review)}
    assert sources[key].category == 'context'
    assert sources[f"m2:{s['id']}:location"].category == 'author_choice'


def test_ai_screenplay_adoption_keeps_origin_and_manual_preview_separate(project_client, monkeypatch):
    from test_screenplay_writing import WritingProvider, generate, adopt
    from app.api.routes import screenplays
    client, _ = project_client
    p = start(client, prepare(client)).json()
    provider = WritingProvider()
    monkeypatch.setattr(screenplays, 'get_screenplay_provider', lambda: provider)
    p = generate(client, p)[0].json()
    proposal = p['screenplay_proposals'][-1]
    preview = deepcopy(proposal['scene'])
    preview['blocks'][1]['text'] = '  Lời người viết tự chỉnh.  '
    url = f"/api/projects/{p['id']}"
    p = client.put(url, json={**payload(p), 'screenplay_proposal_previews': {proposal['id']: preview}}).json()
    p = client.put(url, json=adopt(p, p['screenplay_proposals'][-1])).json()
    scene = p['screenplay']['scenes'][0]
    origins = p['screenplay']['provenance']
    assert origins[f"block:{scene['blocks'][0]['id']}:text"] == {'origin': 'ai_proposal', 'author_confirmed': False}
    assert origins[f"block:{scene['blocks'][1]['id']}:text"]['origin'] == 'author_input'
    assert scene['blocks'][1]['text'] == preview['blocks'][1]['text']


def test_confirming_one_choice_does_not_confirm_entire_ai_scene():
    from app.application.provenance import attribute_edits
    fields = {'action': 'AI kể cảnh', 'blocking': 'Đứng bên cửa'}
    origins = {key: TextProvenance(origin='ai_proposal') for key in fields}
    confirmed = attribute_edits(origins, fields, fields, confirmed={'blocking'})
    assert confirmed['blocking'].origin == 'ai_proposal' and confirmed['blocking'].author_confirmed
    assert not confirmed['action'].is_author_choice


def test_staging_adoption_confirms_only_the_selected_field(project_client, monkeypatch):
    from test_scene_staging import Provider, generate, use_payload
    client, _ = project_client
    p = prepare(client)
    monkeypatch.setattr(routes, 'get_scene_provider', lambda: Provider())
    p = generate(client, p)[0].json()
    batch = p['staging_proposals'][-1]
    idea = batch['staging_ideas'][0]
    body = use_payload(p, batch, idea, idea['suggestion'])
    p = client.put(f"/api/projects/{p['id']}", json=body).json()
    key = f"m2:{batch['target_scene_id']}:staging:{idea['field']}"
    assert p['scene_outline']['provenance'][key] == {'origin':'ai_proposal', 'author_confirmed':True}
    assert all(not value['author_confirmed'] for field, value in p['scene_outline']['provenance'].items() if field != key)


def test_draft_autosave_keeps_restore_origin_and_whitespace(project_client):
    from test_projects import start_project, develop_project
    client, _ = project_client
    p = develop_project(client, start_project(client))
    url, session = f"/api/projects/{p['id']}", str(uuid4())
    original = deepcopy(p['draft'])
    count = len(p['versions'])
    for text in ['  Con ga\u0301i nhìn.\n\nChưa mở thư.  ', 'Một lần sửa tiếp.']:
        draft = deepcopy(p['draft'])
        draft['logline'] = text
        body = {**payload(p), 'draft': draft, 'save_mode': 'autosave', 'edit_session_id': session, 'save_id': str(uuid4())}
        p = client.put(url, json=body).json()
        assert p['draft']['logline'] == text and len(p['versions']) <= count + 1
        assert p['draft_provenance']['logline']['origin'] == 'author_input'
        assert p['draft_provenance']['title']['origin'] == 'ai_proposal'
    version = next(v for v in p['versions'] if v['draft'] == original)
    p = client.put(url, json={**payload(p), 'draft': version['draft'], 'restore_draft_id': version['id']}).json()
    assert p['draft'] == original
    assert p['draft_provenance'] == version['draft_provenance']
