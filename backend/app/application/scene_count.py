"""Bounds from explicit author scene counts, never from an AI-generated plan."""
import re

from app.api.schemas.projects import AuthorContext

WORDS = {"một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5, "sáu": 6,
         "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
NUMBER = r"(?:\d+|" + "|".join(WORDS) + r")"
UNIT = r"(?:phân\s+cảnh|cảnh|scenes?)\b"
COUNT = re.compile(
    rf"\b(?:(?P<range>{NUMBER})\s*(?:đến|tới|to|[-–—])\s*)?"
    rf"(?P<count>{NUMBER})\s*(?:(?:rất\s+)?ngắn\s+|(?:very\s+)?short\s+)?{UNIT}", re.I)
MAXIMUM = re.compile(r"\b(?:tối đa|không quá|nhiều nhất|không vượt quá|giới hạn(?: ở)?|at most|no more than|up to|limit(?:ed)? to|max(?:imum)?(?: of)?)[\s.:]*(?:là\s+)?$")
MINIMUM = re.compile(r"\b(?:ít nhất|tối thiểu|at least|min(?:imum)?(?: of)?)[\s.:]*(?:là\s+)?$")
EXACT = re.compile(r"\b(?:chỉ(?: có)?|đúng|gồm|tổng cộng|exactly|only|consists of)\s*$")
SCENE_QUESTION = re.compile(
    r"\b(?:(?:bao nhiêu|mấy|số(?:\s+lượng)?)\s+(?:phân\s+)?cảnh|"
    r"(?:how many|number of|maximum(?:\s+number of)?|minimum(?:\s+number of)?)\s+scenes)\b")


class SceneCountConflict(ValueError):
    pass


def scene_count_bounds(context: AuthorContext, ceiling: int = 60) -> tuple[int, int]:
    lower, upper = 1, ceiling
    texts = [context.idea, *context.constraints]
    for choice in context.clarifications:
        answer = choice.answer.strip().casefold()
        # A numeric answer is usable only when the author actually answered a scene-count question.
        if re.fullmatch(NUMBER, answer) and SCENE_QUESTION.search(choice.question.casefold()):
            prefix = "tối đa " if re.search(r"tối đa|nhiều nhất|không quá|maximum|at most", choice.question.casefold()) else (
                "ít nhất " if re.search(r"tối thiểu|ít nhất|minimum|at least", choice.question.casefold()) else "")
            answer = f"{prefix}{answer} cảnh"
        texts.append(answer)

    def number(value):
        try:
            return WORDS[value] if value in WORDS else int(value)
        except ValueError as error:
            raise SceneCountConflict("Số cảnh quá lớn hoặc không hợp lệ; hãy dùng số trong giới hạn hỗ trợ.") from error

    for text in texts:
        text = text.casefold()
        for match in COUNT.finditer(text):
            prefix = text[:match.start()]
            bound = MAXIMUM.search(prefix) or MINIMUM.search(prefix) or EXACT.search(prefix)
            if not bound and re.match(r"\s+(?:đầu|cuối|tiếp theo|trước|sau)\b", text[match.end():]):
                continue
            if bound and re.search(r"(?:không(?: cần| phải| còn)?|not|no longer)\s*$", prefix[:bound.start()]):
                continue
            count = number(match['count'])
            if match['range']:
                lower, upper = max(lower, number(match['range'])), min(upper, count)
            elif MAXIMUM.search(prefix):
                upper = min(upper, count)
            elif MINIMUM.search(prefix):
                lower = max(lower, count)
            elif (EXACT.search(prefix) or not prefix.strip()
                  or prefix.rstrip().endswith((',', ';', ':'))
                  or re.match(r"\s+duy nhất\b", text[match.end():])):
                lower, upper = max(lower, count), min(upper, count)
    if lower > upper:
        raise SceneCountConflict(f"Giới hạn số cảnh của tác giả mâu thuẫn hoặc vượt mức hỗ trợ {ceiling} cảnh; hãy làm rõ trước khi tạo dàn cảnh.")
    return lower, upper
