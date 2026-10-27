"""Three approved local calls only. Freeze first; never overwrites a run or retries."""
import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import replace
from datetime import UTC,datetime
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT/'backend/.env')
from fastapi.testclient import TestClient
from app.api.routes import projects,screenplays
from app.api.schemas.projects import ProjectResponse,StoryDraft
from app.api.schemas.screenplays import SceneWritingResult
from app.application.project_store import ProjectStore
from app.infrastructure.ollama_provider import OllamaProvider
from app.main import create_app
import httpx

OUT=Path(__file__).resolve().parent
DATA=ROOT/'backend/.data/m3-scene-writing-qwen7b-2026-10-27'
os.environ['DATASET_DIR']=str(DATA/'datasets')
FILES=['backend/app/application/screenplay_writing.py','backend/app/api/routes/screenplays.py',
       'backend/app/api/routes/projects.py','backend/app/api/schemas/projects.py','backend/app/api/schemas/screenplays.py',
       'backend/app/infrastructure/ollama_provider.py','backend/app/application/ai_provider.py',
       'backend/app/application/project_store.py','domains/short-film/prompts/screenplay_scene_prompt.md',str(Path(__file__).resolve().relative_to(ROOT))]

def dump(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}

def provider():
    configured=OllamaProvider.from_env()
    assert configured.metadata.model=='qwen2.5:7b'
    assert configured._config.base_url in ('http://127.0.0.1:11434','http://localhost:11434')
    return OllamaProvider(replace(configured._config,timeout_seconds=120))

CASES=[
 {'name':'quiet-open-ending','title':'Lá thư còn kín','idea':'Cha muốn xin lỗi, con gái chưa quyết định có đón nhận hay không.',
  'constraints':['Chỉ cha và con gái trong một căn nhà.','Không nói tha thứ hoặc hòa giải xong.','Phong thư vẫn kín; kết mở, không thêm biến cố.'],
  'previous':'Con gái về nhà, đặt túi cạnh cửa. Cha đứng bên bàn, cầm phong thư kín.',
  'target':'Cha đặt phong thư kín lên bàn rồi lùi lại. Con gái đặt tay cạnh phong thư, chưa nhận hoặc mở; dừng ở đó.',
  'request':'Viết bằng hành động, không lời thoại. Giữ quyền quyết định của con gái.',
  'checks':['Đúng một cảnh; không kể lại cảnh trở về.','Thư kín, không lời tha thứ, không chốt hòa giải.','Bố trí/hành động đọc được; giữ kết mở.']},
 {'name':'gentle-comedy','title':'Khóa áo','idea':'Nam mượn áo của chị Hà đi gặp bạn; khóa áo bị kẹt khiến cậu lúng túng.',
  'constraints':['Chỉ Nam và chị Hà trong phòng khách.','Chuyện vui nhẹ, không làm nhục hoặc mắng em.','Không thêm người tới, không chuyển cảnh ra ngoài.'],
  'previous':'Nam mặc thử áo khoác của chị Hà trong phòng khách. Khóa áo kẹt ở giữa, Hà chờ cạnh cửa.',
  'target':'Nam lấy chiếc túi đang cầm che chỗ khóa kẹt. Hà nhìn thấy, đưa tay chờ Nam chịu nhờ giúp; Nam miễn cưỡng đưa vạt áo ra.',
  'request':'Có thể dùng lời thoại ngắn tự nhiên giữa chị và em, ưu tiên cử chỉ gây cười.',
  'checks':['Đúng một cảnh; tiếp diễn khóa kẹt.','Hài nhẹ, xưng hô chị/em, không mắng hoặc thêm người.','Có hành động cụ thể, không biến thành đoạn giải thích.']},
 {'name':'limited-resources','title':'Chiếc đèn pin hỏng','idea':'Lan và Bình ở phòng trọ mất điện, cùng tìm cách đọc một tờ giấy mà không có đèn hoạt động.',
  'constraints':['Chỉ Lan và Bình, một phòng trọ ban đêm.','Đèn pin hỏng không sáng, không điện thoại/đạo cụ mới.','Dùng bàn, tờ giấy và rèm đã có; ánh đèn đường từ cửa sổ, không đổi thành ban ngày.'],
  'previous':'Lan đặt tờ giấy lên bàn sát cửa sổ có rèm. Bình bấm chiếc đèn pin hỏng; đèn không sáng.',
  'target':'Bình đặt đèn pin xuống. Lan kéo rèm để ánh đèn đường rọi vào bàn; cả hai nghiêng tờ giấy để đọc.',
  'request':'Viết một cảnh ngắn, hành động rõ; có thể không cần lời thoại.',
  'checks':['Đúng một cảnh và giữ liên tục đồ vật.','Không làm đèn pin sáng, thêm điện thoại/người/địa điểm.','Ánh đèn đường ban đêm và hành động đọc giấy có thể hình dung.']},
]

