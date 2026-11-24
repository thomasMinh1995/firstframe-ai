from copy import deepcopy
from uuid import uuid4
import json
import pytest
from test_screenplay_writing import writing, generate, adopt
from test_screenplays import edit, block
from test_projects import payload, project_client
from test_draft_runs import drafting
from app.api.routes import screenplays
from app.api.schemas.screenplays import BlockRevisionResult
from app.application.ai_provider import StructuredResult


def setup_blocks(writing,monkeypatch):
    client,provider,p,text=writing
    body=edit(p);body['screenplay']['scenes'][0]['blocks']=[block(text='Giữ đoạn này.'),block('dialogue','Con chưa quyết định.'),block(text='Giữ kết mở.')]
    p=client.put(f"/api/projects/{p['id']}",json=body).json()
    def revise(request):
        provider.requests.append(request)
        data=json.loads(request.input_text)
        return StructuredResult(output=BlockRevisionResult(replacements=[{'block_id':b['id'],'expected':{k:b[k] for k in ('kind','text','speaker')},'replacement':{'kind':b['kind'],'text':'  Con im lặng.  ','speaker':b['speaker']}} for b in data['selected_blocks']]),model='revision-fixture')
    monkeypatch.setattr(provider,'request_structured',revise)
    return client,provider,p


