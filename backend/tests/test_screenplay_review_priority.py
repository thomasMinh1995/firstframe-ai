"""Scripted provider responses test the contract, not a model's reasoning ability."""
import json
from pathlib import Path

import pytest
from test_projects import project_client  # noqa: F401

from app.api.routes import screenplay_reviews as routes
from app.api.schemas.screenplays import SceneReviewResult
from app.application.ai_provider import ProviderMetadata, StructuredResult


@pytest.mark.parametrize('variant,response',[
    ('compliant','empty'),
    ('violating','conflict'),
    ('violating','conflict_without_suggestion'),
    ('violating','unsupported_craft'),
    ('violating','contradictory_secondary_note'),
])
def test_flashlight_priority_contract_with_scripted_provider(project_client,monkeypatch,variant,response):
    client,_=project_client
    root=Path(__file__).resolve().parents[2]
    cases=json.loads((root/'docs/evaluations/m3-scene-review-qwen7b-2026-10-27/inputs.json').read_text())
    case=next(c for c in cases if c['name']==f'broken-flashlight-{variant}')
    p=routes.ProjectResponse.model_validate(case['project'])
    routes.projects.get_project_store().create(p.model_dump(exclude_computed_fields=True))
    target=next(s for s in p.screenplay.scenes if s.id==case['request']['target_scene_id'])
    expected_text=target.blocks[1].text
    calls=[]

    class ScriptedProvider:
        metadata=ProviderMetadata('fake','constraint-priority-fixture',{})

        def request_structured(self,request):
            calls.append(request)
            prompt=request.instructions
            assert prompt.index('1. Before optional craft feedback')<prompt.index('2. Only if the target action/result directly contradicts')<prompt.index('3. Only after this comparison')
            assert 'Adding explanatory dialogue does not fix an incompatible action' in prompt
            assert 'criticize dialogue that is absent' in prompt
            data=json.loads(request.input_text)
            action=next(s for s in data['sources'] if s['is_target'] and s['field']=='text' and s['text']==expected_text)
            constraint=next(s for s in data['sources'] if s['category']=='author_choice' and s['text']=='Đèn pin bị hỏng, không thể sáng.')
            assert action['block_kind']=='action'
            assert all(s['block_kind']=='action' for s in data['sources'] if s['is_target'] and s['field']=='text')
            evidence=[{'source_id':action['id'],'quote':action['text']},{'source_id':constraint['id'],'quote':constraint['text']}]
            if response=='empty':
                output={'notes':[],'question':''}
            elif response=='unsupported_craft':
                # The reference guard cannot infer whether the provider followed the priority.
                output={'notes':[{'kind':'craft','observation':'Lời thoại cần tự nhiên hơn.',
                    'impact':'Có thể tăng cảm xúc.','suggestion':'Thêm câu giải thích đèn pin hỏng.',
                    'evidence':[evidence[0]]}],'question':''}
            else:
                output={'notes':[{'kind':'intent_mismatch',
                    'observation':'Hành động làm đèn pin sáng trái giới hạn đèn pin hỏng không thể sáng.',
                    'impact':'Cảnh thay đổi điều kiện nguồn sáng tác giả đã chọn.',
                    'suggestion':'' if response=='conflict_without_suggestion' else 'Cân nhắc bỏ hành động làm đèn pin sáng, giữ cách đọc bằng ánh đèn đường đã có.',
                    'evidence':evidence}],'question':''}
                if response=='contradictory_secondary_note':
                    # Valid references still cannot certify consistency across notes.
                    output['notes'].append({'kind':'craft','observation':'Cần nhìn tờ giấy rõ hơn.',
                        'impact':'Có thể dễ nhìn hơn.','suggestion':'Thêm điện thoại bật đèn.',
                        'evidence':[evidence[0]]})
            return StructuredResult(output=SceneReviewResult.model_validate(output),model=self.metadata.model,
                raw_output=json.dumps(output,ensure_ascii=False))

    monkeypatch.setattr(routes,'get_review_provider',lambda:ScriptedProvider())
    r=client.post(f'/api/projects/{p.id}/screenplay-reviews',json=case['request']);assert r.status_code==200,r.text
    saved=r.json();item=saved['screenplay_reviews'][-1]
    assert item['status']=='ready' and item['prompt_version']=='screenplay-review-v5-provenance'
    assert len(calls)==1 and saved['screenplay']==case['project']['screenplay']
    assert saved['scene_outline']==case['project']['scene_outline']
    if response=='empty':
        assert item['notes']==[]
    else:
        note=item['notes'][0];sources={s['id']:s for s in item['sources']}
        assert note['evidence'][0]['source_id']==f'block:{target.blocks[1].id}:text'
        assert all(e['quote'] in sources[e['source_id']]['text'] for e in note['evidence'])
        if response.startswith('conflict') or response=='contradictory_secondary_note':
            assert note['kind']=='intent_mismatch' and len(note['evidence'])==2
            if response=='conflict_without_suggestion':
                assert note['suggestion']==''
            else:
                assert 'bỏ hành động' in note['suggestion']
            if response=='contradictory_secondary_note':
                assert len(item['notes'])==2 and item['notes'][1]['suggestion']=='Thêm điện thoại bật đèn.'
        else:
            assert note['kind']=='craft','Source validity must not be presented as semantic certification'
    assert client.get(f'/api/projects/{p.id}').json()['screenplay_reviews']==saved['screenplay_reviews']
