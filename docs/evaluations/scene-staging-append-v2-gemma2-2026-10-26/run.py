"""Frozen local-only smoke run. No retries, no project database, no paid API."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from app.api.schemas.projects import SceneProposal
from app.api.schemas.scenes import SceneSuggestionResult, SingleSceneSuggestionResult
from app.application.scene_suggestions import PROMPT, suggest_scenes
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check():
    manifest = json.loads((HERE / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        assert sha((HERE / name).read_bytes()) == digest, name
    assert sha(PROMPT.read_bytes()) == manifest['prompt_sha256'], 'Runtime prompt changed'
    assert SceneSuggestionResult.model_json_schema() == json.loads((HERE / 'schema.json').read_text())
    assert sha((ROOT / 'backend/app/application/scene_suggestions.py').read_bytes()) == manifest['service_sha256']
    assert SingleSceneSuggestionResult.model_json_schema() == json.loads((HERE / 'single-schema.json').read_text())
    assert manifest['base_url'] == 'http://127.0.0.1:11434'
    return manifest


def worker(index):
    manifest = check()
    case = json.loads((HERE / 'inputs.json').read_text())[index]
    destination = HERE / 'results' / (case['id'] + '.json')
    result = {'id': case['id'], 'started_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'status': 'running', 'request_count': 0, 'http_status': None, 'raw_response': None,
              'output': None, 'error_type': None, 'error': None, 'events': []}
    started = time.monotonic()
    from app.application.progress import progress_listener
    from app.infrastructure import ollama_provider as transport
    original_post = transport.httpx.post
    def post(url, **kwargs):
        assert url == manifest['base_url'] + '/api/chat'
        result['request_count'] += 1
        assert result['request_count'] == 1
        result['http_request'] = kwargs['json']
        write(destination, result)
        response = original_post(url, **kwargs)
        result['http_status'] = response.status_code
        result['raw_response_text'] = response.text
        try:
            result['raw_response'] = response.json()
        except ValueError:
            pass
        write(destination, result)
        return response
    transport.httpx.post = post
    token = progress_listener.set(lambda e: result['events'].append(e))
    write(destination, result)
    try:
        provider = OllamaProvider(OllamaProviderConfig(
            model=manifest['model'], base_url=manifest['base_url'],
            temperature=manifest['parameters']['temperature'], timeout_seconds=120,
            context_length=manifest['parameters']['num_ctx']))
        proposal = SceneProposal.model_validate(case['proposal'])
        output = suggest_scenes(proposal, provider)
        result['output'] = output.model_dump(mode='json')
        result['status'] = 'valid_proposal'
    except Exception as error:
        result.update(status='error', error_type=type(error).__name__, error=str(error),
                      error_raw_output=getattr(error, 'raw_output', None))
    finally:
        progress_listener.reset(token)
        result['duration_seconds'] = round(time.monotonic() - started, 3)
        write(destination, result)


def run():
    manifest = check()
    results = HERE / 'results'
    results.mkdir(exist_ok=False)  # Never replace or selectively retry an earlier run.
    cases = json.loads((HERE / 'inputs.json').read_text())
    assert len(cases) == 3
    for index, case in enumerate(cases):
        started = time.monotonic()
        path = results / (case['id'] + '.json')
        try:
            completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', str(index)],
                                       timeout=120, capture_output=True, text=True)
            if completed.returncode:
                record = json.loads(path.read_text()) if path.exists() else {'id': case['id']}
                record.update(status='worker_error', error_type='WorkerExit', stderr=completed.stderr)
                write(path, record)
        except subprocess.TimeoutExpired as error:
            record = json.loads(path.read_text()) if path.exists() else {'id': case['id']}
            record.update(status='error', error_type='HardDeadlineExceeded', error='120-second wall budget exceeded',
                          duration_seconds=round(time.monotonic() - started, 3))
            write(path, record)
        record = json.loads(path.read_text())
        print(json.dumps({k: record.get(k) for k in ('id', 'status', 'duration_seconds', 'error_type')}, ensure_ascii=False), flush=True)
    records = [json.loads((results / (c['id'] + '.json')).read_text()) for c in cases]
    write(HERE / 'results.json', records)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(int(sys.argv[2]))
    else:
        run()
