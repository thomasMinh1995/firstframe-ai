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
OUT=Path(__file__).resolve().parent;DATA=ROOT/'backend/.data/m3-scene-review-qwen7b-2026-10-27'
os.environ['DATASET_DIR']=str(DATA/'datasets')
FILES=['backend/app/application/screenplay_review.py','backend/app/application/screenplay_context.py','backend/app/api/routes/screenplay_reviews.py','backend/app/api/routes/projects.py','backend/app/api/schemas/projects.py','backend/app/api/schemas/screenplays.py','backend/app/infrastructure/ollama_provider.py','backend/app/application/ai_provider.py','backend/app/application/project_store.py','domains/short-film/prompts/screenplay_review_prompt.md',str(Path(__file__).resolve().relative_to(ROOT))]
CASES=[
 {'name':'open-ending','title':'Lá thư','idea':'Cha xin lỗi; con gái ở lại nhưng chưa nói đã tha thứ.',
  'constraints':['Chỉ cha và con gái.','Kết mở; con gái không nói hoặc xác nhận đã tha thứ, không chốt hòa giải.','Lá thư vẫn kín.'],
  'previous':'Cha đặt phong thư kín lên bàn rồi lùi lại.',
  'action':'Con gái nhìn cha, kéo ghế ngồi. Phong thư còn kín trên bàn.',
  'source':'Con gái ở lại, giữ khoảng lặng và chưa khẳng định đã tha thứ. Dừng ở kết mở.',
  'kind':'dialogue','speaker':'Con gái','compliant':'Cha…','violating':'Con tha thứ cho cha. Mọi chuyện đã được giải quyết.',
  'expected':'Bản vi phạm chốt tha thứ/hòa giải trái lựa chọn kết mở; góp ý cần dẫn câu thoại và quyết định nguồn. Không buộc bản tuân thủ thêm câu tha thứ.'},
 {'name':'free-choice','title':'Lối đi','idea':'Người cha xin lỗi và để con gái tự quyết định ở lại hay ra đi.',
  'constraints':['Chỉ cha và con gái trong nhà.','Cha không giữ giấy tờ hoặc ép con gái ở lại.','Con gái tự quyết định việc ra đi.'],
  'previous':'Con gái đặt túi cạnh cửa. Cha đứng bên bàn.',
  'action':'Con gái nhìn về cửa, chưa bước đi.',
  'source':'Cha đặt lá thư xin lỗi lên bàn, lùi lại và để lối đi trống; con gái tự quyết định.',
  'kind':'action','speaker':'','compliant':'Cha đặt lá thư xin lỗi lên bàn, lùi lại để lối đi trống.',
  'violating':'Cha giấu hộ chiếu của con gái vào túi để cô không thể ra đi.',
  'expected':'Bản vi phạm giữ giấy tờ/ép ở lại; dẫn đúng hành động và lựa chọn tự quyết. Không khuyên bản tuân thủ giấu hộ chiếu hoặc chặn cửa.'},
 {'name':'broken-flashlight','title':'Đọc giấy','idea':'Lan và Bình đọc giấy nhờ ánh đèn đường trong phòng trọ mất điện.',
  'constraints':['Chỉ Lan và Bình, một phòng trọ ban đêm.','Đèn pin bị hỏng, không thể sáng.','Không thêm điện thoại hoặc nguồn sáng mới; dùng ánh đèn đường qua rèm.'],
  'previous':'Lan đặt tờ giấy lên bàn gần cửa sổ có rèm. Bình cầm chiếc đèn pin hỏng.',
  'action':'Lan kéo rèm, để ánh đèn đường rọi lên tờ giấy.',
  'source':'Bình đặt đèn pin hỏng xuống. Lan kéo rèm; hai người nghiêng giấy để đọc bằng ánh đèn đường.',
  'kind':'action','speaker':'','compliant':'Bình đặt đèn pin hỏng xuống, nghiêng tờ giấy về phía ánh đèn đường.',
  'violating':'Bình bật chiếc đèn pin hỏng; đèn sáng rực, rọi rõ tờ giấy.',
  'expected':'Bản vi phạm làm đèn pin hỏng sáng; dẫn hành động và giới hạn. Không buộc bản tuân thủ bật đèn hoặc thêm điện thoại.'}
]

def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}
def provider():
    p=OllamaProvider.from_env();assert p.metadata.model=='qwen2.5:7b' and p._config.base_url in ('http://127.0.0.1:11434','http://localhost:11434')
    return OllamaProvider(replace(p._config,timeout_seconds=60))
def payload(p):return {k:p[k] for k in ('revision','title','idea','constraints','answers','draft','response_language')}

