from copy import deepcopy
from uuid import uuid4

import pytest
from test_projects import project_client, payload  # noqa: F401
from test_screenplays import prepare, start, edit, block

from app.api.routes import projects, screenplays


@pytest.fixture
def written(project_client,monkeypatch):
    client,provider=project_client;p=start(client,prepare(client)).json();url=f"/api/projects/{p['id']}"
    body=edit(p)
    body['screenplay']['scenes'][0]['blocks']=[block(text='  Cha đặt thư.\n\nThư còn kín.  ')]
    body['screenplay']['scenes'][1]['blocks']=[block('dialogue','  Không sao đâu cha ạ…\n  ')]
    p=client.put(url,json=body).json()
    def no_ai():raise AssertionError('Selecting a saved source must not call AI')
    monkeypatch.setattr(screenplays,'get_screenplay_provider',no_ai)
    return client,provider,p


def select(client,p,source='current',rid=None):
    body={'revision':p['revision'],'request_id':rid or str(uuid4()),'source_version_id':source}
    return client.post(f"/api/projects/{p['id']}/screenplay-selections",json=body),body


def test_select_snapshot_immutable_after_edits_restore_and_new_selection(written):
    client,provider,p=written;url=f"/api/projects/{p['id']}";calls=len(provider.requests)
    r,request=select(client,p);assert r.status_code==200,r.text
    selected=r.json();first=deepcopy(selected['screenplay_handoff'])
    assert first['screenplay']==p['screenplay'] and first['source_revision']==p['revision']
    assert selected['screenplay']==p['screenplay'] and selected['screenplay_versions']==p['screenplay_versions']
    assert selected['screenplay_handoff']==selected['screenplay_selections'][-1]
    assert client.post(url+'/screenplay-selections',json=request).json()==selected
    body=edit(selected);body['screenplay']['scenes'][0]['blocks'][0]['text']='Bản tác giả sửa mới.'
    updated=client.put(url,json=body).json();assert updated['screenplay_handoff']==first
    history=next(v for v in updated['screenplay_versions'] if v['screenplay']==first['screenplay'])
    restored=client.post(f"{url}/screenplay-versions/{history['id']}/restore",json={'revision':updated['revision']}).json()
    assert restored['screenplay_handoff']==first
    next_selected=select(client,restored)[0].json();assert len(next_selected['screenplay_selections'])==2
    assert next_selected['screenplay_handoff']['screenplay']==restored['screenplay']
    assert next_selected['screenplay_selections'][0]==first
    # Replaying the first selection after a later choice must not reactivate the old source.
    assert client.post(url+'/screenplay-selections',json=request).json()==next_selected
    legacy=client.put(url,json=payload(next_selected)).json();assert legacy['screenplay_selections']==next_selected['screenplay_selections']
    assert client.get(url).json()==legacy and len(provider.requests)==calls
    assert 'screenplay_handoff' not in projects.dataset_snapshot(projects.load_project(p['id']))
    assert 'screenplay_selections' not in projects.dataset_snapshot(projects.load_project(p['id']))
    for key in ('draft','feedback_source','scene_outline','scene_sketches','selected_scene_sketches'):assert legacy[key]==p[key]


@pytest.mark.parametrize('problem',['scene_empty','blank_text','blank_speaker','blank_heading','extra_blank_block'])
def test_incomplete_drafts_save_but_cannot_replace_selected_source(written,problem):
    client,_,p=written;url=f"/api/projects/{p['id']}";p=select(client,p)[0].json();first=deepcopy(p['screenplay_handoff'])
    body=edit(p);scene=body['screenplay']['scenes'][1]
    if problem=='scene_empty':scene['blocks']=[]
    elif problem=='blank_text':scene['blocks'][0]['text']=' \n '
    elif problem=='blank_speaker':scene['blocks'][0]['speaker']=' '
    elif problem=='blank_heading':scene['heading']=' '
    else:scene['blocks'].append(block(text=''))
    r=client.put(url,json=body);assert r.status_code==200,r.text
    p=r.json();r,_=select(client,p);assert r.status_code==422 and '2' in r.json()['detail']
    assert client.get(url).json()==p and p['screenplay_handoff']==first
    # A complete saved history may be chosen without restoring or changing the incomplete current draft.
    old=next(v for v in p['screenplay_versions'] if v['screenplay']==first['screenplay'])
    r,_=select(client,p,old['id']);assert r.status_code==200,r.text
    assert r.json()['screenplay']==p['screenplay'] and r.json()['screenplay_handoff']['screenplay']==old['screenplay']


def test_revision_scope_untrusted_snapshot_and_idempotency(written):
    client,_,p=written;url=f"/api/projects/{p['id']}"
    r,body=select(client,p);selected=r.json();assert r.status_code==200
    assert select(client,p)[0].status_code==409
    assert client.post(url+'/screenplay-selections',json={**body,'source_version_id':str(uuid4())}).status_code==409
    bad={**body,'revision':selected['revision'],'request_id':str(uuid4())}
    for extra in ({'screenplay':p['screenplay']},{'source_revision':0},{'quality_approved':True}):
        assert client.post(url+'/screenplay-selections',json={**bad,**extra}).status_code==422
    assert select(client,selected,str(uuid4()))[0].status_code==404
    other=client.post('/api/projects').json();history=selected['screenplay_versions'][0]['id']
    assert select(client,other,history)[0].status_code==404
    assert select(client,other)[0].status_code==404
    assert client.put(url,json={**payload(selected),'screenplay_selections':[]}).status_code==422
    assert client.get(url).json()==selected


def test_legacy_storage_and_selection_quota_keep_manual_path(written):
    client,_,p=written;url=f"/api/projects/{p['id']}";store=projects.get_project_store()
    raw=store.get(p['id']);raw.pop('screenplay_selections',None);store.save(raw,raw['revision'])
    p=client.get(url).json();assert p['screenplay_selections']==[] and p['screenplay_handoff'] is None
    p=select(client,p)[0].json();first=deepcopy(p['screenplay_handoff'])
    raw=store.get(p['id']);raw['screenplay_selections']=[{**raw['screenplay_selections'][0],'id':str(uuid4())} for _ in range(100)];store.save(raw,raw['revision'])
    full=client.get(url).json();assert select(client,full)[0].status_code==422
    body=edit(full);body['screenplay']['scenes'][0]['blocks'][0]['text']='Tự sửa sau khi đủ số lần chọn.'
    r=client.put(url,json=body);assert r.status_code==200,r.text
    assert r.json()['screenplay_handoff']==full['screenplay_handoff']
    assert full['screenplay_handoff']['screenplay']==first['screenplay']


def test_late_writer_preserves_selected_m4_source(written,monkeypatch):
    from test_screenplay_writing import WritingProvider
    client,_,p=written;url=f"/api/projects/{p['id']}";provider=WritingProvider();chosen=[]
    def choose_while_waiting():
        current=client.get(url).json();r,_=select(client,current);assert r.status_code==200,r.text
        chosen.append(r.json()['screenplay_handoff'])
    provider.hook=choose_while_waiting
    monkeypatch.setattr(screenplays,'get_screenplay_provider',lambda:provider)
    r=client.post(url+'/screenplay-proposals',json={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':p['screenplay']['scenes'][0]['id'],'instructions':''})
    assert r.status_code==200,r.text
    assert r.json()['screenplay_handoff']==chosen[0] and r.json()['screenplay']==p['screenplay']
    assert r.json()['screenplay_proposals'][-1]['status']=='ready'
