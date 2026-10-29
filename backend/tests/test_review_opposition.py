from types import SimpleNamespace
import pytest
from app.application.review_opposition import literal_opposition


@pytest.mark.parametrize(
    "author,target,speaker,kind,characters,expected",
    [
        (
            "Đèn pin bị hỏng, không thể sáng.",
            "Lan kéo rèm để ánh đèn đường rọi vào.",
            "",
            "action",
            "Lan, Bình",
            False,
        ),
        (
            "Đèn pin bị hỏng, không thể sáng.",
            "Bình đặt đèn pin hỏng xuống, nghiêng giấy về ánh đèn đường.",
            "",
            "action",
            "Lan, Bình",
            False,
        ),
        (
            "Đèn pin bị hỏng, không thể sáng.",
            "Bình bật chiếc đèn pin hỏng; đèn sáng rực.",
            "",
            "action",
            "Lan, Bình",
            True,
        ),
        (
            "Đèn pin bị hỏng, không thể sáng.",
            "Bình đặt đèn pin hỏng xuống; ánh đèn đường sáng rực.",
            "",
            "action",
            "Lan, Bình",
            False,
        ),
        ("Cửa sổ không được mở.", "Mai mở cửa tủ.", "", "action", "Mai", False),
        ("Cửa sổ không được mở.", "Mai mở cửa sổ.", "", "action", "Mai", True),
        ("Mai mở cửa tủ, cửa sổ không được mở.", "Mai mở cửa tủ.", "", "action", "Mai", False),
        ("Cha không mở lá thư.", "Con gái mở lá thư của cha.", "", "action", "Cha, con gái", False),
        ("Cha không mở lá thư.", "Cha mở lá thư.", "", "action", "Cha, con gái", True),
        (
            "Giữ lá thư chưa mở.",
            "Cô mở lá thư và đọc lời xin lỗi.",
            "",
            "action",
            "Cha, con gái",
            True,
        ),
        (
            "Con gái chưa nói đã tha thứ.",
            "Con tha thứ cho cha.",
            "Con gái",
            "dialogue",
            "Cha, con gái",
            True,
        ),
        (
            "Con gái chưa nói đã tha thứ.",
            "Con tha thứ cho cha.",
            "Cha",
            "dialogue",
            "Cha, con gái",
            False,
        ),
        (
            "Con gái chưa nói đã tha thứ.",
            "Con gái nhìn cha, kéo ghế ngồi.",
            "",
            "action",
            "Cha, con gái",
            False,
        ),
        (
            "Con gái tự quyết định việc ra đi.",
            "Con gái nhìn về cửa, chưa bước đi.",
            "",
            "action",
            "Cha, con gái",
            False,
        ),
        (
            "Con gái tự quyết định việc ra đi.",
            "Cha giấu hộ chiếu của con gái để cô không thể ra đi.",
            "",
            "action",
            "Cha, con gái",
            True,
        ),
        ("Mai không chỉ mở cửa.", "Mai mở cửa.", "", "action", "Mai", False),
        ("Mai không cần mở cửa.", "Mai mở cửa.", "", "action", "Mai", False),
        ("Mai không phải không mở cửa.", "Mai mở cửa.", "", "action", "Mai", False),
        ("Mai must not open the door.", "Mai will open the door.", "", "action", "Mai", True),
        ("Mai must not open the door.", "Mai will not open the door.", "", "action", "Mai", False),
        ("An không mở cửa.", "Lan mở cửa.", "", "action", "An, Lan", False),
        ("Áo có màu đỏ.", "Áo có màu xanh.", "", "action", "Mai", False),
    ],
)
def test_precise_literal_opposition_abstains_on_mentions_other_objects_roles_and_unsupported_scope(
    author, target, speaker, kind, characters, expected
):
    assert (
        literal_opposition(author, target, SimpleNamespace(kind=kind, speaker=speaker), characters)
        is expected
    )
