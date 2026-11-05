"""Exact source anchors shared by initial and manual review."""

import re
from bisect import bisect_right
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai_provider import MalformedProviderResponseError
from app.core.artifacts import RevisionNote, RevisionTarget

BROWSER_WHITESPACE = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)


class CardReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    card_id: str
    decision_id: str
    related_card_id: str | None
    observation: str = Field(min_length=1)
    comparison: Literal["aligned", "uncertain", "mismatch"]
    suggestion: str


class DecisionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision_id: str
    draft_comparison: Literal["aligned", "mismatch", "uncertain", "not_applicable"]
    card_ids: list[str]
    draft_reason: str = Field(min_length=1)
    suggestion_comparison: Literal["aligned", "mismatch", "uncertain", "not_applicable"]
    suggestion_reason: str = Field(min_length=1)


class GroundedDecisionCheck(DecisionCheck):
    draft_quote: str = Field(description="Exact excerpt from cited card(s) in original source order, not author decisions. Empty only for uncertain/not_applicable.")
    suggestion_comparison: Literal["aligned", "mismatch", "uncertain", "not_applicable"] = Field(
        description="If reviews[0].suggestion is empty, this MUST be not_applicable. Otherwise check that exact suggestion.")


def review_card_ids(context: dict) -> list[str]:
    neighbors = [pair["related_card_id"] for pair in context["neighbor_checks"]]
    return list(dict.fromkeys([*context["focus_card_ids"], *neighbors])) or [
        card["id"] for card in context["cards"]]


def _quote_matches_cards(check: GroundedDecisionCheck, context: dict) -> bool:
    cited = set(check.card_ids)
    if any(check.draft_quote in c["text"] for c in context["cards"] if c["id"] in cited):
        return True
    # Preserve original separators when a quote spans adjacent cited cards.
    for passage in context.get("passages", []):
        spans = card_spans(passage["text"])
        ids = passage["card_ids"]
        if len(spans) != len(ids):
            continue
        start = 0
        while start < len(ids):
            end = start
            while end < len(ids) and ids[end] in cited:
                end += 1
            if end > start and check.draft_quote in passage["text"][spans[start][0]:spans[end - 1][1]]:
                return True
            start = max(end, start + 1)
    return False


def validate_decision_checks(reviews: list[CardReview], checks: list[DecisionCheck], context: dict) -> None:
    expected = {d["id"] for d in context["decisions"]}
    if len(reviews) != 1 or len(checks) != len(expected) or {c.decision_id for c in checks} != expected:
        raise MalformedProviderResponseError("Card review did not check each author decision exactly once.")
    review = reviews[0]
    scope = set(review_card_ids(context)) & {card["id"] for card in context["cards"]}
    for check in checks:
        if (not set(check.card_ids).issubset(scope)
                or check.draft_comparison == "mismatch" and not check.card_ids
                or review.suggestion.strip() and check.suggestion_comparison in {"mismatch", "uncertain"}
                or not review.suggestion.strip() and check.suggestion_comparison != "not_applicable"):
            raise MalformedProviderResponseError("Decision check has invalid evidence or an unsafe suggestion.")
        if isinstance(check, GroundedDecisionCheck):
            if (check.draft_quote and not _quote_matches_cards(check, context)
                    or not check.draft_quote and check.draft_comparison in {"aligned", "mismatch"}):
                raise MalformedProviderResponseError("Decision check does not quote its cited draft evidence.")
    selected = next((c for c in checks if c.decision_id == review.decision_id), None)
    if selected is None or selected.draft_comparison == "not_applicable":
        raise MalformedProviderResponseError("Card review cites an unchecked or unrelated decision.")
    mismatches = {c.decision_id for c in checks if c.draft_comparison == "mismatch"}
    cited_evidence = set(selected.card_ids).intersection((review.card_id, review.related_card_id))
    if mismatches and (review.comparison != "mismatch" or review.decision_id not in mismatches or not cited_evidence):
        raise MalformedProviderResponseError("Card review skipped a decision violation.")
    if review.comparison == "aligned" and (not cited_evidence or selected.draft_comparison != "aligned"
            or any(c.draft_comparison == "uncertain" for c in checks)):
        raise MalformedProviderResponseError("Card review contradicts its decision checks.")


