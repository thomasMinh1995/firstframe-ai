"""Offline framing experiment contract; not imported by the application runtime."""

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROMPT_PATH = Path(__file__).with_name("prompts") / "framing_assessment_vi.md"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class ThemeAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: Literal["R1", "R2", "R3"]
    stance: Literal["not_applicable", "critical", "endorsing", "unclear"]
    evidence: list[Evidence] = Field(max_length=3)

    @model_validator(mode="after")
    def require_supported_stance(self) -> "ThemeAssessment":
        if self.stance in {"critical", "endorsing"} and not self.evidence:
            raise ValueError("critical/endorsing requires evidence; use unclear if unsupported")
        return self


class LanguageAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["no_violation", "clear_violation", "uncertain"]
    evidence: list[Evidence] = Field(max_length=3)

    @model_validator(mode="after")
    def require_violation_evidence(self) -> "LanguageAssessment":
        if self.status == "clear_violation" and not self.evidence:
            raise ValueError("clear_violation requires evidence")
        return self


class FramingAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    themes: list[ThemeAssessment] = Field(min_length=3, max_length=3)
    language: LanguageAssessment

    @model_validator(mode="after")
    def require_unique_topics(self) -> "FramingAssessment":
        if {theme.topic_id for theme in self.themes} != {"R1", "R2", "R3"}:
            raise ValueError("Exactly one assessment is required for each of R1, R2 and R3")
        return self


def validate_sources(assessment: FramingAssessment, cards: Mapping[str, str]) -> None:
    """Check exact references, without repairing output or judging its meaning."""
    for item in [*assessment.themes, assessment.language]:
        seen: set[tuple[str, str]] = set()
        for evidence in item.evidence:
            reference = (evidence.card_id, evidence.quote)
            if reference in seen:
                raise ValueError("Duplicate evidence reference")
            seen.add(reference)
            if evidence.card_id not in cards:
                raise ValueError("Evidence references an unknown card")
            if not evidence.quote.strip() or evidence.quote not in cards[evidence.card_id]:
                raise ValueError("Evidence quote is not an exact nonblank source excerpt")
