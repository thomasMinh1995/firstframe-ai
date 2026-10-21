"""Evidence gates for author intent; literal checks do not certify AI judgments."""

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai_provider import StructuredProvider, StructuredRequest


class EvidenceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_index: int = Field(ge=-2)
    draft_quote: str = Field(min_length=1, max_length=10000)
    author_quote: str = Field(min_length=1, max_length=10000)
    explanation: str
    suggestion: str


class FidelityScan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["clear", "issues", "uncertain"]
    issues: list[EvidenceIssue] = Field(max_length=3)


class SpanIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_span_id: str
    author_span_id: str
    explanation: str
    suggestion: str


class SpanScan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["clear", "issues", "uncertain"]
    issues: list[SpanIssue] = Field(max_length=3)


class FidelityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    relation: Literal["contradictory", "compatible", "uncertain"]
    relation_reason: str = Field(min_length=1)
    concern: Literal["supported", "unsupported", "uncertain"]
    concern_reason: str = Field(min_length=1)
    revision: Literal["aligned", "violates", "uncertain"]
    revision_reason: str = Field(min_length=1)


class SuggestionAudit(FidelityAssessment):
    draft_span_id: str
    author_span_id: str


class FidelityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["fidelity", "craft"] = "fidelity"
    section_index: int
    section_title: str
    section_text: str
    draft_quote: str
    author_quote: str
    explanation: str
    suggestion: str | None
    suggestion_status: Literal["supported", "unverified"]
    verification_note: str | None = None
    assessment: FidelityAssessment | None = None


class FidelityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["clear", "issues", "unverified"]
    checks: list[FidelityCheck]
    withheld_count: int = 0


def author_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            text
            for key, child in value.items()
            if key != "question"
            for text in author_values(child)
        ]
    if isinstance(value, list):
        return [text for child in value for text in author_values(child)]
    return []


def cited_check(issue: EvidenceIssue, draft: dict, author: dict) -> FidelityCheck | None:
    sections = [
        {"title": "Title", "content": draft.get("title") or ""},
        {"title": "Logline", "content": draft.get("logline") or ""},
        *draft["sections"],
    ]
    index = issue.section_index + 2
    if index < 0 or index >= len(sections):
        return None
    section = sections[index]
    # Ambiguous or invented quotes must never become a precise-looking highlight.
    start = section["content"].find(issue.draft_quote)
    if (
        not issue.draft_quote.strip()
        or start < 0
        or section["content"].find(issue.draft_quote, start + 1) >= 0
    ):
        return None
    if not issue.author_quote.strip() or not any(
        issue.author_quote in value for value in author_values(author)
    ):
        return None
    return FidelityCheck(
        section_index=issue.section_index,
        section_title=section["title"],
        section_text=section["content"],
        draft_quote=issue.draft_quote,
        author_quote=issue.author_quote,
        explanation=issue.explanation,
        suggestion=None,
        suggestion_status="unverified",
    )


def fidelity_request(
    provider: StructuredProvider, prompt: str, payload: dict, model: type[BaseModel], stage: str
):
    return provider.request_structured(
        StructuredRequest(
            instructions=prompt,
            input_text=json.dumps(payload, ensure_ascii=False),
            response_model=model,
            stage=stage,
        )
    ).output


def evidence_spans(draft: dict, author: dict) -> tuple[dict, dict]:
    def pieces(text):
        return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]

    author_spans = {
        f"a{i}": text
        for i, text in enumerate(part for value in author_values(author) for part in pieces(value))
    }
    sections = [
        {"title": "Title", "content": draft.get("title") or ""},
        {"title": "Logline", "content": draft.get("logline") or ""},
        *draft["sections"],
    ]
    draft_spans = {}
    for index, section in enumerate(sections):
        for part in pieces(section["content"]):
            draft_spans[f"d{len(draft_spans)}"] = {
                "section_index": index - 2,
                "section_title": section["title"],
                "text": part,
            }
    return author_spans, draft_spans