def freeze():
    assert not (OUT/'manifest.json').exists(),'Already frozen'
    DATA.mkdir(parents=True,exist_ok=True);store=ProjectStore(DATA/'freeze.sqlite3');projects.get_project_store=lambda:store
    client=TestClient(create_app());inputs=[];real=provider()
    for case in CASES:
        p=ProjectResponse(id=str(uuid4()),updated_at=datetime.now(UTC).isoformat(),title=case['title'],response_language='vi',idea=case['idea'],constraints=case['constraints'],draft=StoryDraft(title=case['title'],logline=case['idea'],sections=[{'title':'Đầu','purpose':'Mở','content':case['previous']},{'title':'Cuối','purpose':'Diễn tiến','content':case['source']}]))
        store.create(p.model_dump(exclude_computed_fields=True));url=f'/api/projects/{p.id}'
        r=client.post(url+'/scene-outline',json={'revision':p.revision,'source_version_id':'current'});assert r.status_code==200,r.text;p=r.json()
        scenes=[{'id':str(uuid4()),'title':title,'action':text} for title,text in [('Trước đó',case['previous']),('Khoảnh khắc',case['source'])]]
        r=client.put(url,json={**payload(p),'scene_outline':{'id':p['scene_outline']['id'],'version':p['scene_outline']['version'],'scenes':scenes}});assert r.status_code==200,r.text;p=r.json()
        r=client.post(url+'/screenplay',json={'revision':p['revision'],'request_id':str(uuid4())});assert r.status_code==200,r.text;p=r.json()
        p['screenplay']['scenes'][0]['blocks']=[{'id':str(uuid4()),'kind':'action','text':case['previous'],'speaker':''}]
        p['screenplay']['scenes'][1]['blocks']=[{'id':str(uuid4()),'kind':'action','text':case['action'],'speaker':''},{'id':str(uuid4()),'kind':case['kind'],'text':case['compliant'],'speaker':case['speaker']}]
        r=client.put(url,json={**payload(p),'screenplay':{k:p['screenplay'][k] for k in ('id','version','scenes')}});assert r.status_code==200,r.text;base=r.json()
        for variant in ('compliant','violating'):
            p=deepcopy(base);p['id']=str(uuid4());p['screenplay']['scenes'][1]['blocks'][1]['text']=case[variant]
            parsed=ProjectResponse.model_validate(p);request={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':p['screenplay']['scenes'][1]['id'],'instructions':'Chỉ nêu góp ý có bằng chứng về cảnh này; tác giả tự sửa.'}
            preview=ScreenplayReview(id=request['request_id'],created_at=p['updated_at'],source_revision=p['revision'],source_content=parsed.content_key(),source_screenplay=parsed.screenplay,source_outline=parsed.scene_outline,target_scene_id=request['target_scene_id'],instructions=request['instructions'],prompt_version=PROMPT_VERSION)
            preview.sources=review_sources(preview)
            class Probe:
                metadata=real.metadata
                def request_structured(self,req):
                    self.request={'instructions':req.instructions,'input':json.loads(req.input_text),'schema':req.response_model.model_json_schema()}
                    return StructuredResult(output=SceneReviewResult(notes=[]),model='preflight-no-model')
            probe=Probe();review_scene(preview,probe)
            inputs.append({'name':case['name']+'-'+variant,'pair':case['name'],'variant':variant,'project':p,'request':request,'expected':case['expected'],'frozen_request':probe.request})
    tags=httpx.get('http://127.0.0.1:11434/api/tags',timeout=10).json();model=next(m for m in tags['models'] if m['name']==real.metadata.model)
    dump(OUT/'inputs.json',inputs);dump(OUT/'schema.json',SceneReviewResult.model_json_schema())
    dump(OUT/'manifest.json',{'frozen_at':datetime.now(UTC).isoformat(),'maximum_calls':6,'timeout_seconds_per_call':60,'retry':False,'model':real.metadata.model,'digest':model['digest'],'parameters':real.metadata.parameters,'inputs_sha256':hashlib.sha256((OUT/'inputs.json').read_bytes()).hexdigest(),'schema_sha256':hashlib.sha256((OUT/'schema.json').read_bytes()).hexdigest(),'hashes':hashes()})
    print('FROZEN: 3 pairs / 6 reviews; all request budgets checked with fake provider; 0 model calls',flush=True)

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
    assert sum(x['model_calls'] for x in results)<=6;print('DONE: all outputs/errors retained; no retries or automatic edits',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run']);args=parser.parse_args();freeze() if args.mode=='freeze' else run()
