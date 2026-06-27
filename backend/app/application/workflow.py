from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.application.example_loader import DomainExample, ExampleLoader
from app.application.knowledge_loader import KnowledgeLoader
from app.application.prompt_loader import PromptLoader
from app.core.artifacts import (
    ArtifactKind,
    ArtifactMetadata,
    Constraint,
    EvaluationArtifact,
    EvaluationFinding,
    IdeaArtifact,
    PlanningArtifact,
    PlanSection,
    ReasoningArtifact,
    ReasoningNote,
    StoryPlanArtifact,
)
from app.core.domains import (
    DomainMetadata,
    DomainPlugin,
    DomainRegistry,
    DomainResource,
    DomainResourceCatalog,
)
from app.core.harness import EvaluationLayer, PlanningLayer, ReasoningLayer
from app.infrastructure.openai_provider import OpenAIProvider, OpenAIStructuredRequest


DEFAULT_DOMAIN_ID = "short-film"
MAX_PLANNING_EXAMPLES = 3
OutputT = TypeVar("OutputT", bound=BaseModel)


class _ReasoningNoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str
    content: str


class _ReasoningOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str
    notes: list[_ReasoningNoteOutput] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class _PlanningOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    story_plan: "_StructuredStoryPlanOutput"


class EvaluationRubricScores(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    story_clarity: int = Field(ge=1, le=5)
    character: int = Field(ge=1, le=5)
    conflict: int = Field(ge=1, le=5)
    emotional_impact: int = Field(ge=1, le=5)
    ending: int = Field(ge=1, le=5)
    production_feasibility: int = Field(ge=1, le=5)


class _EvaluationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    passed: bool
    rubric_scores: EvaluationRubricScores
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]


class WorkingTitle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str


