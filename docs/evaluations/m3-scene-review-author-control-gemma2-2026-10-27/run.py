"""Six approved local review calls on frozen compliant/violating pairs, no retries."""
import hashlib,json,os,sys,time,argparse
from pathlib import Path
from dataclasses import replace
from datetime import UTC,datetime
from uuid import uuid4
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT/'backend/.env')
from fastapi.testclient import TestClient
from app.api.routes import projects,screenplay_reviews
from app.api.schemas.projects import ProjectResponse,StoryDraft,ScreenplayReview
from app.api.schemas.screenplays import SceneReviewResult
from app.application.project_store import ProjectStore
from app.application.screenplay_review import PROMPT_VERSION,review_scene,review_sources
from app.infrastructure.ollama_provider import OllamaProvider
from app.main import create_app
from app.application.ai_provider import StructuredResult
import httpx
OUT=Path(__file__).resolve().parent;DATA=ROOT/'backend/.data/m3-scene-review-author-control-gemma2-2026-10-27'
os.environ['DATASET_DIR']=str(DATA/'datasets')
FILES=['backend/app/application/screenplay_review.py','backend/app/application/screenplay_context.py','backend/app/api/routes/screenplay_reviews.py','backend/app/api/routes/projects.py','backend/app/api/schemas/projects.py','backend/app/api/schemas/screenplays.py','backend/app/infrastructure/ollama_provider.py','backend/app/application/ai_provider.py','backend/app/application/project_store.py','domains/short-film/prompts/screenplay_review_prompt.md',str(Path(__file__).resolve().relative_to(ROOT))]
BASE=ROOT/'docs/evaluations/m3-scene-review-author-control-qwen7b-2026-10-27'

def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}
def provider():
    p=OllamaProvider.from_env();assert p.metadata.model=='qwen2.5:7b' and p._config.base_url in ('http://127.0.0.1:11434','http://localhost:11434')
    return OllamaProvider(replace(p._config,model='gemma2:9b-instruct-q4_K_M',timeout_seconds=60))
def payload(p):return {k:p[k] for k in ('revision','title','idea','constraints','answers','draft','response_language')}

def freeze():
    assert not (OUT/'manifest.json').exists(),'Already frozen'
    assert PROMPT_VERSION=='screenplay-review-v4-author-control'
    DATA.mkdir(parents=True,exist_ok=True);real=provider()
    baseline=json.loads((BASE/'manifest.json').read_text());inputs=json.loads((BASE/'inputs.json').read_text())
    assert len(inputs)==6 and real.metadata.parameters==baseline['parameters']
    assert SceneReviewResult.model_json_schema()==json.loads((BASE/'schema.json').read_text())
    for case in inputs:
        parsed=ProjectResponse.model_validate(case['project']);req=case['request']
        preview=ScreenplayReview(id=req['request_id'],created_at=parsed.updated_at,source_revision=parsed.revision,
            source_content=parsed.content_key(),source_screenplay=parsed.screenplay,source_outline=parsed.scene_outline,
            target_scene_id=req['target_scene_id'],instructions=req['instructions'],prompt_version=PROMPT_VERSION)
        preview.sources=review_sources(preview)
        class Probe:
            metadata=real.metadata
            def request_structured(self,request):
                self.request={'instructions':request.instructions,'input':json.loads(request.input_text),'schema':request.response_model.model_json_schema()}
                return StructuredResult(output=SceneReviewResult(notes=[]),model='preflight-no-model')
        probe=Probe();review_scene(preview,probe)
        assert probe.request==case['frozen_request'],'Prompt/input/schema changed from Qwen v4'
        case['frozen_request']=probe.request
    originals=json.loads((BASE/'inputs.json').read_text())
    assert [{k:v for k,v in c.items() if k!='frozen_request'} for c in inputs]==[{k:v for k,v in c.items() if k!='frozen_request'} for c in originals]
    tags=httpx.get('http://127.0.0.1:11434/api/tags',timeout=10,trust_env=False).json()
    model=next(m for m in tags['models'] if m['name']==real.metadata.model)
    assert model['digest']=='c20bec88025f3aefa420efd64dca0ee4abc8e36078d6b74b0f660cdcbd5d1982'
    dump(OUT/'model-info.json',model)
    dump(OUT/'ollama-ps-before.json',httpx.get('http://127.0.0.1:11434/api/ps',timeout=10,trust_env=False).json())
    dump(OUT/'inputs.json',inputs);dump(OUT/'schema.json',SceneReviewResult.model_json_schema())
    code_hashes=hashes()
    for name,h in code_hashes.items():
        destination=OUT/'source'/name;destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes((ROOT/name).read_bytes());assert hashlib.sha256(destination.read_bytes()).hexdigest()==h
    dump(OUT/'manifest.json',{'frozen_at':datetime.now(UTC).isoformat(),'maximum_calls':6,'timeout_seconds_per_call':60,'retry':False,
        'model':real.metadata.model,'digest':model['digest'],'parameters':real.metadata.parameters,'seed':'not exposed/sent by existing provider',
        'inputs_sha256':hashlib.sha256((OUT/'inputs.json').read_bytes()).hexdigest(),'schema_sha256':hashlib.sha256((OUT/'schema.json').read_bytes()).hexdigest(),
        'hashes':code_hashes,'baseline':str(BASE.relative_to(ROOT)),
        'baseline_hashes':{name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in ['inputs.json','schema.json','manifest.json','results.json','comparison.json']},
        'same_six_cases_project_request_expected':True,'change':'Gemma 2 9B only; identical v4 prompt/input/schema and requested temperature/context/timeout to saved Qwen v4; no runtime change'})
    print('FROZEN: same six cases/project/request/expected; Gemma digest frozen, same requested parameters/schema as Qwen v4; preflight fake only; 0 model calls',flush=True)

