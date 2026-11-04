"""Small, isolated Task 2 measurement. Explicit operations; no AI retries."""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time
from dataclasses import asdict
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root/'backend'))
os.environ.update(AI_PROVIDER='ollama', OLLAMA_MODEL='qwen2.5:7b', TEMPERATURE='0.3', OLLAMA_CONTEXT_LENGTH='16384', OLLAMA_TIMEOUT_SECONDS='180')
parser=argparse.ArgumentParser()
parser.add_argument('operation', choices=['plan','review','replay'])
parser.add_argument('--case', required=True)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--source', type=Path)
parser.add_argument('--edit', type=Path)
args=parser.parse_args()
args.output=args.output.resolve()
evidence=root/'docs/evaluations/task2-story-quality-2026-11-04'
args.output.mkdir(parents=True,exist_ok=False)
os.environ['DATASET_DIR']=tempfile.mkdtemp(prefix='firstframe-task2-datasets-')
from app.infrastructure.ollama_provider import OllamaProvider
from app.application import workflow
from app.application.ai_provider import StructuredRequest
from app.application.project_store import ProjectStore
from app.api.routes import projects
from app.main import create_app
from fastapi.testclient import TestClient

def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
case=next(c for c in json.loads((evidence/'cases.json').read_text())['cases'] if c['id']==args.case)
ledger_path=evidence/'calls.json'
calls=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
provider=OllamaProvider.from_env()
class Measured:
    metadata=provider.metadata
    def request_structured(self,request):
        if len(calls)>=32 or sum(c.get('seconds',0) for c in calls)>=1200:
            raise RuntimeError('Frozen Task 2 budget exhausted; do not retry.')
        record=dict(case=args.case,operation=args.operation,stage=request.stage,output=str(args.output.relative_to(evidence)),seconds=0)
        calls.append(record);save(ledger_path,calls)
        index=len(list(args.output.glob('request-*.json')))+1
        payload=dict(stage=request.stage,instructions=request.instructions,input_text=request.input_text,schema=request.response_model.model_json_schema())
        save(args.output/f'request-{index:02}.json',payload)
        started=time.monotonic()
        print(json.dumps(dict(case=args.case,stage=request.stage,event='start')),flush=True)
        try:
            result=provider.request_structured(request)
            save(args.output/f'response-{index:02}.json',dict(model=result.model,raw_output=result.raw_output,output=result.output.model_dump(mode='json')))
            return result
        except Exception as error:
            record['error']=str(error)
            save(args.output/f'error-{index:02}.json',dict(error=str(error),raw_output=getattr(error,'raw_output',None)))
            raise
        finally:
            record['seconds']=round(time.monotonic()-started,3);save(ledger_path,calls)
            print(json.dumps(record),flush=True)

save(args.output/'profile.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),provider=asdict(provider.metadata),case=args.case,operation=args.operation,fixtures_sha256=hashlib.sha256((evidence/'cases.json').read_bytes()).hexdigest(),diff=subprocess.check_output(['git','diff'],cwd=root,text=True)))
workflow.create_provider=lambda:Measured()
if args.operation=='replay':
    original=json.loads(args.source.read_text())
    stage=original['stage'];instructions=original['instructions']
    from app.application.prompt_loader import PromptLoader
    paths={'reasoning':'story_mentor_prompt.md','planning':'story_planner_prompt.md','evaluation':'card_review_vi_prompt.md'}
    name=paths[stage]
    current=(root/'domains/short-film/prompts'/name).read_text().strip()
    # Only instructions change; saved input/schema remain the same.
    suffix='\nUnanswered questions are intentionally left open.'
    if stage=='planning' and suffix in instructions:
        current+=suffix+instructions.split(suffix,1)[1]
    if stage=='evaluation':
        context=json.loads(original['input_text'].split('Card review context (JSON data):\n',1)[1])
        model=workflow._card_review_schema(context)
    else:
        model={'reasoning':workflow._ReasoningOutput,'planning':workflow._PlanningOutput}[stage]
    assert model.model_json_schema()==original['schema']
    result=Measured().request_structured(StructuredRequest(instructions=current,input_text=original['input_text'],response_model=model,stage=stage))
    if stage=='evaluation':
        workflow.revision_evaluation(result.output,context)
    save(args.output/'result.json',result.output.model_dump(mode='json'))
else:
    store=ProjectStore(Path(tempfile.mkdtemp(prefix='firstframe-task2-db-'))/'projects.sqlite3')
    projects.get_project_store=lambda:store
    with TestClient(create_app()) as client:
        if args.operation=='plan':
            p=client.post('/api/projects').json();url='/api/projects/'+p['id']
            body={k:p[k] for k in ('revision','title','idea','constraints','answers','draft')}
            p=client.put(url,json={**body,'idea':case['idea'],'constraints':case['constraints'],'response_language':'vi'}).json()
            for action in ('analyze','plan'):
                response=client.post(url+'/'+action,json={'revision':p['revision']})
                save(args.output/(action+'.json'),response.json())
                response.raise_for_status();p=response.json()
        else:
            p=json.loads(args.source.read_text())
            from app.api.schemas.projects import ProjectResponse
            store.create(ProjectResponse.model_validate(p).model_dump(mode='json',exclude_computed_fields=True))
            url='/api/projects/'+p['id'];edit=json.loads(args.edit.read_text())
            body={k:p[k] for k in ('revision','title','idea','constraints','answers','draft')}
            body['draft']['sections'][edit['section_index']]['content']=edit['text']
            response=client.put(url,json=body);response.raise_for_status();p=response.json()
            save(args.output/'edited.json',p)
            response=client.post(url+'/review',json={'revision':p['revision']});save(args.output/'review.json',response.json());response.raise_for_status()
            assert response.json()['draft']==p['draft']
        save(args.output/'project.json',response.json())
