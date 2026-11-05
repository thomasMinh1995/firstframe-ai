"""Bounded API comparison for Task 2; synthetic snapshots, no model retries."""
import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from time import monotonic

root = Path(os.environ.get('TASK2_SOURCE_ROOT', Path(__file__).resolve().parents[3]))
evidence = Path(__file__).resolve().parent
sys.path.insert(0, str(root / 'backend'))
os.environ.update(AI_PROVIDER='ollama', OLLAMA_MODEL='qwen2.5:7b', TEMPERATURE='0.3',
                  OLLAMA_CONTEXT_LENGTH='16384', OLLAMA_TIMEOUT_SECONDS='180',
                  DATASET_DIR=tempfile.mkdtemp(prefix='firstframe-task2-context-dataset-'))
from fastapi.testclient import TestClient
from app.api.routes import projects
from app.api.schemas.projects import ProjectResponse
from app.application import workflow
from app.application.project_store import ProjectStore
from app.infrastructure.ollama_provider import OllamaProvider
from app.main import create_app

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
config = json.loads((evidence / 'cases.json').read_text())
case = next(c for c in config['cases'] if c['id'] == args.case)
out = evidence / args.output
out.mkdir(exist_ok=False)

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

archive = root / 'docs/evaluations/task2-story-quality-2026-11-04/raw-evidence.tar.gz'
with tarfile.open(archive) as stored:
    project = json.load(stored.extractfile(case['source']))
if 'idea' in case:
    for key in ('idea', 'constraints', 'clarifications'):
        project[key] = case[key]
    project.update(analysis=None, answers=[], feedback=None, feedback_source=None,
                   versions=[], plan_generations=[])
    project['draft'] = dict(title=case['id'], logline=case['idea'], sections=case['sections'])
project.update(case.get('overrides', {}))
if 'ending' in case:
    next(s for s in project['draft']['sections'] if s['title'] == 'Ending')['content'] = case['ending']
project = ProjectResponse.model_validate(project).model_dump(mode='json', exclude_computed_fields=True)
save(out / 'source.json', project)
provider = OllamaProvider.from_env()
ledger = evidence / 'calls.json'
calls = json.loads(ledger.read_text()) if ledger.exists() else []

class Measured:
    metadata = provider.metadata

    def request_structured(self, request):
        context = json.loads(request.input_text.split('Card review context (JSON data):\n', 1)[1])
        if case.get('focus_section'):
            focus = [c for c in context['cards'] if c['id'] in context['focus_card_ids']]
            assert focus and all(c['section'] == case['focus_section'] for c in focus)
        remaining = config['max_provider_seconds'] - sum(c['seconds'] for c in calls)
        if len(calls) >= config['max_calls'] or remaining <= 0:
            raise RuntimeError('Frozen budget exhausted; no retry.')
        request = replace(request, timeout_seconds=min(remaining, request.timeout_seconds or 180))
        save(out / 'request.json', dict(instructions=request.instructions, input_text=request.input_text,
             schema=request.response_model.model_json_schema(), timeout_seconds=request.timeout_seconds))
        record = dict(case=args.case, output=args.output, seconds=0)
        calls.append(record)
        save(ledger, calls)
        start = monotonic()
        print(json.dumps(dict(case=args.case, event='start')), flush=True)
        try:
            result = provider.request_structured(request)
            save(out / 'response.json', dict(raw_output=result.raw_output, model=result.model,
                 output=result.output.model_dump(mode='json')))
            return result
        except Exception as error:
            record['error'] = str(error)
            save(out / 'error.json', dict(error=str(error), raw_output=getattr(error, 'raw_output', None)))
            raise
        finally:
            record['seconds'] = round(monotonic() - start, 3)
            save(ledger, calls)
            print(json.dumps(record), flush=True)

save(out / 'profile.json', dict(source_root=str(root), commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
     provider=asdict(provider.metadata), cases_sha256=sha256((evidence/'cases.json').read_bytes()).hexdigest(),
     diff=subprocess.check_output(['git', 'diff'], cwd=root, text=True)))
store = ProjectStore(Path(tempfile.mkdtemp(prefix='firstframe-task2-context-db-')) / 'projects.sqlite3')
store.create(project)
projects.get_project_store = lambda: store
workflow.create_provider = lambda: Measured()
with TestClient(create_app()) as client:
    response = client.post('/api/projects/' + project['id'] + '/review', json={'revision': project['revision']})
    save(out / 'result.json', dict(http=response.status_code, project=response.json()))
    reopened = client.get('/api/projects/' + project['id']).json()
    save(out / 'reopened.json', reopened)
    assert reopened['draft'] == project['draft']
    if response.status_code != 200:
        assert reopened['feedback'] == project['feedback']
        assert reopened['feedback_source'] == project['feedback_source']
        raise SystemExit('Review rejected; saved draft/feedback preserved, no retry.')
    saved = response.json()
    assert saved['draft'] == project['draft']
    assert saved['feedback_source']['draft'] == project['draft']
    assert client.get('/api/projects/' + project['id']).json()['draft'] == project['draft']
