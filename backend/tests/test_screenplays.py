from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_projects import project_client, payload  # noqa: F401
from test_scene_outline import begin, scene, update

from app.api.routes import projects as routes
from app.main import create_app


def prepare(client):
    _, p = begin(client)
    return client.put(f"/api/projects/{p['id']}",json=update(p,[scene("Trùng tên"),scene("Trùng tên")])).json()


def start(client,p,rid=None):
    return client.post(f"/api/projects/{p['id']}/screenplay",json={"revision":p['revision'],"request_id":rid or str(uuid4())})


def edit(p):
    return {**payload(p),"screenplay":{k:deepcopy(p['screenplay'][k]) for k in ('id','version','scenes')}}


def block(kind="action",text="  Cha đặt thư.\n\nCon gái chưa mở.  "):
    return {"id":str(uuid4()),"kind":kind,"text":text,"speaker":"Con gái" if kind=="dialogue" else ""}


def test_source_manual_blocks_legacy_reopen_no_ai(project_client):
    client,provider=project_client;p=prepare(client);url=f"/api/projects/{p['id']}";calls=len(provider.requests)
    result=start(client,p);assert result.status_code==200,result.text
    begun=result.json();script=begun['screenplay']
    assert script['source_outline']==p['scene_outline'] and script['source_revision']==p['revision']
    assert [s['source_scene_id'] for s in script['scenes']]==[s['id'] for s in p['scene_outline']['scenes']]
    assert all(not s['blocks'] for s in script['scenes']) and begun['screenplay_source_is_current']
    body=edit(begun);a,b=block(),block('dialogue','Không sao đâu cha ạ…')
    body['screenplay']['scenes'][0]['blocks']=[b,a]
    body['screenplay']['scenes'][0]['heading']='  NỘI. CĂN NHÀ — CHIỀU  '
    saved=client.put(url,json=body).json()
    assert saved['screenplay']['version']==2 and saved['screenplay']['scenes']==body['screenplay']['scenes']
    assert len(saved['screenplay_versions'])==1
    assert saved['scene_outline']==p['scene_outline'] and saved['feedback_source']==p['feedback_source']
    assert saved['feedback_is_current']==p['feedback_is_current'] and TestClient(create_app()).get(url).json()==saved
    legacy=client.put(url,json={**payload(saved),'title':'Tên mới'}).json()
    assert legacy['screenplay']==saved['screenplay'] and legacy['screenplay_versions']==saved['screenplay_versions']
    removed=edit(legacy);removed['screenplay']['scenes'][0]['blocks']=[a]
    latest=client.put(url,json=removed).json()
    assert latest['screenplay']['scenes'][0]['blocks']==[a] and not latest['screenplay']['scenes'][1]['blocks']
    assert len(provider.requests)==calls
    assert 'screenplay' not in routes.dataset_snapshot(routes.load_project(p['id']))


def test_changed_m2_m1_and_metadata_preserve_source(project_client):
    client,_=project_client;p=start(client,prepare(client)).json();url=f"/api/projects/{p['id']}";snapshot=deepcopy(p['screenplay'])
    p=client.put(url,json={**payload(p),'title':'Tên khác'}).json()
    assert p['screenplay_source_is_current'] and p['screenplay']==snapshot
    scenes=deepcopy(p['scene_outline']['scenes']);scenes.reverse()
    changed=client.put(url,json=update(p,scenes)).json()
    assert not changed['screenplay_source_is_current'] and changed['screenplay']==snapshot
    changed=client.put(url,json=update(changed,list(reversed(scenes)))).json()
    assert changed['screenplay_source_is_current']
    changed=client.put(url,json={**payload(changed),'constraints':[*changed['constraints'],'Không thêm người.']}).json()
    assert not changed['screenplay_source_is_current'] and changed['screenplay']==snapshot