def run():
    m=json.loads((OUT/'manifest.json').read_text());assert hashes()==m['hashes']
    assert hashlib.sha256((OUT/'inputs.json').read_bytes()).hexdigest()==m['inputs_sha256']
    assert hashlib.sha256((OUT/'schema.json').read_bytes()).hexdigest()==m['schema_sha256']
    real=provider();assert real.metadata.parameters==m['parameters']
    model=next(x for x in httpx.get('http://127.0.0.1:11434/api/tags',timeout=10).json()['models'] if x['name']==m['model']);assert model['digest']==m['digest']
    with (OUT/'run-started.json').open('x') as f:json.dump({'at':datetime.now(UTC).isoformat()},f)
    store=ProjectStore(DATA/'run.sqlite3');projects.get_project_store=lambda:store;results=[]
    inputs=json.loads((OUT/'inputs.json').read_text());assert len(inputs)==6
    for case in inputs:
        folder=OUT/case['name'];folder.mkdir(exist_ok=False);calls=[]
        class Logged:
            metadata=real.metadata
            def request_structured(self,req):
                actual={'instructions':req.instructions,'input':json.loads(req.input_text),'schema':req.response_model.model_json_schema()}
                assert actual==case['frozen_request'] and not calls,'Changed input or retry';calls.append(req.stage);dump(folder/'request.json',actual)
                try:
                    r=real.request_structured(req);dump(folder/'raw-output.json',{'raw_output':r.raw_output,'output':r.output.model_dump(mode='json'),'model':r.model});return r
                except Exception as e:
                    dump(folder/'error.json',{'type':type(e).__name__,'message':str(e),'raw_output':getattr(e,'raw_output',None)});raise
        screenplay_reviews.get_review_provider=lambda:Logged()
        p=ProjectResponse.model_validate(case['project']);store.create(p.model_dump(exclude_computed_fields=True));client=TestClient(create_app(),raise_server_exceptions=False)
        started=time.monotonic();r=client.post(f'/api/projects/{p.id}/screenplay-reviews',json=case['request']);elapsed=time.monotonic()-started
        after=client.get(f'/api/projects/{p.id}').json();dump(folder/'project-after.json',after);assert after['screenplay']==case['project']['screenplay'] and after['scene_outline']==case['project']['scene_outline']
        review=after['screenplay_reviews'][-1];row={'name':case['name'],'pair':case['pair'],'variant':case['variant'],'status_code':r.status_code,'duration_seconds':round(elapsed,3),'model_calls':len(calls),'review_status':review['status'],'validated_notes':len(review['notes']),'error':review['error'],'response_error':r.text if r.status_code!=200 else None,'author_script_unchanged':True}
        results.append(row);dump(folder/'result.json',row);dump(OUT/'results.json',results);print(json.dumps(row,ensure_ascii=False),flush=True)
    dump(OUT/'ollama-ps-after.json',httpx.get('http://127.0.0.1:11434/api/ps',timeout=10,trust_env=False).json())
    assert sum(x['model_calls'] for x in results)<=6;print('DONE: all outputs/errors retained; no retries or automatic edits',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run']);args=parser.parse_args();freeze() if args.mode=='freeze' else run()