def resolve_span(issue: SpanIssue, authors: dict, drafts: dict) -> EvidenceIssue | None:
    if issue.author_span_id not in authors or issue.draft_span_id not in drafts:
        return None
    span = drafts[issue.draft_span_id]
    return EvidenceIssue(
        section_index=span["section_index"],
        draft_quote=span["text"],
        author_quote=authors[issue.author_span_id],
        explanation=issue.explanation,
        suggestion=issue.suggestion,
    )


def scan_fidelity(
    provider: StructuredProvider, prompt: str, draft: dict, author: dict, language: str
) -> tuple[FidelityScan, list[FidelityCheck]]:
    authors, drafts = evidence_spans(draft, author)
    raw = SpanScan.model_validate(
        fidelity_request(
            provider,
            prompt,
            {
                "response_language": language,
                "author_context": author,
                "author_spans": authors,
                "draft_spans": drafts,
            },
            SpanScan,
            "fidelity",
        )
    )
    issues = [resolve_span(issue, authors, drafts) for issue in raw.issues]
    valid = [issue for issue in issues if issue is not None]
    checks = [cited_check(issue, draft, author) for issue in valid]
    status = raw.status
    if (
        (status == "issues") != bool(raw.issues)
        or len(valid) != len(issues)
        or any(check is None for check in checks)
    ):
        status = "uncertain"
    return FidelityScan(status=status, issues=valid), [c for c in checks if c is not None]


def audit_suggestions(
    provider: StructuredProvider,
    prompt: str,
    draft: dict,
    author: dict,
    language: str,
    candidates: list[dict],
    checks: list[FidelityCheck],
) -> FidelityReport:
    authors, drafts = evidence_spans(draft, author)
    approved = []
    for candidate in candidates:
        item = SuggestionAudit.model_validate(
            fidelity_request(
                provider,
                prompt,
                {
                    "response_language": language,
                    "author_context": author,
                    "author_spans": authors,
                    "draft_spans": drafts,
                    "candidate": candidate,
                    "kind": "fidelity" if "section_index" in candidate else "craft",
                },
                SuggestionAudit,
                "fidelity_audit",
            )
        )
        evidence = resolve_span(
            SpanIssue(
                draft_span_id=item.draft_span_id,
                author_span_id=item.author_span_id,
                explanation=candidate["explanation"],
                suggestion=candidate["suggestion"],
            ),
            authors,
            drafts,
        )
        check = cited_check(evidence, draft, author) if evidence is not None else None
        original = next((c.model_copy(deep=True) for c in checks if (
            c.section_index == candidate.get("section_index")
            and c.draft_quote == candidate.get("draft_quote")
            and c.author_quote == candidate.get("author_quote")
        )), None)
        same_evidence = "section_index" not in candidate or (check is not None and (
            check.section_index == candidate["section_index"]
            and check.draft_quote == candidate["draft_quote"]
            and check.author_quote == candidate["author_quote"]
        ))
        is_fidelity = "section_index" in candidate
        rejected_concern = item.concern == "unsupported" or (
            is_fidelity and item.relation == "compatible"
        )
        supported = (
            item.concern == "supported"
            and item.revision == "aligned"
            and (item.relation == "contradictory" if is_fidelity
                 else item.relation != "uncertain")
        )
        assessment = FidelityAssessment.model_validate(
            item.model_dump(exclude={"draft_span_id", "author_span_id"})
        )
        if not supported or check is None or not same_evidence:
            # A bad repair must not erase a valid concern; an unsupported concern is withheld.
            observation = original or (check if item.concern == "supported" else None)
            if observation is not None and not rejected_concern:
                if check is not None and same_evidence:
                    observation.assessment = assessment
                approved.append(observation)
            continue
        check.explanation = candidate["explanation"]
        check.suggestion = candidate["suggestion"]
        check.suggestion_status = "supported"
        check.assessment = assessment
        approved.append(check)
    withheld = len(candidates) - sum(c.suggestion_status == "supported" for c in approved)
    return FidelityReport(
        status="unverified" if withheld else "issues", checks=approved, withheld_count=withheld
    )
