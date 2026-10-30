import pytest

from app.api.schemas.projects import AuthorContext
from app.application.scene_count import SceneCountConflict, scene_count_bounds


def context(text, **updates):
    return AuthorContext(idea=updates.pop('idea', ''), constraints=[text],
                         clarifications=updates.pop('clarifications', []), pending_questions=[], **updates)


@pytest.mark.parametrize('text,expected', [
    ('Tối đa một cảnh, hai nhân vật.', (1, 1)),
    ('Chỉ một cảnh sau cơn mưa.', (1, 1)),
    ('Tối đa một cảnh trước khi trời tối.', (1, 1)),
    ('Phim 30 giây, tối đa 2 cảnh rất ngắn, 2 nhân vật, một căn bếp.', (1, 2)),
    ('Không quá sáu cảnh.', (1, 6)), ('Chỉ một cảnh.', (1, 1)),
    ('Đúng 2 cảnh.', (2, 2)), ('Từ một đến ba cảnh.', (1, 3)),
    ('2–6 cảnh.', (2, 6)), ('Ít nhất hai cảnh.', (2, 6)),
    ('at most two short scenes', (1, 2)), ('no more than 1 scene', (1, 1)),
    ('exactly six scenes', (6, 6)), ('up to 10 scenes', (1, 6)),
    ('Giới hạn ở 2cảnh.', (1, 2)), ('Tối đa là 2 cảnh.', (1, 2)),
    ('Không cần đúng 2 cảnh.', (1, 6)), ('Không giới hạn 2 cảnh.', (1, 6)),
    ('Only one apartment; two characters.', (1, 6)),
    ('Giữ khoảng lặng trong hai cảnh cuối.', (1, 6)),
    ('Hai cảnh cuối cần giữ khoảng lặng.', (1, 6)),
    ('The climax two scenes before the ending stays quiet.', (1, 6)),
])
def test_explicit_counts_only(text, expected):
    assert scene_count_bounds(context(text), 6) == expected


def test_idea_and_answer_are_author_sources_but_question_is_not():
    assert scene_count_bounds(context('', idea='Chỉ một cảnh trong bếp.'), 6) == (1, 1)
    assert scene_count_bounds(context('', clarifications=[{'question':'Tối đa bao nhiêu cảnh?', 'answer':'hai'}]), 6) == (1, 2)
    assert scene_count_bounds(context('', clarifications=[{'question':'Có nên dùng hai cảnh?', 'answer':'Chưa chọn.'}]), 6) == (1, 6)
    assert scene_count_bounds(context('', clarifications=[{'question':'Bao nhiêu nhân vật?', 'answer':'2'}]), 6) == (1, 6)


@pytest.mark.parametrize('question', [
    'Bao nhiêu nhân vật trong cảnh?', 'Số nhân vật tối đa trong cảnh là bao nhiêu?',
    'How many characters are in the scene?', 'Maximum number of characters per scene?',
])
def test_character_question_cannot_turn_numeric_answer_into_scene_count(question):
    assert scene_count_bounds(context('', clarifications=[{'question':question, 'answer':'2'}]), 6) == (1, 6)


@pytest.mark.parametrize('question,expected', [
    ('Tối đa bao nhiêu cảnh?', (1, 2)), ('Số lượng cảnh tối đa?', (1, 2)),
    ('How many scenes?', (2, 2)), ('Maximum number of scenes?', (1, 2)),
    ('Minimum number of scenes?', (2, 6)),
    ('Số cảnh ít nhất?', (2, 6)),
])
def test_numeric_scene_answers_keep_the_question_count_type(question, expected):
    assert scene_count_bounds(context('', clarifications=[{'question':question, 'answer':'2'}]), 6) == expected


@pytest.mark.parametrize('text', ['Đúng 7 cảnh.', 'Tối đa 0 cảnh.', 'Từ 3 đến 2 cảnh.', 'Ít nhất 3 cảnh; tối đa hai cảnh.'])
def test_impossible_bounds_fail_before_generation(text):
    with pytest.raises(ValueError, match='Giới hạn số cảnh'):
        scene_count_bounds(context(text), 6)


def test_oversized_numeric_idea_is_a_validation_error_not_an_api_crash():
    with pytest.raises(SceneCountConflict, match='Số cảnh'):
        scene_count_bounds(context('', idea='Đúng ' + '9'*4400 + ' cảnh.'), 6)
