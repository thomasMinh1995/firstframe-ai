"""One synthetic live-model draft-to-PDF check, with isolated SQLite and evidence.

Run from backend with --output NEW_DIRECTORY. Never retries failed model calls.
"""
import argparse
import gzip
import json
import os
import sys
import subprocess
import tempfile
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--model', default='qwen2.5:7b')
parser.add_argument('--brief-source', type=Path, help='Saved result/candidate (.json or .json.gz) or brief; reuse only its synthetic idea and constraints')
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
data = Path(tempfile.mkdtemp(prefix='firstframe-live-draft-'))
os.environ.update(AI_PROVIDER='ollama', OLLAMA_MODEL=args.model,
                  OLLAMA_BASE_URL='http://127.0.0.1:11434',
                  OLLAMA_CONTEXT_LENGTH='16384', TEMPERATURE='0.3', DATASET_DIR=str(data/'dataset'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import create_app
from app.api.routes import projects, draft_runs, screenplays
from app.application import draft_workflow
from app.application.project_store import ProjectStore
from app.application.draft_run_store import DraftRunStore
from app.application.ai_provider import ProviderTimeoutError
from app.api.schemas.projects import ProjectResponse
from app.application.scene_count import scene_count_bounds

start = time.monotonic()
calls, progress = [], []
def save(name, value):
    (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
class Timed:
    def __init__(self, provider):
        self.provider, self.metadata = provider, provider.metadata
    def request_structured(self, request):
        if len(calls) >= 14 or time.monotonic()-start > 600:
            raise ProviderTimeoutError('QA budget reached; no more model calls')
        entry = dict(stage=request.stage, input_bytes=len(request.input_text.encode()),
                     instructions_bytes=len(request.instructions.encode()), timeout_seconds=request.timeout_seconds)
        calls.append(entry)
        save(f'request-{len(calls):02d}.json', dict(stage=request.stage, instructions=request.instructions,
            input_text=request.input_text, schema=request.response_model.model_json_schema()))
        began = time.monotonic()
        print(json.dumps({'stage': request.stage, 'event': 'start'}), flush=True)
        try:
            result = self.provider.request_structured(request)
            entry.update(model=result.model, output=result.output.model_dump(mode='json'))
            entry['raw_output'] = result.raw_output
            return result
        except Exception as error:
            entry['error'] = str(error)
            entry['raw_output'] = getattr(error, 'raw_output', None)
            entry['validation_error'] = str(error.__cause__) if error.__cause__ else None
            raise
        finally:
            entry['seconds'] = round(time.monotonic()-began, 3)
            save('calls.json', calls)
            print(json.dumps({'stage': request.stage, 'seconds': entry['seconds'], 'error': entry.get('error')}), flush=True)
class EvidenceStore(DraftRunStore):
    def change(self, project_id, run_id, fn):
        r = super().change(project_id, run_id, fn)
        state = dict(seconds=round(time.monotonic()-start, 3), status=r['status'], step=r['step'],
                     candidate_revision=r['candidate_revision'], progress_revision=r.get('progress_revision'),
                     workflow_items=r.get('workflow_items', []))
        if not progress or (state['candidate_revision'], state['progress_revision']) != (progress[-1]['candidate_revision'], progress[-1]['progress_revision']):
            progress.append(state); save('progress.json', progress)
        return r

projects.get_project_store = lambda: ProjectStore(data/'projects.sqlite3')
draft_runs.store = lambda: EvidenceStore(data/'projects.sqlite3')
providers = [Timed(p) for p in draft_runs.providers()]
draft_runs.providers = lambda: providers
draft_workflow.launch = lambda *values: draft_workflow.execute(*values)
profile = dict(model=args.model, context_length=16384, temperature=0.3,
               started_at=datetime.now(UTC).isoformat(), database=str(data/'projects.sqlite3'),
               providers=[asdict(p.metadata) for p in providers], max_calls=14, budget_seconds=600)
profile['application_revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[2], text=True).strip()
save('profile.json', profile)
report = {'checks': {}, 'http': {}}
brief = None
if args.brief_source:
    if args.brief_source.suffix == '.gz':
        with gzip.open(args.brief_source, 'rt', encoding='utf-8') as f: brief = json.load(f)
    else:
        brief = json.loads(args.brief_source.read_text(encoding='utf-8'))
    brief = brief.get('candidate', brief).get('project', brief.get('candidate', brief))
    profile['brief_source'] = str(args.brief_source)
    save('profile.json', profile)
with TestClient(create_app()) as client:
    p = client.post('/api/projects').json()
    base = f"/api/projects/{p['id']}"
    p = client.put(base, json=dict(revision=p['revision'], title='QA thật — Lá thư chưa mở',
        idea='Phim ngắn hai phút. Trong căn bếp chiều mưa, bố đưa Linh một lá thư trước khi cô rời quê. Hai người ngại nói lời chia tay. Linh nhận thư nhưng chưa mở. Kết ở cánh cửa, cô vẫn giữ quyền quyết định có đọc thư hay không.',
        constraints=['Tối đa hai cảnh, một căn bếp và ngưỡng cửa.', 'Chỉ hai nhân vật bố và Linh.', 'Giữ lá thư chưa mở; không hồi tưởng, không thuyết minh, không tự xác nhận hòa giải.'],
        answers=[], draft=None, response_language='vi')).json()
    if brief:
        p = client.put(base, json={**{k:p[k] for k in ('revision','title','answers','draft')}, 'idea':brief['idea'], 'constraints':brief['constraints'], 'response_language':'vi'}).json()
    save('brief.json', {k:p[k] for k in ('idea','constraints','response_language')})
    run_id = str(uuid4()); url = base+'/draft-runs/'+run_id
    response = client.post(base+'/draft-runs', json={'revision':p['revision'], 'request_id':run_id})
    report['http']['start'] = response.status_code
    r = client.get(url).json()
    if r['status'] == 'needs_input':
        c = client.get(url+'/candidate').json()
        response = client.post(url+'/continue', json={'candidate_revision':c['revision'], 'answers':['']*len(c['project']['answers'])})
        report['http']['continue'] = response.status_code
    r, c = client.get(url).json(), client.get(url+'/candidate').json()
    save('run.json', r)
    with gzip.open(out/'candidate.json.gz', 'wt', encoding='utf-8') as f: json.dump(c, f, ensure_ascii=False)
    script = c['project'].get('screenplay')
    report.update(project_id=p['id'], run_id=run_id, run_status=r['status'], review_error=r['review_error'],
                  scene_count=len(script['scenes']) if script else 0,
                  reviewed_scenes=len(c['project'].get('screenplay_reviews', [])))
    bounds = scene_count_bounds(ProjectResponse.model_validate(c['project']).author_context, draft_workflow.MAX_AUTO_SCENES)
    report['scene_count_bounds'] = list(bounds)
    report['checks'].update(ready=r['status']=='ready', review_completed=not r['review_error'] and any(i['kind']=='review' and i['status']=='completed' for i in r.get('workflow_items', [])),
        author_scene_limit=bool(script) and bounds[0]<=len(script['scenes'])<=bounds[1],
        all_scenes_written=bool(script) and all(s['blocks'] for s in script['scenes']))
    if script and any(s['blocks'] for s in script['scenes']) and r['status'] in ('ready', 'partial'):
        adopted = client.post(url+'/adopt', json={'revision':p['revision'], 'candidate_revision':c['revision']})
        report['http']['adopt'] = adopted.status_code
        if adopted.status_code == 200:
            p = adopted.json(); before = len(calls)
            def no_ai(): raise RuntimeError('AI disabled during selection/export verification')
            draft_runs.providers = projects.get_scene_provider = screenplays.get_screenplay_provider = no_ai
            selection_id = str(uuid4())
            selected = client.post(base+'/screenplay-selections', json={'revision':p['revision'], 'request_id':selection_id, 'source_version_id':'current'})
            report['http']['select'] = selected.status_code
            if selected.status_code == 200:
                selection = selected.json()['screenplay_selections'][-1]
                save('selection.json', selection)
                report['checks']['exact_selected_script'] = selection['screenplay']==p['screenplay']
                pdf = client.get(base+'/screenplay-selections/'+selection_id+'/pdf')
                report['http']['pdf'] = pdf.status_code
                if pdf.status_code == 200: (out/'screenplay.pdf').write_bytes(pdf.content)
                report['checks']['pdf_without_ai'] = pdf.status_code==200 and len(calls)==before
    report.update(total_seconds=round(time.monotonic()-start, 3), model_seconds=round(sum(c['seconds'] for c in calls),3), call_count=len(calls))
    report['technical_pass'] = all(report['checks'].values()) and report['http'].get('pdf')==200
    report['release_approved'] = False  # Independent content/device acceptance is a separate gate.
    save('report.json', report)
print(json.dumps(report, ensure_ascii=False), flush=True)
sys.exit(0 if report['technical_pass'] else 1)