class Logline(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str


class Characters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    protagonist: str
    supporting_characters: list[str]
    antagonist_or_obstacle: str | None


class Conflict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    external: str
    internal: str | None
    stakes: str | None


class Beginning(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    setup: str
    key_event: str | None


class Middle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    escalation: str
    turning_point: str | None


class Ending(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resolution: str
    final_image: str | None


class Theme(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: str


class VisualStyle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str | None
    visual_motifs: list[str]


class Tone(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str


class ProductionNotes(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    notes: str
    locations: list[str]
    cast_size: str | None


class _StructuredStoryPlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    working_title: WorkingTitle
    logline: Logline
    characters: Characters
    conflict: Conflict
    beginning: Beginning
    middle: Middle
    ending: Ending
    theme: Theme
    visual_style: VisualStyle
    tone: Tone
    production_notes: ProductionNotes

_PlanningOutput.model_rebuild()


@dataclass(frozen=True)
class _OpenAIPlanningArtifact(PlanningArtifact):
    title: str | None = None
    logline: str | None = None
    target_response_language: str = "English"


@dataclass(frozen=True)
class StaticDomainPlugin:
    metadata: DomainMetadata
    resources: DomainResourceCatalog = field(default_factory=DomainResourceCatalog)

    @property
    def knowledge(self) -> tuple[DomainResource, ...]:
        return self.resources.knowledge

    @property
    def glossary(self) -> tuple[DomainResource, ...]:
        return self.resources.glossary

    @property
    def prompts(self) -> tuple[DomainResource, ...]:
        return self.resources.prompts

    @property
    def rubrics(self) -> tuple[DomainResource, ...]:
        return self.resources.rubrics

    @property
    def examples(self) -> tuple[DomainResource, ...]:
        return self.resources.examples


@dataclass(frozen=True)
class HarnessRun:
    analysis: ReasoningArtifact
    story_plan: StoryPlanArtifact
    evaluation: EvaluationArtifact


class OpenAIReasoningLayer(ReasoningLayer):
    def __init__(self, provider: OpenAIProvider) -> None:
        self._provider = provider

    def reason(self, idea: IdeaArtifact, domain: DomainPlugin) -> ReasoningArtifact:
        target_language = _target_response_language(idea)
        result = self._provider.request_structured(
            OpenAIStructuredRequest(
                instructions=(
                    "You are the reasoning layer for FirstFrame AI. Analyze a vague "
                    f"{domain.metadata.display_name} idea. Identify what is present, what is "
                    "missing, and mentor questions the creator should answer. Return only the "
                    "requested structured object. Detect the user's input language and return "
                    "all string values in the same language while preserving JSON field names "
                    "in English."
                ),
                input_text=_idea_input(idea),
                response_model=_ReasoningOutput,
            )
        )
        output = _expect_output(result.output, _ReasoningOutput)
        return ReasoningArtifact(
            metadata=_metadata(idea.metadata.domain_id, "reasoning"),
            source_idea_id=idea.metadata.artifact_id,
            notes=(
                ReasoningNote(label="Original idea", content=idea.text),
                ReasoningNote(label="Target response language", content=target_language),
                ReasoningNote(label="Analysis summary", content=output.summary),
                *(
                    ReasoningNote(label=note.label, content=note.content)
                    for note in output.notes
                ),
            ),
            open_questions=tuple(output.missing_information),
        )


class OpenAIPlanningLayer(PlanningLayer):
    def __init__(
        self,
        provider: OpenAIProvider,
        prompt_loader: PromptLoader,
        knowledge_loader: KnowledgeLoader,
        example_loader: ExampleLoader,
    ) -> None:
        self._provider = provider
        self._prompt_loader = prompt_loader
        self._knowledge_loader = knowledge_loader
        self._example_loader = example_loader

    def plan(self, reasoning: ReasoningArtifact, domain: DomainPlugin) -> PlanningArtifact:
        knowledge = {
            "film_glossary": self._knowledge_loader.load("film_glossary", domain),
            "film_rules": self._knowledge_loader.load("film_rules", domain),
            "story_patterns": self._knowledge_loader.load("story_patterns", domain),
        }
        examples = self._example_loader.load(domain, limit=MAX_PLANNING_EXAMPLES)
        result = self._provider.request_structured(
            OpenAIStructuredRequest(
                instructions=self._prompt_loader.load("story_planner", domain),
                input_text=_reasoning_input(reasoning, knowledge, examples),
                response_model=_PlanningOutput,
            )
        )
        output = _expect_output(result.output, _PlanningOutput)
        story_plan = output.story_plan
        return _OpenAIPlanningArtifact(
            metadata=_metadata(reasoning.metadata.domain_id, "planning"),
            source_reasoning_id=reasoning.metadata.artifact_id,
            title=story_plan.working_title.title,
            logline=story_plan.logline.text,
            sections=tuple(_structured_plan_sections(story_plan)),
            target_response_language=_find_note(reasoning, "Target response language"),
        )


class OpenAIEvaluationLayer(EvaluationLayer):
    def __init__(
        self,
        provider: OpenAIProvider,
        prompt_loader: PromptLoader,
        knowledge_loader: KnowledgeLoader,
    ) -> None:
        self._provider = provider
        self._prompt_loader = prompt_loader
        self._knowledge_loader = knowledge_loader

    def evaluate(self, planning: PlanningArtifact, domain: DomainPlugin) -> EvaluationArtifact:
        rubric = self._knowledge_loader.load_rubric("story_rubric", domain)
        target_language = getattr(planning, "target_response_language", "English")
        result = self._provider.request_structured(
            OpenAIStructuredRequest(
                instructions=self._prompt_loader.load("script_critic", domain),
                input_text=_evaluation_input(planning, rubric),
                response_model=_EvaluationOutput,
            )
        )
        output = _expect_output(result.output, _EvaluationOutput)
        return EvaluationArtifact(
            metadata=_metadata(planning.metadata.domain_id, "evaluation"),
            source_planning_id=planning.metadata.artifact_id,
            passed=output.passed,
            findings=tuple(_evaluation_findings(output, target_language)),
        )


class CreativeReasoningHarness:
    def __init__(
        self,
        domains: DomainRegistry,
        reasoning_layer: ReasoningLayer,
        planning_layer: PlanningLayer,
        evaluation_layer: EvaluationLayer,
    ) -> None:
        self.domains = domains
        self._reasoning_layer = reasoning_layer
        self._planning_layer = planning_layer
        self._evaluation_layer = evaluation_layer

    def generate(self, idea: IdeaArtifact) -> HarnessRun:
        domain = self.domains.get(idea.metadata.domain_id)
        reasoning = self._reasoning_layer.reason(idea, domain)
        planning = self._planning_layer.plan(reasoning, domain)
        story_plan = StoryPlanArtifact(
            metadata=_metadata(idea.metadata.domain_id, "story_plan"),
            source_planning_id=planning.metadata.artifact_id,
            title=getattr(planning, "title", None) or "Untitled Short Film",
            logline=getattr(planning, "logline", None) or _make_logline(idea.text),
            sections=planning.sections,
        )
        evaluation = self._evaluation_layer.evaluate(planning, domain)
        return HarnessRun(analysis=reasoning, story_plan=story_plan, evaluation=evaluation)


class StoryGenerationService:
    def __init__(self, harness: CreativeReasoningHarness) -> None:
        self._harness = harness

    def generate(
        self,
        idea_text: str,
        domain_id: str = DEFAULT_DOMAIN_ID,
        constraints: tuple[Constraint, ...] = (),
    ) -> HarnessRun:
        target_response_language = _detect_response_language(idea_text)
        idea = IdeaArtifact(
            metadata=_metadata(domain_id, "idea"),
            text=idea_text,
            constraints=(
                *constraints,
                Constraint(name="target_response_language", value=target_response_language),
            ),
        )
        return self._harness.generate(idea)


def create_story_generation_service(provider: OpenAIProvider | None = None) -> StoryGenerationService:
    openai_provider = provider or OpenAIProvider.from_env()
    prompt_loader = PromptLoader()
    knowledge_loader = KnowledgeLoader()
    example_loader = ExampleLoader()
    registry = DomainRegistry(
        [
            StaticDomainPlugin(
                metadata=DomainMetadata(
                    domain_id=DEFAULT_DOMAIN_ID,
                    display_name="Short Film Story Development",
                    version="0.1.0",
                    description="Demo domain for short film story planning.",
                    tags=("story", "film", "demo"),
                ),
                resources=DomainResourceCatalog(
                    knowledge=(
                        DomainResource(
                            resource_id="short-film-placeholder-knowledge",
                            title="Short Film Knowledge Placeholder",
                            path=Path("domains/short-film/knowledge"),
                            description="Reserved for future short-film knowledge assets.",
                        ),
                    )
                ),
            )
        ]
    )
    harness = CreativeReasoningHarness(
        domains=registry,
        reasoning_layer=OpenAIReasoningLayer(openai_provider),
        planning_layer=OpenAIPlanningLayer(
            openai_provider,
            prompt_loader,
            knowledge_loader,
            example_loader,
        ),
        evaluation_layer=OpenAIEvaluationLayer(openai_provider, prompt_loader, knowledge_loader),
    )
    return StoryGenerationService(harness)


def _metadata(domain_id: str, kind: ArtifactKind) -> ArtifactMetadata:
    return ArtifactMetadata(
        artifact_id=str(uuid4()),
        domain_id=domain_id,
        kind=kind,
        created_at=datetime.now(UTC),
    )


def _target_response_language(idea: IdeaArtifact) -> str:
    for constraint in idea.constraints:
        if constraint.name == "target_response_language":
            return constraint.value
    return _detect_response_language(idea.text)


def _detect_response_language(text: str) -> str:
    normalized = text.lower()
    has_vietnamese_diacritics = any(
        character in normalized
        for character in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    )
    common_vietnamese_words = (
        "một",
        "người",
        "câu chuyện",
        "gia đình",
        "cha",
        "mẹ",
        "con",
        "trước khi",
        "rời",
        "việt nam",
        "muốn",
    )
    if has_vietnamese_diacritics or any(word in normalized for word in common_vietnamese_words):
        return "Vietnamese"
    return "English"


def _is_vietnamese_language(language: str) -> bool:
    return language.strip().lower() in {"vietnamese", "tiếng việt", "tieng viet", "vi"}


def _find_note(reasoning: ReasoningArtifact, label: str) -> str:
    for note in reasoning.notes:
        if note.label == label:
            return note.content
    return "A vague creative idea."


def _make_logline(idea_text: str) -> str:
    return (
        "When an unresolved situation starts closing in, one character must make a visible "
        f"choice that transforms the idea: {idea_text}"
    )


def _idea_input(idea: IdeaArtifact) -> str:
    constraints = "\n".join(f"- {constraint.value}" for constraint in idea.constraints)
    target_language = _target_response_language(idea)
    return (
        f"Idea:\n{idea.text}\n\n"
        f"Domain ID: {idea.metadata.domain_id}\n\n"
        f"Target response language: {target_language}\n"
        "All generated JSON string values must use this language. Preserve JSON field names "
        "in English.\n\n"
        f"Constraints:\n{constraints or '- None provided'}"
    )


def _reasoning_input(
    reasoning: ReasoningArtifact,
    knowledge: dict[str, object],
    examples: tuple[DomainExample, ...],
) -> str:
    notes = "\n".join(f"- {note.label}: {note.content}" for note in reasoning.notes)
    questions = "\n".join(f"- {question}" for question in reasoning.open_questions)
    target_language = _find_note(reasoning, "Target response language")
    return (
        f"Target response language: {target_language}\n"
        "All generated JSON string values must use this language. Preserve JSON field names "
        "in English.\n\n"
        f"Reasoning notes:\n{notes}\n\n"
        f"Missing information / mentor questions:\n{questions or '- None'}\n\n"
        f"Short-film domain knowledge:\n{json.dumps(knowledge, ensure_ascii=False)}\n\n"
        f"Reusable domain examples:\n{json.dumps(_example_payloads(examples), ensure_ascii=False)}"
    )


def _example_payloads(examples: tuple[DomainExample, ...]) -> list[dict[str, object]]:
    return [
        {
            "source_id": example.source_id,
            "theme": example.theme,
            "genre": example.genre,
            "user_idea": example.user_idea,
            "example": example.payload,
        }
        for example in examples
    ]


def _structured_plan_sections(story_plan: _StructuredStoryPlanOutput) -> list[PlanSection]:
    section_specs = [
        (
            "Core idea",
            "State the short film's central promise.",
            story_plan.logline.text,
        ),
        (
            "Main character",
            "Define the protagonist and key character pressure.",
            _characters_text(story_plan.characters),
        ),
        (
            "Main conflict",
            "Describe the obstacle and stakes.",
            _conflict_text(story_plan.conflict),
        ),
        (
            "Beginning",
            "Set up the story world and first dramatic turn.",
            _beginning_text(story_plan.beginning),
        ),
        (
            "Middle",
            "Escalate pressure and reveal the emotional turn.",
            _middle_text(story_plan.middle),
        ),
        (
            "Ending",
            "Resolve the short film through a visible choice or image.",
            _ending_text(story_plan.ending),
        ),
        (
            "Theme",
            "Name the human idea underneath the plot.",
            story_plan.theme.statement,
        ),
        (
            "Visual Style",
            "Capture the visual approach and recurring motifs.",
            _visual_style_text(story_plan.visual_style),
        ),
        (
            "Tone",
            "Describe the intended emotional register.",
            story_plan.tone.description,
        ),
        (
            "Production Notes",
            "Keep the idea grounded for short-film production.",
            _production_notes_text(story_plan.production_notes),
        ),
    ]
    return [
        PlanSection(
            section_id=f"section-{index + 1}",
            title=title,
            purpose=purpose,
            content=content,
        )
        for index, (title, purpose, content) in enumerate(section_specs)
    ]


def _characters_text(characters: Characters) -> str:
    details = [characters.protagonist]
    if characters.supporting_characters:
        details.append(", ".join(characters.supporting_characters))
    if characters.antagonist_or_obstacle:
        details.append(characters.antagonist_or_obstacle)
    return " ".join(details)


def _conflict_text(conflict: Conflict) -> str:
    details = [conflict.external]
    if conflict.internal:
        details.append(conflict.internal)
    if conflict.stakes:
        details.append(conflict.stakes)
    return " ".join(details)


def _beginning_text(beginning: Beginning) -> str:
    if beginning.key_event:
        return f"{beginning.setup} {beginning.key_event}"
    return beginning.setup


def _middle_text(middle: Middle) -> str:
    if middle.turning_point:
        return f"{middle.escalation} {middle.turning_point}"
    return middle.escalation


def _ending_text(ending: Ending) -> str:
    if ending.final_image:
        return f"{ending.resolution} {ending.final_image}"
    return ending.resolution


def _visual_style_text(visual_style: VisualStyle) -> str:
    details: list[str] = []
    if visual_style.description:
        details.append(visual_style.description)
    if visual_style.visual_motifs:
        details.append(", ".join(visual_style.visual_motifs))
    return " ".join(details) or "Use simple, readable visual choices that support the emotion."


def _production_notes_text(production_notes: ProductionNotes) -> str:
    details = [production_notes.notes]
    if production_notes.locations:
        details.append(", ".join(production_notes.locations))
    if production_notes.cast_size:
        details.append(production_notes.cast_size)
    return " ".join(details)


def _planning_input(planning: PlanningArtifact) -> str:
    title = getattr(planning, "title", None) or "Untitled Short Film"
    logline = getattr(planning, "logline", None) or "No logline provided."
    sections = "\n".join(
        f"- {section.title}: {section.purpose}\n  {section.content}"
        for section in planning.sections
    )
    return f"Title: {title}\nLogline: {logline}\n\nSections:\n{sections}"


def _evaluation_input(planning: PlanningArtifact, rubric: object) -> str:
    target_language = getattr(planning, "target_response_language", "English")
    return (
        f"Target response language: {target_language}\n"
        "All generated JSON string values must use this language. Preserve JSON field names "
        "in English.\n\n"
        f"{_planning_input(planning)}\n\n"
        f"Short-film story rubric:\n{json.dumps(rubric, ensure_ascii=False)}"
    )


def _evaluation_findings(
    output: _EvaluationOutput,
    target_language: str = "English",
) -> list[EvaluationFinding]:
    findings: list[EvaluationFinding] = []
    for criterion_id, score in output.rubric_scores.model_dump().items():
        findings.append(
            EvaluationFinding(
                criterion_id=criterion_id,
                message=_score_message(criterion_id, score, target_language),
                severity="info",
                score=score,
            )
        )
    for index, strength in enumerate(output.strengths, start=1):
        findings.append(
            EvaluationFinding(
                criterion_id=f"strength-{index}",
                message=strength,
                severity="info",
            )
        )
    for index, weakness in enumerate(output.weaknesses, start=1):
        findings.append(
            EvaluationFinding(
                criterion_id=f"weakness-{index}",
                message=weakness,
                severity="warning",
            )
        )
    for index, suggestion in enumerate(output.suggestions, start=1):
        findings.append(
            EvaluationFinding(
                criterion_id=f"suggestion-{index}",
                message=suggestion,
                severity="info",
            )
        )
    return findings


def _score_message(criterion_id: str, score: int, target_language: str) -> str:
    if _is_vietnamese_language(target_language):
        labels = {
            "story_clarity": "Độ rõ của câu chuyện",
            "character": "Nhân vật",
            "conflict": "Xung đột",
            "emotional_impact": "Tác động cảm xúc",
            "ending": "Kết thúc",
            "production_feasibility": "Tính khả thi sản xuất",
        }
        return f"{labels.get(criterion_id, criterion_id.replace('_', ' '))}: {score}/5."
    return f"{criterion_id.replace('_', ' ').title()} score: {score}/5."


def _expect_output(output: BaseModel, expected_type: type[OutputT]) -> OutputT:
    if not isinstance(output, expected_type):
        raise TypeError("Provider returned an unexpected structured response type.")
    return output