def freeze():
    assert not (OUT/'manifest.json').exists(),'Already frozen; do not replace inputs'
    DATA.mkdir(parents=True,exist_ok=True)
    store=ProjectStore(DATA/'freeze.sqlite3');projects.get_project_store=lambda:store
    client=TestClient(create_app());inputs=[]
    for case in CASES:
        p=ProjectResponse(id=str(uuid4()),updated_at=datetime.now(UTC).isoformat(),title=case['title'],
          response_language='vi',idea=case['idea'],constraints=case['constraints'],draft=StoryDraft(title=case['title'],logline=case['idea'],
          sections=[{'title':'Đầu','purpose':'Mở','content':case['previous']},{'title':'Cuối','purpose':'Diễn tiến','content':case['target']}]))
        store.create(p.model_dump(exclude_computed_fields=True));url=f'/api/projects/{p.id}'
        r=client.post(url+'/scene-outline',json={'revision':p.revision,'source_version_id':'current'});assert r.status_code==200,r.text;p=r.json()
        scenes=[{'id':str(uuid4()),'title':title,'action':action,'location':'Một căn phòng','time':'','characters':'','staging_choices':{}}
                for title,action in [('Trước đó',case['previous']),('Khoảnh khắc',case['target'])]]
        body={k:p[k] for k in ('revision','title','idea','constraints','answers','draft','response_language')}
        r=client.put(url,json={**body,'scene_outline':{'id':p['scene_outline']['id'],'version':p['scene_outline']['version'],'scenes':scenes}});assert r.status_code==200,r.text;p=r.json()
        r=client.post(url+'/screenplay',json={'revision':p['revision'],'request_id':str(uuid4())});assert r.status_code==200,r.text;p=r.json()
        p['screenplay']['scenes'][0]['blocks']=[{'id':str(uuid4()),'kind':'action','text':case['previous'],'speaker':''}]
        p['screenplay']['scenes'][1]['blocks']=[{'id':str(uuid4()),'kind':'action','text':case['target'].split('.')[0]+'.','speaker':''}]
        body={k:p[k] for k in ('revision','title','idea','constraints','answers','draft','response_language')}
        r=client.put(url,json={**body,'screenplay':{k:p['screenplay'][k] for k in ('id','version','scenes')}});assert r.status_code==200,r.text;p=r.json()
        inputs.append({'name':case['name'],'project':p,'request':{'revision':p['revision'],'request_id':str(uuid4()),
          'target_scene_id':p['screenplay']['scenes'][1]['id'],'instructions':case['request']},'expected':case['checks']})
    config=provider().metadata
    tags=httpx.get('http://127.0.0.1:11434/api/tags',timeout=10).json()
    model=next(m for m in tags['models'] if m['name']==config.model)
    dump(OUT/'inputs.json',inputs);dump(OUT/'schema.json',SceneWritingResult.model_json_schema())
    dump(OUT/'manifest.json',{'frozen_at':datetime.now(UTC).isoformat(),'maximum_calls':3,'timeout_seconds_per_call':120,'retry':False,
      'provider':config.provider,'model':config.model,'digest':model['digest'],'parameters':config.parameters,
      'inputs_sha256':hashlib.sha256((OUT/'inputs.json').read_bytes()).hexdigest(),
      'schema_sha256':hashlib.sha256((OUT/'schema.json').read_bytes()).hexdigest(),'hashes':hashes()})
    print('FROZEN 3 cases, prompt/schema/runtime/model digest; no inference',flush=True)


def run():
    manifest=json.loads((OUT/'manifest.json').read_text())
    assert hashes()==manifest['hashes']
    assert hashlib.sha256((OUT/'inputs.json').read_bytes()).hexdigest()==manifest['inputs_sha256']
    assert hashlib.sha256((OUT/'schema.json').read_bytes()).hexdigest()==manifest['schema_sha256']
    real=provider();assert real.metadata.parameters==manifest['parameters']
    model=next(m for m in httpx.get('http://127.0.0.1:11434/api/tags',timeout=10).json()['models'] if m['name']==manifest['model'])
    assert model['digest']==manifest['digest']
    with (OUT/'run-started.json').open('x') as f:json.dump({'at':datetime.now(UTC).isoformat()},f)
    store=ProjectStore(DATA/'run.sqlite3');projects.get_project_store=lambda:store
    results=[];inputs=json.loads((OUT/'inputs.json').read_text());assert len(inputs)==3
    for case in inputs:
        folder=OUT/case['name'];folder.mkdir(exist_ok=False);calls=[]
        class Logged:
            metadata=real.metadata
            def request_structured(self,request):
                assert len(calls)==0,'No retry';calls.append(request.stage)
                dump(folder/'request.json',{'instructions':request.instructions,'input':json.loads(request.input_text),'schema':request.response_model.model_json_schema()})
                try:
                    result=real.request_structured(request)
                    dump(folder/'raw-output.json',{'raw_output':result.raw_output,'output':result.output.model_dump(mode='json'),'model':result.model})
                    return result
                except Exception as e:
                    dump(folder/'error.json',{'type':type(e).__name__,'message':str(e),'raw_output':getattr(e,'raw_output',None)})
                    raise
        screenplays.get_screenplay_provider=lambda:Logged()
        p=ProjectResponse.model_validate(case['project']);store.create(p.model_dump(exclude_computed_fields=True))
        client=TestClient(create_app(),raise_server_exceptions=False);started=time.monotonic()
        r=client.post(f'/api/projects/{p.id}/screenplay-proposals',json=case['request']);duration=time.monotonic()-started
        after=client.get(f'/api/projects/{p.id}').json();dump(folder/'project-after.json',after)
        assert after['screenplay']==case['project']['screenplay']
        assert after['scene_outline']==case['project']['scene_outline']
        row={'name':case['name'],'status_code':r.status_code,'duration_seconds':round(duration,3),'model_calls':len(calls),
          'proposal_status':after['screenplay_proposals'][-1]['status'],'response_error':r.text if r.status_code!=200 else None,
          'author_draft_unchanged':True,'automatically_applied':False}
        results.append(row);dump(folder/'result.json',row);dump(OUT/'results.json',results)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    assert sum(r['model_calls'] for r in results)<=3
    print('DONE; all calls/errors retained; no retries',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run']);args=parser.parse_args()
    freeze() if args.mode=='freeze' else run()