def card_spans(text: str) -> list[tuple[int, int]]:
    # Mirror StoryPlanEditor.splitStorySection so anchors match the visible cards.
    space = f"[{re.escape(BROWSER_WHITESPACE)}]"
    spans = []
    units = [0]
    for char in text:
        units.append(units[-1] + (2 if ord(char) > 0xFFFF else 1))
    start = 0
    boundaries = [m.end() for m in re.finditer(rf'''(?:[.!?…。！？]+[”"'’)\]]*(?={space}|$)|\r?\n+)''', text)]
    for end in [*boundaries, len(text)]:
        while start < end and text[start] in BROWSER_WHITESPACE:
            start += 1
        stop = end
        while stop > start and text[stop - 1] in BROWSER_WHITESPACE:
            stop -= 1
        while units[stop] - units[start] > 200:
            limit = bisect_right(units, units[start] + 200) - 1
            gaps = list(re.finditer(f"{space}+", text[start:limit]))
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
    passages = [{"section": sections[i]["title"], "text": sections[i]["content"],
                 "card_ids": [card["id"] for card in cards if card["id"] == f"section-{i}"
                              or card["id"].startswith(f"section-{i}-part-")]}
                for i in path]
    return {"cards": cards, "decisions": decisions, "neighbor_checks": neighbors,
            "passages": passages,
            "focus_card_ids": [card["id"] for card in cards if card["changed"]]}


def feedback_messages(reviews: list[CardReview], context: dict) -> tuple[list[str], list[str], list[str], list[str]]:
    cards = {card["id"]: card for card in context["cards"]}
    decisions = {decision["id"]: decision for decision in context["decisions"]}
    strengths, weaknesses, suggestions, clarifications = [], [], [], []
    for review in reviews:
        if (review.card_id not in cards or review.decision_id not in decisions
                or review.related_card_id is not None and review.related_card_id not in cards
                or review.related_card_id == review.card_id
                or review.comparison == "aligned" and review.suggestion.strip()
                or review.comparison == "mismatch" and not review.suggestion.strip()):
            raise MalformedProviderResponseError("Card review contains an invalid anchor or missing next step.")
        card, decision = cards[review.card_id], decisions[review.decision_id]
        anchor = f'{card["label"]}: “{card["text"]}”'
        if review.related_card_id:
            related = cards[review.related_card_id]
            anchor += f' ↔ {related["label"]}: “{related["text"]}”'
        message = f'{anchor}\n{decision["label"]}: “{decision["text"]}”\n{review.observation}'
        if review.comparison == "aligned":
            strengths.append(message)
        elif review.comparison == "uncertain":
            clarifications.append(message)
            if review.suggestion.strip():
                suggestions.append(f'{card["label"]} — {review.suggestion}')
        else:
            weaknesses.append(message)
            suggestions.append(f'{card["label"]} — {review.suggestion}')
    focus = set(context["focus_card_ids"])
    if focus and not focus.intersection((reviews[0].card_id, reviews[0].related_card_id)):
        raise MalformedProviderResponseError("Card review did not examine any edited card.")
    neighbors = context.get("neighbor_checks", [])
    if neighbors and not any({"card_id": review.card_id, "related_card_id": review.related_card_id} in neighbors
                            or {"card_id": review.related_card_id, "related_card_id": review.card_id} in neighbors
                            for review in reviews):
        raise MalformedProviderResponseError("Card review skipped continuity with neighboring cards.")
    return strengths, weaknesses, suggestions, clarifications


def revision_notes(reviews: list[CardReview], context: dict, artifact_id: str) -> tuple[RevisionNote, ...]:
    # Validate the entire result before attaching any actionable source metadata.
    feedback_messages(reviews, context)
    cards = {card["id"]: card for card in context["cards"]}
    decisions = {decision["id"]: decision for decision in context["decisions"]}
    return tuple(RevisionNote(
        note_id=f"revision-{i + 1}", artifact_id=artifact_id, comparison=review.comparison,
        observation=review.observation, suggestion=review.suggestion,
        decision_id=review.decision_id, decision_quote=decisions[review.decision_id]["text"],
        decision_question=decisions[review.decision_id].get("question"),
        targets=tuple(RevisionTarget(target_id=key, quote=cards[key]["text"])
                      for key in (review.card_id, review.related_card_id) if key is not None),
    ) for i, review in enumerate(reviews) if review.comparison != "aligned")