def test_scoped_blocks_preview_apply_repeat_and_guarded_undo(writing,monkeypatch):
    client,provider,p=setup_blocks(writing,monkeypatch);url=f"/api/projects/{p['id']}"
    target=p['screenplay']['scenes'][0];selected=target['blocks'][1]['id']
    result=client.post(url+'/screenplay-proposals',json={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':target['id'],'instructions':'Giảm thoại cảnh 1','scope':'blocks','block_ids':[selected]})
    assert result.status_code==200,result.text
    ready=result.json();proposal=ready['screenplay_proposals'][-1];after=proposal['scene']
    assert after['heading']==target['heading']
    assert after['blocks'][0]==target['blocks'][0] and after['blocks'][2]==target['blocks'][2]
    assert [b['id'] for b in after['blocks']]==[b['id'] for b in target['blocks']]
    forged=deepcopy(after);forged['blocks'][0]['text']='Ngoài phạm vi'
    assert client.put(url,json={**payload(ready),'screenplay_proposal_previews':{proposal['id']:forged}}).status_code==422
    applied=client.post(url+f"/screenplay-proposals/{proposal['id']}/apply",json={'revision':ready['revision']})
    assert applied.status_code==200,applied.text
    saved=applied.json();assert saved['screenplay']['scenes'][0]==after
    assert saved['screenplay']['scenes'][1]==p['screenplay']['scenes'][1]
    assert client.post(url+f"/screenplay-proposals/{proposal['id']}/apply",json={'revision':ready['revision']}).json()==saved
    undone=client.post(url+f"/screenplay-proposals/{proposal['id']}/undo",json={'revision':saved['revision']})
    assert undone.status_code==200,undone.text
    assert undone.json()['screenplay']['scenes']==p['screenplay']['scenes']
    assert client.post(url+f"/screenplay-proposals/{proposal['id']}/undo",json={'revision':saved['revision']}).json()==undone.json()
    assert len(provider.requests)==1


def test_undo_refuses_target_edited_after_apply(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    ready=generate(client,p)[0].json();proposal=ready['screenplay_proposals'][-1]
    p=client.post(url+f"/screenplay-proposals/{proposal['id']}/apply",json={'revision':ready['revision']}).json()
    body=edit(p);body['screenplay']['scenes'][0]['blocks'][0]['text']='Chữ mới của tác giả'
    p=client.put(url,json=body).json()
    assert client.post(url+f"/screenplay-proposals/{proposal['id']}/undo",json={'revision':p['revision']}).status_code==409
    assert client.get(url).json()==p


@pytest.mark.parametrize('foreign_replacement', [False, True])
def test_block_script_guard_preserves_foreign_author_text_outside_scope(writing, monkeypatch, foreign_replacement):
    client, provider, p = setup_blocks(writing, monkeypatch)
    url = f"/api/projects/{p['id']}"
    body = edit(p)
    body['screenplay']['scenes'][0]['blocks'][0]['text'] = 'Tác giả giữ nguyên chữ 原文.'
    p = client.put(url, json=body).json()
    target = p['screenplay']['scenes'][0]
    selected = target['blocks'][1]
    def output(request):
        provider.requests.append(request)
        return StructuredResult(output=BlockRevisionResult(replacements=[{
            'block_id':selected['id'], 'expected':{k:selected[k] for k in ('kind','text','speaker')},
            'replacement':{'kind':'dialogue','speaker':selected['speaker'],
                           'text':'Con vẫn chưa quyết định.' + (' 漉漉的' if foreign_replacement else '')}}]),model='fixture')
    monkeypatch.setattr(provider, 'request_structured', output)
    response = client.post(url+'/screenplay-proposals', json={'revision':p['revision'],
        'request_id':str(uuid4()),'target_scene_id':target['id'],'scope':'blocks','block_ids':[selected['id']]})
    assert response.status_code == (502 if foreign_replacement else 200)
    saved = client.get(url).json()
    assert saved['screenplay'] == p['screenplay']
    assert len(provider.requests) == 1


def test_resolver_and_direct_api_do_not_rewrite_wrong_scene_or_structure(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}";scene=p['screenplay']['scenes'][0]
    body={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':scene['id'],'instructions':'Giảm thoại cảnh 2'}
    resolved=client.post(url+'/screenplay-revision-target',json=body).json()
    assert resolved['scene_id']==p['screenplay']['scenes'][1]['id']
    assert client.post(url+'/screenplay-proposals',json=body).status_code==422
    body['instructions']='Thêm cảnh ở cuối rồi đổi kết thúc'
    result=client.post(url+'/screenplay-revision-target',json=body).json()
    assert result['kind']=='candidate' and len(result['affected_scene_ids'])==2
    assert client.post(url+'/screenplay-proposals',json=body).status_code==422
    assert provider.requests==[]


def test_forged_expected_block_does_not_create_ready_proposal(writing,monkeypatch):
    client,provider,p=setup_blocks(writing,monkeypatch);url=f"/api/projects/{p['id']}";target=p['screenplay']['scenes'][0]
    original=provider.request_structured
    def wrong(request):
        result=original(request);result.output.replacements[0].expected.text='Không phải nguồn'
        return result
    monkeypatch.setattr(provider,'request_structured',wrong)
    response=client.post(url+'/screenplay-proposals',json={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':target['id'],'scope':'blocks','block_ids':[target['blocks'][1]['id']]})
    assert response.status_code==502,response.text
    assert client.get(url).json()['screenplay']==p['screenplay']


def test_verified_feedback_can_request_block_revision_without_new_prompt(writing,monkeypatch):
    from test_screenplay_review import ReviewProvider
    from app.api.routes import screenplay_reviews
    client,provider,p=setup_blocks(writing,monkeypatch);url=f"/api/projects/{p['id']}";target=p['screenplay']['scenes'][0]
    monkeypatch.setattr(screenplay_reviews,'get_review_provider',lambda:ReviewProvider())
    result=client.post(url+'/screenplay-reviews',json={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':target['id']})
    assert result.status_code==200,result.text
    p=result.json();review=p['screenplay_reviews'][-1];note=review['notes'][0]
    body={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':target['id'],'scope':'blocks','block_ids':[target['blocks'][0]['id']],'review_id':review['id'],'note_id':note['id']}
    bad=client.post(url+'/screenplay-proposals',json={**body,'note_id':str(uuid4())})
    assert bad.status_code==409 and not provider.requests
    response=client.post(url+'/screenplay-proposals',json=body)
    assert response.status_code==200,response.text
    proposal=response.json()['screenplay_proposals'][-1]
    assert proposal['review_id']==review['id'] and proposal['note_id']==note['id']
    assert note['observation'] in json.loads(provider.requests[-1].input_text)['author_request']
    assert client.post(url+'/screenplay-proposals',json=body).json()==response.json()
    assert len(provider.requests)==1


def test_structural_candidate_keeps_original_and_records_impact(drafting):
    from test_draft_runs import begin,complete
    client,providers,p,base,url,body=begin(drafting)
    r,c=complete(client,url)
    p=client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']}).json()
    request={'revision':p['revision'],'request_id':str(uuid4()),'revision_instructions':'Thêm cảnh ở cuối, giữ kết mở.'}
    response=client.post(base,json=request);assert response.status_code==200,response.text
    next_url=base+'/'+request['request_id']
    r,c=complete(client,next_url)
    assert r['revision_instructions']==request['revision_instructions']
    assert r['affected_scene_ids']==[s['id'] for s in p['screenplay']['scenes']]
    assert client.get(f"/api/projects/{p['id']}").json()==p
    assert client.post(base,json={**request,'revision_instructions':'Một yêu cầu khác'}).status_code==409
    adopted=client.post(next_url+'/adopt',json={'revision':p['revision'],'candidate_revision':c['revision']})
    assert adopted.status_code==200,adopted.text
    assert adopted.json()['constraints'][-1]==request['revision_instructions']


def test_block_revision_keeps_unfinished_fields_outside_scope(writing,monkeypatch):
    client,provider,p=setup_blocks(writing,monkeypatch);url=f"/api/projects/{p['id']}"
    data=edit(p);data['screenplay']['scenes'][0]['heading']='';data['screenplay']['scenes'][0]['blocks'][0]['text']=''
    p=client.put(url,json=data).json();scene=p['screenplay']['scenes'][0]
    result=client.post(url+'/screenplay-proposals',json={'revision':p['revision'],'request_id':str(uuid4()),'target_scene_id':scene['id'],'scope':'blocks','block_ids':[scene['blocks'][1]['id']]})
    assert result.status_code==200,result.text
    revised=result.json()['screenplay_proposals'][-1]['scene']
    assert revised['heading']=='' and revised['blocks'][0]['text']==''


def test_undo_preserves_other_scene_edits(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    ready=generate(client,p)[0].json();proposal=ready['screenplay_proposals'][-1]
    p=client.post(url+f"/screenplay-proposals/{proposal['id']}/apply",json={'revision':ready['revision']}).json()
    data=edit(p);data['screenplay']['scenes'][1]['blocks']=[block(text='Phần khác được giữ nguyên.')]
    p=client.put(url,json=data).json()
    undone=client.post(url+f"/screenplay-proposals/{proposal['id']}/undo",json={'revision':p['revision']})
    assert undone.status_code==200,undone.text
    assert undone.json()['screenplay']['scenes'][1]==p['screenplay']['scenes'][1]


def test_undo_refuses_reused_original_block_ids(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    original=block(text='Khối gốc trước khi nhận.')
    data=edit(p);data['screenplay']['scenes'][0]['blocks']=[original]
    p=client.put(url,json=data).json()
    ready=generate(client,p)[0].json();proposal=ready['screenplay_proposals'][-1]
    p=client.post(url+f"/screenplay-proposals/{proposal['id']}/apply",json={'revision':ready['revision']}).json()
    data=edit(p);data['screenplay']['scenes'][1]['blocks']=[original]
    changed=client.put(url,json=data);assert changed.status_code==200,changed.text
    p=changed.json()
    result=client.post(url+f"/screenplay-proposals/{proposal['id']}/undo",json={'revision':p['revision']})
    assert result.status_code==409,result.text
    assert client.get(url).json()==p


def test_apply_rejects_preview_colliding_with_neighbor_without_writing(writing):
    client,provider,p,_=writing;url=f"/api/projects/{p['id']}"
    data=edit(p);data['screenplay']['scenes'][1]['blocks']=[block(text='Cảnh bên cạnh.')]
    p=client.put(url,json=data).json()
    ready=generate(client,p)[0].json();proposal=ready['screenplay_proposals'][-1]
    preview=deepcopy(proposal['scene'])
    preview['blocks'][0]['id']=ready['screenplay']['scenes'][1]['blocks'][0]['id']
    result=client.post(url+f"/screenplay-proposals/{proposal['id']}/apply",json={'revision':ready['revision'],'scene':preview})
    assert result.status_code==422,result.text
    assert client.get(url).json()==ready