def test_start_replay_new_draft_restore_conflict(project_client):
    client,provider=project_client;p=prepare(client);url=f"/api/projects/{p['id']}";calls=len(provider.requests)
    rid=str(uuid4());begun=start(client,p,rid).json()
    assert start(client,p,rid).json()==begun and start(client,p).status_code==409
    body=edit(begun);body['screenplay']['scenes'][0]['blocks']=[block()]
    saved=client.put(url,json=body).json();assert client.put(url,json=body).status_code==409
    second=start(client,saved).json()
    assert second['screenplay']['id']!=rid and not second['screenplay']['scenes'][0]['blocks']
    assert second['screenplay_versions'][-1]['screenplay']==saved['screenplay']
    assert start(client,p,rid).json()==second
    history=second['screenplay_versions'][-1];restore=f"{url}/screenplay-versions/{history['id']}/restore"
    assert client.post(restore,json={'revision':saved['revision']}).status_code==409
    restored=client.post(restore,json={'revision':second['revision']}).json()
    assert restored['screenplay']['scenes']==saved['screenplay']['scenes']
    assert restored['screenplay']['source_outline']==saved['screenplay']['source_outline']
    assert restored['screenplay_versions'][-1]['screenplay']==second['screenplay']
    assert restored['scene_outline']==saved['scene_outline'] and restored['feedback_source']==saved['feedback_source']
    assert client.post(f"{url}/screenplay-versions/{uuid4()}/restore",json={'revision':restored['revision']}).status_code==404
    assert len(provider.requests)==calls


@pytest.mark.parametrize('mutation',['source','null','id','version','reorder','source_id','scene_id','duplicate','move_block','kind','extra_block','oversize','too_many_blocks'])
def test_invalid_edits_preserve_saved_project(project_client,mutation):
    client,_=project_client;p=start(client,prepare(client)).json();url=f"/api/projects/{p['id']}"
    body=edit(p);body['screenplay']['scenes'][0]['blocks']=[block()]
    p=client.put(url,json=body).json();body=edit(p);e=body['screenplay']
    if mutation=='source':e['source_outline']=p['scene_outline']
    elif mutation=='null':body['screenplay']=None
    elif mutation=='id':e['id']=str(uuid4())
    elif mutation=='version':e['version']+=1
    elif mutation=='reorder':e['scenes'].reverse()
    elif mutation=='source_id':e['scenes'][0]['source_scene_id']=str(uuid4())
    elif mutation=='scene_id':e['scenes'][0]['id']=str(uuid4())
    elif mutation=='duplicate':e['scenes'][0]['blocks']*=2
    elif mutation=='move_block':e['scenes'][1]['blocks']=e['scenes'][0]['blocks'];e['scenes'][0]['blocks']=[]
    elif mutation=='kind':e['scenes'][0]['blocks'][0]['kind']='html'
    elif mutation=='extra_block':e['scenes'][0]['blocks'][0]['source']='forged'
    elif mutation=='oversize':e['scenes'][0]['blocks']=[block(text='x'*10000) for _ in range(21)]
    elif mutation=='too_many_blocks':e['scenes'][0]['blocks']=[block(text='') for _ in range(201)]
    response=client.put(url,json=body);assert response.status_code in (409,422),response.text
    assert client.get(url).json()==p


def test_missing_handoff_and_untrusted_source_rejected(project_client):
    client,_=project_client;_,p=begin(client);url=f"/api/projects/{p['id']}"
    assert start(client,p).status_code==422
    assert client.post(url+'/screenplay',json={'revision':p['revision'],'request_id':str(uuid4()),'source_outline':{}}).status_code==422
    assert client.get(url).json()['screenplay'] is None
    other=client.post('/api/projects').json()
    assert client.post(f"/api/projects/{other['id']}/screenplay-versions/{uuid4()}/restore",json={'revision':other['revision']}).status_code==404


def test_start_old_m2_context_and_pre_m3_storage(project_client):
    client,_=project_client;p=prepare(client);url=f"/api/projects/{p['id']}";source=deepcopy(p['scene_outline'])
    p=client.put(url,json={**payload(p),'constraints':[*p['constraints'],'Ý đồ M1 mới chưa dùng cho M2.']}).json()
    begun=start(client,p).json()
    assert begun['screenplay']['source_outline']==source and not begun['screenplay_source_is_current']
    assert begun['scene_sketches']==p['scene_sketches'] and begun['selected_scene_sketches']==p['selected_scene_sketches']
    store=routes.get_project_store();raw=store.get(p['id'])
    for key in ('screenplay','screenplay_versions'):
        raw.pop(key,None)
    store.save(raw,raw['revision'])
    old=client.get(url).json();assert old['screenplay'] is None and old['screenplay_versions']==[]
