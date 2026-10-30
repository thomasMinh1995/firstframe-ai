import pytest

from app.api.schemas.projects import AuthorContext
from app.application.scene_count import scene_count_bounds


def context(text, **updates):
    return AuthorContext(idea=updates.pop('idea', ''), constraints=[text],
                         clarifications=updates.pop('clarifications', []), pending_questions=[], **updates)


@pytest.mark.parametrize('text,expected', [
    ('Tối đa một cảnh, hai nhân vật.', (1, 1)),
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


@pytest.mark.parametrize('text', ['Đúng 7 cảnh.', 'Tối đa 0 cảnh.', 'Từ 3 đến 2 cảnh.', 'Ít nhất 3 cảnh; tối đa hai cảnh.'])
def test_impossible_bounds_fail_before_generation(text):
    with pytest.raises(ValueError, match='Giới hạn số cảnh'):
        scene_count_bounds(context(text), 6)
