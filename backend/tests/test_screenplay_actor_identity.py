import json
from pathlib import Path
from uuid import uuid4
import pytest
from app.api.schemas.projects import Screenplay, ScreenplayProposal
from app.application.screenplay_composition import actor_events, fixed_beats, composition_request, SceneSourceConflict, sentences

@pytest.mark.parametrize('text', ['Cha đặt lòng bàn tay lên tấm gỗ.', 'Cha 58 tuổi đặt lòng bàn tay lên tấm gỗ.'])
def test_age_qualified_character_has_one_identity(text):
    assert set(actor_events(text, 'Con gái 30 tuổi, Cha 58 tuổi')) == {('đặt lòng bàn tay', 'cha 58 tuổi')}


def test_ambiguous_short_role_does_not_guess_age():
    assert not list(actor_events('Cha đặt lòng bàn tay lên tấm gỗ.', 'Cha 58 tuổi, Cha 70 tuổi'))
    assert set(actor_events('Cha 58 tuổi đặt lòng bàn tay lên tấm gỗ.', 'Cha 58 tuổi, Cha 70 tuổi')) == {('đặt lòng bàn tay','cha 58 tuổi')}


def proposal():
    script=Screenplay.model_validate(json.loads((Path(__file__).parent/'fixtures/screenplay-aged-actor.json').read_text()))
    return ScreenplayProposal(id=str(uuid4()),created_at='2026-11-01',source_revision=0,source_content='regression',
        source_screenplay=script,source_outline=script.source_outline,target_scene_id=script.scenes[0].id,prompt_version='regression')


def test_blocked_saved_source_passes_both_scene_preflights_without_mutation():
    p=proposal(); before=p.model_dump(mode='json')
    for scene in p.source_screenplay.scenes:
        p.target_scene_id=scene.id
        source=next(s for s in p.source_screenplay.source_outline.scenes if s.id==scene.source_scene_id)
        beats,reconciled=fixed_beats(p)
        assert beats==sentences(source.action) and not reconciled
        request, kept=composition_request(p, 'Vietnamese')
        assert kept==beats and request.stage=='screenplay_generation'
    p.target_scene_id=before['target_scene_id']
    assert p.model_dump(mode='json')==before


def test_real_actor_swap_is_still_rejected():
    p=proposal()
    p.source_screenplay.source_outline.scenes[0].action='Con gái 30 tuổi đặt lòng bàn tay lên đầu tấm gỗ.'
    with pytest.raises(SceneSourceConflict):fixed_beats(p)
