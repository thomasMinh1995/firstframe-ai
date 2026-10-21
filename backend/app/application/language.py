"""Conservative Vietnamese/English hints; the creator can always choose explicitly."""

import re
import unicodedata
from typing import Literal

ResponseLanguage = Literal["auto", "vi", "en"]

VI_WORDS = frozenset(
    ["một", "người", "của", "và", "muốn", "học", "hành", "trình", "hướng", "dẫn", "các", "bạn", "làm", "bài", "tập", "không", "được", "vẫn", "tiếp", "tục", "giúp", "khi", "tôi", "là", "có", "để", "với", "nhưng", "trong", "chưa", "đến", "từ", "sau", "về", "gia", "đình", "mẹ", "cha", "con", "trước", "rời", "câu", "chuyện", "phim", "nhân", "vật", "tên", "chờ", "đợi", "giữ", "kết", "mở", "chỉ", "quay", "hai", "căn", "bếp", "cảm", "giác", "im", "lặng", "thoại", "xin", "lỗi", "gái", "trai", "mình", "cô", "ấy", "ông", "anh", "em", "này", "những", "lựa", "chọn", "quyết", "định", "thấy", "biết", "cuộc", "sống"]
)
EN_WORDS = frozenset(
    ["a", "an", "the", "and", "or", "but", "of", "to", "for", "with", "without", "from", "in", "on", "at", "before", "after", "while", "who", "whose", "that", "this", "these", "those", "is", "are", "was", "were", "be", "has", "have", "her", "his", "their", "he", "she", "they", "we", "you", "i", "it", "my", "our", "not", "wants", "want", "helps", "help", "young", "named", "tutor", "learner", "student", "mother", "father", "daughter", "son", "story", "idea", "film", "short", "quiet", "kitchen", "waits", "waiting", "goodbye", "leaves", "meet", "must", "one", "last", "time", "learning", "exercise"]
)


class LanguageSelectionRequired(ValueError):
    pass


def detect_response_language(text: str) -> str | None:
    # Whole words avoid `con` in `concert`; accents or names alone are not language evidence.
    words = re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", text).casefold())
    vi = [word for word in words if word in VI_WORDS]
    en = [word for word in words if word in EN_WORDS]
    # Sparse shared words (French `film`, `son`) cannot establish a language.
    # Place-name tokens `Việt`, `Nam` are deliberately not Vietnamese hints.
    if len(set(vi)) >= 2 and len(vi) > 2 * len(en) and 3 * len(vi) >= len(words):
        return "Vietnamese"
    if len(set(en)) >= 2 and len(en) > 2 * len(vi) and 3 * len(en) >= len(words):
        return "English"
    return None


def resolve_response_language(text: str, choice: ResponseLanguage = "auto") -> str:
    if choice == "vi":
        return "Vietnamese"
    if choice == "en":
        return "English"
    if choice != "auto":
        raise ValueError("Unsupported response language.")
    detected = detect_response_language(text)
    if detected is None:
        raise LanguageSelectionRequired(
            "Chưa xác định chắc chắn ngôn ngữ. FirstFrame hiện hỗ trợ tiếng Việt và tiếng Anh; "
            "hãy chọn ngôn ngữ đầu ra trước khi tiếp tục. Nội dung đã lưu vẫn được giữ."
        )
    return detected
