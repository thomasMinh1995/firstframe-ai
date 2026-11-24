"""Real SQLite/filesystem recovery; synthetic providers and no user data."""
import json
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_projects import project_client as project_client, payload
from test_screenplay_selection import written as written, select
from test_scene_sketches import FakeImageProvider, generate, decide
from app.api.routes import projects, scene_sketches, draft_runs
from app.application import draft_workflow
from app.application.draft_run_store import DraftRunStore
from app.application.project_store import ProjectStore
from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_datasets(tmp_path, monkeypatch):
    monkeypatch.setenv('DATASET_DIR', str(tmp_path / 'datasets'))


def backup(source, destination):
    # Stop writers first: the DB and image tree must describe the same point in time.
    destination.mkdir()
    with sqlite3.connect(source / 'projects.sqlite3') as live:
        with sqlite3.connect(destination / 'projects.sqlite3') as snapshot:
            live.backup(snapshot)
            assert snapshot.execute('PRAGMA integrity_check').fetchone() == ('ok',)
    shutil.copytree(source / 'scene-images', destination / 'scene-images')


def test_main_database_opens_edits_and_restarts_without_losing_legacy_content(tmp_path, monkeypatch):
    fixture = json.loads((Path(__file__).parent / 'fixtures/project-main-9db2f6f.json').read_text())
    assert fixture['source_commit'] == '9db2f6f53bd980a43a8c9e15d6ef3c121524b581'
    raw = fixture['project']
    store = ProjectStore(tmp_path / 'legacy' / 'projects.sqlite3')
    store.path.parent.mkdir()
    with sqlite3.connect(store.path) as db:
        db.execute(fixture['schema'])
        db.execute('INSERT INTO projects VALUES (?, ?, ?)', (raw['id'], raw['revision'], json.dumps(raw, ensure_ascii=False)))
    monkeypatch.setattr(projects, 'get_project_store', lambda: store)
    with TestClient(create_app()) as client:
        url = '/api/projects/' + raw['id']
        opened = client.get(url)
        assert opened.status_code == 200, opened.text
        p = opened.json()
        assert store.get(raw['id']) == raw, 'Opening a legacy project must not rewrite its content'
        for key in ['idea', 'constraints', 'draft', 'versions', 'answers']:
            assert p[key] == raw[key]
        assert p['screenplay']['scenes'] == raw['screenplay']['scenes']
        assert p['scene_outline']['scenes'] == raw['scene_outline']['scenes']
        assert [v['screenplay']['scenes'] for v in p['screenplay_versions']] == [v['screenplay']['scenes'] for v in raw['screenplay_versions']]
        update = {**payload(p), 'title': 'Tên mới, giữ kịch bản cũ'}
        saved = client.put(url, json=update)
        assert saved.status_code == 200, saved.text
        saved = saved.json()
        assert saved['revision'] == raw['revision'] + 1
        assert saved['draft'] == raw['draft'] and saved['idea'] == raw['idea']
        assert saved['screenplay']['scenes'] == raw['screenplay']['scenes']
        assert saved['screenplay']['version'] == raw['screenplay']['version']
    with TestClient(create_app()) as restarted:
        assert restarted.get(url).json() == saved


def test_sqlite_and_images_restore_exactly_without_ai_or_original_directory(written, tmp_path, monkeypatch):
    client, provider, p = written
    image_provider = FakeImageProvider()
    monkeypatch.setattr(scene_sketches, 'get_image_provider', lambda: image_provider)
    response, request = generate(client, p)
    assert response.status_code == 200, response.text
    p = decide(client, response.json(), request['request_id'], 'keep').json()
    selected = select(client, p)[0]
    assert selected.status_code == 200, selected.text
    p = selected.json()
    source = projects.get_project_store().path.parent
    url = '/api/projects/' + p['id']
    # A pending run belongs to another process; restore must preserve it without resending.
    run_id = str(uuid4())
    store = DraftRunStore(source / 'projects.sqlite3')
    store.create_run(p['id'], run_id, p['revision'], {}, 'old-process')
    # A synthetic saved candidate checkpoint exercises non-empty restored content.
    checkpoint = projects.get_project_store().get(p['id'])
    store.change(p['id'], run_id, lambda r: r.update(candidate=checkpoint, candidate_revision=1))
    before_run = store.get_run(p['id'], run_id)
    original_image = client.get(f"{url}/scene-sketches/{request['request_id']}/image").content
    assert original_image == image_provider.data
    original_pdf = client.get(f"{url}/screenplay-selections/{p['screenplay_handoff']['id']}/pdf").content
    assert original_pdf.startswith(b'%PDF')
    snapshot = tmp_path / 'backup'
    backup(source, snapshot)
    with sqlite3.connect(snapshot / 'projects.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM draft_runs').fetchone() == (1,)
        assert db.execute('SELECT COUNT(*) FROM projects').fetchone()[0] >= 1
    # Writes after the backup must not leak into the restored snapshot.
    newer = client.put(url, json={**payload(p), 'title': 'Sau thời điểm backup'})
    assert newer.status_code == 200, newer.text
    asset = next((source / 'scene-images').rglob('*.png'))
    asset.write_bytes(b'corrupt original after backup')
    restored = tmp_path / 'restored'
    shutil.copytree(snapshot, restored)
    # Remove the original files to prove all reads use the restored copy.
    shutil.rmtree(source / 'scene-images')
    for path in source.glob('projects.sqlite3*'):
        path.unlink()
    monkeypatch.setattr(projects, 'get_project_store', lambda: ProjectStore(restored / 'projects.sqlite3'))
    calls = len(provider.requests), len(image_provider.requests)
    def no_ai(*args, **kwargs):
        raise AssertionError('Restore/restart/read/export must not invoke providers')
    monkeypatch.setattr(draft_runs, 'providers', no_ai)
    monkeypatch.setattr(draft_workflow, 'launch', no_ai)
    with TestClient(create_app()) as reopened:
        assert reopened.get(url).json() == p
        assert reopened.get(f"{url}/scene-sketches/{request['request_id']}/image").content == original_image
        assert reopened.get(f"{url}/screenplay-selections/{p['screenplay_handoff']['id']}/pdf").content == original_pdf
        recovered = DraftRunStore(restored / 'projects.sqlite3').get_run(p['id'], run_id)
        assert recovered['status'] == 'interrupted'
        for key in ['candidate', 'candidate_revision', 'original', 'source_content', 'calls']:
            assert recovered[key] == before_run[key]
        assert reopened.get(f'{url}/draft-runs/{run_id}').json()['status'] == 'interrupted'
    assert (len(provider.requests), len(image_provider.requests)) == calls
    with sqlite3.connect(restored / 'projects.sqlite3') as db:
        assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
