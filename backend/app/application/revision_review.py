"""Card anchors for manual review; project and feedback wire formats stay unchanged."""

import re
from bisect import bisect_right
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai_provider import MalformedProviderResponseError


class CardReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    card_id: str
    decision_id: str
    related_card_id: str | None
    observation: str = Field(min_length=1)
    comparison: Literal["aligned", "uncertain", "mismatch"]
    suggestion: str


def card_spans(text: str) -> list[tuple[int, int]]:
    # Mirror StoryPlanEditor.splitStorySection so anchors match the visible cards.
    spans = []
    units = [0]
    for char in text:
        units.append(units[-1] + (2 if ord(char) > 0xFFFF else 1))
    start = 0
    boundaries = [m.end() for m in re.finditer(r'''(?:[.!?…。！？]+[”"'’)\]]*(?=\s|$)|\r?\n+)''', text)]
    for end in [*boundaries, len(text)]:
        while start < end and text[start].isspace():
            start += 1
        stop = end
        while stop > start and text[stop - 1].isspace():
            stop -= 1
        while units[stop] - units[start] > 200:
            limit = bisect_right(units, units[start] + 200) - 1
            gaps = list(re.finditer(r"\s+", text[start:limit]))
            if not gaps or units[start + gaps[-1].start()] - units[start] < 40:
                break
            gap = gaps[-1]
            spans.append((start, start + gap.start()))
            start += gap.end()
        if start < stop:
            spans.append((start, stop))
        start = end
    return spans or [(0, len(text))]


def review_context(draft: dict, previous: dict | None, author: dict, vietnamese: bool) -> dict:
    sections = draft["sections"]
    narrative = [i for i, s in enumerate(sections) if s["title"] in {"Beginning", "Middle", "Ending"}]
    path = narrative or list(range(len(sections)))
    labels = {"Beginning": "Mở đầu", "Middle": "Phần giữa", "Ending": "Kết thúc"} if vietnamese else {}
    cards = []
    for i in [*path, *(j for j in range(len(sections)) if j not in path)]:
        section = sections[i]
        text = section["content"]
        spans = card_spans(text) if i in path else [(0, len(text))]
        old = None
        if previous and i < len(previous["sections"]) and previous["sections"][i]["title"] == section["title"]:
            old = previous["sections"][i]["content"]
        edits = [] if old is None else [(b1, b2) for tag, _, _, b1, b2
            in SequenceMatcher(None, old, text, autojunk=False).get_opcodes() if tag != "equal"]
        deletions = {min(range(len(spans)), key=lambda p: min(abs(spans[p][0] - b1), abs(spans[p][1] - b1)))
                     for b1, b2 in edits if b1 == b2}
        for part, (start, end) in enumerate(spans):
            label = labels.get(section["title"], section["title"])
            if len(spans) > 1:
                label += f" · {part + 1}"
            if i in path:
                label = f"Card {len(cards) + 1} · {label}"
            cards.append({
                "id": f"section-{i}" + (f"-part-{part}" if part else ""),
                "label": label, "section": section["title"], "text": text[start:end],
                "changed": previous is not None and (old is None or part in deletions or any(
                    start < b2 and end > b1
                    for b1, b2 in edits)),
            })
    for key in ("title", "logline"):
        cards.append({"id": f"draft-{key}", "label": key, "section": key, "text": draft[key],
                      "changed": previous is not None and previous[key] != draft[key]})
    decisions = [{"id": "idea", "label": "Ý tưởng" if vietnamese else "Idea", "text": author["idea"]}]
    decisions += [{"id": f"constraint-{i}", "label": f"Giới hạn {i + 1}" if vietnamese else f"Constraint {i + 1}",
                   "text": text} for i, text in enumerate(author["constraints"])]
    for i, item in enumerate(author["clarifications"]):
        index = item.get("input_index", i)
        label = (f"Làm rõ {index + 1}" if vietnamese else f"Clarification {index + 1}") if index is not None else (
            "Lựa chọn đã lưu" if vietnamese else "Saved decision")
        decisions.append({"id": f"answer-{i}", "label": label, "question": item["question"], "text": item["answer"]})
    path_cards = [card for card in cards if card["label"].startswith("Card ")]
    neighbors = [{"card_id": card["id"], "related_card_id": path_cards[j]["id"]}
                 for i, card in enumerate(path_cards) if card["changed"]
                 for j in (i - 1, i + 1) if 0 <= j < len(path_cards)]
    return {"cards": cards, "decisions": decisions, "neighbor_checks": neighbors,
            "focus_card_ids": [card["id"] for card in cards if card["changed"]]}


def feedback_messages(reviews: list[CardReview], context: dict) -> tuple[list[str], list[str], list[str]]:
    cards = {card["id"]: card for card in context["cards"]}
    decisions = {decision["id"]: decision for decision in context["decisions"]}
    strengths, weaknesses, suggestions = [], [], []
    for review in reviews:
        if (review.card_id not in cards or review.decision_id not in decisions
                or review.related_card_id is not None and review.related_card_id not in cards
                or review.related_card_id == review.card_id
                or review.comparison == "aligned" and review.suggestion.strip()
                or review.comparison != "aligned" and not review.suggestion.strip()):
            raise MalformedProviderResponseError("Card review contains an invalid anchor or missing next step.")
        card, decision = cards[review.card_id], decisions[review.decision_id]
        anchor = f'{card["label"]}: “{card["text"]}”'
        if review.related_card_id:
            related = cards[review.related_card_id]
            anchor += f' ↔ {related["label"]}: “{related["text"]}”'
        message = f'{anchor}\n{decision["label"]}: “{decision["text"]}”\n{review.observation}'
        if review.comparison == "aligned":
            strengths.append(message)
        else:
            weaknesses.append(message)
            suggestions.append(f'{card["label"]} — {review.suggestion}')
    focus = set(context["focus_card_ids"])
    if focus and not focus.intersection((reviews[0].card_id, reviews[0].related_card_id)):
        raise MalformedProviderResponseError("Card review did not examine any edited card.")
    if any(key.startswith("answer-") for key in decisions) and not any(
            review.decision_id.startswith("answer-") for review in reviews):
        raise MalformedProviderResponseError("Card review did not compare any clarification answer.")
    neighbors = context.get("neighbor_checks", [])
    if neighbors and not any({"card_id": review.card_id, "related_card_id": review.related_card_id} in neighbors
                            or {"card_id": review.related_card_id, "related_card_id": review.card_id} in neighbors
                            for review in reviews):
        raise MalformedProviderResponseError("Card review skipped continuity with neighboring cards.")
    return strengths, weaknesses, suggestions
