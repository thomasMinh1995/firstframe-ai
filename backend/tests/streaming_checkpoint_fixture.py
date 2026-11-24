"""Isolated HTTP fixture for the focused streaming browser test; only FakeProvider is used."""
import os,sys,threading,tempfile
from pathlib import Path
backend=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(backend),str(backend/'tests')]
data=Path(tempfile.mkdtemp(prefix='firstframe-streaming-fixture-'))
os.environ['DATASET_DIR']=str(data/'datasets')
from app.main import create_app
from app.api.routes import projects
from app.application.project_store import ProjectStore
from app.application import workflow
from app.application.ai_provider import ProviderTimeoutError
from test_generate_workflow import FakeProvider
from test_plan_recovery import ready
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import uvicorn
store=ProjectStore(data/'projects.sqlite3')
projects.get_project_store=lambda:store
provider=FakeProvider();workflow.create_provider=lambda:provider
app=create_app();app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:3055'],allow_methods=['*'],allow_headers=['*'])
p=ready(TestClient(app),True)
release=threading.Event();original=provider.request_structured;calls=[];state={'fixture':True,'failed':False,'critic_waiting':False}
def respond(request):
 calls.append(request.stage)
 if request.stage=='evaluation':
  state['critic_waiting']=True
  if not release.wait(60):raise ProviderTimeoutError('fixture hold deadline')
  state['critic_waiting']=False
  if state['failed']:raise ProviderTimeoutError('fixture unavailable')
 result=original(request)
 if request.stage=='planning':result.output.story_plan.working_title.title='Story plan đọc sớm'
 return result
provider.request_structured=respond
@app.post('/_fixture/control')
async def control(request:Request):
 body=await request.json();state['failed']=body.get('failed',False);release.clear();calls.clear();return {'ok':True}
@app.post('/_fixture/release')
def finish():release.set();return {'ok':True}
@app.get('/_fixture/state')
def status():return {**state,'calls':calls,'project':store.get(p['id'])}
print('FIXTURE_PROJECT='+p['id'],flush=True)
uvicorn.run(app,host='127.0.0.1',port=8055,log_level='warning')
